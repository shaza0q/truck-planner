"""
Enumerations for HOS duty statuses, stop types, and violation codes.
"""

from enum import Enum


class DutyStatus(str, Enum):
    """FMCSA standard driver duty statuses."""
    OFF_DUTY = "OFF_DUTY"
    SLEEPER_BERTH = "SLEEPER_BERTH"
    DRIVING = "DRIVING"
    ON_DUTY_NOT_DRIVING = "ON_DUTY_NOT_DRIVING"

    @property
    def is_on_duty(self) -> bool:
        """Returns True if this status counts towards on-duty cycle hours."""
        return self in (DutyStatus.DRIVING, DutyStatus.ON_DUTY_NOT_DRIVING)

    @property
    def is_rest(self) -> bool:
        """Returns True if this status qualifies as rest/off-duty."""
        return self in (DutyStatus.OFF_DUTY, DutyStatus.SLEEPER_BERTH)


class StopType(str, Enum):
    """Types of stops during a trip."""
    PICKUP = "PICKUP"
    DROPOFF = "DROPOFF"
    FUEL = "FUEL"
    REST = "REST"
    BREAK = "BREAK"


class ViolationCode(str, Enum):
    """Violation error codes for independent validation."""
    EXCEEDED_11_HOUR_DRIVING_LIMIT = "EXCEEDED_11_HOUR_DRIVING_LIMIT"
    DRIVING_PAST_14_HOUR_WINDOW = "DRIVING_PAST_14_HOUR_WINDOW"
    MISSING_30_MIN_BREAK = "MISSING_30_MIN_BREAK"
    EXCEEDED_70_HOUR_CYCLE = "EXCEEDED_70_HOUR_CYCLE"
    INVALID_PICKUP_DURATION = "INVALID_PICKUP_DURATION"
    INVALID_DROPOFF_DURATION = "INVALID_DROPOFF_DURATION"
    EXCEEDED_FUEL_INTERVAL = "EXCEEDED_FUEL_INTERVAL"
    INVALID_DAILY_LOG_TOTAL = "INVALID_DAILY_LOG_TOTAL"
    OVERLAPPING_SEGMENTS = "OVERLAPPING_SEGMENTS"
    INVALID_SEGMENT_DURATION = "INVALID_SEGMENT_DURATION"
    INVALID_SEGMENT_TIMES = "INVALID_SEGMENT_TIMES"
    ROUTE_DISTANCE_MISMATCH = "ROUTE_DISTANCE_MISMATCH"
