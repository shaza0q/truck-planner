"""
Integration tests for POST /api/hos/plan/ API endpoint.
"""

import pytest
from rest_framework.test import APIClient
from rest_framework import status


@pytest.fixture
def client():
    return APIClient()


def test_api_plan_valid_request(client):
    """Test successful plan generation via POST /api/hos/plan/."""
    payload = {
        "currentLocation": "Dallas, TX",
        "pickupLocation": "Houston, TX",
        "dropoffLocation": "Atlanta, GA",
        "currentCycleUsed": 42.0,
        "mockRoute": {
            "distanceMiles": 850.0,
            "drivingMinutes": 780
        }
    }
    response = client.post("/api/hos/plan/", payload, format="json")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "segments" in data
    assert "stops" in data
    assert "dailyLogs" in data
    assert "summary" in data
    assert "validationResult" in data
    assert data["summary"]["isValid"] is True
    assert data["validationResult"]["valid"] is True


def test_api_plan_invalid_cycle_hours(client):
    """Test API rejection when currentCycleUsed > 70."""
    payload = {
        "currentLocation": "Dallas, TX",
        "pickupLocation": "Houston, TX",
        "dropoffLocation": "Atlanta, GA",
        "currentCycleUsed": 75.0,
        "mockRoute": {
            "distanceMiles": 850.0,
            "drivingMinutes": 780
        }
    }
    response = client.post("/api/hos/plan/", payload, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "error" in data


def test_api_plan_cycle_exhausted(client):
    """Test API rejection when currentCycleUsed == 70 (no on-duty work can be scheduled)."""
    payload = {
        "currentLocation": "Dallas, TX",
        "pickupLocation": "Houston, TX",
        "dropoffLocation": "Atlanta, GA",
        "currentCycleUsed": 70.0,
        "mockRoute": {
            "distanceMiles": 850.0,
            "drivingMinutes": 780
        }
    }
    response = client.post("/api/hos/plan/", payload, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["error"]["code"] == "INSUFFICIENT_CYCLE_HOURS"


def test_api_plan_missing_fields(client):
    """Test API rejection when required fields are missing."""
    payload = {
        "currentLocation": "Dallas, TX",
        # Missing pickup, dropoff, etc.
    }
    response = client.post("/api/hos/plan/", payload, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
