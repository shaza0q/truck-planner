"""
Trips routing endpoints.
"""

from django.urls import path
from .views import PlanTripView, PlanTripScheduleView

urlpatterns = [
    # Phase 3 Real Route + Geographic HOS schedule endpoint
    path('plan/', PlanTripScheduleView.as_view(), name='trips-plan'),
    # Phase 1 MockRoute HOS plan endpoint
    path('hos/plan/', PlanTripView.as_view(), name='hos-plan'),
]
