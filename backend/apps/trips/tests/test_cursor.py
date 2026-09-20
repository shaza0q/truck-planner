"""
Unit tests for RouteCursor geometry interpolation engine.
"""

import pytest
from apps.routing.models import Coordinate, GeocodedLocation, RouteLeg, RoutePlan
from apps.trips.cursor import RouteCursor, haversine_distance_meters


@pytest.fixture
def sample_route():
    """
    Creates a sample 3-point route:
    Point 0 (Dallas): 32.7767, -96.7970
    Point 1 (Houston): 29.7604, -95.3698
    Point 2 (Atlanta): 33.7490, -84.3880
    """
    p0 = GeocodedLocation("Dallas, TX", "Dallas, TX", Coordinate(32.7767, -96.7970))
    p1 = GeocodedLocation("Houston, TX", "Houston, TX", Coordinate(29.7604, -95.3698))
    p2 = GeocodedLocation("Atlanta, GA", "Atlanta, GA", Coordinate(33.7490, -84.3880))

    leg1_dist_m = haversine_distance_meters(p0.coordinate, p1.coordinate)
    leg2_dist_m = haversine_distance_meters(p1.coordinate, p2.coordinate)
    total_dist_m = leg1_dist_m + leg2_dist_m

    legs = [
        RouteLeg(
            type="CURRENT_TO_PICKUP",
            origin=p0,
            destination=p1,
            distance_meters=leg1_dist_m,
            duration_seconds=14400.0,
            geometry={},
        ),
        RouteLeg(
            type="PICKUP_TO_DROPOFF",
            origin=p1,
            destination=p2,
            distance_meters=leg2_dist_m,
            duration_seconds=36000.0,
            geometry={},
        ),
    ]

    geometry = {
        "type": "LineString",
        "coordinates": [
            [-96.7970, 32.7767],  # Dallas
            [-95.3698, 29.7604],  # Houston
            [-84.3880, 33.7490],  # Atlanta
        ],
    }

    return RoutePlan(
        origin=p0,
        pickup=p1,
        destination=p2,
        legs=legs,
        total_distance_meters=total_dist_m,
        total_duration_seconds=50400.0,
        geometry=geometry,
    )


def test_1_position_at_route_start(sample_route):
    """TEST 1: Position at route start (distance = 0)."""
    cursor = RouteCursor(sample_route)
    pos = cursor.position_at_distance(0.0)

    assert abs(pos.latitude - sample_route.origin.coordinate.latitude) < 1e-4
    assert abs(pos.longitude - sample_route.origin.coordinate.longitude) < 1e-4


def test_2_position_at_route_end(sample_route):
    """TEST 2: Position at route end (distance = total_distance)."""
    cursor = RouteCursor(sample_route)
    pos = cursor.position_at_distance(sample_route.total_distance_meters)

    assert abs(pos.latitude - sample_route.destination.coordinate.latitude) < 1e-4
    assert abs(pos.longitude - sample_route.destination.coordinate.longitude) < 1e-4


def test_3_position_in_middle_of_route(sample_route):
    """TEST 3: Position in the middle of a route."""
    cursor = RouteCursor(sample_route)
    mid_dist = sample_route.total_distance_meters / 2.0
    pos = cursor.position_at_distance(mid_dist)

    # Must be valid coordinate between endpoints
    assert -90.0 <= pos.latitude <= 90.0
    assert -180.0 <= pos.longitude <= 180.0


def test_4_distance_exactly_at_geometry_vertex(sample_route):
    """TEST 4: Distance exactly at a geometry vertex (Houston pickup)."""
    cursor = RouteCursor(sample_route)
    leg1_dist = sample_route.legs[0].distance_meters
    pos = cursor.position_at_distance(leg1_dist)

    assert abs(pos.latitude - sample_route.pickup.coordinate.latitude) < 1e-3
    assert abs(pos.longitude - sample_route.pickup.coordinate.longitude) < 1e-3


def test_5_distance_between_two_geometry_points_interpolates(sample_route):
    """TEST 5: Distance between two vertices interpolates smoothly."""
    cursor = RouteCursor(sample_route)
    half_leg1 = sample_route.legs[0].distance_meters / 2.0
    pos = cursor.position_at_distance(half_leg1)

    p0 = sample_route.origin.coordinate
    p1 = sample_route.pickup.coordinate

    # Interpolated latitude should be strictly between p0 and p1
    min_lat, max_lat = min(p0.latitude, p1.latitude), max(p0.latitude, p1.latitude)
    assert min_lat <= pos.latitude <= max_lat


def test_6_correct_longitude_latitude_ordering(sample_route):
    """TEST 6: Correct longitude/latitude ordering (GeoJSON [lon, lat] -> Coordinate(lat, lon))."""
    cursor = RouteCursor(sample_route)
    # First point must have lat = 32.7767 and lon = -96.7970
    assert abs(cursor.points[0].latitude - 32.7767) < 1e-4
    assert abs(cursor.points[0].longitude - (-96.7970)) < 1e-4


def test_7_route_leg_detection(sample_route):
    """TEST 7: Route leg detection (CURRENT_TO_PICKUP before pickup, PICKUP_TO_DROPOFF after)."""
    cursor = RouteCursor(sample_route)
    leg1_dist = sample_route.legs[0].distance_meters

    prog_before = cursor.progress_at_distance(leg1_dist * 0.5)
    assert prog_before.leg_type == "CURRENT_TO_PICKUP"

    prog_after = cursor.progress_at_distance(leg1_dist + 1000.0)
    assert prog_after.leg_type == "PICKUP_TO_DROPOFF"


def test_8_distance_beyond_route_end_is_safe(sample_route):
    """TEST 8: Distance beyond route end clamps to final destination."""
    cursor = RouteCursor(sample_route)
    pos = cursor.position_at_distance(sample_route.total_distance_meters + 500000.0)

    assert abs(pos.latitude - sample_route.destination.coordinate.latitude) < 1e-4
    assert abs(pos.longitude - sample_route.destination.coordinate.longitude) < 1e-4


def test_9_zero_length_route():
    """TEST 9: Zero-length route behavior."""
    p0 = GeocodedLocation("Origin", "Origin", Coordinate(30.0, -97.0))
    zero_route = RoutePlan(
        origin=p0,
        pickup=p0,
        destination=p0,
        legs=[],
        total_distance_meters=0.0,
        total_duration_seconds=0.0,
        geometry={"type": "LineString", "coordinates": [[-97.0, 30.0]]},
    )
    cursor = RouteCursor(zero_route)
    pos = cursor.position_at_distance(0.0)
    assert pos.latitude == 30.0
    assert pos.longitude == -97.0


def test_10_multi_leg_route_progress_fraction(sample_route):
    """TEST 10: Multi-leg route progress fraction calculation."""
    cursor = RouteCursor(sample_route)
    prog = cursor.progress_at_distance(sample_route.total_distance_meters * 0.5)
    assert abs(prog.fraction_of_route - 0.5) < 0.01
