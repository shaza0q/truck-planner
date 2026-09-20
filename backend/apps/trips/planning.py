"""
TripPlanningService: Geographically-aware HOS stop scheduling and route integration.
Orchestrates RoutePlan, RouteCursor, HOSState, and constraint-driven stop placement.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

from apps.hos.constants import (
    MAX_DRIVING_MINUTES,
    MAX_DUTY_WINDOW_MINUTES,
    REQUIRED_OFF_DUTY_MINUTES,
    BREAK_THRESHOLD_DRIVING_MINUTES,
    REQUIRED_BREAK_MINUTES,
    MAX_CYCLE_HOURS,
    MAX_CYCLE_MINUTES,
    FUEL_INTERVAL_MILES,
    PICKUP_DURATION_MINUTES,
    DROPOFF_DURATION_MINUTES,
    FUEL_DURATION_MINUTES,
)
from apps.hos.enums import DutyStatus, StopType
from apps.hos.exceptions import (
    InvalidTripInputError,
    InsufficientCycleHoursError,
    ImpossibleRouteError,
)
from apps.hos.models import (
    DutySegment,
    Stop,
    DailyLog,
    DailySchedule,
    HOSState,
    ValidationResult,
    TripPlan,
)
from apps.hos.rules import calculate_available_driving_minutes, apply_segment_to_state
from apps.hos.daily_logs import split_segments_by_calendar_day, build_daily_schedules
from apps.hos.validators import HOSValidator
from apps.routing.constants import METERS_TO_MILES
from apps.routing.models import Coordinate, RoutePlan, RouteLeg
from .cursor import RouteCursor


@dataclass
class TripScheduleSummary:
    """Comprehensive summary comparing route driving time vs total trip elapsed time."""
    total_distance_miles: float
    total_driving_minutes: int
    total_driving_hours: float
    total_elapsed_minutes: int
    total_elapsed_hours: float
    total_on_duty_hours: float
    total_off_duty_hours: float
    total_sleeper_hours: float
    starting_cycle_used: float
    final_cycle_used: float
    cycle_hours_remaining: float
    cycle_hours_added: float
    days_count: int
    is_valid: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "totalDistanceMiles": round(self.total_distance_miles, 2),
            "totalDrivingMinutes": self.total_driving_minutes,
            "totalDrivingHours": round(self.total_driving_hours, 2),
            "totalElapsedMinutes": self.total_elapsed_minutes,
            "totalElapsedHours": round(self.total_elapsed_hours, 2),
            "totalOnDutyHours": round(self.total_on_duty_hours, 2),
            "totalOffDutyHours": round(self.total_off_duty_hours, 2),
            "totalSleeperHours": round(self.total_sleeper_hours, 2),
            "startingCycleUsed": round(self.starting_cycle_used, 2),
            "finalCycleUsed": round(self.final_cycle_used, 2),
            "cycleHoursRemaining": round(self.cycle_hours_remaining, 2),
            "cycleHoursAdded": round(self.cycle_hours_added, 2),
            "daysCount": self.days_count,
            "isValid": self.is_valid,
        }


@dataclass
class TripSchedule:
    """Geographically-aware trip schedule integrating road route and HOS compliance."""
    route: RoutePlan
    segments: List[DutySegment]
    stops: List[Stop]
    daily_schedules: List[DailySchedule]
    daily_logs: List[DailyLog]
    summary: TripScheduleSummary
    validation_result: Optional[ValidationResult] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "route": self.route.to_dict(),
            "summary": self.summary.to_dict(),
            "segments": [s.to_dict() for s in self.segments],
            "stops": [st.to_dict() for st in self.stops],
            "dailyLogs": [dl.to_dict() for dl in self.daily_logs],
            "dailySchedules": [ds.to_dict() for ds in self.daily_schedules],
            "validationResult": self.validation_result.to_dict() if self.validation_result else None,
        }


class TripPlanningService:
    """
    Core Phase 3 service.
    Translates a real road RoutePlan into a legally-compliant, geographically-positioned TripSchedule.
    """

    def __init__(self, fuel_interval_miles: float = FUEL_INTERVAL_MILES):
        self.fuel_interval_miles = fuel_interval_miles
        self.validator = HOSValidator()

    def plan(
        self,
        route: RoutePlan,
        cycle_hours_used: float,
        start_time: Optional[datetime] = None,
    ) -> TripSchedule:
        """
        Plans a complete HOS-compliant trip schedule with geographic stops along the route.
        """
        # 1. Input validations
        logger.info(
            "[TripPlanningService.plan] Planning trip: Total Route Distance=%.2f mi, Total Duration=%.1f min, Starting Cycle Used=%.2fh",
            route.total_distance_miles, route.total_duration_minutes, cycle_hours_used
        )
        if cycle_hours_used < 0.0 or cycle_hours_used > 70.0:
            logger.warning("[TripPlanningService.plan] Invalid cycle hours provided: %.2f", cycle_hours_used)
            raise InvalidTripInputError(
                "Current cycle used must be between 0.0 and 70.0 hours.",
                code="INVALID_CYCLE_HOURS"
            )

        if cycle_hours_used >= 70.0:
            logger.warning("[TripPlanningService.plan] Cycle hours exhausted (%.2f >= 70.0)", cycle_hours_used)
            raise InsufficientCycleHoursError(
                "Driver has 70.0 cycle hours used. No on-duty work can be scheduled.",
                code="INSUFFICIENT_CYCLE_HOURS"
            )

        if route.total_distance_meters < 0 or route.total_duration_seconds < 0:
            logger.warning("[TripPlanningService.plan] Negative route distance or duration")
            raise InvalidTripInputError(
                "Route distance and duration must be non-negative.",
                code="INVALID_ROUTE_PARAMS"
            )

        if route.total_distance_meters > 0 and route.total_duration_seconds == 0:
            logger.warning("[TripPlanningService.plan] Impossible route (distance > 0, duration = 0)")
            raise ImpossibleRouteError(
                "Route has positive distance but zero driving time.",
                code="IMPOSSIBLE_ROUTE"
            )

        # Default start time: 06:00 UTC today
        if start_time is None:
            now = datetime.now(timezone.utc)
            start_time = datetime(now.year, now.month, now.day, 6, 0, 0, tzinfo=timezone.utc)

        logger.debug("[TripPlanningService.plan] Initializing RouteCursor and HOSState at start_time=%s", start_time.isoformat())
        cursor = RouteCursor(route)
        state = HOSState(
            cycle_hours_used=cycle_hours_used,
            current_time=start_time,
            current_miles=0.0,
        )

        segments: List[DutySegment] = []
        stops: List[Stop] = []
        cumulative_meters = 0.0

        # Extract route legs
        leg1 = next((l for l in route.legs if l.type == "CURRENT_TO_PICKUP"), route.legs[0] if route.legs else None)
        leg2 = next((l for l in route.legs if l.type == "PICKUP_TO_DROPOFF"), route.legs[1] if len(route.legs) > 1 else None)

        # =====================================================================
        # PHASE 1: LEG 1 DRIVING (Current -> Pickup)
        # =====================================================================
        if leg1 and leg1.duration_minutes > 0:
            rem_leg1_mins = round(leg1.duration_minutes)
            leg1_speed = leg1.distance_miles / (leg1.duration_minutes / 60.0) if leg1.duration_minutes > 0 else 55.0
            leg1_target_m = leg1.distance_meters

            while rem_leg1_mins > 0:
                avail_drive_mins = calculate_available_driving_minutes(
                    state=state,
                    remaining_trip_minutes=rem_leg1_mins,
                    speed_mph=leg1_speed,
                    fuel_interval_miles=self.fuel_interval_miles,
                )

                if avail_drive_mins <= 0:
                    # Determine binding constraint & insert geographic stop
                    stop_coord = cursor.position_at_distance(cumulative_meters)
                    cycle_left_mins = round((70.0 - state.cycle_hours_used) * 60)
                    if cycle_left_mins <= 0:
                        break

                    used_drive_mins = round(state.driving_hours_since_reset * 60)
                    window_left_mins = MAX_DUTY_WINDOW_MINUTES - round(state.window_elapsed_hours * 60)

                    # 10-hour Rest required
                    if used_drive_mins >= MAX_DRIVING_MINUTES or window_left_mins <= 0:
                        rest_start = state.current_time
                        rest_end = rest_start + timedelta(minutes=REQUIRED_OFF_DUTY_MINUTES)
                        rest_loc = f"Rest Area ({round(state.current_miles)} mi)"

                        rest_seg = DutySegment(
                            status=DutyStatus.SLEEPER_BERTH,
                            start=rest_start,
                            end=rest_end,
                            duration_minutes=REQUIRED_OFF_DUTY_MINUTES,
                            location=rest_loc,
                            miles=0.0,
                            reason="Mandatory 10-hour Daily Reset",
                            coordinate=stop_coord,
                            leg="CURRENT_TO_PICKUP",
                        )
                        segments.append(rest_seg)
                        apply_segment_to_state(state, rest_seg)

                        stops.append(Stop(
                            type=StopType.REST,
                            start=rest_start,
                            end=rest_end,
                            duration_minutes=REQUIRED_OFF_DUTY_MINUTES,
                            reason="10-hour Daily Reset",
                            location=rest_loc,
                            miles_from_start=round(state.current_miles, 2),
                            coordinate=stop_coord,
                        ))
                        continue

                    # 30-minute Break required (after 8 cumulative driving hours)
                    used_break_drive = round(state.driving_hours_since_break * 60)
                    if used_break_drive >= BREAK_THRESHOLD_DRIVING_MINUTES:
                        # Check if fuel stop also coincides
                        miles_to_fuel = max(0.0, self.fuel_interval_miles - state.miles_since_fuel)
                        if miles_to_fuel <= 30.0:  # Coinciding fuel stop
                            fuel_start = state.current_time
                            fuel_end = fuel_start + timedelta(minutes=FUEL_DURATION_MINUTES)
                            fuel_loc = f"Fuel Station ({round(state.current_miles)} mi)"

                            fuel_seg = DutySegment(
                                status=DutyStatus.ON_DUTY_NOT_DRIVING,
                                start=fuel_start,
                                end=fuel_end,
                                duration_minutes=FUEL_DURATION_MINUTES,
                                location=fuel_loc,
                                miles=0.0,
                                reason="Fuel Stop & 30-min Break",
                                coordinate=stop_coord,
                                leg="CURRENT_TO_PICKUP",
                            )
                            segments.append(fuel_seg)
                            apply_segment_to_state(state, fuel_seg)

                            stops.append(Stop(
                                type=StopType.FUEL,
                                start=fuel_start,
                                end=fuel_end,
                                duration_minutes=FUEL_DURATION_MINUTES,
                                reason="Fuel Stop & 30-min Break",
                                location=fuel_loc,
                                miles_from_start=round(state.current_miles, 2),
                                coordinate=stop_coord,
                            ))
                            continue
                        else:
                            break_start = state.current_time
                            break_end = break_start + timedelta(minutes=REQUIRED_BREAK_MINUTES)
                            break_loc = f"En route ({round(state.current_miles)} mi)"

                            break_seg = DutySegment(
                                status=DutyStatus.OFF_DUTY,
                                start=break_start,
                                end=break_end,
                                duration_minutes=REQUIRED_BREAK_MINUTES,
                                location=break_loc,
                                miles=0.0,
                                reason="Required 30-minute Driving Break",
                                coordinate=stop_coord,
                                leg="CURRENT_TO_PICKUP",
                            )
                            segments.append(break_seg)
                            apply_segment_to_state(state, break_seg)

                            stops.append(Stop(
                                type=StopType.BREAK,
                                start=break_start,
                                end=break_end,
                                duration_minutes=REQUIRED_BREAK_MINUTES,
                                reason="30-minute Driving Break",
                                location=break_loc,
                                miles_from_start=round(state.current_miles, 2),
                                coordinate=stop_coord,
                            ))
                            continue

                    # Fuel Stop required
                    miles_to_fuel = max(0.0, self.fuel_interval_miles - state.miles_since_fuel)
                    time_to_fuel = int((miles_to_fuel / leg1_speed) * 60) if leg1_speed > 0 else 999999
                    if time_to_fuel <= 0 or state.miles_since_fuel >= (self.fuel_interval_miles - 1.0):
                        if cycle_left_mins < FUEL_DURATION_MINUTES:
                            break

                        fuel_start = state.current_time
                        fuel_end = fuel_start + timedelta(minutes=FUEL_DURATION_MINUTES)
                        fuel_loc = f"Fuel Station ({round(state.current_miles)} mi)"

                        fuel_seg = DutySegment(
                            status=DutyStatus.ON_DUTY_NOT_DRIVING,
                            start=fuel_start,
                            end=fuel_end,
                            duration_minutes=FUEL_DURATION_MINUTES,
                            location=fuel_loc,
                            miles=0.0,
                            reason="Fuel Stop (1,000-mile interval)",
                            coordinate=stop_coord,
                            leg="CURRENT_TO_PICKUP",
                        )
                        segments.append(fuel_seg)
                        apply_segment_to_state(state, fuel_seg)

                        stops.append(Stop(
                            type=StopType.FUEL,
                            start=fuel_start,
                            end=fuel_end,
                            duration_minutes=FUEL_DURATION_MINUTES,
                            reason="Fuel Stop",
                            location=fuel_loc,
                            miles_from_start=round(state.current_miles, 2),
                            coordinate=stop_coord,
                        ))
                        continue

                    break

                # Drive chunk in Leg 1
                drive_start = state.current_time
                drive_end = drive_start + timedelta(minutes=avail_drive_mins)
                
                if rem_leg1_mins - avail_drive_mins == 0:
                    chunk_miles = max(0.0, leg1.distance_miles - state.current_miles)
                    chunk_m = max(0.0, leg1_target_m - cumulative_meters)
                else:
                    chunk_miles = round((avail_drive_mins / 60.0) * leg1_speed, 2)
                    chunk_m = chunk_miles / METERS_TO_MILES

                start_coord = cursor.position_at_distance(cumulative_meters)
                cumulative_meters += chunk_m

                drive_seg = DutySegment(
                    status=DutyStatus.DRIVING,
                    start=drive_start,
                    end=drive_end,
                    duration_minutes=avail_drive_mins,
                    location=f"En route to {route.pickup.display_name or route.pickup.query}",
                    miles=chunk_miles,
                    reason="Driving to Pickup",
                    coordinate=start_coord,
                    leg="CURRENT_TO_PICKUP",
                )
                segments.append(drive_seg)
                apply_segment_to_state(state, drive_seg)
                rem_leg1_mins -= avail_drive_mins

        # =====================================================================
        # CARGO PICKUP (at route.pickup.coordinate)
        # =====================================================================
        cycle_left_mins = round((70.0 - state.cycle_hours_used) * 60)
        if cycle_left_mins < PICKUP_DURATION_MINUTES:
            raise InsufficientCycleHoursError(
                "Driver does not have enough remaining cycle hours to complete pickup.",
                code="INSUFFICIENT_CYCLE_HOURS"
            )

        pickup_coord = route.pickup.coordinate
        pickup_start = state.current_time
        pickup_end = pickup_start + timedelta(minutes=PICKUP_DURATION_MINUTES)
        pickup_loc = route.pickup.display_name or route.pickup.query

        pickup_seg = DutySegment(
            status=DutyStatus.ON_DUTY_NOT_DRIVING,
            start=pickup_start,
            end=pickup_end,
            duration_minutes=PICKUP_DURATION_MINUTES,
            location=pickup_loc,
            miles=0.0,
            reason="Cargo Pickup",
            coordinate=pickup_coord,
            leg="CURRENT_TO_PICKUP",
        )
        segments.append(pickup_seg)
        apply_segment_to_state(state, pickup_seg)

        stops.append(Stop(
            type=StopType.PICKUP,
            start=pickup_start,
            end=pickup_end,
            duration_minutes=PICKUP_DURATION_MINUTES,
            reason="Cargo Pickup",
            location=pickup_loc,
            miles_from_start=round(state.current_miles, 2),
            coordinate=pickup_coord,
        ))

        # =====================================================================
        # PHASE 2: LEG 2 DRIVING (Pickup -> Dropoff)
        # =====================================================================
        if leg2 and leg2.duration_minutes > 0:
            rem_leg2_mins = round(leg2.duration_minutes)
            leg2_speed = leg2.distance_miles / (leg2.duration_minutes / 60.0) if leg2.duration_minutes > 0 else 55.0
            total_target_m = route.total_distance_meters
            start_leg2_miles = state.current_miles

            while rem_leg2_mins > 0:
                avail_drive_mins = calculate_available_driving_minutes(
                    state=state,
                    remaining_trip_minutes=rem_leg2_mins,
                    speed_mph=leg2_speed,
                    fuel_interval_miles=self.fuel_interval_miles,
                )

                if avail_drive_mins <= 0:
                    stop_coord = cursor.position_at_distance(cumulative_meters)
                    cycle_left_mins = round((70.0 - state.cycle_hours_used) * 60)
                    if cycle_left_mins <= 0:
                        break

                    used_drive_mins = round(state.driving_hours_since_reset * 60)
                    window_left_mins = MAX_DUTY_WINDOW_MINUTES - round(state.window_elapsed_hours * 60)

                    # 10-hour Rest required
                    if used_drive_mins >= MAX_DRIVING_MINUTES or window_left_mins <= 0:
                        rest_start = state.current_time
                        rest_end = rest_start + timedelta(minutes=REQUIRED_OFF_DUTY_MINUTES)
                        rest_loc = f"Rest Area ({round(state.current_miles)} mi)"

                        rest_seg = DutySegment(
                            status=DutyStatus.SLEEPER_BERTH,
                            start=rest_start,
                            end=rest_end,
                            duration_minutes=REQUIRED_OFF_DUTY_MINUTES,
                            location=rest_loc,
                            miles=0.0,
                            reason="Mandatory 10-hour Daily Reset",
                            coordinate=stop_coord,
                            leg="PICKUP_TO_DROPOFF",
                        )
                        segments.append(rest_seg)
                        apply_segment_to_state(state, rest_seg)

                        stops.append(Stop(
                            type=StopType.REST,
                            start=rest_start,
                            end=rest_end,
                            duration_minutes=REQUIRED_OFF_DUTY_MINUTES,
                            reason="10-hour Daily Reset",
                            location=rest_loc,
                            miles_from_start=round(state.current_miles, 2),
                            coordinate=stop_coord,
                        ))
                        continue

                    # 30-minute Break required
                    used_break_drive = round(state.driving_hours_since_break * 60)
                    if used_break_drive >= BREAK_THRESHOLD_DRIVING_MINUTES:
                        miles_to_fuel = max(0.0, self.fuel_interval_miles - state.miles_since_fuel)
                        if miles_to_fuel <= 30.0:  # Coinciding fuel stop
                            fuel_start = state.current_time
                            fuel_end = fuel_start + timedelta(minutes=FUEL_DURATION_MINUTES)
                            fuel_loc = f"Fuel Station ({round(state.current_miles)} mi)"

                            fuel_seg = DutySegment(
                                status=DutyStatus.ON_DUTY_NOT_DRIVING,
                                start=fuel_start,
                                end=fuel_end,
                                duration_minutes=FUEL_DURATION_MINUTES,
                                location=fuel_loc,
                                miles=0.0,
                                reason="Fuel Stop & 30-min Break",
                                coordinate=stop_coord,
                                leg="PICKUP_TO_DROPOFF",
                            )
                            segments.append(fuel_seg)
                            apply_segment_to_state(state, fuel_seg)

                            stops.append(Stop(
                                type=StopType.FUEL,
                                start=fuel_start,
                                end=fuel_end,
                                duration_minutes=FUEL_DURATION_MINUTES,
                                reason="Fuel Stop & 30-min Break",
                                location=fuel_loc,
                                miles_from_start=round(state.current_miles, 2),
                                coordinate=stop_coord,
                            ))
                            continue
                        else:
                            break_start = state.current_time
                            break_end = break_start + timedelta(minutes=REQUIRED_BREAK_MINUTES)
                            break_loc = f"En route ({round(state.current_miles)} mi)"

                            break_seg = DutySegment(
                                status=DutyStatus.OFF_DUTY,
                                start=break_start,
                                end=break_end,
                                duration_minutes=REQUIRED_BREAK_MINUTES,
                                location=break_loc,
                                miles=0.0,
                                reason="Required 30-minute Driving Break",
                                coordinate=stop_coord,
                                leg="PICKUP_TO_DROPOFF",
                            )
                            segments.append(break_seg)
                            apply_segment_to_state(state, break_seg)

                            stops.append(Stop(
                                type=StopType.BREAK,
                                start=break_start,
                                end=break_end,
                                duration_minutes=REQUIRED_BREAK_MINUTES,
                                reason="30-minute Driving Break",
                                location=break_loc,
                                miles_from_start=round(state.current_miles, 2),
                                coordinate=stop_coord,
                            ))
                            continue

                    # Fuel Stop required
                    miles_to_fuel = max(0.0, self.fuel_interval_miles - state.miles_since_fuel)
                    time_to_fuel = int((miles_to_fuel / leg2_speed) * 60) if leg2_speed > 0 else 999999
                    if time_to_fuel <= 0 or state.miles_since_fuel >= (self.fuel_interval_miles - 1.0):
                        if cycle_left_mins < FUEL_DURATION_MINUTES:
                            break

                        fuel_start = state.current_time
                        fuel_end = fuel_start + timedelta(minutes=FUEL_DURATION_MINUTES)
                        fuel_loc = f"Fuel Station ({round(state.current_miles)} mi)"

                        fuel_seg = DutySegment(
                            status=DutyStatus.ON_DUTY_NOT_DRIVING,
                            start=fuel_start,
                            end=fuel_end,
                            duration_minutes=FUEL_DURATION_MINUTES,
                            location=fuel_loc,
                            miles=0.0,
                            reason="Fuel Stop (1,000-mile interval)",
                            coordinate=stop_coord,
                            leg="PICKUP_TO_DROPOFF",
                        )
                        segments.append(fuel_seg)
                        apply_segment_to_state(state, fuel_seg)

                        stops.append(Stop(
                            type=StopType.FUEL,
                            start=fuel_start,
                            end=fuel_end,
                            duration_minutes=FUEL_DURATION_MINUTES,
                            reason="Fuel Stop",
                            location=fuel_loc,
                            miles_from_start=round(state.current_miles, 2),
                            coordinate=stop_coord,
                        ))
                        continue

                    break

                # Drive chunk in Leg 2
                drive_start = state.current_time
                drive_end = drive_start + timedelta(minutes=avail_drive_mins)

                if rem_leg2_mins - avail_drive_mins == 0:
                    chunk_miles = max(0.0, route.total_distance_miles - state.current_miles)
                    chunk_m = max(0.0, total_target_m - cumulative_meters)
                else:
                    chunk_miles = round((avail_drive_mins / 60.0) * leg2_speed, 2)
                    chunk_m = chunk_miles / METERS_TO_MILES

                start_coord = cursor.position_at_distance(cumulative_meters)
                cumulative_meters += chunk_m

                drive_seg = DutySegment(
                    status=DutyStatus.DRIVING,
                    start=drive_start,
                    end=drive_end,
                    duration_minutes=avail_drive_mins,
                    location=f"En route to {route.destination.display_name or route.destination.query}",
                    miles=chunk_miles,
                    reason="Driving to Dropoff",
                    coordinate=start_coord,
                    leg="PICKUP_TO_DROPOFF",
                )
                segments.append(drive_seg)
                apply_segment_to_state(state, drive_seg)
                rem_leg2_mins -= avail_drive_mins

        # =====================================================================
        # CARGO DROPOFF (at route.destination.coordinate)
        # =====================================================================
        cycle_left_mins = round((70.0 - state.cycle_hours_used) * 60)
        if cycle_left_mins >= DROPOFF_DURATION_MINUTES:
            dropoff_coord = route.destination.coordinate
            dropoff_start = state.current_time
            dropoff_end = dropoff_start + timedelta(minutes=DROPOFF_DURATION_MINUTES)
            dropoff_loc = route.destination.display_name or route.destination.query

            dropoff_seg = DutySegment(
                status=DutyStatus.ON_DUTY_NOT_DRIVING,
                start=dropoff_start,
                end=dropoff_end,
                duration_minutes=DROPOFF_DURATION_MINUTES,
                location=dropoff_loc,
                miles=0.0,
                reason="Cargo Dropoff",
                coordinate=dropoff_coord,
                leg="PICKUP_TO_DROPOFF",
            )
            segments.append(dropoff_seg)
            apply_segment_to_state(state, dropoff_seg)

            stops.append(Stop(
                type=StopType.DROPOFF,
                start=dropoff_start,
                end=dropoff_end,
                duration_minutes=DROPOFF_DURATION_MINUTES,
                reason="Cargo Dropoff",
                location=dropoff_loc,
                miles_from_start=round(state.current_miles, 2),
                coordinate=dropoff_coord,
            ))

        # =====================================================================
        # DAILY LOGS & SUMMARY
        # =====================================================================
        logger.debug("[TripPlanningService.plan] Slicing %d duty segments into 24-hour daily logs...", len(segments))
        daily_logs = split_segments_by_calendar_day(segments)
        daily_schedules = build_daily_schedules(daily_logs)

        total_driving_mins = sum(s.duration_minutes for s in segments if s.status == DutyStatus.DRIVING)
        total_driving_hrs = total_driving_mins / 60.0
        total_on_duty_hrs = sum(s.duration_minutes for s in segments if s.status.is_on_duty) / 60.0
        total_off_duty_hrs = sum(s.duration_minutes for s in segments if s.status == DutyStatus.OFF_DUTY) / 60.0
        total_sleeper_hrs = sum(s.duration_minutes for s in segments if s.status == DutyStatus.SLEEPER_BERTH) / 60.0
        total_distance = sum(s.miles for s in segments)

        total_elapsed_secs = (segments[-1].end - segments[0].start).total_seconds() if segments else 0.0
        total_elapsed_mins = int(total_elapsed_secs / 60.0)
        total_elapsed_hrs = total_elapsed_secs / 3600.0

        summary = TripScheduleSummary(
            total_distance_miles=round(total_distance, 2),
            total_driving_minutes=total_driving_mins,
            total_driving_hours=round(total_driving_hrs, 2),
            total_elapsed_minutes=total_elapsed_mins,
            total_elapsed_hours=round(total_elapsed_hrs, 2),
            total_on_duty_hours=round(total_on_duty_hrs, 2),
            total_off_duty_hours=round(total_off_duty_hrs, 2),
            total_sleeper_hours=round(total_sleeper_hrs, 2),
            starting_cycle_used=round(cycle_hours_used, 2),
            final_cycle_used=round(state.cycle_hours_used, 2),
            cycle_hours_remaining=round(max(0.0, 70.0 - state.cycle_hours_used), 2),
            cycle_hours_added=round(state.cycle_hours_used - cycle_hours_used, 2),
            days_count=len(daily_logs),
            is_valid=True,
        )

        schedule = TripSchedule(
            route=route,
            segments=segments,
            stops=stops,
            daily_schedules=daily_schedules,
            daily_logs=daily_logs,
            summary=summary,
        )

        # Run independent HOS validator
        logger.debug("[TripPlanningService.plan] Running independent HOSValidator...")
        temp_plan = TripPlan(
            segments=segments,
            stops=stops,
            daily_schedules=daily_schedules,
            daily_logs=daily_logs,
            summary=summary,
        )
        validation_res = self.validator.validate(temp_plan, expected_route_miles=route.total_distance_miles)
        schedule.validation_result = validation_res
        schedule.summary.is_valid = validation_res.valid

        logger.info(
            "[TripPlanningService.plan] Planning complete: Valid=%s, Total Elapsed=%.1fh, Driving=%.1fh, Stops=%d, Days=%d",
            validation_res.valid, summary.total_elapsed_hours, summary.total_driving_hours, len(stops), len(daily_logs)
        )

        return schedule
