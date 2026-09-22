import L from 'leaflet';
import { Coordinate } from '../../types/routing';

export const DEFAULT_RASTER_TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
export const OSM_RASTER_TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
export const MAP_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors';

/**
 * Calculates a Leaflet LatLngBounds object enclosing all given coordinates and GeoJSON coordinates.
 */
export function calculateLeafletBounds(
  coordinates: Coordinate[],
  geoJsonCoordinates?: [number, number][]
): L.LatLngBounds | null {
  const points: L.LatLngTuple[] = [];

  coordinates.forEach(c => {
    if (c && typeof c.latitude === 'number' && typeof c.longitude === 'number') {
      points.push([c.latitude, c.longitude]);
    }
  });

  if (geoJsonCoordinates && geoJsonCoordinates.length > 0) {
    geoJsonCoordinates.forEach(coord => {
      if (Array.isArray(coord) && coord.length >= 2) {
        // GeoJSON is [lon, lat] -> Leaflet is [lat, lon]
        points.push([coord[1], coord[0]]);
      }
    });
  }

  if (points.length === 0) return null;
  return L.latLngBounds(points);
}
