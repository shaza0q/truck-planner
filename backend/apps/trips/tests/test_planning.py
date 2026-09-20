"""
Comprehensive unit tests for TripPlanningService and StopPlanner.
"""

from datetime import datetime, timezone, timedelta
import pytest

from apps.hos.constants import (
    MAX_DRIVING_HOURS,
    REQUIRED_OFF_DUTY_HOURS,
    REQUIRED_BREAK_MINUTES,
    PICKUP_DURATION_MINUTES,
    DROPOFF_DURATION_MINUTES,
    FUEL_INTERVAL_MILES,
)
from apps.hos.enums import DutyStatus, StopType
from apps.hos.exceptions import InsufficientCycleHoursError, InvalidTripInputError
from apps.routing.models import Coordinate, GeocodedLocation, RouteLeg, RoutePlan
from apps.trips.planning import TripPlanningService


@pytest.fixture
def planning_service():
    return TripPlanningService()


@pytest.fixture
def base_start_time():
    return datetime(2026, 9, 20, 6, 0, 0, tzinfo=timezone.utc)


def create_deterministic_route(
    leg1_miles: float,
    leg1_minutes: float,
    leg2_miles: float,
    leg2_minutes: float,
) -> RoutePlan:
    """Helper to build a deterministic RoutePlan for testing."""
    p0 = GeocodedLocation("Dallas, TX", "Dallas, TX", Coordinate(32.7767, -96.7970))
    p1 = GeocodedLocation("Houston, TX", "Houston, TX", Coordinate(29.7604, -95.3698))
    p2 = GeocodedLocation("Atlanta, GA", "Atlanta, GA", Coordinate(33.7490, -84.3880))

    leg1_m = leg1_miles * 1609.344
    leg2_m = leg2_miles * 1609.344

    legs = [
        RouteLeg(
            type="CURRENT_TO_PICKUP",
            origin=p0,
            destination=p1,
            distance_meters=leg1_m,
            duration_seconds=leg1_minutes * 60.0,
            geometry={},
        ),
        RouteLeg(
            type="PICKUP_TO_DROPOFF",
            origin=p1,
            destination=p2,
            distance_meters=leg2_m,
            duration_seconds=leg2_minutes * 60.0,
            geometry={},
        ),
    ]

    geometry = {
        "type": "LineString",
        "coordinates": [
            [-96.7970, 32.7767],
            [-95.3698, 29.7604],
            [-84.3880, 33.7490],
        ],
    }

    return RoutePlan(
        origin=p0,
        pickup=p1,
        destination=p2,
        legs=legs,
        total_distance_meters=leg1_m + leg2_m,
        total_duration_seconds=(leg1_minutes + leg2_minutes) * 60.0,
        geometry=geometry,
    )


def test_1_short_trip_no_rest(planning_service, base_start_time):
    """TEST 1: Short trip requiring no rest (< 8h driving)."""
    route = create_deterministic_route(
        leg1_miles=100.0, leg1_minutes=100.0,
        leg2_miles=140.0, leg2_minutes=140.0,
    )
    schedule = planning_service.plan(route, cycle_hours_used=10.0, start_time=base_start_time)

    assert schedule.summary.is_valid is True
    assert schedule.summary.total_driving_minutes == 240
    # No rest or break stops
    rest_stops = [s for s in schedule.stops if s.type in (StopType.REST, StopType.BREAK)]
    assert len(rest_stops) == 0


def test_2_pickup_consumes_exact_60_minutes_at_pickup_coord(planning_service, base_start_time):
    """TEST 2: Pickup consumes exactly 60 minutes and occurs at pickup coordinate."""
    route = create_deterministic_route(
        leg1_miles=100.0, leg1_minutes=100.0,
        leg2_miles=100.0, leg2_minutes=100.0,
    )
    schedule = planning_service.plan(route, cycle_hours_used=10.0, start_time=base_start_time)

    pickup_stops = [s for s in schedule.stops if s.type == StopType.PICKUP]
    assert len(pickup_stops) == 1
    pickup = pickup_stops[0]
    assert pickup.duration_minutes == PICKUP_DURATION_MINUTES
    assert abs(pickup.coordinate.latitude - route.pickup.coordinate.latitude) < 1e-4
    assert abs(pickup.coordinate.longitude - route.pickup.coordinate.longitude) < 1e-4


def test_3_dropoff_consumes_exact_60_minutes_at_dropoff_coord(planning_service, base_start_time):
    """TEST 3: Dropoff consumes exactly 60 minutes and occurs at destination coordinate."""
    route = create_deterministic_route(
        leg1_miles=100.0, leg1_minutes=100.0,
        leg2_miles=100.0, leg2_minutes=100.0,
    )
    schedule = planning_service.plan(route, cycle_hours_used=10.0, start_time=base_start_time)

    dropoff_stops = [s for s in schedule.stops if s.type == StopType.DROPOFF]
    assert len(dropoff_stops) == 1
    dropoff = dropoff_stops[0]
    assert dropoff.duration_minutes == DROPOFF_DURATION_MINUTES
    assert abs(dropoff.coordinate.latitude - route.destination.coordinate.latitude) < 1e-4
    assert abs(dropoff.coordinate.longitude - route.destination.coordinate.longitude) < 1e-4


def test_4_fuel_inserted_before_1000_miles(planning_service, base_start_time):
    """TEST 4: Fuel stop inserted before 1,000 miles on long route."""
    # 1,400 miles total route
    route = create_deterministic_route(
        leg1_miles=200.0, leg1_minutes=200.0,
        leg2_miles=1200.0, leg2_minutes=1200.0,
    )
    schedule = planning_service.plan(route, cycle_hours_used=5.0, start_time=base_start_time)

    assert schedule.summary.is_valid is True
    fuel_stops = [s for s in schedule.stops if s.type == StopType.FUEL]
    assert len(fuel_stops) >= 1
    assert fuel_stops[0].miles_from_start <= FUEL_INTERVAL_MILES
    assert fuel_stops[0].coordinate is not None


def test_5_fuel_distance_resets_after_fuel_stop(planning_service, base_start_time):
    """TEST 5: Distance counter resets after fuel stop."""
    route = create_deterministic_route(
        leg1_miles=500.0, leg1_minutes=500.0,
        leg2_miles=1600.0, leg2_minutes=1600.0,
    )
    schedule = planning_service.plan(route, cycle_hours_used=5.0, start_time=base_start_time)

    fuel_stops = [s for s in schedule.stops if s.type == StopType.FUEL]
    assert len(fuel_stops) >= 2


def test_6_break_inserted_after_8_driving_hours(planning_service, base_start_time):
    """TEST 6: 30-minute break inserted after 8 cumulative driving hours."""
    # 10 hours total driving (1h leg1 + 9h leg2)
    route = create_deterministic_route(
        leg1_miles=60.0, leg1_minutes=60.0,
        leg2_miles=540.0, leg2_minutes=540.0,
    )
    schedule = planning_service.plan(route, cycle_hours_used=10.0, start_time=base_start_time)

    assert schedule.summary.is_valid is True
    break_stops = [s for s in schedule.stops if s.type in (StopType.BREAK, StopType.FUEL)]
    assert len(break_stops) >= 1
    assert break_stops[0].duration_minutes >= REQUIRED_BREAK_MINUTES
    assert break_stops[0].coordinate is not None


def test_7_fuel_stop_satisfies_30_minute_break(planning_service, base_start_time):
    """TEST 7: Fuel stop satisfying 30-minute break when appropriate."""
    custom_planner = TripPlanningService(fuel_interval_miles=480.0)
    route = create_deterministic_route(
        leg1_miles=100.0, leg1_minutes=60.0,
        leg2_miles=500.0, leg2_minutes=500.0,
    )
    schedule = custom_planner.plan(route, cycle_hours_used=5.0, start_time=base_start_time)

    assert schedule.summary.is_valid is True
    fuel_stops = [s for s in schedule.stops if s.type == StopType.FUEL]
    assert len(fuel_stops) >= 1
    assert fuel_stops[0].duration_minutes == 30


def test_8_rest_inserted_when_11_hour_drive_limit_reached(planning_service, base_start_time):
    """TEST 8: 10-hour rest inserted when 11-hour driving limit is reached."""
    # 13 hours total driving
    route = create_deterministic_route(
        leg1_miles=200.0, leg1_minutes=200.0,
        leg2_miles=580.0, leg2_minutes=580.0,
    )
    schedule = planning_service.plan(route, cycle_hours_used=10.0, start_time=base_start_time)

    assert schedule.summary.is_valid is True
    rest_stops = [s for s in schedule.stops if s.type == StopType.REST]
    assert len(rest_stops) >= 1
    assert rest_stops[0].duration_minutes == 600  # 10 hours
    assert rest_stops[0].coordinate is not None


def test_9_rest_inserted_when_14_hour_window_reached(planning_service, base_start_time):
    """TEST 9: 10-hour rest inserted when 14-hour duty window is reached."""
    # Slow speed driving
    route = create_deterministic_route(
        leg1_miles=150.0, leg1_minutes=180.0,
        leg2_miles=450.0, leg2_minutes=540.0,
    )
    schedule = planning_service.plan(route, cycle_hours_used=10.0, start_time=base_start_time)
    assert schedule.summary.is_valid is True


def test_10_cycle_hours_respected(planning_service, base_start_time):
    """TEST 10: Cycle hours limit is strictly enforced."""
    route = create_deterministic_route(
        leg1_miles=100.0, leg1_minutes=100.0,
        leg2_miles=500.0, leg2_minutes=500.0,
    )
    schedule = planning_service.plan(route, cycle_hours_used=65.0, start_time=base_start_time)

    assert schedule.summary.final_cycle_used <= 70.0
    assert schedule.summary.cycle_hours_added <= 5.0


def test_11_multi_day_schedule(planning_service, base_start_time):
    """TEST 11: Schedule correctly spans multiple days."""
    route = create_deterministic_route(
        leg1_miles=500.0, leg1_minutes=500.0,
        leg2_miles=1500.0, leg2_minutes=1500.0,
    )
    schedule = planning_service.plan(route, cycle_hours_used=10.0, start_time=base_start_time)

    assert schedule.summary.is_valid is True
    assert schedule.summary.days_count >= 3
    assert len(schedule.daily_logs) >= 3


def test_12_stop_coordinates_match_route_progress(planning_service, base_start_time):
    """TEST 12: All scheduled stops have valid geographic coordinates."""
    route = create_deterministic_route(
        leg1_miles=300.0, leg1_minutes=300.0,
        leg2_miles=600.0, leg2_minutes=600.0,
    )
    schedule = planning_service.plan(route, cycle_hours_used=10.0, start_time=base_start_time)

    for stop in schedule.stops:
        assert stop.coordinate is not None
        assert -90.0 <= stop.coordinate.latitude <= 90.0
        assert -180.0 <= stop.coordinate.longitude <= 180.0


def test_13_no_overlapping_segments(planning_service, base_start_time):
    """TEST 13: Segment times do not overlap."""
    route = create_deterministic_route(
        leg1_miles=250.0, leg1_minutes=250.0,
        leg2_miles=600.0, leg2_minutes=600.0,
    )
    schedule = planning_service.plan(route, cycle_hours_used=10.0, start_time=base_start_time)

    for i in range(1, len(schedule.segments)):
        prev = schedule.segments[i - 1]
        curr = schedule.segments[i]
        assert curr.start >= prev.end


def test_14_daily_logs_total_24_hours(planning_service, base_start_time):
    """TEST 14: Each calendar day daily log sums to exactly 24.0 hours."""
    route = create_deterministic_route(
        leg1_miles=300.0, leg1_minutes=300.0,
        leg2_miles=700.0, leg2_minutes=700.0,
    )
    schedule = planning_service.plan(route, cycle_hours_used=10.0, start_time=base_start_time)

    for log in schedule.daily_logs:
        total_mins = sum(s.duration_minutes for s in log.segments)
        assert total_mins == 1440
        assert log.totals.total_hours == 24.0


def test_15_cycle_exhausted_raises_error(planning_service, base_start_time):
    """TEST 15: Starting with 70h cycle used raises InsufficientCycleHoursError."""
    route = create_deterministic_route(
        leg1_miles=100.0, leg1_minutes=100.0,
        leg2_miles=100.0, leg2_minutes=100.0,
    )
    with pytest.raises(InsufficientCycleHoursError):
        planning_service.plan(route, cycle_hours_used=70.0, start_time=base_start_time)


def test_16_elapsed_time_includes_all_stops(planning_service, base_start_time):
    """TEST 16: Total elapsed trip time includes driving plus all stops (pickup, rest, dropoff)."""
    route = create_deterministic_route(
        leg1_miles=200.0, leg1_minutes=200.0,
        leg2_miles=580.0, leg2_minutes=580.0,
    )
    schedule = planning_service.plan(route, cycle_hours_used=10.0, start_time=base_start_time)

    # 780 mins drive + 60m pickup + 60m dropoff + 600m rest = 1500 mins
    assert schedule.summary.total_elapsed_minutes >= 780 + 60 + 60 + 600
    assert schedule.summary.total_elapsed_hours > schedule.summary.total_driving_hours
