import React, { useState, useMemo } from 'react';
import { DutySegment, DutyStatus } from '../../types/hos';
import {
  STATUS_ROW_Y,
  GRAPH_TOTAL_MINUTES,
  GRAPH_HEIGHT,
  buildDailyLogPath,
  formatMinutesToHM,
  formatMinuteToTimeStr,
} from './dailyLogUtils';
import { Clock, MapPin, Info } from 'lucide-react';

interface Props {
  segments: DutySegment[];
  date?: string;
}

const DUTY_LABELS: Array<{ status: DutyStatus; label: string; y: number; badgeColor: string }> = [
  { status: 'OFF_DUTY', label: '1. Off Duty', y: STATUS_ROW_Y.OFF_DUTY, badgeColor: 'text-[#64748B]' },
  { status: 'SLEEPER_BERTH', label: '2. Sleeper Berth', y: STATUS_ROW_Y.SLEEPER_BERTH, badgeColor: 'text-[#2563EB]' },
  { status: 'DRIVING', label: '3. Driving', y: STATUS_ROW_Y.DRIVING, badgeColor: 'text-[#166534]' },
  { status: 'ON_DUTY_NOT_DRIVING', label: '4. On Duty (Not Driving)', y: STATUS_ROW_Y.ON_DUTY_NOT_DRIVING, badgeColor: 'text-[#D97706]' },
];

export const DailyLogGrid: React.FC<Props> = ({ segments }) => {
  const [hoveredSeg, setHoveredSeg] = useState<{
    segment: DutySegment;
    xStart: number;
    xEnd: number;
  } | null>(null);

  const { pathD, segmentsWithCoords } = useMemo(() => buildDailyLogPath(segments), [segments]);

  // Hourly markers (0 to 24)
  const hours = Array.from({ length: 25 }, (_, i) => {
    let label = '12A';
    if (i === 0 || i === 24) label = '12A';
    else if (i === 12) label = '12P';
    else if (i < 12) label = `${i}A`;
    else label = `${i - 12}P`;
    return { minute: i * 60, label, isMajor: i % 3 === 0 || i === 0 || i === 12 || i === 24 };
  });

  return (
    <div className="space-y-2">
      {/* Grid Container */}
      <div className="overflow-x-auto rounded border border-[#E7E7E2] bg-white p-3">
        <div className="min-w-[760px] flex">
          {/* Left Column: Row Labels */}
          <div className="w-40 shrink-0 pr-3 flex flex-col justify-between py-1 select-none border-r border-[#E7E7E2]">
            {DUTY_LABELS.map(row => (
              <div
                key={row.status}
                className="h-[46px] flex items-center text-[11px] font-semibold text-[#374151] px-2 rounded bg-[#FAFAF8] border border-[#E7E7E2]/80 font-mono"
              >
                <span className={row.badgeColor}>{row.label}</span>
              </div>
            ))}
          </div>

          {/* Right Area: SVG Graph */}
          <div className="flex-1 relative pt-5 pb-4 pl-3">
            <svg
              viewBox={`0 0 ${GRAPH_TOTAL_MINUTES} ${GRAPH_HEIGHT}`}
              className="w-full h-[200px] overflow-visible select-none"
              preserveAspectRatio="none"
            >
              {/* Background Row Lanes */}
              {DUTY_LABELS.map((row, idx) => (
                <rect
                  key={row.status}
                  x="0"
                  y={row.y - 23}
                  width={GRAPH_TOTAL_MINUTES}
                  height="46"
                  className={idx % 2 === 0 ? 'fill-[#FAFAF8]' : 'fill-[#FFFFFF]'}
                />
              ))}

              {/* Horizontal Row Guideline Centered on Statuses */}
              {DUTY_LABELS.map(row => (
                <line
                  key={row.status}
                  x1="0"
                  y1={row.y}
                  x2={GRAPH_TOTAL_MINUTES}
                  y2={row.y}
                  stroke="#E2E8F0"
                  strokeWidth="1"
                  strokeDasharray="2 3"
                />
              ))}

              {/* 30-min Subdivisions */}
              {Array.from({ length: 48 }, (_, i) => {
                const minute = i * 30;
                if (minute % 60 === 0) return null;
                return (
                  <line
                    key={`sub-${minute}`}
                    x1={minute}
                    y1="0"
                    x2={minute}
                    y2={GRAPH_HEIGHT}
                    stroke="#F1F5F9"
                    strokeWidth="0.75"
                    strokeDasharray="2 2"
                  />
                );
              })}

              {/* Hourly Vertical Grid Lines & Labels */}
              {hours.map(h => (
                <g key={`hour-${h.minute}`}>
                  <line
                    x1={h.minute}
                    y1="0"
                    x2={h.minute}
                    y2={GRAPH_HEIGHT}
                    stroke={h.isMajor ? '#CBD5E1' : '#E2E8F0'}
                    strokeWidth={h.isMajor ? '1' : '0.75'}
                  />
                  {/* Top Hour Label */}
                  <text
                    x={h.minute}
                    y="-6"
                    textAnchor="middle"
                    fill={h.isMajor ? '#1E293B' : '#64748B'}
                    fontSize={h.isMajor ? '10' : '9'}
                    fontWeight={h.isMajor ? '600' : 'normal'}
                    fontFamily="monospace"
                  >
                    {h.label}
                  </text>
                </g>
              ))}

              {/* Stepped Status Base Track */}
              <path
                d={pathD}
                fill="none"
                stroke="#CBD5E1"
                strokeWidth="3.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />

              {/* Segment Interaction Lines */}
              {segmentsWithCoords.map((item, idx) => {
                const seg = item.segment;
                const width = Math.max(3, item.xEnd - item.xStart);

                // Semantic stroke color
                let strokeColor = '#64748B';
                if (seg.status === 'DRIVING') strokeColor = '#166534';
                else if (seg.status === 'SLEEPER_BERTH') strokeColor = '#2563EB';
                else if (seg.status === 'ON_DUTY_NOT_DRIVING') strokeColor = '#D97706';

                return (
                  <g
                    key={`seg-${idx}`}
                    className="cursor-pointer"
                    onMouseEnter={() => {
                      setHoveredSeg({
                        segment: seg,
                        xStart: item.xStart,
                        xEnd: item.xEnd,
                      });
                    }}
                    onMouseLeave={() => setHoveredSeg(null)}
                  >
                    {/* Hover Hitbox */}
                    <rect
                      x={item.xStart}
                      y={item.y - 20}
                      width={width}
                      height="40"
                      fill="transparent"
                      className="hover:fill-black/5 transition-colors"
                    />

                    {/* Active Line Overlay */}
                    <line
                      x1={item.xStart}
                      y1={item.y}
                      x2={item.xEnd}
                      y2={item.y}
                      stroke={strokeColor}
                      strokeWidth="4.5"
                      strokeLinecap="round"
                      className="pointer-events-none"
                    />
                  </g>
                );
              })}
            </svg>
          </div>
        </div>
      </div>

      {/* Segment Inspector Bar (Fixed Height to prevent layout jitter / glitching) */}
      <div className="h-11 min-h-[44px] px-3.5 bg-[#FAFAF8] border border-[#E2E3DE] rounded-md text-xs flex items-center justify-between shadow-2xs transition-all overflow-hidden">
        {hoveredSeg ? (
          <>
            <div className="flex items-center gap-2.5 truncate">
              <span
                className={`px-2 py-0.5 rounded font-mono font-semibold uppercase tracking-wider text-[10px] border shrink-0 ${
                  hoveredSeg.segment.status === 'DRIVING'
                    ? 'bg-[#DCFCE7] text-[#166534] border-[#BBF7D0]'
                    : hoveredSeg.segment.status === 'ON_DUTY_NOT_DRIVING'
                    ? 'bg-[#FEF3C7] text-[#D97706] border-[#FDE68A]'
                    : hoveredSeg.segment.status === 'SLEEPER_BERTH'
                    ? 'bg-[#DBEAFE] text-[#2563EB] border-[#BFDBFE]'
                    : 'bg-[#F3F4F6] text-[#4B5563] border-[#E5E7EB]'
                }`}
              >
                {hoveredSeg.segment.status.replace(/_/g, ' ')}
              </span>
              <span className="font-semibold text-[#202321] truncate">
                {hoveredSeg.segment.reason || 'Duty Status'}
              </span>
              {hoveredSeg.segment.location && (
                <span className="text-[#626862] hidden md:flex items-center gap-1 truncate text-[11px]">
                  <MapPin className="w-3 h-3 text-[#858A84] shrink-0" />
                  <span className="truncate">{hoveredSeg.segment.location}</span>
                </span>
              )}
            </div>

            <div className="flex items-center gap-3 font-mono text-[#4B5563] text-[11px] shrink-0">
              <span className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-[#164E3D]" />
                {formatMinuteToTimeStr(hoveredSeg.xStart)} → {formatMinuteToTimeStr(hoveredSeg.xEnd)}
              </span>
              <strong className="text-[#164E3D] font-bold">
                {formatMinutesToHM(hoveredSeg.segment.durationMinutes)}
              </strong>
              {hoveredSeg.segment.miles > 0 && (
                <span className="text-[#202321] font-semibold">({hoveredSeg.segment.miles.toFixed(1)} mi)</span>
              )}
            </div>
          </>
        ) : (
          <div className="flex items-center gap-2 text-[#858A84] text-[11px]">
            <Info className="w-3.5 h-3.5 text-[#858A84]" />
            <span>Hover over any segment in the 24-hour graph to inspect exact duty times, durations, and location details.</span>
          </div>
        )}
      </div>
    </div>
  );
};
