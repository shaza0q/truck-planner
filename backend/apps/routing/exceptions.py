"""
Domain exceptions for Geocoding and Routing.
"""


class RoutingError(Exception):
    """Base exception for routing domain errors."""
    def __init__(self, message: str, code: str = "ROUTING_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class LocationNotFoundError(RoutingError):
    """Raised when a geocoding query cannot be resolved to any location."""
    def __init__(self, query: str):
        message = f"Could not find a location for '{query}'. Please try a more specific city, state, or address."
        super().__init__(message, code="LOCATION_NOT_FOUND")
        self.query = query


class GeocodingProviderError(RoutingError):
    """Raised when the geocoding provider fails or returns an error."""
    def __init__(self, message: str = "Geocoding service is temporarily unavailable. Please try again."):
        super().__init__(message, code="GEOCODING_PROVIDER_ERROR")


class GeocodingRateLimitError(RoutingError):
    """Raised when the geocoding provider returns 429 Too Many Requests."""
    def __init__(self, message: str = "Geocoding request rate limit exceeded. Please wait a moment and try again."):
        super().__init__(message, code="GEOCODING_RATE_LIMIT")


class NoRouteFoundError(RoutingError):
    """Raised when OSRM cannot find a drivable route between coordinates."""
    def __init__(self, message: str = "No drivable route could be found between the supplied locations."):
        super().__init__(message, code="NO_ROUTE_FOUND")


class RoutingProviderError(RoutingError):
    """Raised when the OSRM routing provider fails or encounters network errors."""
    def __init__(self, message: str = "Routing service is temporarily unavailable. Please try again."):
        super().__init__(message, code="ROUTING_PROVIDER_ERROR")
