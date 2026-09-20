"""
DRF Serializers for Routing API requests.
"""

from rest_framework import serializers


class RoutePlanRequestSerializer(serializers.Serializer):
    currentLocation = serializers.CharField(required=False, max_length=255)
    pickupLocation = serializers.CharField(required=False, max_length=255)
    dropoffLocation = serializers.CharField(required=False, max_length=255)

    # Support snake_case fallbacks
    current_location = serializers.CharField(required=False, max_length=255)
    pickup_location = serializers.CharField(required=False, max_length=255)
    dropoff_location = serializers.CharField(required=False, max_length=255)

    def validate(self, attrs):
        curr = (attrs.get('currentLocation') or attrs.get('current_location') or '').strip()
        pickup = (attrs.get('pickupLocation') or attrs.get('pickup_location') or '').strip()
        dropoff = (attrs.get('dropoffLocation') or attrs.get('dropoff_location') or '').strip()

        errors = {}
        if not curr:
            errors['currentLocation'] = "Current location is required."
        if not pickup:
            errors['pickupLocation'] = "Pickup location is required."
        if not dropoff:
            errors['dropoffLocation'] = "Dropoff location is required."

        if errors:
            raise serializers.ValidationError(errors)

        attrs['currentLocation'] = curr
        attrs['pickupLocation'] = pickup
        attrs['dropoffLocation'] = dropoff
        return attrs
