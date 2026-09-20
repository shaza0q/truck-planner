"""
Domain models for Geocoding and Route Planning.
Pure Python dataclasses with strong typing and serialization methods.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from .constants import METERS_TO_MILES, SECONDS_TO_MINUTES, SECONDS_TO_HOURS


@dataclass
class Coordinate:
    """Geographic coordinate with validation."""
    latitude: float
    longitude: float

    def __post_init__(self):
        if not (-90.0 <= self.latitude <= 90.0):
            raise ValueError(f"Latitude must be between -90 and 90. Received: {self.latitude}")
        if not (-180.0 <= self.longitude <= 180.0):
            raise ValueError(f"Longitude must be between -180 and 180. Received: {self.longitude}")

    def to_osrm_format(self) -> str:
        """Returns coordinate formatted as {longitude},{latitude} for OSRM API."""
        return f"{self.longitude:.6f},{self.latitude:.6f}"

    def to_dict(self) -> Dict[str, float]:
        return {
            "latitude": round(self.latitude, 6),
            "longitude": round(self.longitude, 6),
        }


@dataclass
class GeocodedLocation:
    """Normalized geocoded location from Nominatim / OSM."""
    query: str
    display_name: str
    coordinate: Coordinate
    place_type: Optional[str] = None
    address: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "displayName": self.display_name,
            "coordinate": self.coordinate.to_dict(),
            "placeType": self.place_type,
            "address": self.address or {},
        }


@dataclass
class RouteStep:
    """Individual maneuver step in a route leg."""
    instruction: str
    distance_meters: float
    duration_seconds: float
    name: str = ""

    @property
    def distance_miles(self) -> float:
        return self.distance_meters * METERS_TO_MILES

    @property
    def duration_minutes(self) -> float:
        return self.duration_seconds * SECONDS_TO_MINUTES

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instruction": self.instruction,
            "name": self.name,
            "distanceMeters": round(self.distance_meters, 1),
            "distanceMiles": round(self.distance_miles, 2),
            "durationSeconds": round(self.duration_seconds, 1),
            "durationMinutes": round(self.duration_minutes, 1),
        }


@dataclass
class RouteLeg:
    """A distinct leg of the journey (e.g. Current->Pickup or Pickup->Dropoff)."""
    type: str  # "CURRENT_TO_PICKUP" or "PICKUP_TO_DROPOFF"
    origin: GeocodedLocation
    destination: GeocodedLocation
    distance_meters: float
    duration_seconds: float
    geometry: Dict[str, Any] = field(default_factory=dict)
    steps: List[RouteStep] = field(default_factory=list)

    @property
    def distance_miles(self) -> float:
        return self.distance_meters * METERS_TO_MILES

    @property
    def duration_minutes(self) -> float:
        return self.duration_seconds * SECONDS_TO_MINUTES

    @property
    def duration_hours(self) -> float:
        return self.duration_seconds * SECONDS_TO_HOURS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "origin": self.origin.to_dict(),
            "destination": self.destination.to_dict(),
            "distanceMeters": round(self.distance_meters, 1),
            "distanceMiles": round(self.distance_miles, 2),
            "durationSeconds": round(self.duration_seconds, 1),
            "durationMinutes": round(self.duration_minutes, 1),
            "durationHours": round(self.duration_hours, 2),
            "geometry": self.geometry,
            "steps": [s.to_dict() for s in self.steps],
        }


@dataclass
class RoutePlan:
    """Normalized complete road route plan containing distinct legs and full geometry."""
    origin: GeocodedLocation
    pickup: GeocodedLocation
    destination: GeocodedLocation
    legs: List[RouteLeg]
    total_distance_meters: float
    total_duration_seconds: float
    geometry: Dict[str, Any]
    waypoints: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def total_distance_miles(self) -> float:
        return self.total_distance_meters * METERS_TO_MILES

    @property
    def total_duration_minutes(self) -> float:
        return self.total_duration_seconds * SECONDS_TO_MINUTES

    @property
    def total_duration_hours(self) -> float:
        return self.total_duration_seconds * SECONDS_TO_HOURS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "locations": {
                "current": self.origin.to_dict(),
                "pickup": self.pickup.to_dict(),
                "dropoff": self.destination.to_dict(),
            },
            "route": {
                "totalDistanceMeters": round(self.total_distance_meters, 1),
                "totalDistanceMiles": round(self.total_distance_miles, 2),
                "totalDurationSeconds": round(self.total_duration_seconds, 1),
                "totalDurationMinutes": round(self.total_duration_minutes, 1),
                "totalDurationHours": round(self.total_duration_hours, 2),
                "legs": [leg.to_dict() for leg in self.legs],
                "geometry": self.geometry,
                "waypoints": self.waypoints,
            },
        }
