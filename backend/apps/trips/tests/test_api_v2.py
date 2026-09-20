"""
Integration tests for POST /api/trips/plan/ Phase 3 endpoint.
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
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [-96.7970, 32.7767],
                            [-95.3698, 29.7604],
                            [-84.3880, 33.7490],
                        ],
                    },
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
def test_api_trips_plan_success(client, mock_all_providers):
    """Test successful trip schedule generation via POST /api/trips/plan/."""
    payload = {
        "currentLocation": "Dallas, TX",
        "pickupLocation": "Houston, TX",
        "dropoffLocation": "Atlanta, GA",
        "cycleHoursUsed": 20.0,
    }
    response = client.post("/api/trips/plan/", payload, format="json")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "route" in data
    assert "summary" in data
    assert "segments" in data
    assert "stops" in data
    assert "dailyLogs" in data
    assert "validationResult" in data

    assert data["summary"]["isValid"] is True
    assert data["summary"]["totalDistanceMiles"] > 0
    assert data["summary"]["totalDrivingMinutes"] > 0
    assert data["summary"]["totalElapsedMinutes"] > data["summary"]["totalDrivingMinutes"]

    # Verify stops have coordinates
    assert len(data["stops"]) >= 2
    for s in data["stops"]:
        assert "coordinate" in s
        assert "type" in s


def test_api_trips_plan_missing_fields(client):
    """Test rejection when required fields are missing."""
    payload = {
        "currentLocation": "Dallas, TX",
    }
    response = client.post("/api/trips/plan/", payload, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_api_trips_plan_invalid_cycle_hours(client):
    """Test rejection when cycleHoursUsed > 70."""
    payload = {
        "currentLocation": "Dallas, TX",
        "pickupLocation": "Houston, TX",
        "dropoffLocation": "Atlanta, GA",
        "cycleHoursUsed": 75.0,
    }
    response = client.post("/api/trips/plan/", payload, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


@responses.activate
def test_api_trips_plan_location_not_found(client):
    """Test 400 when a location cannot be geocoded."""
    responses.add(
        responses.GET,
        f"{NOMINATIM_BASE_URL}/search?q=NonExistentCity9999&format=jsonv2&addressdetails=1&limit=5",
        json=[],
        status=200,
    )

    payload = {
        "currentLocation": "NonExistentCity9999",
        "pickupLocation": "Houston, TX",
        "dropoffLocation": "Atlanta, GA",
        "cycleHoursUsed": 10.0,
    }
    response = client.post("/api/trips/plan/", payload, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["error"]["code"] == "LOCATION_NOT_FOUND"
