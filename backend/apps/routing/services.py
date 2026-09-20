import logging
import time
from typing import Optional

from .constants import NOMINATIM_REQUEST_DELAY_SECONDS
from .geocoding import GeocodingService
from .osrm import OSRMService
from .models import RoutePlan

logger = logging.getLogger(__name__)


class TripRoutingService:
    """
    Coordinates geocoding of origin, pickup, and destination locations,
    followed by OSRM road routing and route leg extraction.
    """

    def __init__(
        self,
        geocoding_service: Optional[GeocodingService] = None,
        osrm_service: Optional[OSRMService] = None,
        request_delay_seconds: float = NOMINATIM_REQUEST_DELAY_SECONDS,
    ):
        self.geocoding_service = geocoding_service or GeocodingService()
        self.osrm_service = osrm_service or OSRMService()
        self.request_delay_seconds = request_delay_seconds

    def plan_trip_route(
        self,
        current_location_query: str,
        pickup_location_query: str,
        dropoff_location_query: str,
    ) -> RoutePlan:
        """
        Sequentially geocodes the 3 locations with polite delays,
        then calculates the complete road route via OSRM.
        """
        logger.info(
            "[TripRoutingService] Starting route planning: origin='%s', pickup='%s', dropoff='%s'",
            current_location_query, pickup_location_query, dropoff_location_query
        )

        # 1. Geocode current location
        logger.debug("[TripRoutingService] Geocoding origin: %s", current_location_query)
        current_geo = self.geocoding_service.geocode(current_location_query)
        logger.debug("[TripRoutingService] Origin resolved: %s -> (%f, %f)", current_location_query, current_geo.coordinate.latitude, current_geo.coordinate.longitude)

        # Courtesy delay between sequential Nominatim requests if needed
        if self.request_delay_seconds > 0:
            time.sleep(self.request_delay_seconds)

        # 2. Geocode pickup location
        logger.debug("[TripRoutingService] Geocoding pickup: %s", pickup_location_query)
        pickup_geo = self.geocoding_service.geocode(pickup_location_query)
        logger.debug("[TripRoutingService] Pickup resolved: %s -> (%f, %f)", pickup_location_query, pickup_geo.coordinate.latitude, pickup_geo.coordinate.longitude)

        if self.request_delay_seconds > 0:
            time.sleep(self.request_delay_seconds)

        # 3. Geocode dropoff location
        logger.debug("[TripRoutingService] Geocoding dropoff: %s", dropoff_location_query)
        dropoff_geo = self.geocoding_service.geocode(dropoff_location_query)
        logger.debug("[TripRoutingService] Dropoff resolved: %s -> (%f, %f)", dropoff_location_query, dropoff_geo.coordinate.latitude, dropoff_geo.coordinate.longitude)

        # 4. Request OSRM route for Current -> Pickup -> Dropoff
        logger.info("[TripRoutingService] Requesting OSRM road route between all 3 waypoints...")
        route_plan = self.osrm_service.route(
            origin=current_geo,
            pickup=pickup_geo,
            destination=dropoff_geo,
        )

        logger.info(
            "[TripRoutingService] Route successfully resolved: %.2f miles, %.1f driving minutes, %d route legs",
            route_plan.total_distance_miles, route_plan.total_duration_minutes, len(route_plan.legs)
        )

        return route_plan
