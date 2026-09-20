"""
URL Configuration for HOS Trip Planner.
"""

from django.urls import path, include
from apps.trips.views import PlanTripView, HealthCheckView

urlpatterns = [
    # Health check
    path('api/health/', HealthCheckView.as_view(), name='health-check'),
    # Phase 1 endpoint
    path('api/hos/plan/', PlanTripView.as_view(), name='hos-plan'),
    # Phase 3 endpoints
    path('api/trips/', include('apps.trips.urls')),
    # Phase 2 routing endpoints
    path('api/routes/', include('apps.routing.urls')),
]
