"""
Views for Route Planning API.
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import RoutePlanRequestSerializer
from .services import TripRoutingService
from .exceptions import (
    RoutingError,
    LocationNotFoundError,
    GeocodingProviderError,
    GeocodingRateLimitError,
    NoRouteFoundError,
    RoutingProviderError,
)

logger = logging.getLogger(__name__)


class PlanRouteView(APIView):
    """
    POST /api/routes/plan/
    Geocodes locations and computes a multi-leg road route with OSRM.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.routing_service = TripRoutingService()

    def post(self, request, *args, **kwargs):
        logger.info("[PlanRouteView] POST /api/routes/plan/ received: %s", request.data)
        serializer = RoutePlanRequestSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning("[PlanRouteView] Validation error: %s", serializer.errors)
            first_field = next(iter(serializer.errors))
            err_msg = serializer.errors[first_field]
            if isinstance(err_msg, list):
                err_msg = err_msg[0]
            return Response(
                {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": str(err_msg),
                        "details": serializer.errors,
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        try:
            route_plan = self.routing_service.plan_trip_route(
                current_location_query=data["currentLocation"],
                pickup_location_query=data["pickupLocation"],
                dropoff_location_query=data["dropoffLocation"],
            )
            logger.info(
                "[PlanRouteView] Route plan computed: distance=%.2f mi, duration=%.1f min",
                route_plan.total_distance_miles, route_plan.total_duration_minutes
            )
            return Response(route_plan.to_dict(), status=status.HTTP_200_OK)

        except LocationNotFoundError as e:
            logger.warning("[PlanRouteView] Location not found: %s", e.message)
            return Response(
                {
                    "error": {
                        "code": e.code,
                        "message": e.message,
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except NoRouteFoundError as e:
            logger.warning("[PlanRouteView] No route found: %s", e.message)
            return Response(
                {
                    "error": {
                        "code": e.code,
                        "message": e.message,
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except GeocodingRateLimitError as e:
            logger.warning("[PlanRouteView] Rate limited: %s", e.message)
            return Response(
                {
                    "error": {
                        "code": e.code,
                        "message": e.message,
                    }
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except (GeocodingProviderError, RoutingProviderError) as e:
            logger.error("[PlanRouteView] Provider error: code=%s, msg=%s", e.code, e.message)
            return Response(
                {
                    "error": {
                        "code": e.code,
                        "message": e.message,
                    }
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except RoutingError as e:
            logger.warning("[PlanRouteView] Routing error: code=%s, msg=%s", e.code, e.message)
            return Response(
                {
                    "error": {
                        "code": e.code,
                        "message": e.message,
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.exception("[PlanRouteView] Unexpected error: %s", str(e))
            return Response(
                {
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred while planning the route.",
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
