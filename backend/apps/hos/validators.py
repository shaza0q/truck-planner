"""
Independent Hours of Service (HOS) Validator.
Validates trip plans against FMCSA regulations and structural constraints.
"""

from datetime import datetime, timedelta
from typing import List, Optional
import logging

from .constants import (
    MAX_DRIVING_MINUTES,
    MAX_DUTY_WINDOW_MINUTES,
    REQUIRED_OFF_DUTY_MINUTES,
    BREAK_THRESHOLD_DRIVING_MINUTES,
    REQUIRED_BREAK_MINUTES,
    MAX_CYCLE_HOURS,
    FUEL_INTERVAL_MILES,
    PICKUP_DURATION_MINUTES,
    DROPOFF_DURATION_MINUTES,
)
from .enums import DutyStatus, ViolationCode
from .models import TripPlan, ValidationResult, Violation, DutySegment

logger = logging.getLogger(__name__)


class HOSValidator:
    """
    Independent validator for HOS trip plans.
    Strictly verifies all FMCSA constraints and data integrity rules.
    """

    def validate(
        self,
        plan: TripPlan,
        expected_route_miles: Optional[float] = None,
        fuel_interval_miles: float = FUEL_INTERVAL_MILES,
    ) -> ValidationResult:
        violations: List[Violation] = []
        warnings: List[str] = []

        segments = plan.segments
        if not segments:
            violations.append(Violation(
                code=ViolationCode.INVALID_SEGMENT_TIMES,
                message="Plan contains no scheduled duty segments.",
            ))
            return ValidationResult(valid=False, violations=violations, warnings=warnings)

        # 1. Check segment integrity and sequence (no overlap, positive duration, start < end)
        for i, seg in enumerate(segments):
            if seg.duration_minutes <= 0:
                violations.append(Violation(
                    code=ViolationCode.INVALID_SEGMENT_DURATION,
                    message=f"Segment {i} has non-positive duration: {seg.duration_minutes} minutes.",
                    segment_index=i,
                ))

            if seg.start >= seg.end:
                violations.append(Violation(
                    code=ViolationCode.INVALID_SEGMENT_TIMES,
                    message=f"Segment {i} start time ({seg.start}) is not before end time ({seg.end}).",
                    segment_index=i,
                ))

            expected_duration = int((seg.end - seg.start).total_seconds() / 60)
            if seg.duration_minutes != expected_duration:
                violations.append(Violation(
                    code=ViolationCode.INVALID_SEGMENT_DURATION,
                    message=f"Segment {i} duration ({seg.duration_minutes}m) does not match start-end diff ({expected_duration}m).",
                    segment_index=i,
                ))

            if i > 0:
                prev_seg = segments[i - 1]
                if seg.start < prev_seg.end:
                    violations.append(Violation(
                        code=ViolationCode.OVERLAPPING_SEGMENTS,
                        message=f"Segment {i} starts ({seg.start}) before segment {i-1} ends ({prev_seg.end}).",
                        segment_index=i,
                    ))

        # 2. Check Pickup duration and status
        pickup_segs = [s for s in segments if s.reason and ("cargo pickup" in s.reason.lower() or s.reason.strip().lower() == "pickup")]
        if pickup_segs:
            total_pickup_mins = sum(s.duration_minutes for s in pickup_segs)
            if total_pickup_mins != PICKUP_DURATION_MINUTES:
                violations.append(Violation(
                    code=ViolationCode.INVALID_PICKUP_DURATION,
                    message=f"Pickup duration must be exactly {PICKUP_DURATION_MINUTES} minutes (found {total_pickup_mins}m).",
                ))
            for s in pickup_segs:
                if s.status != DutyStatus.ON_DUTY_NOT_DRIVING:
                    violations.append(Violation(
                        code=ViolationCode.INVALID_PICKUP_DURATION,
                        message=f"Pickup segment must be ON_DUTY_NOT_DRIVING (found {s.status.value}).",
                    ))

        # 3. Check Dropoff duration and status
        dropoff_segs = [s for s in segments if s.reason and ("cargo dropoff" in s.reason.lower() or s.reason.strip().lower() == "dropoff")]
        if dropoff_segs:
            total_dropoff_mins = sum(s.duration_minutes for s in dropoff_segs)
            if total_dropoff_mins != DROPOFF_DURATION_MINUTES:
                violations.append(Violation(
                    code=ViolationCode.INVALID_DROPOFF_DURATION,
                    message=f"Dropoff duration must be exactly {DROPOFF_DURATION_MINUTES} minutes (found {total_dropoff_mins}m).",
                ))
            for s in dropoff_segs:
                if s.status != DutyStatus.ON_DUTY_NOT_DRIVING:
                    violations.append(Violation(
                        code=ViolationCode.INVALID_DROPOFF_DURATION,
                        message=f"Dropoff segment must be ON_DUTY_NOT_DRIVING (found {s.status.value}).",
                    ))

        # 4. HOS Clock State Machine Simulation for independent verification
        drive_mins_since_reset = 0
        drive_mins_since_break = 0
        window_start: Optional[datetime] = None
        miles_since_fuel = 0.0
        total_cycle_mins = round(plan.summary.starting_cycle_used * 60)

        for i, seg in enumerate(segments):
            mins = seg.duration_minutes

            # Check if this segment is a 10-hour reset
            if seg.status.is_rest and mins >= REQUIRED_OFF_DUTY_MINUTES:
                drive_mins_since_reset = 0
                drive_mins_since_break = 0
                window_start = None
                continue

            # Start of duty window
            if seg.status.is_on_duty and window_start is None:
                window_start = seg.start

            # Check for qualifying 30-min break
            if seg.status != DutyStatus.DRIVING and mins >= REQUIRED_BREAK_MINUTES:
                drive_mins_since_break = 0

            # If fuel stop
            if seg.reason and "fuel" in seg.reason.lower():
                miles_since_fuel = 0.0

            # If driving segment
            if seg.status == DutyStatus.DRIVING:
                # 4.1 Check 14-hour window limit
                if window_start is not None:
                    elapsed_to_drive_end = int((seg.end - window_start).total_seconds() / 60)
                    if elapsed_to_drive_end > MAX_DUTY_WINDOW_MINUTES:
                        violations.append(Violation(
                            code=ViolationCode.DRIVING_PAST_14_HOUR_WINDOW,
                            message=(
                                f"Segment {i} drove past 14-hour window limit. "
                                f"Elapsed window: {elapsed_to_drive_end / 60:.2f}h (max 14.0h)."
                            ),
                            segment_index=i,
                        ))

                # 4.2 Check 11-hour driving limit
                if drive_mins_since_reset + mins > MAX_DRIVING_MINUTES:
                    violations.append(Violation(
                        code=ViolationCode.EXCEEDED_11_HOUR_DRIVING_LIMIT,
                        message=(
                            f"Segment {i} exceeded 11-hour driving limit. "
                            f"Driving in window: {(drive_mins_since_reset + mins) / 60:.2f}h (max 11.0h)."
                        ),
                        segment_index=i,
                    ))

                # 4.3 Check 8-hour driving threshold without 30-min break
                if drive_mins_since_break + mins > BREAK_THRESHOLD_DRIVING_MINUTES:
                    violations.append(Violation(
                        code=ViolationCode.MISSING_30_MIN_BREAK,
                        message=(
                            f"Segment {i} drove over 8 consecutive hours without a 30-minute break. "
                            f"Cumulative drive: {(drive_mins_since_break + mins) / 60:.2f}h (max 8.0h)."
                        ),
                        segment_index=i,
                    ))

                # 4.4 Check Fuel Interval
                if miles_since_fuel + seg.miles > fuel_interval_miles + 0.5:
                    violations.append(Violation(
                        code=ViolationCode.EXCEEDED_FUEL_INTERVAL,
                        message=(
                            f"Segment {i} exceeded {fuel_interval_miles}-mile fuel interval. "
                            f"Miles since last fuel: {miles_since_fuel + seg.miles:.1f} mi."
                        ),
                        segment_index=i,
                    ))

                drive_mins_since_reset += mins
                drive_mins_since_break += mins
                miles_since_fuel += seg.miles

            # Track cycle hours for on-duty activities
            if seg.status.is_on_duty:
                total_cycle_mins += mins
                if total_cycle_mins > (MAX_CYCLE_HOURS * 60) + 1:  # Allow 1-min rounding tolerance
                    violations.append(Violation(
                        code=ViolationCode.EXCEEDED_70_HOUR_CYCLE,
                        message=(
                            f"Segment {i} exceeded 70-hour / 8-day cycle limit. "
                            f"Total cycle hours used: {total_cycle_mins / 60:.2f}h (max 70.0h)."
                        ),
                        segment_index=i,
                    ))

        # 5. Check Daily Logs total exactly 24 hours (1440 minutes)
        for d_idx, d_log in enumerate(plan.daily_logs):
            tot_mins = sum(s.duration_minutes for s in d_log.segments)
            if tot_mins != 1440:
                violations.append(Violation(
                    code=ViolationCode.INVALID_DAILY_LOG_TOTAL,
                    message=f"Daily log for date {d_log.date} totals {tot_mins} minutes ({tot_mins / 60.0:.2f}h), must be 1440 mins (24.0h).",
                    details={"date": d_log.date, "total_minutes": tot_mins},
                ))

        # 6. Check Total Distance matches expected route miles if provided
        if expected_route_miles is not None and expected_route_miles > 0:
            total_driving_miles = sum(s.miles for s in segments if s.status == DutyStatus.DRIVING)
            if abs(total_driving_miles - expected_route_miles) > 1.0:
                violations.append(Violation(
                    code=ViolationCode.ROUTE_DISTANCE_MISMATCH,
                    message=f"Total driving miles ({total_driving_miles:.1f} mi) does not match expected route ({expected_route_miles:.1f} mi).",
                ))

        is_valid = len(violations) == 0
        if is_valid:
            logger.info("[HOSValidator.validate] Plan validation PASSED with 0 violations (%d segments checked)", len(segments))
        else:
            logger.warning("[HOSValidator.validate] Plan validation FAILED with %d violations: %s", len(violations), [v.code for v in violations])
        return ValidationResult(valid=is_valid, violations=violations, warnings=warnings)
