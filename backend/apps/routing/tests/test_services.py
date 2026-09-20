"""
Integration tests for TripRoutingService domain orchestrator.
"""

import re
import pytest
import responses

from apps.routing.constants import NOMINATIM_BASE_URL, OSRM_BASE_URL
from apps.routing.services import TripRoutingService


@pytest.fixture
def mock_external_services():
    # Nominatim mocks for 3 locations
    responses.add(
        responses.GET,
        f"{NOMINATIM_BASE_URL}/search?q=Dallas%2C+TX&format=jsonv2&addressdetails=1&limit=5",
        json=[{"lat": "32.7767", "lon": "-96.7970", "display_name": "Dallas, Texas, United States", "type": "city"}],
        status=200,
    )
    responses.add(
        responses.GET,
        f"{NOMINATIM_BASE_URL}/search?q=Houston%2C+TX&format=jsonv2&addressdetails=1&limit=5",
        json=[{"lat": "29.7604", "lon": "-95.3698", "display_name": "Houston, Texas, United States", "type": "city"}],
        status=200,
    )
    responses.add(
        responses.GET,
        f"{NOMINATIM_BASE_URL}/search?q=Atlanta%2C+GA&format=jsonv2&addressdetails=1&limit=5",
        json=[{"lat": "33.7490", "lon": "-84.3880", "display_name": "Atlanta, Georgia, United States", "type": "city"}],
        status=200,
    )

    # OSRM mock
    osrm_data = {
        "code": "Ok",
        "routes": [
            {
                "distance": 1368500.0,
                "duration": 46800.0,
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
                        "distance": 387000.0,
                        "duration": 13200.0,
                        "steps": [],
                    },
                    {
                        "distance": 981500.0,
                        "duration": 33600.0,
                        "steps": [],
                    },
                ],
            }
        ],
        "waypoints": [],
    }
    responses.add(
        responses.GET,
        re.compile(f"^{OSRM_BASE_URL}/route/v1/driving/.*"),
        json=osrm_data,
        status=200,
    )


@responses.activate
def test_trip_routing_service_full_flow(mock_external_services):
    """Verify TripRoutingService geocodes all 3 locations and produces 2 distinct legs."""
    service = TripRoutingService(request_delay_seconds=0.0)  # 0 delay for fast tests
    plan = service.plan_trip_route(
        current_location_query="Dallas, TX",
        pickup_location_query="Houston, TX",
        dropoff_location_query="Atlanta, GA",
    )

    assert plan.origin.display_name == "Dallas, Texas, United States"
    assert plan.pickup.display_name == "Houston, Texas, United States"
    assert plan.destination.display_name == "Atlanta, Georgia, United States"

    assert len(plan.legs) == 2
    assert plan.legs[0].type == "CURRENT_TO_PICKUP"
    assert plan.legs[1].type == "PICKUP_TO_DROPOFF"

    # Verify sum of legs equals total distance & duration
    sum_legs_dist_m = sum(leg.distance_meters for leg in plan.legs)
    assert abs(plan.total_distance_meters - sum_legs_dist_m) < 0.01

    sum_legs_dur_s = sum(leg.duration_seconds for leg in plan.legs)
    assert abs(plan.total_duration_seconds - sum_legs_dur_s) < 0.01

    # Verify geometry is preserved
    assert plan.geometry["type"] == "LineString"
    assert len(plan.geometry["coordinates"]) == 3
