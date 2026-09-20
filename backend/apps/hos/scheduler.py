"""
Deterministic, constraint-driven Hours of Service (HOS) Scheduler.
Pure domain logic: No database, HTTP, or external API dependencies.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List
import logging

from .constants import (
    MAX_DRIVING_MINUTES,
    MAX_DUTY_WINDOW_MINUTES,
    REQUIRED_OFF_DUTY_MINUTES,
    BREAK_THRESHOLD_DRIVING_MINUTES,
    REQUIRED_BREAK_MINUTES,
    MAX_CYCLE_MINUTES,
    FUEL_INTERVAL_MILES,
    PICKUP_DURATION_MINUTES,
    DROPOFF_DURATION_MINUTES,
    FUEL_DURATION_MINUTES,
)
from .enums import DutyStatus, StopType
from .exceptions import InvalidTripInputError, InsufficientCycleHoursError, ImpossibleRouteError
from .models import (
    TripInput,
    MockRoute,
    DutySegment,
    Stop,
    HOSState,
    TripPlan,
    TripSummary,
)
from .rules import calculate_available_driving_minutes, apply_segment_to_state
from .daily_logs import split_segments_by_calendar_day, build_daily_schedules
from .validators import HOSValidator

logger = logging.getLogger(__name__)


class HOSScheduler:
    """
    Event-driven HOS Trip Scheduler.
    Determines optimal, compliant duty segments and stops based on FMCSA rules.
    """

    def __init__(self, fuel_interval_miles: float = FUEL_INTERVAL_MILES):
        self.fuel_interval_miles = fuel_interval_miles

    def plan_trip(
        self,
        trip_input: TripInput,
        route: MockRoute,
        start_time: Optional[datetime] = None,
    ) -> TripPlan:
        """
        Plans a complete HOS-compliant trip schedule.
        """
        # 1. Validate basic input constraints
        logger.info(
            "[HOSScheduler.plan_trip] Planning mock trip: %s -> %s -> %s (%.1f mi, %d min drive, %.1fh cycle used)",
            trip_input.current_location, trip_input.pickup_location, trip_input.dropoff_location,
            route.total_distance_miles, route.total_driving_minutes, trip_input.current_cycle_used
        )
        if trip_input.current_cycle_used < 0.0 or trip_input.current_cycle_used > 70.0:
            logger.warning("[HOSScheduler.plan_trip] Invalid cycle hours: %.2f", trip_input.current_cycle_used)
            raise InvalidTripInputError(
                "Current cycle used must be between 0.0 and 70.0 hours.",
                code="INVALID_CYCLE_HOURS"
            )

        if route.total_distance_miles < 0.0 or route.total_driving_minutes < 0:
            logger.warning("[HOSScheduler.plan_trip] Invalid route params")
            raise InvalidTripInputError(
                "Route distance and driving minutes must be non-negative.",
                code="INVALID_ROUTE_PARAMS"
            )

        if not trip_input.current_location or not trip_input.pickup_location or not trip_input.dropoff_location:
            logger.warning("[HOSScheduler.plan_trip] Missing location fields")
            raise InvalidTripInputError(
                "Locations (current, pickup, dropoff) cannot be empty.",
                code="MISSING_LOCATIONS"
            )

        if route.total_distance_miles > 0 and route.total_driving_minutes == 0:
            logger.warning("[HOSScheduler.plan_trip] Impossible route")
            raise ImpossibleRouteError(
                "Route has positive distance but zero driving time.",
                code="IMPOSSIBLE_ROUTE"
            )

        # If driver has already exhausted full 70 hours
        if trip_input.current_cycle_used >= 70.0:
            logger.warning("[HOSScheduler.plan_trip] Cycle exhausted (70.0h)")
            raise InsufficientCycleHoursError(
                "Driver has 70.0 cycle hours used. No on-duty work or driving can be scheduled.",
                code="INSUFFICIENT_CYCLE_HOURS"
            )

        # Default start time: 06:00:00 on the current day (UTC)
        if start_time is None:
            now = datetime.now(timezone.utc)
            start_time = datetime(now.year, now.month, now.day, 6, 0, 0, tzinfo=timezone.utc)

        logger.debug("[HOSScheduler.plan_trip] Starting simulation at %s", start_time.isoformat())
        state = HOSState(
            cycle_hours_used=trip_input.current_cycle_used,
            current_time=start_time,
            current_miles=0.0,
        )

        segments: List[DutySegment] = []
        stops: List[Stop] = []

        # 2. Schedule Cargo Pickup (1 hour ON_DUTY_NOT_DRIVING)
        avail_cycle_mins = round((70.0 - state.cycle_hours_used) * 60)
        if avail_cycle_mins < PICKUP_DURATION_MINUTES:
            # Cannot even complete pickup within 70-hour cycle
            raise InsufficientCycleHoursError(
                "Driver does not have enough remaining cycle hours to complete pickup.",
                code="INSUFFICIENT_CYCLE_HOURS"
            )

        pickup_start = state.current_time
        pickup_end = pickup_start + timedelta(minutes=PICKUP_DURATION_MINUTES)
        pickup_seg = DutySegment(
            status=DutyStatus.ON_DUTY_NOT_DRIVING,
            start=pickup_start,
            end=pickup_end,
            duration_minutes=PICKUP_DURATION_MINUTES,
            location=trip_input.pickup_location,
            miles=0.0,
            reason="Cargo Pickup",
        )
        segments.append(pickup_seg)
        apply_segment_to_state(state, pickup_seg)

        stops.append(Stop(
            type=StopType.PICKUP,
            start=pickup_start,
            end=pickup_end,
            duration_minutes=PICKUP_DURATION_MINUTES,
            reason="Cargo Pickup",
            location=trip_input.pickup_location,
            miles_from_start=0.0,
        ))

        # 3. Driving Loop
        remaining_drive_mins = route.total_driving_minutes
        speed_mph = route.average_mph
        total_trip_miles = route.total_distance_miles

        while remaining_drive_mins > 0:
            avail_drive_mins = calculate_available_driving_minutes(
                state=state,
                remaining_trip_minutes=remaining_drive_mins,
                speed_mph=speed_mph,
                fuel_interval_miles=self.fuel_interval_miles,
            )

            if avail_drive_mins <= 0:
                # Determine which constraint was reached and insert the required non-driving event
                cycle_left_mins = round((70.0 - state.cycle_hours_used) * 60)
                if cycle_left_mins <= 0:
                    # 70-hour cycle exhausted! Cannot drive or work further.
                    break

                # Check if 11h drive or 14h window is exhausted -> 10-hour Rest
                used_drive_mins = round(state.driving_hours_since_reset * 60)
                window_left_mins = MAX_DUTY_WINDOW_MINUTES - round(state.window_elapsed_hours * 60)
                
                if used_drive_mins >= MAX_DRIVING_MINUTES or window_left_mins <= 0:
                    # Schedule 10-hour rest
                    rest_start = state.current_time
                    rest_end = rest_start + timedelta(minutes=REQUIRED_OFF_DUTY_MINUTES)
                    rest_location = f"Rest Area ({round(state.current_miles)} mi)"
                    
                    rest_seg = DutySegment(
                        status=DutyStatus.OFF_DUTY,
                        start=rest_start,
                        end=rest_end,
                        duration_minutes=REQUIRED_OFF_DUTY_MINUTES,
                        location=rest_location,
                        miles=0.0,
                        reason="Mandatory 10-hour Daily Reset",
                    )
                    segments.append(rest_seg)
                    apply_segment_to_state(state, rest_seg)

                    stops.append(Stop(
                        type=StopType.REST,
                        start=rest_start,
                        end=rest_end,
                        duration_minutes=REQUIRED_OFF_DUTY_MINUTES,
                        reason="10-hour Daily Reset",
                        location=rest_location,
                        miles_from_start=round(state.current_miles, 2),
                    ))
                    continue

                # Check if 8h cumulative drive threshold reached -> 30-min break
                used_break_drive_mins = round(state.driving_hours_since_break * 60)
                if used_break_drive_mins >= BREAK_THRESHOLD_DRIVING_MINUTES:
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
                    ))
                    continue

                # Check if fuel interval reached -> 30-min Fuel Stop
                miles_to_fuel = max(0.0, self.fuel_interval_miles - state.miles_since_fuel)
                time_to_fuel = int((miles_to_fuel / speed_mph) * 60) if speed_mph > 0 else 999999
                if time_to_fuel <= 0 or state.miles_since_fuel >= (self.fuel_interval_miles - 1.0):
                    if cycle_left_mins < FUEL_DURATION_MINUTES:
                        # Cannot even complete fuel stop within cycle
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
                    ))
                    continue

                # Fallback to prevent infinite loops if an unforeseen edge case arises
                break

            # Schedule driving chunk
            drive_start = state.current_time
            drive_end = drive_start + timedelta(minutes=avail_drive_mins)
            
            # Calculate miles for this chunk
            if remaining_drive_mins - avail_drive_mins == 0:
                # Final driving segment gets exact remaining miles
                chunk_miles = max(0.0, total_trip_miles - state.current_miles)
            else:
                chunk_miles = round((avail_drive_mins / 60.0) * speed_mph, 2)

            drive_location = f"En route to {trip_input.dropoff_location}"
            drive_seg = DutySegment(
                status=DutyStatus.DRIVING,
                start=drive_start,
                end=drive_end,
                duration_minutes=avail_drive_mins,
                location=drive_location,
                miles=chunk_miles,
                reason="Driving",
            )
            segments.append(drive_seg)
            apply_segment_to_state(state, drive_seg)
            remaining_drive_mins -= avail_drive_mins

        # 4. Schedule Cargo Dropoff if destination reached
        if remaining_drive_mins == 0:
            cycle_left_mins = round((70.0 - state.cycle_hours_used) * 60)
            if cycle_left_mins >= DROPOFF_DURATION_MINUTES:
                dropoff_start = state.current_time
                dropoff_end = dropoff_start + timedelta(minutes=DROPOFF_DURATION_MINUTES)
                dropoff_seg = DutySegment(
                    status=DutyStatus.ON_DUTY_NOT_DRIVING,
                    start=dropoff_start,
                    end=dropoff_end,
                    duration_minutes=DROPOFF_DURATION_MINUTES,
                    location=trip_input.dropoff_location,
                    miles=0.0,
                    reason="Cargo Dropoff",
                )
                segments.append(dropoff_seg)
                apply_segment_to_state(state, dropoff_seg)

                stops.append(Stop(
                    type=StopType.DROPOFF,
                    start=dropoff_start,
                    end=dropoff_end,
                    duration_minutes=DROPOFF_DURATION_MINUTES,
                    reason="Cargo Dropoff",
                    location=trip_input.dropoff_location,
                    miles_from_start=round(state.current_miles, 2),
                ))

        # 5. Build 24-hour Daily Logs & Schedules
        daily_logs = split_segments_by_calendar_day(segments)
        daily_schedules = build_daily_schedules(daily_logs)

        # 6. Calculate Trip Summary
        total_driving_hrs = sum(s.duration_minutes for s in segments if s.status == DutyStatus.DRIVING) / 60.0
        total_on_duty_hrs = sum(s.duration_minutes for s in segments if s.status.is_on_duty) / 60.0
        total_off_duty_hrs = sum(s.duration_minutes for s in segments if s.status == DutyStatus.OFF_DUTY) / 60.0
        total_sleeper_hrs = sum(s.duration_minutes for s in segments if s.status == DutyStatus.SLEEPER_BERTH) / 60.0
        total_dist_miles = sum(s.miles for s in segments)
        total_duration_hrs = (segments[-1].end - segments[0].start).total_seconds() / 3600.0 if segments else 0.0

        summary = TripSummary(
            total_duration_hours=round(total_duration_hrs, 2),
            total_driving_hours=round(total_driving_hrs, 2),
            total_on_duty_hours=round(total_on_duty_hrs, 2),
            total_off_duty_hours=round(total_off_duty_hrs, 2),
            total_sleeper_hours=round(total_sleeper_hrs, 2),
            total_distance_miles=round(total_dist_miles, 2),
            starting_cycle_used=round(trip_input.current_cycle_used, 2),
            final_cycle_used=round(state.cycle_hours_used, 2),
            cycle_hours_added=round(state.cycle_hours_used - trip_input.current_cycle_used, 2),
            days_count=len(daily_logs),
            is_valid=True,
        )

        plan = TripPlan(
            segments=segments,
            stops=stops,
            daily_schedules=daily_schedules,
            daily_logs=daily_logs,
            summary=summary,
        )

        # 7. Run Independent Validator
        validator = HOSValidator()
        validation_res = validator.validate(plan, expected_route_miles=route.total_distance_miles)
        plan.validation_result = validation_res
        plan.summary.is_valid = validation_res.valid

        return plan
