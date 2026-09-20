"""
DRF Serializers for HOS Planning requests and responses.
"""

from rest_framework import serializers


class MockRouteSerializer(serializers.Serializer):
    distanceMiles = serializers.FloatField(required=False)
    drivingMinutes = serializers.IntegerField(required=False)
    # Support snake_case as fallback
    distance_miles = serializers.FloatField(required=False)
    driving_minutes = serializers.IntegerField(required=False)

    def validate(self, attrs):
        dist = attrs.get('distanceMiles', attrs.get('distance_miles'))
        mins = attrs.get('drivingMinutes', attrs.get('driving_minutes'))

        if dist is None:
            raise serializers.ValidationError({"distanceMiles": "Route distance is required."})
        if mins is None:
            raise serializers.ValidationError({"drivingMinutes": "Driving minutes are required."})

        if dist < 0:
            raise serializers.ValidationError({"distanceMiles": "Distance cannot be negative."})
        if mins < 0:
            raise serializers.ValidationError({"drivingMinutes": "Driving minutes cannot be negative."})

        attrs['distanceMiles'] = dist
        attrs['drivingMinutes'] = mins
        return attrs


class TripPlanRequestSerializer(serializers.Serializer):
    currentLocation = serializers.CharField(required=False, max_length=255)
    pickupLocation = serializers.CharField(required=False, max_length=255)
    dropoffLocation = serializers.CharField(required=False, max_length=255)
    currentCycleUsed = serializers.FloatField(required=False)
    mockRoute = MockRouteSerializer(required=False)

    # Support snake_case fallbacks
    current_location = serializers.CharField(required=False, max_length=255)
    pickup_location = serializers.CharField(required=False, max_length=255)
    dropoff_location = serializers.CharField(required=False, max_length=255)
    current_cycle_used = serializers.FloatField(required=False)
    mock_route = MockRouteSerializer(required=False)

    startTime = serializers.DateTimeField(required=False, allow_null=True)
    start_time = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs):
        curr_loc = attrs.get('currentLocation', attrs.get('current_location'))
        pickup_loc = attrs.get('pickupLocation', attrs.get('pickup_location'))
        dropoff_loc = attrs.get('dropoffLocation', attrs.get('dropoff_location'))
        cycle_used = attrs.get('currentCycleUsed', attrs.get('current_cycle_used'))
        mock_route = attrs.get('mockRoute', attrs.get('mock_route'))
        start_t = attrs.get('startTime', attrs.get('start_time'))

        errors = {}
        if not curr_loc:
            errors['currentLocation'] = "Current location is required."
        if not pickup_loc:
            errors['pickupLocation'] = "Pickup location is required."
        if not dropoff_loc:
            errors['dropoffLocation'] = "Dropoff location is required."
        if cycle_used is None:
            errors['currentCycleUsed'] = "Current cycle used is required."
        elif cycle_used < 0.0 or cycle_used > 70.0:
            errors['currentCycleUsed'] = "Current cycle used must be between 0.0 and 70.0 hours."
        if mock_route is None:
            errors['mockRoute'] = "Mock route object is required."

        if errors:
            raise serializers.ValidationError(errors)

        attrs['currentLocation'] = curr_loc
        attrs['pickupLocation'] = pickup_loc
        attrs['dropoffLocation'] = dropoff_loc
        attrs['currentCycleUsed'] = cycle_used
        attrs['mockRoute'] = mock_route
        attrs['startTime'] = start_t
        return attrs


class TripScheduleRequestSerializer(serializers.Serializer):
    currentLocation = serializers.CharField(required=False, max_length=255)
    pickupLocation = serializers.CharField(required=False, max_length=255)
    dropoffLocation = serializers.CharField(required=False, max_length=255)
    cycleHoursUsed = serializers.FloatField(required=False)

    # Support alternative field name and snake_case
    currentCycleUsed = serializers.FloatField(required=False)
    current_location = serializers.CharField(required=False, max_length=255)
    pickup_location = serializers.CharField(required=False, max_length=255)
    dropoff_location = serializers.CharField(required=False, max_length=255)
    cycle_hours_used = serializers.FloatField(required=False)
    current_cycle_used = serializers.FloatField(required=False)

    startTime = serializers.DateTimeField(required=False, allow_null=True)
    start_time = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs):
        curr_loc = (attrs.get('currentLocation') or attrs.get('current_location') or '').strip()
        pickup_loc = (attrs.get('pickupLocation') or attrs.get('pickup_location') or '').strip()
        dropoff_loc = (attrs.get('dropoffLocation') or attrs.get('dropoff_location') or '').strip()

        cycle_used = attrs.get('cycleHoursUsed')
        if cycle_used is None:
            cycle_used = attrs.get('currentCycleUsed')
        if cycle_used is None:
            cycle_used = attrs.get('cycle_hours_used')
        if cycle_used is None:
            cycle_used = attrs.get('current_cycle_used')

        start_t = attrs.get('startTime') or attrs.get('start_time')

        errors = {}
        if not curr_loc:
            errors['currentLocation'] = "Current location is required."
        if not pickup_loc:
            errors['pickupLocation'] = "Pickup location is required."
        if not dropoff_loc:
            errors['dropoffLocation'] = "Dropoff location is required."
        if cycle_used is None:
            errors['cycleHoursUsed'] = "Cycle hours used is required."
        elif cycle_used < 0.0 or cycle_used > 70.0:
            errors['cycleHoursUsed'] = "Cycle hours used must be between 0.0 and 70.0 hours."

        if errors:
            raise serializers.ValidationError(errors)

        attrs['currentLocation'] = curr_loc
        attrs['pickupLocation'] = pickup_loc
        attrs['dropoffLocation'] = dropoff_loc
        attrs['cycleHoursUsed'] = cycle_used
        attrs['startTime'] = start_t
        return attrs
