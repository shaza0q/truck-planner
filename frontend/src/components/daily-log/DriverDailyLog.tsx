import React, { useState } from 'react';
import { DailyLog } from '../../types/hos';
import { DailyLogGrid } from './DailyLogGrid';
import { ClipboardList, ChevronLeft, ChevronRight, ShieldCheck, Download } from 'lucide-react';
import { formatMinutesToHM } from './dailyLogUtils';

interface Props {
  dailyLogs: DailyLog[];
  onDownloadPdf?: () => void;
  isDownloadingPdf?: boolean;
}

export const DriverDailyLog: React.FC<Props> = ({
  dailyLogs,
  onDownloadPdf,
  isDownloadingPdf = false,
}) => {
  const [selectedDayIdx, setSelectedDayIdx] = useState<number>(0);

  if (!dailyLogs || dailyLogs.length === 0) {
    return (
      <div className="bg-white border border-[#E2E3DE] rounded-lg p-8 text-center space-y-2 w-full flex flex-col items-center justify-center">
        <ClipboardList className="w-8 h-8 text-[#858A84] mx-auto" />
        <h3 className="text-sm font-bold text-[#202321]">No Daily Driver Logs Available</h3>
        <p className="text-xs text-[#626862]">
          Plan a trip to generate FMCSA 24-hour daily logs.
        </p>
      </div>
    );
  }

  const activeLog = dailyLogs[Math.min(selectedDayIdx, dailyLogs.length - 1)];

  const formatDayLabel = (log: DailyLog, idx: number) => {
    try {
      const d = new Date(log.date + 'T00:00:00');
      const monthDay = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      return `Day ${idx + 1} (${monthDay})`;
    } catch {
      return `Day ${idx + 1}`;
    }
  };

  const formatDateFull = (dateStr: string) => {
    try {
      const d = new Date(dateStr + 'T00:00:00');
      return d.toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  const offDutyMin = activeLog.totals.offDutyMinutes ?? Math.round(activeLog.totals.offDuty * 60);
  const sleeperMin = activeLog.totals.sleeperBerthMinutes ?? Math.round(activeLog.totals.sleeperBerth * 60);
  const drivingMin = activeLog.totals.drivingMinutes ?? Math.round(activeLog.totals.driving * 60);
  const onDutyMin = activeLog.totals.onDutyNotDrivingMinutes ?? Math.round(activeLog.totals.onDutyNotDriving * 60);
  const totalMin = offDutyMin + sleeperMin + drivingMin + onDutyMin;

  return (
    <div className="bg-white border border-[#E2E3DE] rounded-lg p-4 sm:p-5 shadow-xs flex flex-col justify-between w-full space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#E7E7E2]">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded-full bg-[#164E3D]/10 text-[#164E3D] flex items-center justify-center">
            <ClipboardList className="w-3.5 h-3.5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-[#202321] tracking-tight">
                Driver's Daily Log
              </h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#FAFAF8] text-[#626862] border border-[#E7E7E2] uppercase font-semibold">
                FMCSA 49 CFR § 395.8
              </span>
            </div>
            <p className="text-[11px] text-[#626862]">
              {formatDateFull(activeLog.date)} • 24-hour continuous duty status record (00:00 to 24:00)
            </p>
          </div>
        </div>

        {/* Day Selector Pills & Controls */}
        <div className="flex items-center gap-1.5 self-start sm:self-auto flex-wrap">
          {onDownloadPdf && (
            <button
              onClick={onDownloadPdf}
              disabled={isDownloadingPdf}
              className="flex items-center gap-1.5 px-2.5 py-1 bg-white hover:bg-[#FAFAF8] text-[#164E3D] rounded border border-[#164E3D]/30 text-xs font-semibold transition cursor-pointer shadow-2xs mr-2 disabled:opacity-60"
              title="Download full trip schedule and FMCSA daily logs as PDF"
            >
              <Download className={`w-3.5 h-3.5 ${isDownloadingPdf ? 'animate-bounce' : ''}`} />
              <span>{isDownloadingPdf ? 'Exporting...' : 'Export PDF'}</span>
            </button>
          )}

          {dailyLogs.map((log, idx) => (
            <button
              key={log.date || idx}
              onClick={() => setSelectedDayIdx(idx)}
              className={`px-3 py-1 rounded text-xs font-mono font-medium transition cursor-pointer ${
                idx === selectedDayIdx
                  ? 'bg-[#164E3D] text-white font-semibold shadow-2xs'
                  : 'bg-[#F4F4F0] text-[#626862] hover:bg-[#EAEAE5]'
              }`}
            >
              {formatDayLabel(log, idx)}
            </button>
          ))}

          {dailyLogs.length > 1 && (
            <div className="flex items-center gap-1 ml-1.5">
              <button
                disabled={selectedDayIdx === 0}
                onClick={() => setSelectedDayIdx(p => Math.max(0, p - 1))}
                className="p-1.5 rounded hover:bg-[#F4F4F0] text-[#626862] border border-[#E7E7E2] disabled:opacity-30 cursor-pointer"
                title="Previous day"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
              </button>
              <button
                disabled={selectedDayIdx === dailyLogs.length - 1}
                onClick={() => setSelectedDayIdx(p => Math.min(dailyLogs.length - 1, p + 1))}
                className="p-1.5 rounded hover:bg-[#F4F4F0] text-[#626862] border border-[#E7E7E2] disabled:opacity-30 cursor-pointer"
                title="Next day"
              >
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* 24-Hour Stepped SVG Grid (Full Width) */}
      <div className="py-1">
        <DailyLogGrid segments={activeLog.segments} date={activeLog.date} />
      </div>

      {/* Daily Totals Bottom Row */}
      <div className="pt-3 border-t border-[#E7E7E2]">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] uppercase font-mono text-[#858A84] font-semibold tracking-wider">
            Daily Duty Totals ({activeLog.totalMiles.toFixed(1)} miles driven)
          </span>
          <span className="flex items-center gap-1 text-[11px] font-mono text-[#164E3D] font-semibold">
            <ShieldCheck className="w-3.5 h-3.5 text-[#164E3D]" />
            {formatMinutesToHM(totalMin)} / 24h 00m Total
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {/* Off Duty */}
          <div className="p-2.5 bg-[#FAFAF8] rounded border border-[#E7E7E2] pl-3 border-l-3 border-l-[#94A3B8]">
            <div className="text-sm font-bold font-mono text-[#202321]">
              {formatMinutesToHM(offDutyMin)}
            </div>
            <div className="text-[11px] text-[#626862] mt-0.5">1. Off Duty</div>
          </div>

          {/* Sleeper Berth */}
          <div className="p-2.5 bg-[#FAFAF8] rounded border border-[#E7E7E2] pl-3 border-l-3 border-l-[#2563EB]">
            <div className="text-sm font-bold font-mono text-[#2563EB]">
              {formatMinutesToHM(sleeperMin)}
            </div>
            <div className="text-[11px] text-[#626862] mt-0.5">2. Sleeper Berth</div>
          </div>

          {/* Driving */}
          <div className="p-2.5 bg-[#FAFAF8] rounded border border-[#E7E7E2] pl-3 border-l-3 border-l-[#164E3D]">
            <div className="text-sm font-bold font-mono text-[#164E3D]">
              {formatMinutesToHM(drivingMin)}
            </div>
            <div className="text-[11px] text-[#626862] mt-0.5">3. Driving</div>
          </div>

          {/* On Duty */}
          <div className="p-2.5 bg-[#FAFAF8] rounded border border-[#E7E7E2] pl-3 border-l-3 border-l-[#D97706]">
            <div className="text-sm font-bold font-mono text-[#D97706]">
              {formatMinutesToHM(onDutyMin)}
            </div>
            <div className="text-[11px] text-[#626862] mt-0.5">4. On Duty (Not Driving)</div>
          </div>
        </div>
      </div>
    </div>
  );
};
