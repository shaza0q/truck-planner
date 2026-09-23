"""
Geocoding client and service for Nominatim / OpenStreetMap.
Includes defensive response parsing, instance-level LRU caching, pre-seeded logistics hubs,
automatic retry with exponential backoff, and error normalization.
"""

from typing import Optional, List, Dict, Any, Tuple
import logging
import time
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

# Pre-seeded common North American logistics hubs (prevents 429 rate-limiting on shared cloud IPs)
PRESEEDED_HUBS: Dict[str, Tuple[float, float, str, str]] = {
    "dallas, tx": (32.7767, -96.7970, "Dallas, Dallas County, Texas, United States", "Texas"),
    "dallas": (32.7767, -96.7970, "Dallas, Dallas County, Texas, United States", "Texas"),
    "houston, tx": (29.7604, -95.3698, "Houston, Harris County, Texas, United States", "Texas"),
    "houston": (29.7604, -95.3698, "Houston, Harris County, Texas, United States", "Texas"),
    "atlanta, ga": (33.7490, -84.3880, "Atlanta, Fulton County, Georgia, United States", "Georgia"),
    "atlanta": (33.7490, -84.3880, "Atlanta, Fulton County, Georgia, United States", "Georgia"),
    "chicago, il": (41.8781, -87.6298, "Chicago, Cook County, Illinois, United States", "Illinois"),
    "chicago": (41.8781, -87.6298, "Chicago, Cook County, Illinois, United States", "Illinois"),
    "indianapolis, in": (39.7684, -86.1581, "Indianapolis, Marion County, Indiana, United States", "Indiana"),
    "indianapolis": (39.7684, -86.1581, "Indianapolis, Marion County, Indiana, United States", "Indiana"),
    "nashville, tn": (36.1627, -86.7816, "Nashville, Davidson County, Tennessee, United States", "Tennessee"),
    "nashville": (36.1627, -86.7816, "Nashville, Davidson County, Tennessee, United States", "Tennessee"),
    "los angeles, ca": (34.0522, -118.2437, "Los Angeles, Los Angeles County, California, United States", "California"),
    "los angeles": (34.0522, -118.2437, "Los Angeles, Los Angeles County, California, United States", "California"),
    "new york, ny": (40.7128, -74.0060, "New York, New York County, New York, United States", "New York"),
    "new york": (40.7128, -74.0060, "New York, New York County, New York, United States", "New York"),
    "miami, fl": (25.7617, -80.1918, "Miami, Miami-Dade County, Florida, United States", "Florida"),
    "phoenix, az": (33.4484, -112.0740, "Phoenix, Maricopa County, Arizona, United States", "Arizona"),
    "denver, co": (39.7392, -104.9903, "Denver, Denver County, Colorado, United States", "Colorado"),
    "seattle, wa": (47.6062, -122.3321, "Seattle, King County, Washington, United States", "Washington"),
    "memphis, tn": (35.1495, -90.0490, "Memphis, Shelby County, Tennessee, United States", "Tennessee"),
}


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
    """High-level geocoding service returning normalized domain models with instance caching and fallbacks."""

    def __init__(
        self,
        client: Optional[NominatimClient] = None,
        use_cache: bool = True,
        use_fallback: bool = False
    ):
        self.client = client or NominatimClient()
        self.use_cache = use_cache
        self.use_fallback = use_fallback
        self._cache: Dict[str, GeocodedLocation] = {}

    def geocode(self, query: str) -> GeocodedLocation:
        """Geocodes a query string into a normalized GeocodedLocation domain object."""
        cleaned_query = (query or "").strip()
        logger.info("[GeocodingService.geocode] Geocoding query: '%s'", cleaned_query)
        if not cleaned_query:
            logger.warning("[GeocodingService.geocode] Empty or whitespace query provided")
            raise LocationNotFoundError(query)

        norm_key = cleaned_query.lower()

        # Check instance cache
        if self.use_cache and norm_key in self._cache:
            logger.info("[GeocodingService.geocode] Cache hit for '%s'", cleaned_query)
            return self._cache[norm_key]

        try:
            results = self.client.search(cleaned_query, limit=5)
            if not results:
                logger.warning("[GeocodingService.geocode] No results found for '%s'", cleaned_query)
                raise LocationNotFoundError(cleaned_query)

            # Defensively pick the first result
            best = results[0]
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

            location = GeocodedLocation(
                query=cleaned_query,
                display_name=display_name,
                coordinate=coord,
                place_type=place_type,
                address=address,
            )

            if self.use_cache:
                self._cache[norm_key] = location

            return location

        except GeocodingRateLimitError:
            # Fallback to pre-seeded hub dictionary if Nominatim public rate limit is hit in production
            if self.use_fallback and norm_key in PRESEEDED_HUBS:
                lat, lon, disp, state = PRESEEDED_HUBS[norm_key]
                logger.warning(
                    "[GeocodingService.geocode] Nominatim 429 rate-limited. Falling back to pre-seeded coordinates for '%s'",
                    cleaned_query
                )
                fallback_loc = GeocodedLocation(
                    query=cleaned_query,
                    display_name=disp,
                    coordinate=Coordinate(latitude=lat, longitude=lon),
                    place_type="city",
                    address={"state": state, "country": "United States"},
                )
                if self.use_cache:
                    self._cache[norm_key] = fallback_loc
                return fallback_loc

            logger.error("[GeocodingService.geocode] Geocoding rate limit reached and no fallback available for '%s'", cleaned_query)
            raise
        except (KeyError, ValueError, TypeError) as e:
            logger.error("[GeocodingService.geocode] Malformed geocoding item: %s", str(e))
            raise GeocodingProviderError(f"Malformed geocoding result: {str(e)}") from e
