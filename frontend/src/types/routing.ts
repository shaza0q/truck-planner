export interface Coordinate {
  latitude: number;
  longitude: number;
}

export interface GeocodedLocation {
  query: string;
  displayName: string;
  coordinate: Coordinate;
  placeType?: string;
  address?: Record<string, any>;
}

export interface RouteStep {
  instruction: string;
  name: string;
  distanceMeters: number;
  distanceMiles: number;
  durationSeconds: number;
  durationMinutes: number;
}

export interface RouteLeg {
  type: 'CURRENT_TO_PICKUP' | 'PICKUP_TO_DROPOFF' | string;
  origin: GeocodedLocation;
  destination: GeocodedLocation;
  distanceMeters: number;
  distanceMiles: number;
  durationSeconds: number;
  durationMinutes: number;
  durationHours: number;
  geometry: GeoJSON.LineString | Record<string, any>;
  steps: RouteStep[];
}

export interface RoutePlanResponse {
  locations: {
    current: GeocodedLocation;
    pickup: GeocodedLocation;
    dropoff: GeocodedLocation;
  };
  route: {
    totalDistanceMeters: number;
    totalDistanceMiles: number;
    totalDurationSeconds: number;
    totalDurationMinutes: number;
    totalDurationHours: number;
    legs: RouteLeg[];
    geometry: GeoJSON.LineString;
    waypoints: Array<{ name: string; location: [number, number] }>;
  };
}

export interface RoutePlanRequest {
  currentLocation: string;
  pickupLocation: string;
  dropoffLocation: string;
}

export interface RoutingApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, any>;
  };
}
