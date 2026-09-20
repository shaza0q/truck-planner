"""
Phase 5 Hardening & Edge-Case Test Suite.
Tests health check endpoint, input validation edge cases, error schemas, and replanning safety.
"""

from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework.test import APIClient
import pytest

from apps.routing.models import RoutePlan, RouteLeg, GeocodedLocation, Coordinate


@pytest.fixture
def api_client():
    return APIClient()


def create_mock_route() -> RoutePlan:
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
        query="Atlanta, GA",
        display_name="Atlanta, GA",
        coordinate=Coordinate(33.7490, -84.3880),
    )

    leg1 = RouteLeg(
        type="CURRENT_TO_PICKUP",
        origin=current_loc,
        destination=pickup_loc,
        distance_meters=380000.0,
        duration_seconds=14000.0,
        geometry={"type": "LineString", "coordinates": [[-96.7970, 32.7767], [-95.3698, 29.7604]]},
    )
    leg2 = RouteLeg(
        type="PICKUP_TO_DROPOFF",
        origin=pickup_loc,
        destination=dropoff_loc,
        distance_meters=1200000.0,
        duration_seconds=42000.0,
        geometry={"type": "LineString", "coordinates": [[-95.3698, 29.7604], [-84.3880, 33.7490]]},
    )

    return RoutePlan(
        origin=current_loc,
        pickup=pickup_loc,
        destination=dropoff_loc,
        legs=[leg1, leg2],
        total_distance_meters=1580000.0,
        total_duration_seconds=56000.0,
        geometry={"type": "LineString", "coordinates": [[-96.7970, 32.7767], [-95.3698, 29.7604], [-84.3880, 33.7490]]},
    )


def test_1_health_check_endpoint(api_client):
    """TEST 1: GET /api/health/ returns 200 OK and valid status payload."""
    url = reverse("health-check")
    response = api_client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data
    assert "version" in data


def test_2_empty_and_whitespace_locations_rejected(api_client):
    """TEST 2: Empty or whitespace-only location strings are rejected with validation error."""
    url = reverse("trips-plan")
    
    # Whitespace current location
    res1 = api_client.post(url, {
        "currentLocation": "   ",
        "pickupLocation": "Houston, TX",
        "dropoffLocation": "Atlanta, GA",
        "cycleHoursUsed": 10.0,
    }, format="json")
    assert res1.status_code == 400
    assert res1.json()["error"]["code"] == "VALIDATION_ERROR"

    # Empty pickup location
    res2 = api_client.post(url, {
        "currentLocation": "Dallas, TX",
        "pickupLocation": "",
        "dropoffLocation": "Atlanta, GA",
        "cycleHoursUsed": 10.0,
    }, format="json")
    assert res2.status_code == 400
    assert res2.json()["error"]["code"] == "VALIDATION_ERROR"

    # Whitespace dropoff location
    res3 = api_client.post(url, {
        "currentLocation": "Dallas, TX",
        "pickupLocation": "Houston, TX",
        "dropoffLocation": "\t \n",
        "cycleHoursUsed": 10.0,
    }, format="json")
    assert res3.status_code == 400
    assert res3.json()["error"]["code"] == "VALIDATION_ERROR"


def test_3_negative_and_excessive_cycle_hours_rejected(api_client):
    """TEST 3: Cycle hours < 0 or > 70 are rejected with clear validation error."""
    url = reverse("trips-plan")

    # Negative cycle
    res1 = api_client.post(url, {
        "currentLocation": "Dallas, TX",
        "pickupLocation": "Houston, TX",
        "dropoffLocation": "Atlanta, GA",
        "cycleHoursUsed": -5.0,
    }, format="json")
    assert res1.status_code == 400
    assert "between 0.0 and 70.0" in res1.json()["error"]["message"]

    # Cycle > 70
    res2 = api_client.post(url, {
        "currentLocation": "Dallas, TX",
        "pickupLocation": "Houston, TX",
        "dropoffLocation": "Atlanta, GA",
        "cycleHoursUsed": 75.5,
    }, format="json")
    assert res2.status_code == 400
    assert "between 0.0 and 70.0" in res2.json()["error"]["message"]


@patch("apps.trips.views.TripRoutingService.plan_trip_route")
def test_4_cycle_boundary_zero_is_accepted(mock_route_service, api_client):
    """TEST 4: Cycle hours of exactly 0.0 is accepted."""
    mock_route_service.return_value = create_mock_route()
    url = reverse("trips-plan")

    res = api_client.post(url, {
        "currentLocation": "Dallas, TX",
        "pickupLocation": "Houston, TX",
        "dropoffLocation": "Atlanta, GA",
        "cycleHoursUsed": 0.0,
    }, format="json")
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["startingCycleUsed"] == 0.0


@patch("apps.trips.views.TripRoutingService.plan_trip_route")
def test_5_cycle_boundary_70_raises_insufficient_cycle_hours(mock_route_service, api_client):
    """TEST 5: Starting with exactly 70.0 cycle used triggers INSUFFICIENT_CYCLE_HOURS."""
    mock_route_service.return_value = create_mock_route()
    url = reverse("trips-plan")

    res = api_client.post(url, {
        "currentLocation": "Dallas, TX",
        "pickupLocation": "Houston, TX",
        "dropoffLocation": "Atlanta, GA",
        "cycleHoursUsed": 70.0,
    }, format="json")
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INSUFFICIENT_CYCLE_HOURS"


@patch("apps.trips.views.TripRoutingService.plan_trip_route")
def test_6_replanning_independence(mock_route_service, api_client):
    """TEST 6: Multiple consecutive requests produce completely independent schedules."""
    mock_route_service.return_value = create_mock_route()
    url = reverse("trips-plan")

    # Request A with 10h cycle
    res_a = api_client.post(url, {
        "currentLocation": "Dallas, TX",
        "pickupLocation": "Houston, TX",
        "dropoffLocation": "Atlanta, GA",
        "cycleHoursUsed": 10.0,
    }, format="json")
    assert res_a.status_code == 200

    # Request B with 30h cycle
    res_b = api_client.post(url, {
        "currentLocation": "Dallas, TX",
        "pickupLocation": "Houston, TX",
        "dropoffLocation": "Atlanta, GA",
        "cycleHoursUsed": 30.0,
    }, format="json")
    assert res_b.status_code == 200

    data_a = res_a.json()
    data_b = res_b.json()

    assert data_a["summary"]["startingCycleUsed"] == 10.0
    assert data_b["summary"]["startingCycleUsed"] == 30.0
    assert data_a["summary"]["finalCycleUsed"] != data_b["summary"]["finalCycleUsed"]
