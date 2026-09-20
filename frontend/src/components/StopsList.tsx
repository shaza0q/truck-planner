import React from 'react';
import { Stop, StopType } from '../types/hos';
import { PackageOpen, PackageCheck, Fuel, Moon, Coffee, ClipboardList } from 'lucide-react';

interface Props {
  stops: Stop[];
  onViewTimeline?: () => void;
}

const STOP_CONFIG: Record<StopType, { label: string; icon: any; circleBg: string; textClass: string }> = {
  PICKUP: {
    label: 'Cargo Pickup',
    icon: PackageOpen,
    circleBg: 'bg-[#164E3D] text-white',
    textClass: 'text-[#164E3D]',
  },
  DROPOFF: {
    label: 'Cargo Dropoff',
    icon: PackageCheck,
    circleBg: 'bg-[#DC2626] text-white',
    textClass: 'text-[#DC2626]',
  },
  FUEL: {
    label: 'Fuel Stop',
    icon: Fuel,
    circleBg: 'bg-[#D97706] text-white',
    textClass: 'text-[#D97706]',
  },
  REST: {
    label: '10h Daily Rest',
    icon: Moon,
    circleBg: 'bg-[#2563EB] text-white',
    textClass: 'text-[#2563EB]',
  },
  BREAK: {
    label: '30m Rest Break',
    icon: Coffee,
    circleBg: 'bg-[#4B5563] text-white',
    textClass: 'text-[#4B5563]',
  },
};

export const StopsList: React.FC<Props> = ({ stops, onViewTimeline }) => {
  const formatTime = (isoString?: string) => {
    if (!isoString) return '—';
    try {
      const d = new Date(isoString);
      return `${d.toLocaleDateString([], { month: 'short', day: 'numeric' })}, ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })}`;
    } catch {
      return isoString;
    }
  };

  const formatDuration = (minutes: number) => {
    const hrs = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hrs > 0 && mins > 0) return `${hrs}h ${mins.toString().padStart(2, '0')}m`;
    if (hrs > 0) return `${hrs}h 00m`;
    return `${mins}m`;
  };

  return (
    <div className="bg-white border border-[#E2E3DE] rounded-lg p-4 sm:p-5 shadow-xs flex flex-col justify-between w-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3 pb-3 border-b border-[#E7E7E2]">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-[#164E3D]/10 text-[#164E3D] flex items-center justify-center">
            <ClipboardList className="w-3.5 h-3.5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-[#202321] tracking-tight">
              Scheduled Stops ({stops.length})
            </h3>
            <p className="text-[11px] text-[#626862]">
              Sequential itinerary of cargo loading, mandatory 30m rest breaks, 10h daily resets, and fuel stops.
            </p>
          </div>
        </div>

        {onViewTimeline && (
          <button
            onClick={onViewTimeline}
            className="text-xs font-semibold text-[#164E3D] hover:underline flex items-center gap-1 cursor-pointer self-start sm:self-auto"
          >
            View Full Timeline →
          </button>
        )}
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded border border-[#E7E7E2]">
        <table className="w-full text-left text-xs text-[#202321]">
          <thead className="text-[10px] uppercase text-[#858A84] font-mono bg-[#FAFAF8] border-b border-[#E7E7E2]">
            <tr>
              <th className="py-2.5 px-3 font-medium w-10 text-center">#</th>
              <th className="py-2.5 px-3 font-medium">Activity Type</th>
              <th className="py-2.5 px-3 font-medium">Location</th>
              <th className="py-2.5 px-3 font-medium">Arrival</th>
              <th className="py-2.5 px-3 font-medium">Departure</th>
              <th className="py-2.5 px-3 font-medium">Duration</th>
              <th className="py-2.5 px-3 font-medium text-right">Route Mile</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E7E7E2]">
            {stops.map((stop, idx) => {
              const cfg = STOP_CONFIG[stop.type] || STOP_CONFIG.BREAK;
              const Icon = cfg.icon;

              return (
                <tr key={idx} className="hover:bg-[#FAFAF8] transition-colors">
                  {/* Number Badge */}
                  <td className="py-3 px-3 whitespace-nowrap text-center">
                    <div className={`w-5 h-5 rounded-full ${cfg.circleBg} inline-flex items-center justify-center text-[10px] font-mono font-bold shadow-2xs`}>
                      {String(idx + 1).padStart(2, '0')}
                    </div>
                  </td>

                  {/* Stop Type */}
                  <td className="py-3 px-3 whitespace-nowrap">
                    <div className="flex items-center gap-2 font-medium text-[#202321]">
                      <Icon className={`w-4 h-4 ${cfg.textClass}`} />
                      <span className="font-semibold">{cfg.label}</span>
                    </div>
                  </td>

                  {/* Location */}
                  <td className="py-3 px-3 text-[#202321] whitespace-nowrap font-medium">
                    <div>
                      <span>{stop.location}</span>
                      {stop.coordinate && (
                        <span className="text-[10px] font-mono text-[#858A84] block mt-0.5">
                          {stop.coordinate.latitude.toFixed(4)}, {stop.coordinate.longitude.toFixed(4)}
                        </span>
                      )}
                    </div>
                  </td>

                  {/* Arrival */}
                  <td className="py-3 px-3 font-mono text-[#4B5563] whitespace-nowrap text-xs">
                    {formatTime(stop.start)}
                  </td>

                  {/* Departure */}
                  <td className="py-3 px-3 font-mono text-[#4B5563] whitespace-nowrap text-xs">
                    {formatTime(stop.end)}
                  </td>

                  {/* Duration */}
                  <td className="py-3 px-3 font-mono font-bold text-[#164E3D] whitespace-nowrap text-xs">
                    {formatDuration(stop.durationMinutes)}
                  </td>

                  {/* Route Mile */}
                  <td className="py-3 px-3 font-mono font-bold text-[#202321] text-right whitespace-nowrap text-xs">
                    {stop.milesFromStart.toFixed(1)} mi
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
