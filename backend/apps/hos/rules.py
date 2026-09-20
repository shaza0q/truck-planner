"""
Pure HOS rule helper functions and state transition logic.
"""

from datetime import datetime, timedelta
from typing import Optional

from .constants import (
    MAX_DRIVING_MINUTES,
    MAX_DUTY_WINDOW_MINUTES,
    REQUIRED_OFF_DUTY_MINUTES,
    BREAK_THRESHOLD_DRIVING_MINUTES,
    REQUIRED_BREAK_MINUTES,
    MAX_CYCLE_MINUTES,
)
from .enums import DutyStatus
from .models import DutySegment, HOSState


def is_qualifying_reset(duration_minutes: int, status: DutyStatus) -> bool:
    """
    Checks if a segment qualifies as a daily HOS reset.
    Requires at least 10 consecutive hours (600 mins) in OFF_DUTY or SLEEPER_BERTH.
    """
    return status.is_rest and duration_minutes >= REQUIRED_OFF_DUTY_MINUTES


def is_qualifying_break(duration_minutes: int, status: DutyStatus) -> bool:
    """
    Checks if a segment qualifies as a 30-minute driving break interruption.
    Requires at least 30 consecutive minutes of non-driving status.
    """
    return status != DutyStatus.DRIVING and duration_minutes >= REQUIRED_BREAK_MINUTES


def apply_segment_to_state(state: HOSState, segment: DutySegment) -> None:
    """
    Authoritative state transition function.
    Updates the HOSState in-place after scheduling a duty segment.
    """
    duration_mins = segment.duration_minutes
    duration_hrs = duration_mins / 60.0

    # 1. Update current time & location miles
    state.current_time = segment.end
    state.last_status = segment.status

    # 2. Check if this segment qualifies as a 10-hour reset
    if is_qualifying_reset(duration_mins, segment.status):
        state.driving_hours_since_reset = 0.0
        state.duty_hours_since_reset = 0.0
        state.driving_hours_since_break = 0.0
        state.window_start = None
        return

    # 3. If starting a duty period from an inactive/reset window
    if segment.status.is_on_duty and state.window_start is None:
        state.window_start = segment.start

    # 4. If this segment qualifies as a 30-minute break
    if is_qualifying_break(duration_mins, segment.status):
        state.driving_hours_since_break = 0.0

    # 5. Track driving specific metrics
    if segment.status == DutyStatus.DRIVING:
        state.driving_hours_since_reset += duration_hrs
        state.driving_hours_since_break += duration_hrs
        state.miles_since_fuel += segment.miles
        state.current_miles += segment.miles

    # 6. Track on-duty metrics
    if segment.status.is_on_duty:
        state.duty_hours_since_reset += duration_hrs
        state.cycle_hours_used += duration_hrs

    # 7. If fuel event occurred, reset fuel counter
    if segment.reason and "fuel" in segment.reason.lower():
        state.miles_since_fuel = 0.0


def calculate_available_driving_minutes(
    state: HOSState,
    remaining_trip_minutes: int,
    speed_mph: float,
    fuel_interval_miles: float = 1000.0,
) -> int:
    """
    Calculates the maximum driving minutes allowed before the earliest constraint hits.
    
    Constraints considered:
    1. 11-hour driving clock (since reset)
    2. 14-hour duty window (from window_start to current_time + drive_duration)
    3. 8-hour cumulative driving limit (before 30-min break)
    4. 70-hour cycle limit
    5. Distance to next fuel stop (1000 miles since last fuel)
    6. Remaining trip minutes
    """
    # 1. 11-hour limit
    used_drive_mins = round(state.driving_hours_since_reset * 60)
    avail_11h_mins = max(0, MAX_DRIVING_MINUTES - used_drive_mins)

    # 2. 14-hour window limit
    if state.window_start is not None and state.current_time is not None:
        elapsed_window_mins = round((state.current_time - state.window_start).total_seconds() / 60)
        avail_14h_mins = max(0, MAX_DUTY_WINDOW_MINUTES - elapsed_window_mins)
    else:
        # Duty window hasn't started yet, so full 14 hours available
        avail_14h_mins = MAX_DUTY_WINDOW_MINUTES

    # 3. 8-hour break limit
    used_break_drive_mins = round(state.driving_hours_since_break * 60)
    avail_8h_break_mins = max(0, BREAK_THRESHOLD_DRIVING_MINUTES - used_break_drive_mins)

    # 4. 70-hour cycle limit
    used_cycle_mins = round(state.cycle_hours_used * 60)
    avail_cycle_mins = max(0, MAX_CYCLE_MINUTES - used_cycle_mins)

    # 5. Fuel limit in minutes
    if speed_mph > 0:
        miles_to_fuel = max(0.0, fuel_interval_miles - state.miles_since_fuel)
        avail_fuel_mins = int((miles_to_fuel / speed_mph) * 60)
    else:
        avail_fuel_mins = remaining_trip_minutes

    return min(
        remaining_trip_minutes,
        avail_11h_mins,
        avail_14h_mins,
        avail_8h_break_mins,
        avail_cycle_mins,
        avail_fuel_mins,
    )
