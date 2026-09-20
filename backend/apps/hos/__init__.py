"""
HOS Engine package.
"""

from .constants import (
    MAX_DRIVING_HOURS,
    MAX_DUTY_WINDOW_HOURS,
    REQUIRED_OFF_DUTY_HOURS,
    BREAK_THRESHOLD_DRIVING_HOURS,
    REQUIRED_BREAK_MINUTES,
    MAX_CYCLE_HOURS,
    CYCLE_DAYS,
    FUEL_INTERVAL_MILES,
    PICKUP_DURATION_MINUTES,
    DROPOFF_DURATION_MINUTES,
    FUEL_DURATION_MINUTES,
)
from .enums import DutyStatus, StopType, ViolationCode
from .models import (
    TripInput,
    MockRoute,
    DutySegment,
    Stop,
    DailyLog,
    DailySchedule,
    TripSummary,
    ValidationResult,
    Violation,
    TripPlan,
    HOSState,
)
from .exceptions import (
    HOSError,
    InvalidTripInputError,
    InsufficientCycleHoursError,
    ImpossibleRouteError,
)
from .scheduler import HOSScheduler
from .validators import HOSValidator

__all__ = [
    "MAX_DRIVING_HOURS",
    "MAX_DUTY_WINDOW_HOURS",
    "REQUIRED_OFF_DUTY_HOURS",
    "BREAK_THRESHOLD_DRIVING_HOURS",
    "REQUIRED_BREAK_MINUTES",
    "MAX_CYCLE_HOURS",
    "CYCLE_DAYS",
    "FUEL_INTERVAL_MILES",
    "PICKUP_DURATION_MINUTES",
    "DROPOFF_DURATION_MINUTES",
    "FUEL_DURATION_MINUTES",
    "DutyStatus",
    "StopType",
    "ViolationCode",
    "TripInput",
    "MockRoute",
    "DutySegment",
    "Stop",
    "DailyLog",
    "DailySchedule",
    "TripSummary",
    "ValidationResult",
    "Violation",
    "TripPlan",
    "HOSState",
    "HOSError",
    "InvalidTripInputError",
    "InsufficientCycleHoursError",
    "ImpossibleRouteError",
    "HOSScheduler",
    "HOSValidator",
]
