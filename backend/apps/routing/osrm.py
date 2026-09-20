"""
OSRM (Open Source Routing Machine) client and service.
Normalizes OSRM route data into distinct route legs (Current->Pickup, Pickup->Dropoff)
and GeoJSON route geometry.
"""

from typing import Optional, Dict, Any, List
import logging
import requests

from .constants import (
    OSRM_BASE_URL,
    USER_AGENT,
    MAP_REQUEST_TIMEOUT_SECONDS,
)
from .models import (
    Coordinate,
    GeocodedLocation,
    RouteStep,
    RouteLeg,
    RoutePlan,
)
from .exceptions import (
    NoRouteFoundError,
    RoutingProviderError,
)

logger = logging.getLogger(__name__)


class OSRMClient:
    """Low-level HTTP client for OSRM Route API."""

    def __init__(
        self,
        base_url: str = OSRM_BASE_URL,
        user_agent: str = USER_AGENT,
        timeout_seconds: int = MAP_REQUEST_TIMEOUT_SECONDS,
    ):
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds

    def get_route(self, coordinates: List[Coordinate]) -> Dict[str, Any]:
        """
        Sends route request to OSRM driving profile.
        Coordinates must be supplied in longitude,latitude order in the URL path.
        """
        if len(coordinates) < 2:
            raise ValueError("At least two coordinates are required for routing.")

        coords_str = ";".join([c.to_osrm_format() for c in coordinates])
        url = f"{self.base_url}/route/v1/driving/{coords_str}"
        params = {
            "overview": "full",
            "geometries": "geojson",
            "steps": "true",
            "annotations": "false",
        }
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }

        logger.debug("[OSRMClient.get_route] Calling OSRM: url=%s", url)
        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout_seconds,
            )
        except requests.exceptions.SSLError as e:
            if url.startswith("https://"):
                fallback_url = "http://" + url[len("https://"):]
                logger.warning("[OSRMClient.get_route] HTTPS SSL handshake failed (%s), attempting HTTP fallback: %s", str(e), fallback_url)
                try:
                    response = requests.get(
                        fallback_url,
                        params=params,
                        headers=headers,
                        timeout=self.timeout_seconds,
                    )
                except Exception as fb_err:
                    logger.error("[OSRMClient.get_route] HTTP fallback failed: %s", str(fb_err))
                    raise RoutingProviderError(f"Routing network error: {str(fb_err)}") from fb_err
            else:
                logger.error("[OSRMClient.get_route] SSL error for coordinates %s: %s", coords_str, str(e))
                raise RoutingProviderError(f"Routing network error: {str(e)}") from e
        except requests.exceptions.Timeout as e:
            logger.error("[OSRMClient.get_route] Request timed out for coordinates: %s", coords_str)
            raise RoutingProviderError("OSRM routing request timed out.") from e
        except requests.exceptions.RequestException as e:
            # Check if underlying cause was an SSLError
            if "SSLError" in str(e) and url.startswith("https://"):
                fallback_url = "http://" + url[len("https://"):]
                logger.warning("[OSRMClient.get_route] SSL error in RequestException, trying HTTP fallback: %s", fallback_url)
                try:
                    response = requests.get(
                        fallback_url,
                        params=params,
                        headers=headers,
                        timeout=self.timeout_seconds,
                    )
                except Exception as fb_err:
                    logger.error("[OSRMClient.get_route] HTTP fallback failed: %s", str(fb_err))
                    raise RoutingProviderError(f"Routing network error: {str(fb_err)}") from fb_err
            else:
                logger.error("[OSRMClient.get_route] Network error for coordinates %s: %s", coords_str, str(e))
                raise RoutingProviderError(f"Routing network error: {str(e)}") from e

        if response.status_code != 200:
            logger.error("[OSRMClient.get_route] OSRM returned HTTP status %d", response.status_code)
            raise RoutingProviderError(f"OSRM returned HTTP status {response.status_code}.")

        try:
            data = response.json()
        except ValueError as e:
            logger.error("[OSRMClient.get_route] Failed to parse JSON response from OSRM")
            raise RoutingProviderError("Failed to parse OSRM JSON response.") from e

        code = data.get("code")
        if code == "NoRoute":
            logger.warning("[OSRMClient.get_route] OSRM returned code=NoRoute for coordinates: %s", coords_str)
            raise NoRouteFoundError()
        elif code != "Ok":
            message = data.get("message", f"OSRM error code: {code}")
            logger.error("[OSRMClient.get_route] OSRM error code '%s': %s", code, message)
            raise RoutingProviderError(f"OSRM routing failed: {message}")

        logger.debug("[OSRMClient.get_route] OSRM route successfully received (code=Ok)")
        return data


class OSRMService:
    """High-level routing service that normalizes OSRM responses into domain models."""

    def __init__(self, client: Optional[OSRMClient] = None):
        self.client = client or OSRMClient()

    def route(
        self,
        origin: GeocodedLocation,
        pickup: GeocodedLocation,
        destination: GeocodedLocation,
    ) -> RoutePlan:
        """
        Obtains a complete 3-point route: Origin -> Pickup -> Destination.
        Normalizes the response into distinct route legs and GeoJSON geometry.
        """
        logger.info(
            "[OSRMService.route] Computing 3-point route: Origin=(%f, %f) -> Pickup=(%f, %f) -> Dropoff=(%f, %f)",
            origin.coordinate.latitude, origin.coordinate.longitude,
            pickup.coordinate.latitude, pickup.coordinate.longitude,
            destination.coordinate.latitude, destination.coordinate.longitude,
        )
        coordinates = [
            origin.coordinate,
            pickup.coordinate,
            destination.coordinate,
        ]

        data = self.client.get_route(coordinates)
        routes = data.get("routes")
        if not routes or not isinstance(routes, list):
            logger.error("[OSRMService.route] No routes returned by routing provider")
            raise NoRouteFoundError("No routes returned by routing provider.")

        primary_route = routes[0]
        try:
            total_dist_m = float(primary_route["distance"])
            total_dur_s = float(primary_route["duration"])
            geometry = primary_route.get("geometry") or {
                "type": "LineString",
                "coordinates": [
                    [c.longitude, c.latitude] for c in coordinates
                ]
            }

            raw_legs = primary_route.get("legs", [])
            normalized_legs: List[RouteLeg] = []

            # Leg 1: Current -> Pickup
            leg1_dist = float(raw_legs[0]["distance"]) if len(raw_legs) > 0 else 0.0
            leg1_dur = float(raw_legs[0]["duration"]) if len(raw_legs) > 0 else 0.0
            leg1_steps = self._parse_steps(raw_legs[0].get("steps", []) if len(raw_legs) > 0 else [])
            
            normalized_legs.append(RouteLeg(
                type="CURRENT_TO_PICKUP",
                origin=origin,
                destination=pickup,
                distance_meters=leg1_dist,
                duration_seconds=leg1_dur,
                geometry=geometry if len(raw_legs) == 1 else {},
                steps=leg1_steps,
            ))

            # Leg 2: Pickup -> Dropoff
            if len(raw_legs) > 1:
                leg2_dist = float(raw_legs[1]["distance"])
                leg2_dur = float(raw_legs[1]["duration"])
                leg2_steps = self._parse_steps(raw_legs[1].get("steps", []))
                
                normalized_legs.append(RouteLeg(
                    type="PICKUP_TO_DROPOFF",
                    origin=pickup,
                    destination=destination,
                    distance_meters=leg2_dist,
                    duration_seconds=leg2_dur,
                    geometry={},
                    steps=leg2_steps,
                ))

            waypoints = data.get("waypoints", [])

            logger.info(
                "[OSRMService.route] Route parsed: Leg 1=%.1f mi, Leg 2=%.1f mi, Total=%.1f mi",
                normalized_legs[0].distance_miles,
                normalized_legs[1].distance_miles if len(normalized_legs) > 1 else 0.0,
                total_dist_m * 0.000621371
            )

            return RoutePlan(
                origin=origin,
                pickup=pickup,
                destination=destination,
                legs=normalized_legs,
                total_distance_meters=total_dist_m,
                total_duration_seconds=total_dur_s,
                geometry=geometry,
                waypoints=waypoints,
            )
        except (KeyError, ValueError, TypeError) as e:
            logger.error("[OSRMService.route] Malformed route data received from OSRM: %s", str(e))
            raise RoutingProviderError(f"Malformed route data received from OSRM: {str(e)}") from e

    def _parse_steps(self, raw_steps: List[Dict[str, Any]]) -> List[RouteStep]:
        """Parses individual maneuver steps defensively."""
        steps: List[RouteStep] = []
        for s in raw_steps:
            try:
                maneuver = s.get("maneuver", {})
                instruction = maneuver.get("type", "turn")
                if "modifier" in maneuver:
                    instruction = f"{instruction} {maneuver['modifier']}"
                name = s.get("name", "")
                dist = float(s.get("distance", 0.0))
                dur = float(s.get("duration", 0.0))
                steps.append(RouteStep(
                    instruction=instruction,
                    name=name,
                    distance_meters=dist,
                    duration_seconds=dur,
                ))
            except Exception:
                continue
        return steps
