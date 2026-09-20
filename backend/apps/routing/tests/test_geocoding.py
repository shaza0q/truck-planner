"""
Unit tests for Nominatim geocoding client and service with mocked HTTP requests.
"""

import pytest
import responses
import requests

from apps.routing.constants import NOMINATIM_BASE_URL
from apps.routing.geocoding import NominatimClient, GeocodingService
from apps.routing.exceptions import (
    LocationNotFoundError,
    GeocodingProviderError,
    GeocodingRateLimitError,
)


@pytest.fixture
def nominatim_success_fixture():
    return [
        {
            "place_id": 123456,
            "lat": "32.7762719",
            "lon": "-96.7968559",
            "display_name": "Dallas, Dallas County, Texas, United States",
            "type": "city",
            "category": "boundary",
            "address": {
                "city": "Dallas",
                "county": "Dallas County",
                "state": "Texas",
                "country": "United States",
            },
        }
    ]


@responses.activate
def test_1_successful_geocode(nominatim_success_fixture):
    """TEST 1: Successful geocode."""
    responses.add(
        responses.GET,
        f"{NOMINATIM_BASE_URL}/search",
        json=nominatim_success_fixture,
        status=200,
    )

    service = GeocodingService()
    res = service.geocode("Dallas, TX")

    assert res.query == "Dallas, TX"
    assert res.display_name == "Dallas, Dallas County, Texas, United States"
    assert round(res.coordinate.latitude, 4) == 32.7763
    assert round(res.coordinate.longitude, 4) == -96.7969
    assert res.place_type == "city"
    assert res.address["state"] == "Texas"


@responses.activate
def test_2_empty_result_raises_location_not_found():
    """TEST 2: Empty geocoding result."""
    responses.add(
        responses.GET,
        f"{NOMINATIM_BASE_URL}/search",
        json=[],
        status=200,
    )

    service = GeocodingService()
    with pytest.raises(LocationNotFoundError) as exc_info:
        service.geocode("asdfghjkl123NonExistent")
    
    assert "asdfghjkl123NonExistent" in str(exc_info.value)
    assert exc_info.value.code == "LOCATION_NOT_FOUND"


@responses.activate
def test_3_malformed_provider_response():
    """TEST 3: Malformed provider response (missing lat/lon or bad JSON)."""
    responses.add(
        responses.GET,
        f"{NOMINATIM_BASE_URL}/search",
        json=[{"display_name": "Broken Place"}],  # Missing lat and lon
        status=200,
    )

    service = GeocodingService()
    with pytest.raises(GeocodingProviderError):
        service.geocode("Broken Place")


@responses.activate
def test_4_http_error():
    """TEST 4: Provider HTTP 500 server error."""
    responses.add(
        responses.GET,
        f"{NOMINATIM_BASE_URL}/search",
        status=500,
    )

    service = GeocodingService()
    with pytest.raises(GeocodingProviderError):
        service.geocode("Dallas, TX")


@responses.activate
def test_5_timeout_error():
    """TEST 5: Network timeout during geocoding."""
    responses.add(
        responses.GET,
        f"{NOMINATIM_BASE_URL}/search",
        body=requests.exceptions.Timeout("Connection timed out"),
    )

    service = GeocodingService()
    with pytest.raises(GeocodingProviderError):
        service.geocode("Dallas, TX")


@responses.activate
def test_6_rate_limit_429_response():
    """TEST 6: HTTP 429 Too Many Requests response."""
    responses.add(
        responses.GET,
        f"{NOMINATIM_BASE_URL}/search",
        status=429,
    )

    service = GeocodingService()
    with pytest.raises(GeocodingRateLimitError) as exc_info:
        service.geocode("Dallas, TX")
    
    assert exc_info.value.code == "GEOCODING_RATE_LIMIT"
