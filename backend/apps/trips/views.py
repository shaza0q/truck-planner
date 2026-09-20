"""
Views for HOS Trip Planning API.
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

from apps.hos.models import TripInput, MockRoute
from apps.hos.scheduler import HOSScheduler
from apps.hos.exceptions import (
    HOSError,
    InvalidTripInputError,
    InsufficientCycleHoursError,
    ImpossibleRouteError,
)
from apps.routing.services import TripRoutingService
from apps.routing.exceptions import (
    RoutingError,
    LocationNotFoundError,
    NoRouteFoundError,
    GeocodingRateLimitError,
    GeocodingProviderError,
    RoutingProviderError,
)
from .serializers import TripPlanRequestSerializer, TripScheduleRequestSerializer
from .planning import TripPlanningService


class HealthCheckView(APIView):
    """
    GET /api/health/
    Operational health check endpoint for monitoring and deployment verification.
    """

    def get(self, request, *args, **kwargs):
        logger.info("[HealthCheckView] GET /api/health/ called from %s", request.META.get('REMOTE_ADDR'))
        return Response(
            {
                "status": "ok",
                "service": "spotter-trucking-planner",
                "version": "1.0.0",
            },
            status=status.HTTP_200_OK,
        )


class PlanTripView(APIView):
    """
    POST /api/hos/plan/
    Phase 1 MockRoute HOS Planning endpoint.
    """

    def post(self, request, *args, **kwargs):
        logger.info("[PlanTripView] POST /api/hos/plan/ received request payload: %s", request.data)
        serializer = TripPlanRequestSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning("[PlanTripView] Validation failed: %s", serializer.errors)
            first_err_field = next(iter(serializer.errors))
            err_msg = serializer.errors[first_err_field]
            if isinstance(err_msg, list):
                err_msg = err_msg[0]
            elif isinstance(err_msg, dict):
                first_sub = next(iter(err_msg))
                err_msg = err_msg[first_sub]
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
        route_data = data["mockRoute"]

        trip_input = TripInput(
            current_location=data["currentLocation"],
            pickup_location=data["pickupLocation"],
            dropoff_location=data["dropoffLocation"],
            current_cycle_used=data["currentCycleUsed"],
        )

        mock_route = MockRoute(
            total_distance_miles=route_data["distanceMiles"],
            total_driving_minutes=route_data["drivingMinutes"],
        )

        scheduler = HOSScheduler()

        try:
            logger.info("[PlanTripView] Planning trip with mock route: %s miles, %s min", mock_route.total_distance_miles, mock_route.total_driving_minutes)
            plan = scheduler.plan_trip(
                trip_input=trip_input,
                route=mock_route,
                start_time=data.get("startTime"),
            )
            logger.info("[PlanTripView] Successfully planned mock trip. Total stops: %d, days: %d", len(plan.stops), len(plan.daily_logs))
            return Response(plan.to_dict(), status=status.HTTP_200_OK)

        except HOSError as e:
            logger.warning("[PlanTripView] HOS Error during planning: code=%s, msg=%s", e.code, e.message)
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
            logger.exception("[PlanTripView] Unexpected exception during mock trip planning: %s", str(e))
            return Response(
                {
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": str(e),
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PlanTripScheduleView(APIView):
    """
    POST /api/trips/plan/
    Phase 3: Real Route + HOS Integration + Geographic Stop Planning endpoint.
    Geocodes 3 locations, obtains OSRM road route, plans HOS-compliant stops,
    and returns a complete TripSchedule.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.routing_service = TripRoutingService()
        self.planning_service = TripPlanningService()

    def post(self, request, *args, **kwargs):
        logger.info("[PlanTripScheduleView] POST /api/trips/plan/ received request payload: %s", request.data)
        serializer = TripScheduleRequestSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning("[PlanTripScheduleView] Request validation failed: %s", serializer.errors)
            first_err_field = next(iter(serializer.errors))
            err_msg = serializer.errors[first_err_field]
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
        curr_loc = data["currentLocation"]
        pickup_loc = data["pickupLocation"]
        dropoff_loc = data["dropoffLocation"]
        cycle_used = data["cycleHoursUsed"]
        start_time = data.get("startTime")

        logger.info(
            "[PlanTripScheduleView] Processing plan request: current='%s', pickup='%s', dropoff='%s', cycle_used=%.1fh",
            curr_loc, pickup_loc, dropoff_loc, cycle_used
        )

        try:
            # 1. Obtain real road RoutePlan via Geocoding + OSRM
            logger.info("[PlanTripScheduleView] Step 1: Querying routing service for road geometry...")
            route_plan = self.routing_service.plan_trip_route(
                current_location_query=curr_loc,
                pickup_location_query=pickup_loc,
                dropoff_location_query=dropoff_loc,
            )
            logger.info(
                "[PlanTripScheduleView] Step 1 Complete: Total Distance=%.1f mi, Driving Duration=%.1f min",
                route_plan.total_distance_miles, route_plan.total_duration_minutes
            )

            # 2. Plan HOS-compliant geographic TripSchedule
            logger.info("[PlanTripScheduleView] Step 2: Planning HOS-compliant stops and daily logs...")
            trip_schedule = self.planning_service.plan(
                route=route_plan,
                cycle_hours_used=cycle_used,
                start_time=start_time,
            )
            logger.info(
                "[PlanTripScheduleView] Step 2 Complete: %d stops, %d duty segments, %d daily logs generated",
                len(trip_schedule.stops), len(trip_schedule.segments), len(trip_schedule.daily_logs)
            )

            return Response(trip_schedule.to_dict(), status=status.HTTP_200_OK)

        except LocationNotFoundError as e:
            logger.warning("[PlanTripScheduleView] Location not found: %s", e.message)
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
            logger.warning("[PlanTripScheduleView] No route found: %s", e.message)
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
            logger.warning("[PlanTripScheduleView] Geocoding rate limit reached: %s", e.message)
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
            logger.error("[PlanTripScheduleView] Provider error: code=%s, msg=%s", e.code, e.message)
            return Response(
                {
                    "error": {
                        "code": e.code,
                        "message": e.message,
                    }
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except HOSError as e:
            logger.warning("[PlanTripScheduleView] HOS constraint violation or error: code=%s, msg=%s", e.code, e.message)
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
            logger.exception("[PlanTripScheduleView] Unexpected server error: %s", str(e))
            return Response(
                {
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": f"An unexpected error occurred: {str(e)}",
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
