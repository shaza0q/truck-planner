"""
Domain models and dataclasses for the HOS Engine.
Pure Python data structures without Django ORM dependencies.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from typing import List, Optional, Dict, Any

from .enums import DutyStatus, StopType, ViolationCode


@dataclass
class MockRoute:
    """Mocked route input for deterministic scheduling without an external routing API."""
    total_distance_miles: float
    total_driving_minutes: int

    @property
    def total_driving_hours(self) -> float:
        return self.total_driving_minutes / 60.0

    @property
    def average_mph(self) -> float:
        if self.total_driving_minutes <= 0:
            return 0.0
        return self.total_distance_miles / (self.total_driving_minutes / 60.0)


@dataclass
class TripInput:
    """User input for a trucking trip."""
    current_location: str
    pickup_location: str
    dropoff_location: str
    current_cycle_used: float  # In hours (0.0 to 70.0)

    @property
    def remaining_cycle_hours(self) -> float:
        return max(0.0, 70.0 - self.current_cycle_used)


@dataclass
class DutySegment:
    """A single contiguous segment of driver duty status."""
    status: DutyStatus
    start: datetime
    end: datetime
    duration_minutes: int
    location: str
    miles: float = 0.0
    reason: Optional[str] = None
    coordinate: Optional[Any] = None
    leg: Optional[str] = None
    start_minute: Optional[int] = None
    end_minute: Optional[int] = None
    event_type: Optional[str] = None

    @property
    def duration_hours(self) -> float:
        return self.duration_minutes / 60.0

    def to_dict(self) -> Dict[str, Any]:
        coord_dict = None
        if self.coordinate:
            coord_dict = self.coordinate.to_dict() if hasattr(self.coordinate, 'to_dict') else self.coordinate

        return {
            "status": self.status.value,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "startTime": self.start.strftime("%H:%M"),
            "endTime": self.end.strftime("%H:%M"),
            "durationMinutes": self.duration_minutes,
            "durationHours": round(self.duration_hours, 2),
            "startMinute": self.start_minute if self.start_minute is not None else (self.start.hour * 60 + self.start.minute),
            "endMinute": self.end_minute if self.end_minute is not None else (self.end.hour * 60 + self.end.minute),
            "eventType": self.event_type,
            "location": self.location,
            "miles": round(self.miles, 2),
            "reason": self.reason,
            "coordinate": coord_dict,
            "leg": self.leg,
        }


@dataclass
class Stop:
    """A planned stop event along the trip."""
    type: StopType
    start: datetime
    end: datetime
    duration_minutes: int
    reason: str
    location: str
    miles_from_start: float
    coordinate: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        coord_dict = None
        if self.coordinate:
            coord_dict = self.coordinate.to_dict() if hasattr(self.coordinate, 'to_dict') else self.coordinate

        return {
            "type": self.type.value,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "durationMinutes": self.duration_minutes,
            "reason": self.reason,
            "location": self.location,
            "milesFromStart": round(self.miles_from_start, 2),
            "coordinate": coord_dict,
        }


@dataclass
class Remark:
    """Structured remark for FMCSA ELD log events."""
    time: str
    location: str
    description: str
    event_type: Optional[str] = None
    coordinate: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        coord_dict = None
        if self.coordinate:
            coord_dict = self.coordinate.to_dict() if hasattr(self.coordinate, 'to_dict') else self.coordinate

        return {
            "time": self.time,
            "location": self.location,
            "description": self.description,
            "eventType": self.event_type,
            "coordinate": coord_dict,
        }


@dataclass
class DailyTotals:
    """Total hours and minutes by duty status for a single 24-hour log."""
    off_duty: float = 0.0
    sleeper_berth: float = 0.0
    driving: float = 0.0
    on_duty_not_driving: float = 0.0
    off_duty_minutes: int = 0
    sleeper_berth_minutes: int = 0
    driving_minutes: int = 0
    on_duty_not_driving_minutes: int = 0

    @property
    def total_hours(self) -> float:
        return round(self.off_duty + self.sleeper_berth + self.driving + self.on_duty_not_driving, 4)

    @property
    def total_minutes(self) -> int:
        return self.off_duty_minutes + self.sleeper_berth_minutes + self.driving_minutes + self.on_duty_not_driving_minutes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "offDuty": round(self.off_duty, 2),
            "sleeperBerth": round(self.sleeper_berth, 2),
            "driving": round(self.driving, 2),
            "onDutyNotDriving": round(self.on_duty_not_driving, 2),
            "totalHours": round(self.total_hours, 2),
            "offDutyMinutes": self.off_duty_minutes,
            "sleeperBerthMinutes": self.sleeper_berth_minutes,
            "drivingMinutes": self.driving_minutes,
            "onDutyNotDrivingMinutes": self.on_duty_not_driving_minutes,
            "totalMinutes": self.total_minutes,
        }


@dataclass
class DailyLog:
    """FMCSA 24-hour driver's daily log (00:00 to 24:00)."""
    date: str  # YYYY-MM-DD
    total_miles: float
    segments: List[DutySegment] = field(default_factory=list)
    remarks: List[Remark] = field(default_factory=list)
    totals: DailyTotals = field(default_factory=DailyTotals)
    day_number: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "dayNumber": self.day_number,
            "totalMiles": round(self.total_miles, 2),
            "segments": [s.to_dict() for s in self.segments],
            "remarks": [r.to_dict() for r in self.remarks],
            "totals": self.totals.to_dict(),
        }


@dataclass
class DailySchedule:
    """Summary of scheduled activities for a calendar day."""
    date: str
    segments: List[DutySegment]
    total_driving_hours: float
    total_on_duty_hours: float
    total_off_duty_hours: float
    total_sleeper_hours: float
    total_hours: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "segments": [s.to_dict() for s in self.segments],
            "totalDrivingHours": round(self.total_driving_hours, 2),
            "totalOnDutyHours": round(self.total_on_duty_hours, 2),
            "totalOffDutyHours": round(self.total_off_duty_hours, 2),
            "totalSleeperHours": round(self.total_sleeper_hours, 2),
            "totalHours": round(self.total_hours, 2),
        }


@dataclass
class Violation:
    """Violation detected by the independent validator."""
    code: ViolationCode
    message: str
    segment_index: Optional[int] = None
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code.value,
            "message": self.message,
            "segmentIndex": self.segment_index,
            "details": self.details or {},
        }


@dataclass
class ValidationResult:
    """Result of independent plan validation."""
    valid: bool
    violations: List[Violation] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "violations": [v.to_dict() for v in self.violations],
            "warnings": self.warnings,
        }


@dataclass
class TripSummary:
    """Overall summary statistics for the trip plan."""
    total_duration_hours: float
    total_driving_hours: float
    total_on_duty_hours: float
    total_off_duty_hours: float
    total_sleeper_hours: float
    total_distance_miles: float
    starting_cycle_used: float
    final_cycle_used: float
    cycle_hours_added: float
    days_count: int
    is_valid: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "totalDurationHours": round(self.total_duration_hours, 2),
            "totalDrivingHours": round(self.total_driving_hours, 2),
            "totalOnDutyHours": round(self.total_on_duty_hours, 2),
            "totalOffDutyHours": round(self.total_off_duty_hours, 2),
            "totalSleeperHours": round(self.total_sleeper_hours, 2),
            "totalDistanceMiles": round(self.total_distance_miles, 2),
            "startingCycleUsed": round(self.starting_cycle_used, 2),
            "finalCycleUsed": round(self.final_cycle_used, 2),
            "cycleHoursAdded": round(self.cycle_hours_added, 2),
            "daysCount": self.days_count,
            "isValid": self.is_valid,
        }


@dataclass
class HOSState:
    """
    Authoritative state of the driver's HOS clocks.
    Updated strictly upon scheduling each duty segment.
    """
    driving_hours_since_reset: float = 0.0
    duty_hours_since_reset: float = 0.0
    window_start: Optional[datetime] = None
    cycle_hours_used: float = 0.0
    driving_hours_since_break: float = 0.0
    miles_since_fuel: float = 0.0
    last_status: Optional[DutyStatus] = None
    current_time: Optional[datetime] = None
    current_miles: float = 0.0

    @property
    def window_elapsed_hours(self) -> float:
        if self.window_start is None or self.current_time is None:
            return 0.0
        elapsed_seconds = (self.current_time - self.window_start).total_seconds()
        return max(0.0, elapsed_seconds / 3600.0)

    @property
    def remaining_drive_today(self) -> float:
        return max(0.0, 11.0 - self.driving_hours_since_reset)

    @property
    def remaining_window_today(self) -> float:
        return max(0.0, 14.0 - self.window_elapsed_hours)

    @property
    def remaining_drive_until_break(self) -> float:
        return max(0.0, 8.0 - self.driving_hours_since_break)

    @property
    def remaining_cycle(self) -> float:
        return max(0.0, 70.0 - self.cycle_hours_used)

    @property
    def miles_until_fuel(self) -> float:
        return max(0.0, 1000.0 - self.miles_since_fuel)


@dataclass
class TripPlan:
    """Complete planned trip with segments, stops, daily logs, and validation."""
    segments: List[DutySegment]
    stops: List[Stop]
    daily_schedules: List[DailySchedule]
    daily_logs: List[DailyLog]
    summary: TripSummary
    validation_result: Optional[ValidationResult] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segments": [s.to_dict() for s in self.segments],
            "stops": [s.to_dict() for s in self.stops],
            "dailySchedules": [ds.to_dict() for ds in self.daily_schedules],
            "dailyLogs": [dl.to_dict() for dl in self.daily_logs],
            "summary": self.summary.to_dict(),
            "validationResult": self.validation_result.to_dict() if self.validation_result else None,
        }
