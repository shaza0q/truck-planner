"""
Comprehensive unit tests for DailyLogBuilder and 24-hour FMCSA daily log invariants.
"""

from datetime import datetime, timezone, timedelta
import pytest

from apps.hos.enums import DutyStatus, StopType
from apps.hos.models import DutySegment
from apps.hos.daily_logs import DailyLogBuilder, split_segments_by_calendar_day
from apps.trips.planning import TripPlanningService
from apps.routing.models import RoutePlan, RouteLeg, GeocodedLocation, Coordinate


@pytest.fixture
def builder():
    return DailyLogBuilder()


@pytest.fixture
def base_time():
    return datetime(2026, 9, 20, 6, 0, 0, tzinfo=timezone.utc)


def create_deterministic_route(leg1_miles=100.0, leg1_minutes=100.0, leg2_miles=100.0, leg2_minutes=100.0) -> RoutePlan:
    current_loc = GeocodedLocation(
        query="Dallas, TX",
        display_name="Dallas, TX",
        coordinate=Coordinate(32.7767, -96.7970),
    )
    pickup_loc = GeocodedLocation(
        query="Houston, TX",
        display_name="Houston, TX",
        coordinate=Coordinate(29.7604, -95.3698),
    )
    dropoff_loc = GeocodedLocation(
        query="Austin, TX",
        display_name="Austin, TX",
        coordinate=Coordinate(30.2672, -97.7431),
    )

    leg1 = RouteLeg(
        type="CURRENT_TO_PICKUP",
        origin=current_loc,
        destination=pickup_loc,
        distance_meters=leg1_miles * 1609.344,
        duration_seconds=leg1_minutes * 60.0,
        geometry={
            "type": "LineString",
            "coordinates": [[-96.7970, 32.7767], [-95.3698, 29.7604]],
        },
    )
    leg2 = RouteLeg(
        type="PICKUP_TO_DROPOFF",
        origin=pickup_loc,
        destination=dropoff_loc,
        distance_meters=leg2_miles * 1609.344,
        duration_seconds=leg2_minutes * 60.0,
        geometry={
            "type": "LineString",
            "coordinates": [[-95.3698, 29.7604], [-97.7431, 30.2672]],
        },
    )

    return RoutePlan(
        origin=current_loc,
        pickup=pickup_loc,
        destination=dropoff_loc,
        legs=[leg1, leg2],
        total_distance_meters=(leg1_miles + leg2_miles) * 1609.344,
        total_duration_seconds=(leg1_minutes + leg2_minutes) * 60.0,
        geometry={
            "type": "LineString",
            "coordinates": [[-96.7970, 32.7767], [-95.3698, 29.7604], [-97.7431, 30.2672]],
        },
    )


def test_1_daily_log_covers_exactly_1440_minutes(builder, base_time):
    """TEST 1: Daily log accounts for exactly 1,440 minutes across 00:00 to 24:00."""
    segments = [
        DutySegment(
            status=DutyStatus.DRIVING,
            start=base_time,  # 06:00
            end=base_time + timedelta(hours=4),  # 10:00
            duration_minutes=240,
            location="Dallas, TX",
            miles=240.0,
            reason="Driving",
        ),
        DutySegment(
            status=DutyStatus.ON_DUTY_NOT_DRIVING,
            start=base_time + timedelta(hours=4),
            end=base_time + timedelta(hours=5),
            duration_minutes=60,
            location="Houston, TX",
            miles=0.0,
            reason="Cargo Pickup",
        ),
    ]

    logs = builder.build_logs(segments)
    assert len(logs) == 1
    log = logs[0]

    assert log.date == "2026-09-20"
    assert log.day_number == 1
    assert log.totals.total_minutes == 1440
    assert log.totals.total_hours == 24.0

    # Segments breakdown:
    # 00:00-06:00 Off duty (360m)
    # 06:00-10:00 Driving (240m)
    # 10:00-11:00 On duty pickup (60m)
    # 11:00-24:00 Off duty (780m)
    assert len(log.segments) == 4
    assert log.segments[0].start_minute == 0
    assert log.segments[0].end_minute == 360
    assert log.segments[0].status == DutyStatus.OFF_DUTY

    assert log.segments[1].start_minute == 360
    assert log.segments[1].end_minute == 600
    assert log.segments[1].status == DutyStatus.DRIVING

    assert log.segments[2].start_minute == 600
    assert log.segments[2].end_minute == 660
    assert log.segments[2].status == DutyStatus.ON_DUTY_NOT_DRIVING
    assert log.segments[2].event_type == "PICKUP"

    assert log.segments[3].start_minute == 660
    assert log.segments[3].end_minute == 1440
    assert log.segments[3].status == DutyStatus.OFF_DUTY


def test_2_no_gaps_and_no_overlaps_between_segments(builder, base_time):
    """TEST 2: Segments are contiguous with no gaps and no overlaps."""
    segments = [
        DutySegment(
            status=DutyStatus.DRIVING,
            start=base_time,
            end=base_time + timedelta(hours=2),
            duration_minutes=120,
            location="Highway",
            miles=120.0,
        ),
        DutySegment(
            status=DutyStatus.OFF_DUTY,
            start=base_time + timedelta(hours=2),
            end=base_time + timedelta(hours=2, minutes=30),
            duration_minutes=30,
            location="Rest Stop",
            miles=0.0,
            reason="30-minute Driving Break",
        ),
        DutySegment(
            status=DutyStatus.DRIVING,
            start=base_time + timedelta(hours=2, minutes=30),
            end=base_time + timedelta(hours=6),
            duration_minutes=210,
            location="Highway",
            miles=210.0,
        ),
    ]

    logs = builder.build_logs(segments)
    assert len(logs) == 1
    log = logs[0]

    for i in range(len(log.segments) - 1):
        assert log.segments[i].end_minute == log.segments[i + 1].start_minute
        assert log.segments[i].end == log.segments[i + 1].start


def test_3_driving_crossing_midnight_is_split(builder):
    """TEST 3: Driving segment from 22:00 to 02:00 is split cleanly at midnight."""
    night_start = datetime(2026, 9, 20, 22, 0, 0, tzinfo=timezone.utc)
    morning_end = datetime(2026, 9, 21, 2, 0, 0, tzinfo=timezone.utc)

    segments = [
        DutySegment(
            status=DutyStatus.DRIVING,
            start=night_start,
            end=morning_end,
            duration_minutes=240,
            location="Interstate 35",
            miles=240.0,
            reason="Driving",
        )
    ]

    logs = builder.build_logs(segments)
    assert len(logs) == 2

    # Day 1
    assert logs[0].date == "2026-09-20"
    assert logs[0].day_number == 1
    assert logs[0].totals.total_minutes == 1440
    assert logs[0].totals.driving_minutes == 120  # 22:00 to 24:00 (120 mins)
    assert logs[0].totals.off_duty_minutes == 1320
    assert logs[0].segments[-1].start_minute == 1320
    assert logs[0].segments[-1].end_minute == 1440
    assert logs[0].segments[-1].miles == 120.0

    # Day 2
    assert logs[1].date == "2026-09-21"
    assert logs[1].day_number == 2
    assert logs[1].totals.total_minutes == 1440
    assert logs[1].totals.driving_minutes == 120  # 00:00 to 02:00 (120 mins)
    assert logs[1].totals.off_duty_minutes == 1320
    assert logs[1].segments[0].start_minute == 0
    assert logs[1].segments[0].end_minute == 120
    assert logs[1].segments[0].miles == 120.0


def test_4_sleeper_rest_crossing_midnight_is_split(builder):
    """TEST 4: 10-hour sleeper berth from 20:00 to 06:00 is split cleanly."""
    rest_start = datetime(2026, 9, 20, 20, 0, 0, tzinfo=timezone.utc)
    rest_end = datetime(2026, 9, 21, 6, 0, 0, tzinfo=timezone.utc)

    segments = [
        DutySegment(
            status=DutyStatus.SLEEPER_BERTH,
            start=rest_start,
            end=rest_end,
            duration_minutes=600,
            location="Rest Area",
            miles=0.0,
            reason="Mandatory 10-hour Daily Reset",
        )
    ]

    logs = builder.build_logs(segments)
    assert len(logs) == 2

    # Day 1: 20:00 to 24:00 (4 hours = 240 mins)
    assert logs[0].totals.sleeper_berth_minutes == 240
    assert logs[0].totals.total_minutes == 1440

    # Day 2: 00:00 to 06:00 (6 hours = 360 mins)
    assert logs[1].totals.sleeper_berth_minutes == 360
    assert logs[1].totals.total_minutes == 1440

    # Total sleeper time across both days equals 10 hours (600 mins)
    assert logs[0].totals.sleeper_berth_minutes + logs[1].totals.sleeper_berth_minutes == 600


def test_5_operational_event_types_preserved(builder, base_time):
    """TEST 5: Operational event types (PICKUP, DROPOFF, FUEL, BREAK, REST) are correctly mapped."""
    segments = [
        DutySegment(
            status=DutyStatus.ON_DUTY_NOT_DRIVING,
            start=base_time,
            end=base_time + timedelta(minutes=60),
            duration_minutes=60,
            location="Houston, TX",
            reason="Cargo Pickup",
        ),
        DutySegment(
            status=DutyStatus.OFF_DUTY,
            start=base_time + timedelta(minutes=60),
            end=base_time + timedelta(minutes=90),
            duration_minutes=30,
            location="Rest Area",
            reason="30-minute Driving Break",
        ),
        DutySegment(
            status=DutyStatus.ON_DUTY_NOT_DRIVING,
            start=base_time + timedelta(minutes=90),
            end=base_time + timedelta(minutes=120),
            duration_minutes=30,
            location="Fuel Station",
            reason="Fuel Stop (1,000-mile interval)",
        ),
        DutySegment(
            status=DutyStatus.ON_DUTY_NOT_DRIVING,
            start=base_time + timedelta(minutes=120),
            end=base_time + timedelta(minutes=180),
            duration_minutes=60,
            location="Austin, TX",
            reason="Cargo Dropoff",
        ),
    ]

    logs = builder.build_logs(segments)
    assert len(logs) == 1
    events = [s.event_type for s in logs[0].segments if s.event_type]
    assert events == ["PICKUP", "BREAK", "FUEL", "DROPOFF"]


def test_6_integration_with_planning_service(base_time):
    """TEST 6: Real TripPlanningService output generates valid 24h daily logs with start/end minutes."""
    planner = TripPlanningService()
    route = create_deterministic_route(
        leg1_miles=150.0, leg1_minutes=150.0,
        leg2_miles=650.0, leg2_minutes=650.0,
    )
    schedule = planner.plan(route, cycle_hours_used=10.0, start_time=base_time)

    assert len(schedule.daily_logs) >= 2
    for log in schedule.daily_logs:
        assert log.totals.total_minutes == 1440
        assert log.totals.total_hours == 24.0
        assert log.segments[0].start_minute == 0
        assert log.segments[-1].end_minute == 1440
        
        # Verify JSON dictionary serialization includes Phase 4 fields
        d = log.to_dict()
        assert "dayNumber" in d
        assert "totals" in d
        assert "offDutyMinutes" in d["totals"]
        assert "totalMinutes" in d["totals"]
        assert d["totals"]["totalMinutes"] == 1440
        assert len(d["segments"]) > 0
        assert "startMinute" in d["segments"][0]
        assert "endMinute" in d["segments"][0]
        assert "startTime" in d["segments"][0]
        assert "endTime" in d["segments"][0]
