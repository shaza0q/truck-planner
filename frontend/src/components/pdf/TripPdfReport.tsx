import React from 'react';
import { TripScheduleSummary } from '../../types/tripSchedule';
import { Stop, DailyLog, DutyStatus, DutySegment } from '../../types/hos';
import { RoutePlanResponse } from '../../types/routing';
import { formatMinutesToHM } from '../daily-log/dailyLogUtils';

interface Props {
  summary: TripScheduleSummary | null;
  stops: Stop[];
  dailyLogs: DailyLog[];
  routePlan: RoutePlanResponse | null;
  reportRef: React.RefObject<HTMLDivElement>;
}

// Coordinate constants for the PDF SVG log grid
const SVG_TOTAL_MIN = 1440;
const SVG_GRID_LEFT = 160; // Space for left labels
const SVG_GRID_WIDTH = 1280;
const SVG_TOTAL_WIDTH = SVG_GRID_LEFT + SVG_GRID_WIDTH; // 1440
const SVG_ROW_Y: Record<DutyStatus, number> = {
  OFF_DUTY: 45,
  SLEEPER_BERTH: 85,
  DRIVING: 125,
  ON_DUTY_NOT_DRIVING: 165,
};
const SVG_HEIGHT = 205;

const DUTY_ROW_CONFIG: Array<{ status: DutyStatus; label: string; y: number; textCol: string }> = [
  { status: 'OFF_DUTY', label: '1. OFF DUTY', y: SVG_ROW_Y.OFF_DUTY, textCol: '#475569' },
  { status: 'SLEEPER_BERTH', label: '2. SLEEPER BERTH', y: SVG_ROW_Y.SLEEPER_BERTH, textCol: '#1D4ED8' },
  { status: 'DRIVING', label: '3. DRIVING', y: SVG_ROW_Y.DRIVING, textCol: '#15803D' },
  { status: 'ON_DUTY_NOT_DRIVING', label: '4. ON DUTY (NOT DRIVING)', y: SVG_ROW_Y.ON_DUTY_NOT_DRIVING, textCol: '#B45309' },
];

/**
 * Builds the SVG path for the PDF diagram using scaled coordinates
 */
function buildPdfDailyLogPath(segments: DutySegment[]): string {
  if (!segments || segments.length === 0) return '';
  const commands: string[] = [];
  let lastY: number | null = null;

  segments.forEach((seg, idx) => {
    const startM = seg.startMinute ?? 0;
    const endM = seg.endMinute ?? (startM + seg.durationMinutes);
    const y = SVG_ROW_Y[seg.status] ?? SVG_ROW_Y.OFF_DUTY;

    // Scale minute to grid position
    const x1 = SVG_GRID_LEFT + (startM / SVG_TOTAL_MIN) * SVG_GRID_WIDTH;
    const x2 = SVG_GRID_LEFT + (endM / SVG_TOTAL_MIN) * SVG_GRID_WIDTH;

    if (idx === 0) {
      commands.push(`M ${x1.toFixed(1)} ${y}`);
    } else if (lastY !== null && lastY !== y) {
      commands.push(`V ${y}`);
    }

    commands.push(`H ${x2.toFixed(1)}`);
    lastY = y;
  });

  return commands.join(' ');
}

export const TripPdfReport: React.FC<Props> = ({
  summary,
  stops,
  dailyLogs,
  routePlan,
  reportRef,
}) => {
  const rawLocations = (routePlan as any)?.locations || (routePlan as any)?.route?.locations || {};
  const originStr = rawLocations.current?.query || 'Dallas, TX';
  const pickupStr = rawLocations.pickup?.query || 'Houston, TX';
  const dropoffStr = rawLocations.dropoff?.query || 'Atlanta, GA';

  const totalPages = 1 + (dailyLogs.length > 0 ? dailyLogs.length : 1);

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

  // Standard hour ticks (0 to 24)
  const hourTicks = Array.from({ length: 25 }, (_, i) => {
    let label = `${i}`;
    if (i === 0 || i === 24) label = 'Mid';
    else if (i === 12) label = 'Noon';
    else if (i > 12) label = `${i - 12}`;

    const x = SVG_GRID_LEFT + (i / 24) * SVG_GRID_WIDTH;
    const isMajor = i % 3 === 0 || i === 0 || i === 12 || i === 24;
    return { hour: i, label, x, isMajor };
  });

  return (
    <div
      style={{ position: 'absolute', left: '-9999px', top: '-9999px' }}
      aria-hidden="true"
    >
      <div ref={reportRef}>
        {/* ================================================================= */}
        {/* PAGE 1: TRIP OVERVIEW & SCHEDULED STOPS */}
        {/* ================================================================= */}
        <div
          className="pdf-page"
          style={{
            width: '820px',
            minHeight: '1130px',
            backgroundColor: '#FFFFFF',
            color: '#1E293B',
            fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            padding: '36px 40px',
            boxSizing: 'border-box',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            pageBreakAfter: 'always',
          }}
        >
          <div>
            {/* Header */}
            <div style={{ borderBottom: '2.5px solid #164E3D', paddingBottom: '14px', marginBottom: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <h1 style={{ margin: 0, fontSize: '20px', fontWeight: 800, color: '#164E3D', letterSpacing: '-0.4px' }}>
                    TRUCK TRIP PLANNER — FMCSA LOG REPORT
                  </h1>
                  <p style={{ margin: '3px 0 0 0', fontSize: '10.5px', color: '#64748B', fontWeight: 600 }}>
                    Official Record of Duty Status (RODS) & Waypoint Itinerary • 49 CFR § 395.8
                  </p>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ display: 'inline-block', backgroundColor: '#F0FDF4', color: '#166534', border: '1px solid #BBF7D0', padding: '3px 9px', borderRadius: '4px', fontSize: '10px', fontWeight: 700 }}>
                    ✓ HOS COMPLIANT
                  </span>
                  <p style={{ margin: '4px 0 0 0', fontSize: '9px', color: '#94A3B8', fontFamily: 'monospace' }}>
                    Generated: {new Date().toLocaleString()}
                  </p>
                </div>
              </div>

              {/* Corridor Route Strip */}
              <div style={{ marginTop: '12px', padding: '8px 12px', backgroundColor: '#F8FAFC', borderRadius: '6px', border: '1px solid #E2E8F0', display: 'flex', justifyContent: 'space-between', fontSize: '11px' }}>
                <div><strong style={{ color: '#475569' }}>Origin:</strong> {originStr}</div>
                <div><strong style={{ color: '#475569' }}>Pickup (1h):</strong> {pickupStr}</div>
                <div><strong style={{ color: '#475569' }}>Dropoff (1h):</strong> {dropoffStr}</div>
              </div>
            </div>

            {/* 1. Trip Overview Metrics */}
            {summary && (
              <div style={{ marginBottom: '24px' }}>
                <h2 style={{ fontSize: '12px', fontWeight: 700, color: '#0F172A', margin: '0 0 8px 0', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  1. Trip Overview & Operational Metrics
                </h2>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px' }}>
                  <div style={{ backgroundColor: '#F8FAFC', padding: '10px', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                    <div style={{ fontSize: '9px', fontWeight: 600, color: '#64748B', textTransform: 'uppercase' }}>Total Distance</div>
                    <div style={{ fontSize: '16px', fontWeight: 800, color: '#0F172A', marginTop: '2px' }}>
                      {summary.totalDistanceMiles.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} <span style={{ fontSize: '10px', fontWeight: 500, color: '#64748B' }}>mi</span>
                    </div>
                  </div>

                  <div style={{ backgroundColor: '#F8FAFC', padding: '10px', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                    <div style={{ fontSize: '9px', fontWeight: 600, color: '#64748B', textTransform: 'uppercase' }}>Driving Time</div>
                    <div style={{ fontSize: '16px', fontWeight: 800, color: '#166534', marginTop: '2px' }}>
                      {summary.totalDrivingHours} <span style={{ fontSize: '10px', fontWeight: 500, color: '#64748B' }}>hrs</span>
                    </div>
                  </div>

                  <div style={{ backgroundColor: '#F8FAFC', padding: '10px', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                    <div style={{ fontSize: '9px', fontWeight: 600, color: '#64748B', textTransform: 'uppercase' }}>Total Elapsed</div>
                    <div style={{ fontSize: '16px', fontWeight: 800, color: '#0F172A', marginTop: '2px' }}>
                      {summary.totalElapsedHours} <span style={{ fontSize: '10px', fontWeight: 500, color: '#64748B' }}>hrs</span>
                    </div>
                  </div>

                  <div style={{ backgroundColor: '#F8FAFC', padding: '10px', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                    <div style={{ fontSize: '9px', fontWeight: 600, color: '#64748B', textTransform: 'uppercase' }}>70h Cycle Used</div>
                    <div style={{ fontSize: '16px', fontWeight: 800, color: '#0F172A', marginTop: '2px' }}>
                      {summary.finalCycleUsed.toFixed(1)}h <span style={{ fontSize: '10px', fontWeight: 500, color: '#64748B' }}>/ 70h</span>
                    </div>
                    <div style={{ fontSize: '9px', color: '#166534', fontWeight: 600, marginTop: '2px' }}>
                      {summary.cycleHoursRemaining.toFixed(1)}h remaining
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* 2. Scheduled Stops Table */}
            {stops && stops.length > 0 && (
              <div>
                <h2 style={{ fontSize: '12px', fontWeight: 700, color: '#0F172A', margin: '0 0 8px 0', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  2. Scheduled Stops & Waypoint Itinerary ({stops.length} Planned Stops)
                </h2>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '10px', border: '1px solid #E2E8F0' }}>
                  <thead>
                    <tr style={{ backgroundColor: '#F1F5F9', borderBottom: '1px solid #CBD5E1', textAlign: 'left' }}>
                      <th style={{ padding: '6px 8px', fontWeight: 700, width: '28px', textAlign: 'center' }}>#</th>
                      <th style={{ padding: '6px 8px', fontWeight: 700, width: '105px' }}>Activity</th>
                      <th style={{ padding: '6px 8px', fontWeight: 700 }}>Location</th>
                      <th style={{ padding: '6px 8px', fontWeight: 700, width: '110px' }}>Arrival</th>
                      <th style={{ padding: '6px 8px', fontWeight: 700, width: '110px' }}>Departure</th>
                      <th style={{ padding: '6px 8px', fontWeight: 700, width: '60px' }}>Duration</th>
                      <th style={{ padding: '6px 8px', fontWeight: 700, width: '55px', textAlign: 'right' }}>Miles</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stops.map((stop, idx) => {
                      let badgeBg = '#F1F5F9';
                      let badgeText = '#334155';
                      if (stop.type === 'PICKUP') { badgeBg = '#DCFCE7'; badgeText = '#166534'; }
                      else if (stop.type === 'DROPOFF') { badgeBg = '#FEE2E2'; badgeText = '#991B1B'; }
                      else if (stop.type === 'FUEL') { badgeBg = '#FEF3C7'; badgeText = '#92400E'; }
                      else if (stop.type === 'REST') { badgeBg = '#DBEAFE'; badgeText = '#1E40AF'; }
                      else if (stop.type === 'BREAK') { badgeBg = '#F1F5F9'; badgeText = '#334155'; }

                      return (
                        <tr key={idx} style={{ borderBottom: '1px solid #E2E8F0', backgroundColor: idx % 2 === 0 ? '#FFFFFF' : '#F8FAFC' }}>
                          <td style={{ padding: '6px 8px', textAlign: 'center', fontWeight: 700, color: '#64748B' }}>{idx + 1}</td>
                          <td style={{ padding: '6px 8px' }}>
                            <span style={{ backgroundColor: badgeBg, color: badgeText, padding: '2px 6px', borderRadius: '4px', fontWeight: 700, fontSize: '9px' }}>
                              {stop.type}
                            </span>
                          </td>
                          <td style={{ padding: '6px 8px', fontWeight: 600 }}>{stop.location}</td>
                          <td style={{ padding: '6px 8px', color: '#475569' }}>{formatTime(stop.start)}</td>
                          <td style={{ padding: '6px 8px', color: '#475569' }}>{formatTime(stop.end)}</td>
                          <td style={{ padding: '6px 8px', fontWeight: 600 }}>{formatDuration(stop.durationMinutes)}</td>
                          <td style={{ padding: '6px 8px', textAlign: 'right', fontWeight: 700 }}>{stop.milesFromStart.toFixed(1)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Page 1 Footer */}
          <div style={{ borderTop: '1px solid #E2E8F0', paddingTop: '10px', display: 'flex', justifyContent: 'space-between', fontSize: '9px', color: '#94A3B8' }}>
            <div>Spotter Truck Trip Planner • FMCSA 49 CFR Part 395 Record of Duty Status</div>
            <div>Page 1 of {totalPages}</div>
          </div>
        </div>

        {/* ================================================================= */}
        {/* PAGES 2..N: DRIVER DAILY LOGS (ONE PAGE PER DAY) */}
        {/* ================================================================= */}
        {dailyLogs.map((log, dayIdx) => {
          const pathD = buildPdfDailyLogPath(log.segments || []);
          const offDutyMin = log.totals.offDutyMinutes ?? Math.round(log.totals.offDuty * 60);
          const sleeperMin = log.totals.sleeperBerthMinutes ?? Math.round(log.totals.sleeperBerth * 60);
          const drivingMin = log.totals.drivingMinutes ?? Math.round(log.totals.driving * 60);
          const onDutyMin = log.totals.onDutyNotDrivingMinutes ?? Math.round(log.totals.onDutyNotDriving * 60);
          const pageNum = dayIdx + 2;

          return (
            <div
              key={log.date || dayIdx}
              className="pdf-page"
              style={{
                width: '820px',
                minHeight: '1130px',
                backgroundColor: '#FFFFFF',
                color: '#1E293B',
                fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                padding: '36px 40px',
                boxSizing: 'border-box',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                pageBreakAfter: dayIdx === dailyLogs.length - 1 ? 'auto' : 'always',
              }}
            >
              <div>
                {/* Header */}
                <div style={{ borderBottom: '2.5px solid #164E3D', paddingBottom: '12px', marginBottom: '18px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <h1 style={{ margin: 0, fontSize: '18px', fontWeight: 800, color: '#164E3D', letterSpacing: '-0.3px' }}>
                        DAY {dayIdx + 1} DRIVER'S DAILY LOG — 24-HOUR DUTY RECORD
                      </h1>
                      <p style={{ margin: '3px 0 0 0', fontSize: '10.5px', color: '#64748B', fontWeight: 600 }}>
                        Date: <strong>{log.date}</strong> • FMCSA 49 CFR § 395.8 (00:00 to 24:00)
                      </p>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <span style={{ display: 'inline-block', backgroundColor: '#F8FAFC', color: '#475569', border: '1px solid #E2E8F0', padding: '3px 8px', borderRadius: '4px', fontSize: '10px', fontWeight: 700 }}>
                        {log.totalMiles.toFixed(1)} miles driven
                      </span>
                    </div>
                  </div>
                </div>

                {/* Daily Recap Totals */}
                <div style={{ marginBottom: '16px' }}>
                  <h2 style={{ fontSize: '11px', fontWeight: 700, color: '#0F172A', margin: '0 0 8px 0', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    Daily Duty Status Recap (Total 24.0 Hours)
                  </h2>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px' }}>
                    <div style={{ backgroundColor: '#F8FAFC', border: '1px solid #E2E8F0', padding: '8px', borderRadius: '6px' }}>
                      <div style={{ fontSize: '9px', fontWeight: 600, color: '#64748B', textTransform: 'uppercase' }}>1. Off Duty</div>
                      <div style={{ fontSize: '14px', fontWeight: 800, color: '#334155', marginTop: '2px', whiteSpace: 'nowrap' }}>
                        {formatMinutesToHM(offDutyMin)}
                      </div>
                    </div>

                    <div style={{ backgroundColor: '#EFF6FF', border: '1px solid #BFDBFE', padding: '8px', borderRadius: '6px' }}>
                      <div style={{ fontSize: '9px', fontWeight: 600, color: '#1E40AF', textTransform: 'uppercase' }}>2. Sleeper Berth</div>
                      <div style={{ fontSize: '14px', fontWeight: 800, color: '#1D4ED8', marginTop: '2px', whiteSpace: 'nowrap' }}>
                        {formatMinutesToHM(sleeperMin)}
                      </div>
                    </div>

                    <div style={{ backgroundColor: '#F0FDF4', border: '1px solid #BBF7D0', padding: '8px', borderRadius: '6px' }}>
                      <div style={{ fontSize: '9px', fontWeight: 600, color: '#166534', textTransform: 'uppercase' }}>3. Driving</div>
                      <div style={{ fontSize: '14px', fontWeight: 800, color: '#15803D', marginTop: '2px', whiteSpace: 'nowrap' }}>
                        {formatMinutesToHM(drivingMin)}
                      </div>
                    </div>

                    <div style={{ backgroundColor: '#FEF3C7', border: '1px solid #FDE68A', padding: '8px', borderRadius: '6px' }}>
                      <div style={{ fontSize: '9px', fontWeight: 600, color: '#92400E', textTransform: 'uppercase' }}>4. On Duty</div>
                      <div style={{ fontSize: '14px', fontWeight: 800, color: '#B45309', marginTop: '2px', whiteSpace: 'nowrap' }}>
                        {formatMinutesToHM(onDutyMin)}
                      </div>
                    </div>

                    <div style={{ backgroundColor: '#0F172A', color: '#FFFFFF', padding: '8px', borderRadius: '6px' }}>
                      <div style={{ fontSize: '9px', fontWeight: 600, color: '#94A3B8', textTransform: 'uppercase' }}>Daily Total</div>
                      <div style={{ fontSize: '14px', fontWeight: 800, color: '#FFFFFF', marginTop: '2px' }}>
                        24.0 hrs
                      </div>
                    </div>
                  </div>
                </div>

                {/* 24-Hour Stepped SVG Grid Diagram */}
                <div style={{ marginBottom: '18px' }}>
                  <h2 style={{ fontSize: '11px', fontWeight: 700, color: '#0F172A', margin: '0 0 6px 0', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    24-Hour Continuous Duty Graph (00:00 to 24:00)
                  </h2>

                  <div style={{ border: '1px solid #CBD5E1', borderRadius: '6px', overflow: 'hidden', backgroundColor: '#FAFAF8', padding: '8px 10px' }}>
                    <svg
                      viewBox={`0 0 ${SVG_TOTAL_WIDTH} ${SVG_HEIGHT}`}
                      style={{ width: '100%', height: '175px' }}
                      preserveAspectRatio="none"
                    >
                      {/* Alternating Row Lanes */}
                      {DUTY_ROW_CONFIG.map((row, idx) => (
                        <rect
                          key={row.status}
                          x={SVG_GRID_LEFT}
                          y={row.y - 20}
                          width={SVG_GRID_WIDTH}
                          height="40"
                          fill={idx % 2 === 0 ? '#F8FAFC' : '#FFFFFF'}
                        />
                      ))}

                      {/* Left Labels */}
                      {DUTY_ROW_CONFIG.map(row => (
                        <text
                          key={row.status}
                          x="8"
                          y={row.y + 4}
                          fontSize="13"
                          fontWeight="700"
                          fill={row.textCol}
                          fontFamily="Inter, system-ui, sans-serif"
                        >
                          {row.label}
                        </text>
                      ))}

                      {/* Horizontal Guidelines */}
                      {DUTY_ROW_CONFIG.map(row => (
                        <line
                          key={row.status}
                          x1={SVG_GRID_LEFT}
                          y1={row.y}
                          x2={SVG_TOTAL_WIDTH}
                          y2={row.y}
                          stroke="#E2E8F0"
                          strokeWidth="1.2"
                          strokeDasharray="3 3"
                        />
                      ))}

                      {/* 1-Hour Vertical Tick Guidelines */}
                      {hourTicks.map(h => (
                        <g key={h.hour}>
                          <line
                            x1={h.x}
                            y1="25"
                            x2={h.x}
                            y2="185"
                            stroke={h.isMajor ? '#94A3B8' : '#E2E8F0'}
                            strokeWidth={h.isMajor ? '1.5' : '0.8'}
                            opacity={h.isMajor ? '0.8' : '0.5'}
                          />
                          <text
                            x={h.x}
                            y="200"
                            textAnchor="middle"
                            fontSize="12"
                            fontWeight={h.isMajor ? '700' : '500'}
                            fill={h.isMajor ? '#334155' : '#64748B'}
                            fontFamily="Inter, monospace, sans-serif"
                          >
                            {h.label}
                          </text>
                        </g>
                      ))}

                      {/* Stepped Continuous Duty Status Line */}
                      <path
                        d={pathD}
                        fill="none"
                        stroke="#164E3D"
                        strokeWidth="3.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </div>
                </div>

                {/* Duty Segments Table for this Day */}
                {log.segments && log.segments.length > 0 && (
                  <div>
                    <h2 style={{ fontSize: '11px', fontWeight: 700, color: '#0F172A', margin: '0 0 6px 0', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      Duty Segments & Remarks ({log.segments.length} Logged Events)
                    </h2>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '9.5px', border: '1px solid #E2E8F0' }}>
                      <thead>
                        <tr style={{ backgroundColor: '#F1F5F9', borderBottom: '1px solid #CBD5E1', textAlign: 'left', color: '#475569' }}>
                          <th style={{ padding: '5px 8px', width: '85px' }}>Start Time</th>
                          <th style={{ padding: '5px 8px', width: '85px' }}>End Time</th>
                          <th style={{ padding: '5px 8px', width: '120px' }}>Duty Status</th>
                          <th style={{ padding: '5px 8px' }}>Location / Reason</th>
                          <th style={{ padding: '5px 8px', width: '60px', textAlign: 'right' }}>Duration</th>
                          <th style={{ padding: '5px 8px', width: '55px', textAlign: 'right' }}>Miles</th>
                        </tr>
                      </thead>
                      <tbody>
                        {log.segments.map((seg, sIdx) => {
                          let statusColor = '#475569';
                          if (seg.status === 'DRIVING') statusColor = '#166534';
                          else if (seg.status === 'ON_DUTY_NOT_DRIVING') statusColor = '#B45309';
                          else if (seg.status === 'SLEEPER_BERTH') statusColor = '#1D4ED8';

                          return (
                            <tr key={sIdx} style={{ borderBottom: '1px solid #F1F5F9', backgroundColor: sIdx % 2 === 0 ? '#FFFFFF' : '#F8FAFC' }}>
                              <td style={{ padding: '4px 8px', fontFamily: 'monospace', fontWeight: 600 }}>{seg.start ? new Date(seg.start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }) : '--'}</td>
                              <td style={{ padding: '4px 8px', fontFamily: 'monospace', fontWeight: 600 }}>{seg.end ? new Date(seg.end).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }) : '--'}</td>
                              <td style={{ padding: '4px 8px', fontWeight: 700, color: statusColor }}>{seg.status}</td>
                              <td style={{ padding: '4px 8px', color: '#334155' }}>{seg.location || seg.reason || 'Transit Corridor'}</td>
                              <td style={{ padding: '4px 8px', textAlign: 'right', fontWeight: 600 }}>{formatMinutesToHM(seg.durationMinutes)}</td>
                              <td style={{ padding: '4px 8px', textAlign: 'right', fontWeight: 700 }}>{seg.miles ? `${seg.miles.toFixed(1)}` : '0.0'}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Day Page Footer */}
              <div style={{ borderTop: '1px solid #E2E8F0', paddingTop: '10px', display: 'flex', justifyContent: 'space-between', fontSize: '9px', color: '#94A3B8' }}>
                <div>Spotter Truck Trip Planner • Day {dayIdx + 1} Record of Duty Status ({log.date})</div>
                <div>Page {pageNum} of {totalPages}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
