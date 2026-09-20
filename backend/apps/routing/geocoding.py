"""
Geocoding client and service for Nominatim / OpenStreetMap.
Includes defensive response parsing, custom User-Agent, and error normalization.
"""

from typing import Optional, List, Dict, Any
import logging
import requests

from .constants import (
    NOMINATIM_BASE_URL,
    USER_AGENT,
    MAP_REQUEST_TIMEOUT_SECONDS,
)
from .models import Coordinate, GeocodedLocation
from .exceptions import (
    LocationNotFoundError,
    GeocodingProviderError,
    GeocodingRateLimitError,
)

logger = logging.getLogger(__name__)


class NominatimClient:
    """Low-level HTTP client for the OpenStreetMap Nominatim API."""

    def __init__(
        self,
        base_url: str = NOMINATIM_BASE_URL,
        user_agent: str = USER_AGENT,
        timeout_seconds: int = MAP_REQUEST_TIMEOUT_SECONDS,
    ):
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Sends a geocoding search request to Nominatim."""
        url = f"{self.base_url}/search"
        params = {
            "q": query,
            "format": "jsonv2",
            "addressdetails": "1",
            "limit": str(limit),
        }
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }

        logger.debug("[NominatimClient.search] Querying Nominatim: url=%s, q='%s'", url, query)
        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout_seconds,
            )
        except requests.exceptions.Timeout as e:
            logger.error("[NominatimClient.search] Request timed out for query '%s'", query)
            raise GeocodingProviderError("Geocoding request timed out.") from e
        except requests.exceptions.RequestException as e:
            logger.error("[NominatimClient.search] Network error for query '%s': %s", query, str(e))
            raise GeocodingProviderError(f"Geocoding network error: {str(e)}") from e

        if response.status_code == 429:
            logger.warning("[NominatimClient.search] Received HTTP 429 Too Many Requests from Nominatim")
            raise GeocodingRateLimitError()

        if response.status_code != 200:
            logger.error("[NominatimClient.search] Nominatim HTTP %d for query '%s'", response.status_code, query)
            raise GeocodingProviderError(
                f"Nominatim returned HTTP {response.status_code}."
            )

        try:
            data = response.json()
        except ValueError as e:
            logger.error("[NominatimClient.search] Failed to parse JSON response from Nominatim")
            raise GeocodingProviderError("Failed to parse Nominatim JSON response.") from e

        if not isinstance(data, list):
            logger.error("[NominatimClient.search] Invalid response structure from Nominatim (expected list)")
            raise GeocodingProviderError("Invalid response structure from Nominatim.")

        logger.debug("[NominatimClient.search] Received %d results from Nominatim for '%s'", len(data), query)
        return data


class GeocodingService:
    """High-level geocoding service returning normalized domain models."""

    def __init__(self, client: Optional[NominatimClient] = None):
        self.client = client or NominatimClient()

    def geocode(self, query: str) -> GeocodedLocation:
        """Geocodes a query string into a normalized GeocodedLocation domain object."""
        cleaned_query = (query or "").strip()
        logger.info("[GeocodingService.geocode] Geocoding query: '%s'", cleaned_query)
        if not cleaned_query:
            logger.warning("[GeocodingService.geocode] Empty or whitespace query provided")
            raise LocationNotFoundError(query)

        results = self.client.search(cleaned_query, limit=5)
        if not results:
            logger.warning("[GeocodingService.geocode] No results found for '%s'", cleaned_query)
            raise LocationNotFoundError(cleaned_query)

        # Defensively pick the first result
        best = results[0]
        try:
            raw_lat = float(best["lat"])
            raw_lon = float(best["lon"])
            coord = Coordinate(latitude=raw_lat, longitude=raw_lon)
            display_name = str(best.get("display_name", cleaned_query))
            place_type = best.get("type") or best.get("category")
            address = best.get("address") if isinstance(best.get("address"), dict) else None

            logger.info(
                "[GeocodingService.geocode] Resolved '%s' -> (%f, %f) ['%s']",
                cleaned_query, raw_lat, raw_lon, display_name
            )

            return GeocodedLocation(
                query=cleaned_query,
                display_name=display_name,
                coordinate=coord,
                place_type=place_type,
                address=address,
            )
        except (KeyError, ValueError, TypeError) as e:
            logger.error("[GeocodingService.geocode] Malformed geocoding item: %s", str(e))
            raise GeocodingProviderError(f"Malformed geocoding result: {str(e)}") from e
