"""
Constants and environment-driven defaults for Geocoding and Routing services.
"""

import os

# External service URLs (configurable via environment variables)
NOMINATIM_BASE_URL: str = os.getenv("NOMINATIM_BASE_URL", "https://nominatim.openstreetmap.org").rstrip("/")
OSRM_BASE_URL: str = os.getenv("OSRM_BASE_URL", "http://router.project-osrm.org").rstrip("/")

USER_AGENT: str = os.getenv(
    "NOMINATIM_USER_AGENT",
    os.getenv("ROUTING_USER_AGENT", "SpotterTripPlanner/1.0 (contact: admin@spotterplanner.local)")
)
MAP_REQUEST_TIMEOUT_SECONDS: int = int(os.getenv("MAP_REQUEST_TIMEOUT_SECONDS", "10"))

# Rate-limiting / courteous delay between Nominatim queries (seconds)
NOMINATIM_REQUEST_DELAY_SECONDS: float = float(os.getenv("NOMINATIM_REQUEST_DELAY_SECONDS", "1.0"))

# Unit conversion factors
METERS_TO_MILES: float = 0.000621371
SECONDS_TO_MINUTES: float = 1.0 / 60.0
SECONDS_TO_HOURS: float = 1.0 / 3600.0
