"""
Independent unit tests for HOSValidator verifying accurate detection of violations.
"""

from datetime import datetime, timezone, timedelta
import pytest

from apps.hos.constants import FUEL_INTERVAL_MILES
from apps.hos.enums import DutyStatus, ViolationCode
from apps.hos.models import (
    TripPlan,
    DutySegment,
    TripSummary,
    DailyLog,
    DailyTotals,
    MockRoute,
    TripInput,
)
from apps.hos.validators import HOSValidator


@pytest.fixture
def validator():
    return HOSValidator()


@pytest.fixture
def base_time():
    return datetime(2026, 9, 19, 6, 0, 0, tzinfo=timezone.utc)


def create_mock_plan(segments, starting_cycle=10.0, daily_logs=None):
    total_drive = sum(s.duration_minutes for s in segments if s.status == DutyStatus.DRIVING) / 60.0
    total_on_duty = sum(s.duration_minutes for s in segments if s.status.is_on_duty) / 60.0
    total_off_duty = sum(s.duration_minutes for s in segments if s.status == DutyStatus.OFF_DUTY) / 60.0
    total_miles = sum(s.miles for s in segments)
    
    summary = TripSummary(
        total_duration_hours=10.0,
        total_driving_hours=total_drive,
        total_on_duty_hours=total_on_duty,
        total_off_duty_hours=total_off_duty,
        total_sleeper_hours=0.0,
        total_distance_miles=total_miles,
        starting_cycle_used=starting_cycle,
        final_cycle_used=starting_cycle + total_on_duty,
        cycle_hours_added=total_on_duty,
        days_count=1,
        is_valid=True,
    )
    
    if daily_logs is None:
        # Default mock 24h log
        daily_logs = [
            DailyLog(
                date="2026-09-19",
                total_miles=total_miles,
                segments=[
                    DutySegment(
                        status=DutyStatus.OFF_DUTY,
                        start=datetime(2026, 9, 19, 0, 0, tzinfo=timezone.utc),
                        end=datetime(2026, 9, 20, 0, 0, tzinfo=timezone.utc),
                        duration_minutes=1440,
                        location="Dallas, TX",
                    )
                ],
                totals=DailyTotals(off_duty=24.0),
            )
        ]
        
    return TripPlan(
        segments=segments,
        stops=[],
        daily_schedules=[],
        daily_logs=daily_logs,
        summary=summary,
    )


def test_14_validator_detects_12_hour_driving_segment(validator, base_time):
    """TEST 14: Validator detects an intentionally invalid 12-hour driving segment."""
    segments = [
        DutySegment(
            status=DutyStatus.ON_DUTY_NOT_DRIVING,
            start=base_time,
            end=base_time + timedelta(hours=1),
            duration_minutes=60,
            location="Dallas, TX",
            reason="Cargo Pickup",
        ),
        # Invalid 12-hour continuous driving segment
        DutySegment(
            status=DutyStatus.DRIVING,
            start=base_time + timedelta(hours=1),
            end=base_time + timedelta(hours=13),
            duration_minutes=720,
            location="Highway",
            miles=720.0,
            reason="Driving",
        ),
    ]
    plan = create_mock_plan(segments)
    res = validator.validate(plan)

    assert res.valid is False
    violation_codes = [v.code for v in res.violations]
    assert ViolationCode.EXCEEDED_11_HOUR_DRIVING_LIMIT in violation_codes


def test_15_validator_detects_driving_past_14_hour_window(validator, base_time):
    """TEST 15: Validator detects driving after the 14-hour duty window."""
    segments = [
        DutySegment(
            status=DutyStatus.ON_DUTY_NOT_DRIVING,
            start=base_time,
            end=base_time + timedelta(hours=1),
            duration_minutes=60,
            location="Dallas, TX",
            reason="Cargo Pickup",
        ),
        # 13.5 hours of other on-duty/off-duty work (total window elapsed = 14.5 hours)
        DutySegment(
            status=DutyStatus.ON_DUTY_NOT_DRIVING,
            start=base_time + timedelta(hours=1),
            end=base_time + timedelta(hours=14, minutes=30),
            duration_minutes=810,
            location="Yard",
            reason="Waiting/Dock work",
        ),
        # Driving scheduled after 14.5 hours from window start
        DutySegment(
            status=DutyStatus.DRIVING,
            start=base_time + timedelta(hours=14, minutes=30),
            end=base_time + timedelta(hours=16),
            duration_minutes=90,
            location="Highway",
            miles=90.0,
            reason="Driving",
        ),
    ]
    plan = create_mock_plan(segments)
    res = validator.validate(plan)

    assert res.valid is False
    violation_codes = [v.code for v in res.violations]
    assert ViolationCode.DRIVING_PAST_14_HOUR_WINDOW in violation_codes


def test_16_validator_detects_exceeded_70_hour_cycle(validator, base_time):
    """TEST 16: Validator detects >70 cycle hours."""
    # Starting cycle used is 68 hours, then driver works 4 hours (total = 72 hours)
    segments = [
        DutySegment(
            status=DutyStatus.ON_DUTY_NOT_DRIVING,
            start=base_time,
            end=base_time + timedelta(hours=1),
            duration_minutes=60,
            location="Dallas, TX",
            reason="Cargo Pickup",
        ),
        DutySegment(
            status=DutyStatus.DRIVING,
            start=base_time + timedelta(hours=1),
            end=base_time + timedelta(hours=4),
            duration_minutes=180,
            location="Highway",
            miles=180.0,
            reason="Driving",
        ),
    ]
    plan = create_mock_plan(segments, starting_cycle=68.0)
    res = validator.validate(plan)

    assert res.valid is False
    violation_codes = [v.code for v in res.violations]
    assert ViolationCode.EXCEEDED_70_HOUR_CYCLE in violation_codes


def test_17_validator_detects_missing_30_min_break(validator, base_time):
    """TEST 17: Validator detects >8 driving hours without a qualifying break."""
    segments = [
        DutySegment(
            status=DutyStatus.ON_DUTY_NOT_DRIVING,
            start=base_time,
            end=base_time + timedelta(hours=1),
            duration_minutes=60,
            location="Dallas, TX",
            reason="Cargo Pickup",
        ),
        # 8.5 hours driving without any break
        DutySegment(
            status=DutyStatus.DRIVING,
            start=base_time + timedelta(hours=1),
            end=base_time + timedelta(hours=9, minutes=30),
            duration_minutes=510,
            location="Highway",
            miles=510.0,
            reason="Driving",
        ),
    ]
    plan = create_mock_plan(segments)
    res = validator.validate(plan)

    assert res.valid is False
    violation_codes = [v.code for v in res.violations]
    assert ViolationCode.MISSING_30_MIN_BREAK in violation_codes


def test_18_validator_detects_exceeded_fuel_interval(validator, base_time):
    """TEST 18: Validator detects fuel interval exceeding 1,000 miles."""
    segments = [
        DutySegment(
            status=DutyStatus.ON_DUTY_NOT_DRIVING,
            start=base_time,
            end=base_time + timedelta(hours=1),
            duration_minutes=60,
            location="Dallas, TX",
            reason="Cargo Pickup",
        ),
        # Continuous driving segment covering 1,100 miles without a fuel stop
        DutySegment(
            status=DutyStatus.DRIVING,
            start=base_time + timedelta(hours=1),
            end=base_time + timedelta(hours=6),
            duration_minutes=300,
            location="Highway",
            miles=1100.0,
            reason="Driving",
        ),
    ]
    plan = create_mock_plan(segments)
    res = validator.validate(plan)

    assert res.valid is False
    violation_codes = [v.code for v in res.violations]
    assert ViolationCode.EXCEEDED_FUEL_INTERVAL in violation_codes
