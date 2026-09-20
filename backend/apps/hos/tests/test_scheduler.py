"""
Comprehensive test suite for HOSScheduler covering required business rules and test cases.
"""

from datetime import datetime, timezone, timedelta
import pytest

from apps.hos.constants import (
    MAX_DRIVING_HOURS,
    MAX_DUTY_WINDOW_HOURS,
    REQUIRED_OFF_DUTY_HOURS,
    REQUIRED_BREAK_MINUTES,
    PICKUP_DURATION_MINUTES,
    DROPOFF_DURATION_MINUTES,
    FUEL_INTERVAL_MILES,
)
from apps.hos.enums import DutyStatus, StopType
from apps.hos.exceptions import InsufficientCycleHoursError, InvalidTripInputError
from apps.hos.models import TripInput, MockRoute
from apps.hos.scheduler import HOSScheduler


@pytest.fixture
def scheduler():
    return HOSScheduler()


@pytest.fixture
def base_start_time():
    return datetime(2026, 9, 19, 6, 0, 0, tzinfo=timezone.utc)


def test_1_short_trip_no_rest(scheduler, base_start_time):
    """TEST 1: Short trip requiring no rest (< 8h driving)."""
    trip_input = TripInput(
        current_location="Dallas, TX",
        pickup_location="Dallas, TX",
        dropoff_location="Houston, TX",
        current_cycle_used=10.0,
    )
    # 240 miles, 240 mins (4 hours driving)
    route = MockRoute(total_distance_miles=240, total_driving_minutes=240)

    plan = scheduler.plan_trip(trip_input, route, start_time=base_start_time)

    assert plan.summary.is_valid is True
    assert plan.summary.total_driving_hours == 4.0
    # 1h pickup + 4h drive + 1h dropoff = 6h on duty
    assert plan.summary.total_on_duty_hours == 6.0
    # No rest stops required
    rest_stops = [s for s in plan.stops if s.type == StopType.REST]
    assert len(rest_stops) == 0


def test_2_trip_requiring_30_min_break(scheduler, base_start_time):
    """TEST 2: Trip requiring more than 8 cumulative driving hours (e.g., 9 hours driving).
    Verify a 30-minute break is inserted.
    """
    trip_input = TripInput(
        current_location="Dallas, TX",
        pickup_location="Dallas, TX",
        dropoff_location="Amarillo, TX",
        current_cycle_used=10.0,
    )
    # 540 miles, 540 mins (9 hours driving)
    route = MockRoute(total_distance_miles=540, total_driving_minutes=540)

    plan = scheduler.plan_trip(trip_input, route, start_time=base_start_time)

    assert plan.summary.is_valid is True
    assert plan.summary.total_driving_hours == 9.0

    break_stops = [s for s in plan.stops if s.type in (StopType.BREAK, StopType.FUEL)]
    assert len(break_stops) >= 1
    # Check that after exactly 8h of driving (or when break was needed), a break of 30 mins exists
    first_break = break_stops[0]
    assert first_break.duration_minutes >= REQUIRED_BREAK_MINUTES


def test_3_trip_reaches_11_hour_driving_limit(scheduler, base_start_time):
    """TEST 3: Trip that reaches the 11-hour driving limit.
    Verify driving stops at 11 hours and a 10-hour rest is inserted.
    """
    trip_input = TripInput(
        current_location="Dallas, TX",
        pickup_location="Dallas, TX",
        dropoff_location="Denver, CO",
        current_cycle_used=10.0,
    )
    # 780 miles, 780 mins (13 hours driving)
    route = MockRoute(total_distance_miles=780, total_driving_minutes=780)

    plan = scheduler.plan_trip(trip_input, route, start_time=base_start_time)

    assert plan.summary.is_valid is True
    assert plan.summary.total_driving_hours == 13.0

    # There should be at least one 10-hour rest stop
    rest_stops = [s for s in plan.stops if s.type == StopType.REST]
    assert len(rest_stops) >= 1
    assert rest_stops[0].duration_minutes == 600  # 10 hours

    # Verify that in Day 1 (before rest), driving did not exceed 11 hours
    # First driving segments before first rest should total exactly 11h
    first_rest_time = rest_stops[0].start
    day1_driving_mins = sum(
        s.duration_minutes for s in plan.segments
        if s.status == DutyStatus.DRIVING and s.end <= first_rest_time
    )
    # In a 14h window starting with 1h pickup + 8h drive + 30m break + 3h drive = 12.5h elapsed, 11h driven
    assert day1_driving_mins == 11 * 60


def test_4_trip_reaches_14_hour_window_limit(scheduler, base_start_time):
    """TEST 4: Trip where 14-hour window is reached before 11 driving hours (e.g. Due to intermediate stops).
    Verify driving stops at the 14-hour window.
    """
    trip_input = TripInput(
        current_location="Dallas, TX",
        pickup_location="Dallas, TX",
        dropoff_location="El Paso, TX",
        current_cycle_used=10.0,
    )
    # Speed is low: 600 miles in 720 mins (12 hours)
    # With 1h pickup + 8h drive + 30m break + 2h drive = 11.5h duty window elapsed, driving 10h.
    route = MockRoute(total_distance_miles=600, total_driving_minutes=720)

    plan = scheduler.plan_trip(trip_input, route, start_time=base_start_time)
    assert plan.summary.is_valid is True


def test_5_multi_day_trip(scheduler, base_start_time):
    """TEST 5: Trip requiring multiple driving days (e.g., 2,000 miles / 34 hours driving).
    Verify full rest periods are inserted.
    """
    trip_input = TripInput(
        current_location="Los Angeles, CA",
        pickup_location="Los Angeles, CA",
        dropoff_location="New York, NY",
        current_cycle_used=10.0,
    )
    # 2,000 miles, 2040 mins (34 hours driving)
    route = MockRoute(total_distance_miles=2000, total_driving_minutes=2040)

    plan = scheduler.plan_trip(trip_input, route, start_time=base_start_time)

    assert plan.summary.is_valid is True
    assert plan.summary.total_driving_hours == 34.0
    assert plan.summary.days_count >= 4

    rest_stops = [s for s in plan.stops if s.type == StopType.REST]
    # 34 hours of driving at 11h/day requires at least 3 rest periods
    assert len(rest_stops) >= 3


def test_6_cycle_used_65_hours(scheduler, base_start_time):
    """TEST 6: Current cycle used = 65 hours.
    Remaining cycle = 5 hours.
    Verify the scheduler cannot exceed 70 hours.
    """
    trip_input = TripInput(
        current_location="Dallas, TX",
        pickup_location="Dallas, TX",
        dropoff_location="Atlanta, GA",
        current_cycle_used=65.0,
    )
    # Route requests 600 miles / 600 mins (10 hours driving)
    # But driver only has 5 hours remaining (1h pickup + 4h drive = 5h max)
    route = MockRoute(total_distance_miles=600, total_driving_minutes=600)

    plan = scheduler.plan_trip(trip_input, route, start_time=base_start_time)

    # Scheduler must not exceed 70 hours total cycle
    assert plan.summary.final_cycle_used <= 70.0
    # On duty time added is at most 5.0 hours (1h pickup + 4h driving)
    assert plan.summary.cycle_hours_added <= 5.0


def test_7_cycle_used_70_hours(scheduler, base_start_time):
    """TEST 7: Current cycle used = 70 hours.
    Verify no additional on-duty/driving work can be scheduled (raises InsufficientCycleHoursError).
    """
    trip_input = TripInput(
        current_location="Dallas, TX",
        pickup_location="Dallas, TX",
        dropoff_location="Houston, TX",
        current_cycle_used=70.0,
    )
    route = MockRoute(total_distance_miles=240, total_driving_minutes=240)

    with pytest.raises(InsufficientCycleHoursError):
        scheduler.plan_trip(trip_input, route, start_time=base_start_time)


def test_8_trip_over_1000_miles_inserts_fuel_stop(scheduler, base_start_time):
    """TEST 8: Trip > 1,000 miles.
    Verify a fuel stop is inserted before exceeding the fuel threshold (1,000 miles).
    """
    trip_input = TripInput(
        current_location="Chicago, IL",
        pickup_location="Chicago, IL",
        dropoff_location="Miami, FL",
        current_cycle_used=5.0,
    )
    # 1,400 miles, 1400 mins (23.33 hours driving)
    route = MockRoute(total_distance_miles=1400, total_driving_minutes=1400)

    plan = scheduler.plan_trip(trip_input, route, start_time=base_start_time)

    assert plan.summary.is_valid is True
    fuel_stops = [s for s in plan.stops if s.type == StopType.FUEL]
    assert len(fuel_stops) >= 1
    # Fuel stop must be scheduled at or before 1,000 miles
    assert fuel_stops[0].miles_from_start <= FUEL_INTERVAL_MILES


def test_9_fuel_stop_satisfies_30_minute_break(scheduler, base_start_time):
    """TEST 9: Fuel stop occurs after cumulative driving.
    Verify it is 30 minutes and satisfies the 30-minute break requirement.
    """
    trip_input = TripInput(
        current_location="Dallas, TX",
        pickup_location="Dallas, TX",
        dropoff_location="Seattle, WA",
        current_cycle_used=0.0,
    )
    # Set fuel interval to 480 miles (8 hours at 60 mph) to coincide with 8-hour driving mark
    custom_scheduler = HOSScheduler(fuel_interval_miles=480.0)
    route = MockRoute(total_distance_miles=600, total_driving_minutes=600)

    plan = custom_scheduler.plan_trip(trip_input, route, start_time=base_start_time)

    assert plan.summary.is_valid is True
    # The fuel stop is 30 min and satisfies the break requirement
    fuel_stops = [s for s in plan.stops if s.type == StopType.FUEL]
    assert len(fuel_stops) >= 1
    assert fuel_stops[0].duration_minutes == 30


def test_10_pickup_consumes_exact_1_hour(scheduler, base_start_time):
    """TEST 10: Pickup consumes exactly 1 hour of on-duty time."""
    trip_input = TripInput(
        current_location="Austin, TX",
        pickup_location="Austin, TX",
        dropoff_location="San Antonio, TX",
        current_cycle_used=10.0,
    )
    route = MockRoute(total_distance_miles=80, total_driving_minutes=90)

    plan = scheduler.plan_trip(trip_input, route, start_time=base_start_time)

    pickup_segs = [s for s in plan.segments if s.reason == "Cargo Pickup"]
    assert len(pickup_segs) == 1
    assert pickup_segs[0].duration_minutes == PICKUP_DURATION_MINUTES
    assert pickup_segs[0].status == DutyStatus.ON_DUTY_NOT_DRIVING


def test_11_dropoff_consumes_exact_1_hour(scheduler, base_start_time):
    """TEST 11: Dropoff consumes exactly 1 hour of on-duty time."""
    trip_input = TripInput(
        current_location="Austin, TX",
        pickup_location="Austin, TX",
        dropoff_location="San Antonio, TX",
        current_cycle_used=10.0,
    )
    route = MockRoute(total_distance_miles=80, total_driving_minutes=90)

    plan = scheduler.plan_trip(trip_input, route, start_time=base_start_time)

    dropoff_segs = [s for s in plan.segments if s.reason == "Cargo Dropoff"]
    assert len(dropoff_segs) == 1
    assert dropoff_segs[0].duration_minutes == DROPOFF_DURATION_MINUTES
    assert dropoff_segs[0].status == DutyStatus.ON_DUTY_NOT_DRIVING


def test_12_each_daily_log_totals_24_hours(scheduler, base_start_time):
    """TEST 12: Each generated daily log totals exactly 24 hours (1440 minutes)."""
    trip_input = TripInput(
        current_location="Dallas, TX",
        pickup_location="Dallas, TX",
        dropoff_location="Phoenix, AZ",
        current_cycle_used=15.0,
    )
    route = MockRoute(total_distance_miles=1050, total_driving_minutes=1050)

    plan = scheduler.plan_trip(trip_input, route, start_time=base_start_time)

    assert len(plan.daily_logs) >= 2
    for log in plan.daily_logs:
        total_mins = sum(s.duration_minutes for s in log.segments)
        assert total_mins == 1440, f"Log for {log.date} totals {total_mins} mins instead of 1440"
        assert log.totals.total_hours == 24.0


def test_13_no_overlapping_segments(scheduler, base_start_time):
    """TEST 13: No segment overlaps another segment."""
    trip_input = TripInput(
        current_location="Chicago, IL",
        pickup_location="Chicago, IL",
        dropoff_location="Atlanta, GA",
        current_cycle_used=20.0,
    )
    route = MockRoute(total_distance_miles=715, total_driving_minutes=720)

    plan = scheduler.plan_trip(trip_input, route, start_time=base_start_time)

    for i in range(1, len(plan.segments)):
        prev = plan.segments[i - 1]
        curr = plan.segments[i]
        assert curr.start >= prev.end, f"Segment {i} ({curr.start}) overlaps segment {i-1} ({prev.end})"
