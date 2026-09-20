import React from 'react';
import { DutySegment, DutyStatus } from '../types/hos';
import { Clock, MapPin, Gauge, Shield, Bed, Truck, Wrench } from 'lucide-react';

interface Props {
  segments: DutySegment[];
}

const STATUS_CONFIG: Record<DutyStatus, { label: string; borderAccent: string; badge: string; icon: any }> = {
  OFF_DUTY: {
    label: 'Off Duty',
    borderAccent: 'border-l-[#B8BCB7]',
    badge: 'bg-[#F5F5F2] text-[#626862] border-[#D9DAD5]',
    icon: Shield,
  },
  SLEEPER_BERTH: {
    label: 'Sleeper Berth',
    borderAccent: 'border-l-[#60788A]',
    badge: 'bg-[#F0F4F8] text-[#60788A] border-[#60788A]/30',
    icon: Bed,
  },
  DRIVING: {
    label: 'Driving',
    borderAccent: 'border-l-[#245C4A]',
    badge: 'bg-[#EEF4F1] text-[#245C4A] border-[#245C4A]/30',
    icon: Truck,
  },
  ON_DUTY_NOT_DRIVING: {
    label: 'On-Duty',
    borderAccent: 'border-l-[#A66A21]',
    badge: 'bg-[#FEF9EE] text-[#A66A21] border-[#A66A21]/30',
    icon: Wrench,
  },
};

export const SegmentTimeline: React.FC<Props> = ({ segments }) => {
  const formatTime = (isoString: string) => {
    const d = new Date(isoString);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
  };

  const formatDate = (isoString: string) => {
    const d = new Date(isoString);
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  return (
    <div className="bg-white border border-[#D9DAD5] rounded-lg p-5 space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#E7E7E2] pb-3">
        <div>
          <h3 className="text-sm font-semibold text-[#202321] flex items-center gap-2">
            <Clock className="w-4 h-4 text-[#245C4A]" />
            Duty Segments Timeline
          </h3>
          <p className="text-xs text-[#626862] mt-0.5">
            Sequential, minute-accurate duty status events produced by the HOS engine
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          {Object.entries(STATUS_CONFIG).map(([k, cfg]) => (
            <span key={k} className={`px-2 py-0.5 rounded border text-[10px] font-mono font-medium ${cfg.badge}`}>
              {cfg.label}
            </span>
          ))}
        </div>
      </div>

      <div className="space-y-2.5 pt-1">
        {segments.map((seg, idx) => {
          const cfg = STATUS_CONFIG[seg.status] || STATUS_CONFIG.OFF_DUTY;
          const Icon = cfg.icon;

          return (
            <div
              key={idx}
              className={`p-3.5 rounded border border-[#E7E7E2] ${cfg.borderAccent} border-l-4 bg-[#FAFAF8] transition hover:bg-white flex flex-col md:flex-row md:items-center justify-between gap-3`}
            >
              {/* Status & Icon */}
              <div className="flex items-start md:items-center gap-3">
                <div className={`p-1.5 rounded border ${cfg.badge} shrink-0`}>
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-[#202321] text-xs">
                      {seg.reason || cfg.label}
                    </span>
                    <span className={`text-[10px] px-1.5 py-0.2 rounded font-mono font-medium border ${cfg.badge}`}>
                      {cfg.label}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-3 text-xs text-[#626862] mt-0.5">
                    <span className="flex items-center gap-1">
                      <MapPin className="w-3 h-3 text-[#858A84]" />
                      {seg.location}
                    </span>
                    {seg.miles > 0 && (
                      <span className="flex items-center gap-1 text-[#202321] font-mono">
                        <Gauge className="w-3 h-3 text-[#858A84]" />
                        {seg.miles} mi
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Timings */}
              <div className="flex items-center gap-4 text-right self-end md:self-center shrink-0 border-t md:border-t-0 border-[#E7E7E2] pt-2 md:pt-0 w-full md:w-auto justify-between md:justify-end">
                <div className="text-left md:text-right">
                  <div className="font-mono text-xs font-semibold text-[#202321]">
                    {formatDate(seg.start)} {formatTime(seg.start)} → {formatDate(seg.end)} {formatTime(seg.end)}
                  </div>
                  <div className="text-[11px] text-[#626862] mt-0.5 font-mono">
                    Duration: <span className="text-[#202321] font-semibold">{seg.durationHours} hrs</span> ({seg.durationMinutes}m)
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};


