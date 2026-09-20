"""
Unit tests for OSRM client and service with mocked HTTP responses.
"""

import re
import pytest
import responses

from apps.routing.constants import OSRM_BASE_URL, METERS_TO_MILES, SECONDS_TO_MINUTES
from apps.routing.models import Coordinate, GeocodedLocation
from apps.routing.osrm import OSRMClient, OSRMService
from apps.routing.exceptions import NoRouteFoundError, RoutingProviderError


@pytest.fixture
def sample_locations():
    return {
        "current": GeocodedLocation(
            query="Dallas, TX",
            display_name="Dallas, TX",
            coordinate=Coordinate(latitude=32.7767, longitude=-96.7970),
        ),
        "pickup": GeocodedLocation(
            query="Houston, TX",
            display_name="Houston, TX",
            coordinate=Coordinate(latitude=29.7604, longitude=-95.3698),
        ),
        "dropoff": GeocodedLocation(
            query="Atlanta, GA",
            display_name="Atlanta, GA",
            coordinate=Coordinate(latitude=33.7490, longitude=-84.3880),
        ),
    }


@pytest.fixture
def osrm_success_fixture():
    return {
        "code": "Ok",
        "routes": [
            {
                "distance": 1368500.0,  # ~850.35 miles
                "duration": 46800.0,    # ~780 minutes (13 hours)
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [-96.7970, 32.7767],
                        [-95.3698, 29.7604],
                        [-84.3880, 33.7490],
                    ],
                },
                "legs": [
                    {
                        "distance": 387000.0,  # ~240.47 miles
                        "duration": 13200.0,   # ~220 minutes
                        "steps": [
                            {
                                "name": "I-45 S",
                                "distance": 387000.0,
                                "duration": 13200.0,
                                "maneuver": {"type": "depart", "modifier": "straight"},
                            }
                        ],
                    },
                    {
                        "distance": 981500.0,  # ~609.88 miles
                        "duration": 33600.0,   # ~560 minutes
                        "steps": [
                            {
                                "name": "I-10 E / I-85 N",
                                "distance": 981500.0,
                                "duration": 33600.0,
                                "maneuver": {"type": "turn", "modifier": "right"},
                            }
                        ],
                    },
                ],
            }
        ],
        "waypoints": [
            {"name": "Dallas", "location": [-96.7970, 32.7767]},
            {"name": "Houston", "location": [-95.3698, 29.7604]},
            {"name": "Atlanta", "location": [-84.3880, 33.7490]},
        ],
    }


@responses.activate
def test_7_successful_osrm_route(sample_locations, osrm_success_fixture):
    """TEST 7: Successful OSRM route parsing."""
    responses.add(
        responses.GET,
        re.compile(f"^{OSRM_BASE_URL}/route/v1/driving/.*"),
        json=osrm_success_fixture,
        status=200,
    )

    service = OSRMService()
    plan = service.route(
        origin=sample_locations["current"],
        pickup=sample_locations["pickup"],
        destination=sample_locations["dropoff"],
    )

    assert plan.total_distance_meters == 1368500.0
    assert plan.total_duration_seconds == 46800.0
    assert len(plan.legs) == 2
    assert plan.geometry["type"] == "LineString"
    assert len(plan.geometry["coordinates"]) == 3


@responses.activate
def test_8_osrm_no_route(sample_locations):
    """TEST 8: OSRM returns NoRoute (e.g. islands or unroutable points)."""
    responses.add(
        responses.GET,
        re.compile(f"^{OSRM_BASE_URL}/route/v1/driving/.*"),
        json={"code": "NoRoute", "message": "No route found"},
        status=200,
    )

    service = OSRMService()
    with pytest.raises(NoRouteFoundError) as exc_info:
        service.route(
            origin=sample_locations["current"],
            pickup=sample_locations["pickup"],
            destination=sample_locations["dropoff"],
        )
    assert exc_info.value.code == "NO_ROUTE_FOUND"


@responses.activate
def test_9_osrm_provider_http_error(sample_locations):
    """TEST 9: OSRM HTTP 500 server error."""
    responses.add(
        responses.GET,
        re.compile(f"^{OSRM_BASE_URL}/route/v1/driving/.*"),
        status=500,
    )

    service = OSRMService()
    with pytest.raises(RoutingProviderError):
        service.route(
            origin=sample_locations["current"],
            pickup=sample_locations["pickup"],
            destination=sample_locations["dropoff"],
        )


@responses.activate
def test_10_osrm_malformed_response(sample_locations):
    """TEST 10: Malformed OSRM JSON response."""
    responses.add(
        responses.GET,
        re.compile(f"^{OSRM_BASE_URL}/route/v1/driving/.*"),
        json={"code": "Ok", "routes": []},  # Empty routes array
        status=200,
    )

    service = OSRMService()
    with pytest.raises(NoRouteFoundError):
        service.route(
            origin=sample_locations["current"],
            pickup=sample_locations["pickup"],
            destination=sample_locations["dropoff"],
        )


@responses.activate
def test_11_coordinate_order_in_osrm_request(sample_locations, osrm_success_fixture):
    """TEST 11: Verify coordinates are passed in {longitude},{latitude} format."""
    expected_url_pattern = re.compile(
        f"^{OSRM_BASE_URL}/route/v1/driving/-96.797000,32.776700;-95.369800,29.760400;-84.388000,33.749000"
    )

    responses.add(
        responses.GET,
        expected_url_pattern,
        json=osrm_success_fixture,
        status=200,
    )

    client = OSRMClient()
    coords = [
        sample_locations["current"].coordinate,
        sample_locations["pickup"].coordinate,
        sample_locations["dropoff"].coordinate,
    ]
    data = client.get_route(coords)
    assert data["code"] == "Ok"


def test_12_meters_to_miles_conversion():
    """TEST 12: Verify accurate meters to miles conversion."""
    meters = 1609.344  # Exactly 1 mile
    miles = meters * METERS_TO_MILES
    assert round(miles, 3) == 1.0


def test_13_seconds_to_minutes_conversion():
    """TEST 13: Verify accurate seconds to minutes conversion."""
    seconds = 3600.0  # 60 minutes
    minutes = seconds * SECONDS_TO_MINUTES
    assert minutes == 60.0


@responses.activate
def test_14_route_leg_extraction(sample_locations, osrm_success_fixture):
    """TEST 14: Verify extraction of Leg 1 (Current->Pickup) and Leg 2 (Pickup->Dropoff)."""
    responses.add(
        responses.GET,
        re.compile(f"^{OSRM_BASE_URL}/route/v1/driving/.*"),
        json=osrm_success_fixture,
        status=200,
    )

    service = OSRMService()
    plan = service.route(
        origin=sample_locations["current"],
        pickup=sample_locations["pickup"],
        destination=sample_locations["dropoff"],
    )

    assert len(plan.legs) == 2

    leg1 = plan.legs[0]
    assert leg1.type == "CURRENT_TO_PICKUP"
    assert leg1.origin.query == "Dallas, TX"
    assert leg1.destination.query == "Houston, TX"
    assert round(leg1.distance_miles, 1) == 240.5
    assert round(leg1.duration_minutes, 1) == 220.0

    leg2 = plan.legs[1]
    assert leg2.type == "PICKUP_TO_DROPOFF"
    assert leg2.origin.query == "Houston, TX"
    assert leg2.destination.query == "Atlanta, GA"
    assert round(leg2.distance_miles, 1) == 609.9
    assert round(leg2.duration_minutes, 1) == 560.0
