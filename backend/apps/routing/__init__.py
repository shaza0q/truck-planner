"""
Routing package.
"""

from .constants import (
    NOMINATIM_BASE_URL,
    OSRM_BASE_URL,
    USER_AGENT,
    MAP_REQUEST_TIMEOUT_SECONDS,
    METERS_TO_MILES,
    SECONDS_TO_MINUTES,
    SECONDS_TO_HOURS,
)
from .models import (
    Coordinate,
    GeocodedLocation,
    RouteStep,
    RouteLeg,
    RoutePlan,
)
from .exceptions import (
    RoutingError,
    LocationNotFoundError,
    GeocodingProviderError,
    GeocodingRateLimitError,
    NoRouteFoundError,
    RoutingProviderError,
)
from .geocoding import NominatimClient, GeocodingService
from .osrm import OSRMClient, OSRMService
from .services import TripRoutingService

__all__ = [
    "NOMINATIM_BASE_URL",
    "OSRM_BASE_URL",
    "USER_AGENT",
    "MAP_REQUEST_TIMEOUT_SECONDS",
    "METERS_TO_MILES",
    "SECONDS_TO_MINUTES",
    "SECONDS_TO_HOURS",
    "Coordinate",
    "GeocodedLocation",
    "RouteStep",
    "RouteLeg",
    "RoutePlan",
    "RoutingError",
    "LocationNotFoundError",
    "GeocodingProviderError",
    "GeocodingRateLimitError",
    "NoRouteFoundError",
    "RoutingProviderError",
    "NominatimClient",
    "GeocodingService",
    "OSRMClient",
    "OSRMService",
    "TripRoutingService",
]
