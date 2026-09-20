"""
Unit tests for individual HOS rules, state transitions, and constraints.
"""

from datetime import datetime, timezone, timedelta
import pytest

from apps.hos.constants import (
    MAX_DRIVING_MINUTES,
    MAX_DUTY_WINDOW_MINUTES,
    REQUIRED_OFF_DUTY_MINUTES,
    BREAK_THRESHOLD_DRIVING_MINUTES,
    REQUIRED_BREAK_MINUTES,
)
from apps.hos.enums import DutyStatus
from apps.hos.models import DutySegment, HOSState
from apps.hos.rules import (
    is_qualifying_reset,
    is_qualifying_break,
    apply_segment_to_state,
    calculate_available_driving_minutes,
)


def test_qualifying_reset():
    """Verify 10+ consecutive hours in OFF_DUTY or SLEEPER_BERTH qualifies as reset."""
    assert is_qualifying_reset(600, DutyStatus.OFF_DUTY) is True
    assert is_qualifying_reset(660, DutyStatus.SLEEPER_BERTH) is True
    assert is_qualifying_reset(599, DutyStatus.OFF_DUTY) is False
    assert is_qualifying_reset(600, DutyStatus.ON_DUTY_NOT_DRIVING) is False
    assert is_qualifying_reset(600, DutyStatus.DRIVING) is False


def test_qualifying_break():
    """Verify 30+ consecutive minutes of non-driving qualifies as break."""
    assert is_qualifying_break(30, DutyStatus.OFF_DUTY) is True
    assert is_qualifying_break(45, DutyStatus.SLEEPER_BERTH) is True
    assert is_qualifying_break(30, DutyStatus.ON_DUTY_NOT_DRIVING) is True
    assert is_qualifying_break(29, DutyStatus.OFF_DUTY) is False
    assert is_qualifying_break(30, DutyStatus.DRIVING) is False


def test_state_transition_duty_window_start():
    """Verify duty window starts on first on-duty / driving segment."""
    start_t = datetime(2026, 9, 19, 6, 0, 0, tzinfo=timezone.utc)
    state = HOSState(cycle_hours_used=10.0, current_time=start_t)
    assert state.window_start is None

    # Apply 1 hr pickup (on-duty)
    seg = DutySegment(
        status=DutyStatus.ON_DUTY_NOT_DRIVING,
        start=start_t,
        end=start_t + timedelta(hours=1),
        duration_minutes=60,
        location="Dallas, TX",
        reason="Pickup",
    )
    apply_segment_to_state(state, seg)

    assert state.window_start == start_t
    assert state.duty_hours_since_reset == 1.0
    assert state.cycle_hours_used == 11.0
    assert state.driving_hours_since_reset == 0.0


def test_state_transition_10h_reset_clears_clocks():
    """Verify 10-hour rest resets driving hours, duty window, and break clock."""
    start_t = datetime(2026, 9, 19, 6, 0, 0, tzinfo=timezone.utc)
    state = HOSState(
        driving_hours_since_reset=9.0,
        duty_hours_since_reset=11.0,
        window_start=start_t,
        cycle_hours_used=30.0,
        driving_hours_since_break=4.0,
        current_time=start_t + timedelta(hours=11),
    )

    rest_start = state.current_time
    rest_seg = DutySegment(
        status=DutyStatus.OFF_DUTY,
        start=rest_start,
        end=rest_start + timedelta(hours=10),
        duration_minutes=600,
        location="Rest Area",
        reason="Daily Rest",
    )
    apply_segment_to_state(state, rest_seg)

    assert state.driving_hours_since_reset == 0.0
    assert state.duty_hours_since_reset == 0.0
    assert state.driving_hours_since_break == 0.0
    assert state.window_start is None
    # Rest does not increase cycle hours
    assert state.cycle_hours_used == 30.0


def test_available_driving_minutes_bounded_by_14h_window():
    """Verify available driving is limited by the remaining 14h duty window."""
    start_t = datetime(2026, 9, 19, 6, 0, 0, tzinfo=timezone.utc)
    # Driver has been on duty for 8 hours (window elapsed = 8h), but only drove 2h
    state = HOSState(
        driving_hours_since_reset=2.0,
        duty_hours_since_reset=8.0,
        window_start=start_t,
        cycle_hours_used=10.0,
        driving_hours_since_break=0.0,
        current_time=start_t + timedelta(hours=8),
    )

    # 11h limit remaining: 9h (540 mins)
    # 14h window remaining: 14 - 8 = 6h (360 mins)
    avail = calculate_available_driving_minutes(state, remaining_trip_minutes=600, speed_mph=60.0)
    assert avail == 360  # Bounded by 14h window (6 hours)
