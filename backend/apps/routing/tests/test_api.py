"""
Integration tests for POST /api/routes/plan/ endpoint.
"""

import re
import pytest
import responses
from rest_framework.test import APIClient
from rest_framework import status

from apps.routing.constants import NOMINATIM_BASE_URL, OSRM_BASE_URL


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def mock_all_providers():
    responses.add(
        responses.GET,
        f"{NOMINATIM_BASE_URL}/search?q=Dallas%2C+TX&format=jsonv2&addressdetails=1&limit=5",
        json=[{"lat": "32.7767", "lon": "-96.7970", "display_name": "Dallas, Texas", "type": "city"}],
        status=200,
    )
    responses.add(
        responses.GET,
        f"{NOMINATIM_BASE_URL}/search?q=Houston%2C+TX&format=jsonv2&addressdetails=1&limit=5",
        json=[{"lat": "29.7604", "lon": "-95.3698", "display_name": "Houston, Texas", "type": "city"}],
        status=200,
    )
    responses.add(
        responses.GET,
        f"{NOMINATIM_BASE_URL}/search?q=Atlanta%2C+GA&format=jsonv2&addressdetails=1&limit=5",
        json=[{"lat": "33.7490", "lon": "-84.3880", "display_name": "Atlanta, Georgia", "type": "city"}],
        status=200,
    )
    responses.add(
        responses.GET,
        re.compile(f"^{OSRM_BASE_URL}/route/v1/driving/.*"),
        json={
            "code": "Ok",
            "routes": [
                {
                    "distance": 1368500.0,
                    "duration": 46800.0,
                    "geometry": {"type": "LineString", "coordinates": [[-96.79, 32.77], [-84.38, 33.74]]},
                    "legs": [
                        {"distance": 387000.0, "duration": 13200.0, "steps": []},
                        {"distance": 981500.0, "duration": 33600.0, "steps": []},
                    ],
                }
            ],
            "waypoints": [],
        },
        status=200,
    )


@responses.activate
def test_15_valid_route_request(client, mock_all_providers):
    """TEST 15: Valid route planning API request."""
    payload = {
        "currentLocation": "Dallas, TX",
        "pickupLocation": "Houston, TX",
        "dropoffLocation": "Atlanta, GA",
    }
    response = client.post("/api/routes/plan/", payload, format="json")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "locations" in data
    assert "route" in data
    assert data["locations"]["current"]["displayName"] == "Dallas, Texas"
    assert data["locations"]["pickup"]["displayName"] == "Houston, Texas"
    assert data["locations"]["dropoff"]["displayName"] == "Atlanta, Georgia"
    assert len(data["route"]["legs"]) == 2
    assert data["route"]["totalDistanceMiles"] > 0
    assert data["route"]["totalDurationMinutes"] > 0


def test_16_missing_current_location(client):
    """TEST 16: Missing current location."""
    payload = {
        "pickupLocation": "Houston, TX",
        "dropoffLocation": "Atlanta, GA",
    }
    response = client.post("/api/routes/plan/", payload, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_17_missing_pickup_location(client):
    """TEST 17: Missing pickup location."""
    payload = {
        "currentLocation": "Dallas, TX",
        "dropoffLocation": "Atlanta, GA",
    }
    response = client.post("/api/routes/plan/", payload, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_18_missing_dropoff_location(client):
    """TEST 18: Missing dropoff location."""
    payload = {
        "currentLocation": "Dallas, TX",
        "pickupLocation": "Houston, TX",
    }
    response = client.post("/api/routes/plan/", payload, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


@responses.activate
def test_19_location_not_found(client):
    """TEST 19: Geocoding location not found returns 400 with LOCATION_NOT_FOUND."""
    responses.add(
        responses.GET,
        f"{NOMINATIM_BASE_URL}/search?q=NonExistentPlace12345&format=jsonv2&addressdetails=1&limit=5",
        json=[],
        status=200,
    )

    payload = {
        "currentLocation": "NonExistentPlace12345",
        "pickupLocation": "Houston, TX",
        "dropoffLocation": "Atlanta, GA",
    }
    response = client.post("/api/routes/plan/", payload, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["error"]["code"] == "LOCATION_NOT_FOUND"


@responses.activate
def test_20_no_route_found(client):
    """TEST 20: OSRM NoRoute returns 400 with NO_ROUTE_FOUND."""
    responses.add(
        responses.GET,
        f"{NOMINATIM_BASE_URL}/search?q=Dallas%2C+TX&format=jsonv2&addressdetails=1&limit=5",
        json=[{"lat": "32.7767", "lon": "-96.7970", "display_name": "Dallas, TX", "type": "city"}],
        status=200,
    )
    responses.add(
        responses.GET,
        f"{NOMINATIM_BASE_URL}/search?q=Hawaii&format=jsonv2&addressdetails=1&limit=5",
        json=[{"lat": "19.8968", "lon": "-155.5828", "display_name": "Hawaii", "type": "island"}],
        status=200,
    )
    responses.add(
        responses.GET,
        f"{NOMINATIM_BASE_URL}/search?q=Atlanta%2C+GA&format=jsonv2&addressdetails=1&limit=5",
        json=[{"lat": "33.7490", "lon": "-84.3880", "display_name": "Atlanta, GA", "type": "city"}],
        status=200,
    )
    responses.add(
        responses.GET,
        re.compile(f"^{OSRM_BASE_URL}/route/v1/driving/.*"),
        json={"code": "NoRoute", "message": "No route found"},
        status=200,
    )

    payload = {
        "currentLocation": "Dallas, TX",
        "pickupLocation": "Hawaii",
        "dropoffLocation": "Atlanta, GA",
    }
    response = client.post("/api/routes/plan/", payload, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["error"]["code"] == "NO_ROUTE_FOUND"


@responses.activate
def test_21_provider_error(client):
    """TEST 21: External provider error returns HTTP 502 with error code."""
    responses.add(
        responses.GET,
        f"{NOMINATIM_BASE_URL}/search?q=Dallas%2C+TX&format=jsonv2&addressdetails=1&limit=5",
        status=500,
    )

    payload = {
        "currentLocation": "Dallas, TX",
        "pickupLocation": "Houston, TX",
        "dropoffLocation": "Atlanta, GA",
    }
    response = client.post("/api/routes/plan/", payload, format="json")
    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    data = response.json()
    assert data["error"]["code"] == "GEOCODING_PROVIDER_ERROR"
