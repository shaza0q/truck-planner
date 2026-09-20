"""
Route progress and geometry interpolation engine.
Translates cumulative distance traveled into precise geographic coordinates along a road route.
"""

import math
from dataclasses import dataclass
from typing import List, Tuple, Optional

from apps.routing.constants import METERS_TO_MILES
from apps.routing.models import Coordinate, RoutePlan, RouteLeg


def haversine_distance_meters(c1: Coordinate, c2: Coordinate) -> float:
    """
    Calculates the great-circle distance between two geographic coordinates in meters.
    Uses the spherical Haversine formula (Earth radius = 6,371,000 m).
    """
    r = 6371000.0  # Earth radius in meters
    lat1, lon1 = math.radians(c1.latitude), math.radians(c1.longitude)
    lat2, lon2 = math.radians(c2.latitude), math.radians(c2.longitude)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2.0) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return r * c


@dataclass
class RouteProgress:
    """Detailed progress status at a specific point along a route."""
    coordinate: Coordinate
    distance_meters: float
    distance_miles: float
    leg_type: str  # "CURRENT_TO_PICKUP" or "PICKUP_TO_DROPOFF"
    fraction_of_route: float

    def to_dict(self):
        return {
            "coordinate": self.coordinate.to_dict(),
            "distanceMeters": round(self.distance_meters, 1),
            "distanceMiles": round(self.distance_miles, 2),
            "legType": self.leg_type,
            "fractionOfRoute": round(self.fraction_of_route, 4),
        }


class RouteCursor:
    """
    Pure domain cursor that tracks position along a multi-leg RoutePlan.
    Supports continuous geographic interpolation between polyline vertices.
    """

    def __init__(self, route: RoutePlan):
        self.route = route
        self.points: List[Coordinate] = []
        self.cum_distances: List[float] = [0.0]

        # Extract coordinates from GeoJSON LineString ([lon, lat] format)
        geom = route.geometry or {}
        raw_coords = geom.get("coordinates", [])

        if raw_coords:
            for pt in raw_coords:
                # GeoJSON coordinates are [longitude, latitude]
                lon = float(pt[0])
                lat = float(pt[1])
                self.points.append(Coordinate(latitude=lat, longitude=lon))
        else:
            # Fallback to key waypoint coordinates
            self.points = [
                route.origin.coordinate,
                route.pickup.coordinate,
                route.destination.coordinate,
            ]

        # Build cumulative distance array along the polyline
        total_poly_dist = 0.0
        for i in range(1, len(self.points)):
            d = haversine_distance_meters(self.points[i - 1], self.points[i])
            total_poly_dist += d
            self.cum_distances.append(total_poly_dist)

        self.total_polyline_distance_meters = total_poly_dist

        # Identify leg 1 boundary distance
        leg1 = next((l for l in route.legs if l.type == "CURRENT_TO_PICKUP"), None)
        if leg1:
            self.leg1_distance_meters = leg1.distance_meters
        else:
            self.leg1_distance_meters = route.total_distance_meters / 2.0

    def position_at_distance(self, distance_meters: float) -> Coordinate:
        """
        Returns the interpolated Coordinate at the specified distance from route start.
        """
        if not self.points:
            return self.route.origin.coordinate

        if distance_meters <= 0:
            return self.points[0]

        total_route_dist = self.route.total_distance_meters
        if total_route_dist <= 0:
            return self.points[0]

        if distance_meters >= total_route_dist:
            return self.points[-1]

        # Map distance relative to polyline geometry length
        if self.total_polyline_distance_meters > 0:
            target_poly_dist = (distance_meters / total_route_dist) * self.total_polyline_distance_meters
        else:
            target_poly_dist = 0.0

        if target_poly_dist >= self.cum_distances[-1]:
            return self.points[-1]

        # Find polyline segment [i, i+1] containing target distance
        for i in range(len(self.cum_distances) - 1):
            d_start = self.cum_distances[i]
            d_end = self.cum_distances[i + 1]

            if d_start <= target_poly_dist <= d_end:
                seg_len = d_end - d_start
                if seg_len <= 1e-6:
                    return self.points[i]

                t = (target_poly_dist - d_start) / seg_len
                p1 = self.points[i]
                p2 = self.points[i + 1]

                lat = p1.latitude + t * (p2.latitude - p1.latitude)
                lon = p1.longitude + t * (p2.longitude - p1.longitude)
                return Coordinate(latitude=lat, longitude=lon)

        return self.points[-1]

    def progress_at_distance(self, distance_meters: float) -> RouteProgress:
        """
        Returns rich RouteProgress including coordinate, distance, leg, and route fraction.
        """
        coord = self.position_at_distance(distance_meters)
        clamped_dist = max(0.0, min(distance_meters, self.route.total_distance_meters))
        dist_miles = clamped_dist * METERS_TO_MILES

        if clamped_dist <= self.leg1_distance_meters:
            leg_type = "CURRENT_TO_PICKUP"
        else:
            leg_type = "PICKUP_TO_DROPOFF"

        fraction = clamped_dist / self.route.total_distance_meters if self.route.total_distance_meters > 0 else 0.0

        return RouteProgress(
            coordinate=coord,
            distance_meters=clamped_dist,
            distance_miles=dist_miles,
            leg_type=leg_type,
            fraction_of_route=fraction,
        )
