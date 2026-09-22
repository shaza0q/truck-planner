import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { RoutePlanResponse, Coordinate } from '../../types/routing';
import { Stop } from '../../types/hos';
import { TripScheduleSummary } from '../../types/tripSchedule';
import { DEFAULT_RASTER_TILE_URL, MAP_ATTRIBUTION, calculateLeafletBounds } from './mapUtils';
import { Maximize2, Map } from 'lucide-react';

interface Props {
  routePlan: RoutePlanResponse | null;
  stops?: Stop[];
  summary?: TripScheduleSummary | null;
  loading?: boolean;
}

export const RouteMap: React.FC<Props> = ({ routePlan, stops = [], summary, loading = false }) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const routeLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const markersLayerGroupRef = useRef<L.LayerGroup | null>(null);

  // Initialize Leaflet map instance once
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    // Create Leaflet map
    const map = L.map(mapContainerRef.current, {
      center: [32.7767, -96.7970], // Default center (Dallas, TX)
      zoom: 4,
      zoomControl: false, // We'll add zoom control in top-left
      attributionControl: false,
    });

    // Add zoom control to top-left
    L.control.zoom({ position: 'topleft' }).addTo(map);

    // Add CartoDB Voyager / OpenStreetMap basemap raster tiles
    const tileLayer = L.tileLayer(DEFAULT_RASTER_TILE_URL, {
      attribution: MAP_ATTRIBUTION,
      maxZoom: 19,
      subdomains: 'abcd',
    });
    tileLayer.addTo(map);

    // Add attribution control to bottom-left
    L.control.attribution({ position: 'bottomleft' }).addTo(map);

    // Layer groups for route polylines and markers
    const routeGroup = L.layerGroup().addTo(map);
    const markersGroup = L.layerGroup().addTo(map);

    routeLayerGroupRef.current = routeGroup;
    markersLayerGroupRef.current = markersGroup;
    mapRef.current = map;

    // Invalidate size on mount / resize
    const resizeObserver = new ResizeObserver(() => {
      map.invalidateSize();
    });
    if (mapContainerRef.current) {
      resizeObserver.observe(mapContainerRef.current);
    }

    return () => {
      resizeObserver.disconnect();
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update Route Polylines and Markers whenever routePlan or stops change
  useEffect(() => {
    const map = mapRef.current;
    const routeGroup = routeLayerGroupRef.current;
    const markersGroup = markersLayerGroupRef.current;

    if (!map || !routeGroup || !markersGroup) return;

    // Clear previous routes and markers
    routeGroup.clearLayers();
    markersGroup.clearLayers();

    if (!routePlan) return;

    try {
      const rawLocations = (routePlan as any).locations || (routePlan as any).route?.locations || {};
      const rawRoute = (routePlan as any).route || routePlan || {};

      const locations = {
        current: rawLocations.current || null,
        pickup: rawLocations.pickup || null,
        dropoff: rawLocations.dropoff || null,
      };

      const geoCoordinates: [number, number][] = (rawRoute?.geometry?.coordinates as [number, number][]) || [];

      // 1. Render Route Polyline with White Casing + Forest Green Line
      if (geoCoordinates.length > 0) {
        // Convert GeoJSON [lon, lat] to Leaflet [lat, lon]
        const latLngs: L.LatLngTuple[] = geoCoordinates.map(coord => [coord[1], coord[0]]);

        // Casing polyline (White / Light border)
        const casingLine = L.polyline(latLngs, {
          color: '#FFFFFF',
          weight: 7,
          opacity: 0.9,
          lineCap: 'round',
          lineJoin: 'round',
        });
        routeGroup.addLayer(casingLine);

        // Core route polyline (Forest Green)
        const routeLine = L.polyline(latLngs, {
          color: '#1F6B57',
          weight: 4.5,
          opacity: 0.95,
          lineCap: 'round',
          lineJoin: 'round',
        });
        routeGroup.addLayer(routeLine);
      }

      // Helper for creating custom Leaflet DivIcons
      const createCustomIcon = (
        bgClass: string,
        label: string,
        iconSvg: string,
        dotOnly = false
      ) => {
        const html = dotOnly
          ? `
            <div class="flex flex-col items-center cursor-pointer group -translate-x-1/2 -translate-y-1/2">
              <div class="w-4 h-4 rounded-full ${bgClass} border-2 border-white shadow-sm flex items-center justify-center transform group-hover:scale-125 transition">
                <div class="w-1.5 h-1.5 rounded-full bg-white"></div>
              </div>
              ${label ? `<span class="text-[10px] font-bold text-[#202321] bg-white/95 px-1 py-0.5 rounded shadow-2xs mt-0.5 whitespace-nowrap border border-[#E7E7E2]">${label}</span>` : ''}
            </div>
          `
          : `
            <div class="flex flex-col items-center cursor-pointer group -translate-x-1/2 -translate-y-1/2">
              <div class="w-6 h-6 rounded-full ${bgClass} border-2 border-white shadow-md flex items-center justify-center text-white transform group-hover:scale-115 transition">
                ${iconSvg}
              </div>
              ${label ? `<span class="text-[10px] font-bold text-[#202321] bg-white/95 px-1 py-0.5 rounded shadow-2xs mt-0.5 whitespace-nowrap border border-[#E7E7E2]">${label}</span>` : ''}
            </div>
          `;

        return L.divIcon({
          className: 'custom-leaflet-marker',
          html,
          iconSize: [24, 24],
          iconAnchor: [12, 12],
          popupAnchor: [0, -14],
        });
      };

      // 2. Add Origin Marker
      if (locations.current?.coordinate) {
        const { latitude, longitude } = locations.current.coordinate;
        const originName = (locations.current.query || 'Dallas, TX').split(',')[0];
        const originIcon = createCustomIcon(
          'bg-[#164E3D]',
          originName,
          `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/></svg>`,
          true
        );

        const marker = L.marker([latitude, longitude], { icon: originIcon });
        marker.bindPopup(`
          <div class="p-3 font-sans min-w-[200px]">
            <div class="flex items-center gap-1.5 mb-1.5">
              <span class="text-[9px] font-mono font-bold uppercase px-1.5 py-0.5 rounded bg-[#164E3D] text-white">Origin</span>
              <span class="text-xs font-bold text-[#202321]">${locations.current.query || 'Current Location'}</span>
            </div>
            <p class="text-[11px] text-[#626862] font-mono">Mile 0.0 • Departure Point</p>
          </div>
        `);
        markersGroup.addLayer(marker);
      }

      // 3. Add Scheduled Stops & Waypoint Markers
      if (stops && stops.length > 0) {
        stops.forEach((stop, idx) => {
          if (!stop.coordinate) return;
          const { latitude, longitude } = stop.coordinate;
          let bg = 'bg-[#164E3D]';
          let name = stop.location ? stop.location.split(',')[0] : '';
          let icon = `<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`;
          let dotOnly = false;
          let badgeColor = 'bg-[#164E3D] text-white';

          if (stop.type === 'PICKUP') {
            bg = 'bg-[#164E3D]';
            badgeColor = 'bg-[#164E3D] text-white';
            icon = `<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg>`;
          } else if (stop.type === 'DROPOFF') {
            bg = 'bg-[#DC2626]';
            badgeColor = 'bg-[#DC2626] text-white';
            icon = `<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9"/></svg>`;
          } else if (stop.type === 'FUEL') {
            bg = 'bg-[#D97706]';
            badgeColor = 'bg-[#D97706] text-white';
            name = '';
            icon = `<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg>`;
          } else if (stop.type === 'REST') {
            bg = 'bg-[#2563EB]';
            badgeColor = 'bg-[#2563EB] text-white';
            name = '';
            icon = `<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/></svg>`;
          } else if (stop.type === 'BREAK') {
            bg = 'bg-[#4B5563]';
            badgeColor = 'bg-[#4B5563] text-white';
            name = '';
            icon = `<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`;
          }

          const stopIcon = createCustomIcon(bg, name, icon, dotOnly);
          const marker = L.marker([latitude, longitude], { icon: stopIcon });

          const arrivalTime = stop.start ? new Date(stop.start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--';
          const departureTime = stop.end ? new Date(stop.end).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--';
          const durationStr = stop.durationMinutes >= 60 
            ? `${(stop.durationMinutes / 60).toFixed(1)} hrs` 
            : `${stop.durationMinutes} min`;

          marker.bindPopup(`
            <div class="p-3 font-sans min-w-[210px]">
              <div class="flex items-center justify-between gap-2 mb-1.5">
                <span class="text-[9px] font-mono font-bold uppercase px-1.5 py-0.5 rounded ${badgeColor}">
                  #${idx + 1} ${stop.type}
                </span>
                <span class="text-[10px] font-mono font-bold text-[#626862]">
                  ${stop.milesFromStart.toFixed(1)} mi
                </span>
              </div>
              <p class="text-xs font-bold text-[#202321] mb-1">${stop.location || 'Scheduled Stop'}</p>
              <div class="text-[11px] text-[#626862] font-mono flex flex-col gap-0.5 border-t border-[#E7E7E2] pt-1.5 mt-1.5">
                <div>Arrival: <span class="font-bold text-[#202321]">${arrivalTime}</span></div>
                <div>Departure: <span class="font-bold text-[#202321]">${departureTime}</span></div>
                <div>Duration: <span class="font-bold text-[#202321]">${durationStr}</span></div>
                ${stop.reason ? `<div class="text-[10px] text-[#858A84] mt-0.5">${stop.reason}</div>` : ''}
              </div>
            </div>
          `);

          markersGroup.addLayer(marker);
        });
      }

      // 4. Fit Map Bounds with Smooth Animation
      const coords: Coordinate[] = [
        locations.current?.coordinate,
        locations.pickup?.coordinate,
        locations.dropoff?.coordinate,
        ...stops.filter(s => !!s.coordinate).map(s => s.coordinate as Coordinate),
      ].filter(Boolean) as Coordinate[];

      const bounds = calculateLeafletBounds(coords, geoCoordinates);
      if (bounds && bounds.isValid()) {
        map.fitBounds(bounds, {
          padding: [45, 45],
          maxZoom: 14,
          animate: true,
          duration: 0.8,
        });
      }
    } catch (e) {
      console.warn('Leaflet map layer update error:', e);
    }
  }, [routePlan, stops]);

  const handleFitRoute = () => {
    const map = mapRef.current;
    if (!map || !routePlan) return;

    try {
      const rawLocations = (routePlan as any).locations || (routePlan as any).route?.locations || {};
      const rawRoute = (routePlan as any).route || routePlan || {};
      const geoCoordinates: [number, number][] = (rawRoute?.geometry?.coordinates as [number, number][]) || [];

      const coords: Coordinate[] = [
        rawLocations.current?.coordinate,
        rawLocations.pickup?.coordinate,
        rawLocations.dropoff?.coordinate,
        ...stops.filter(s => !!s.coordinate).map(s => s.coordinate as Coordinate),
      ].filter(Boolean) as Coordinate[];

      const bounds = calculateLeafletBounds(coords, geoCoordinates);
      if (bounds && bounds.isValid()) {
        map.fitBounds(bounds, {
          padding: [45, 45],
          maxZoom: 14,
          animate: true,
          duration: 0.5,
        });
      }
    } catch (e) {
      console.warn('Fit route error:', e);
    }
  };

  return (
    <div className="bg-white border border-[#E2E3DE] rounded-lg p-4 flex flex-col shadow-xs h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-3 pb-2.5 border-b border-[#E7E7E2]">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded-full bg-[#164E3D]/10 text-[#164E3D] flex items-center justify-center">
            <Map className="w-3 h-3" />
          </div>
          <h3 className="text-xs font-bold text-[#202321] tracking-tight">
            Route & Stops
          </h3>
          {summary && (
            <span className="text-xs text-[#626862] font-mono ml-2 hidden sm:inline">
              {summary.totalDistanceMiles.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} miles • {summary.totalDrivingHours} driving • {summary.daysCount} days • {stops.length} stops
            </span>
          )}
        </div>

        <button
          onClick={handleFitRoute}
          className="flex items-center gap-1.5 px-2.5 py-1 bg-white hover:bg-[#FAFAF8] text-[#202321] rounded border border-[#D9DAD5] text-[11px] font-semibold transition cursor-pointer shadow-2xs"
          title="Fit route to window"
        >
          <Maximize2 className="w-3 h-3 text-[#164E3D]" />
          <span>Fit Route</span>
        </button>
      </div>

      {/* Map Display Container */}
      <div className="relative w-full h-[340px] md:h-[380px] lg:h-[400px] rounded border border-[#E7E7E2] overflow-hidden bg-[#F5F5F2] isolate">
        <div ref={mapContainerRef} className="w-full h-full" />

        {/* Floating Route Legend on Bottom Right */}
        <div className="absolute bottom-3 right-3 z-10 bg-white/95 backdrop-blur-xs rounded border border-[#E2E3DE] shadow-sm px-2.5 py-2 text-[10px] text-[#202321] pointer-events-auto">
          <div className="flex flex-col gap-1 font-medium">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#164E3D]" />
              <span>Origin</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#164E3D]" />
              <span>Pickup (1h)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#DC2626]" />
              <span>Dropoff (1h)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#D97706]" />
              <span>Fuel Stop</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#4B5563]" />
              <span>30m Break</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#2563EB]" />
              <span>10h Rest</span>
            </div>
          </div>
        </div>

        {/* Loading overlay */}
        {loading && (
          <div className="absolute inset-0 bg-white/80 backdrop-blur-xs flex flex-col items-center justify-center z-20 gap-2">
            <div className="w-5 h-5 border-2 border-[#164E3D]/30 border-t-[#164E3D] rounded-full animate-spin" />
            <p className="text-xs font-medium text-[#202321] font-mono">Routing highway polyline...</p>
          </div>
        )}
      </div>
    </div>
  );
};
