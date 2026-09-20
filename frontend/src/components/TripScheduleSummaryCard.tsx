import React from 'react';
import { TripScheduleSummary } from '../types/tripSchedule';
import { Check, Download } from 'lucide-react';

interface Props {
  summary: TripScheduleSummary;
  stopsCount?: number;
  onDownloadPdf?: () => void;
  isDownloadingPdf?: boolean;
}

export const TripScheduleSummaryCard: React.FC<Props> = ({
  summary,
  stopsCount = 4,
  onDownloadPdf,
  isDownloadingPdf = false,
}) => {
  const cyclePercent = Math.min(100, Math.round((summary.finalCycleUsed / 70.0) * 100));

  return (
    <div className="bg-white border border-[#E2E3DE] rounded-lg p-5 shadow-xs h-full flex flex-col justify-between">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-[#E7E7E2] flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-[#164E3D]/10 text-[#164E3D] flex items-center justify-center">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
            </svg>
          </div>
          <div>
            <h3 className="text-xs font-bold text-[#202321] tracking-tight">Trip Overview</h3>
            <p className="text-[10px] text-[#626862] font-mono">HOS & Operational Metrics</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {onDownloadPdf && (
            <button
              onClick={onDownloadPdf}
              disabled={isDownloadingPdf}
              className="flex items-center gap-1.5 px-2.5 py-1 bg-white hover:bg-[#FAFAF8] text-[#164E3D] rounded border border-[#164E3D]/30 text-xs font-semibold transition cursor-pointer shadow-2xs disabled:opacity-60"
              title="Download full trip schedule and FMCSA daily logs as PDF"
            >
              <Download className={`w-3.5 h-3.5 ${isDownloadingPdf ? 'animate-bounce' : ''}`} />
              <span>{isDownloadingPdf ? 'Exporting...' : 'PDF Report'}</span>
            </button>
          )}

          {/* HOS Compliant Status Pill */}
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-[#DCFCE7] text-[#166534] border border-[#BBF7D0] text-xs font-semibold shadow-2xs">
            <Check className="w-3.5 h-3.5 stroke-[2.5]" />
            <span>HOS Compliant</span>
          </div>
        </div>
      </div>

      {/* 3x2 Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-y-5 gap-x-4 my-auto py-2">
        {/* Total Distance */}
        <div className="p-2.5 rounded bg-[#FAFAF8] border border-[#E7E7E2]">
          <div className="text-lg font-bold text-[#202321] font-mono tracking-tight leading-tight">
            {summary.totalDistanceMiles.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}{' '}
            <span className="text-xs font-normal text-[#626862]">mi</span>
          </div>
          <div className="text-[11px] text-[#626862] font-medium mt-1">Total Distance</div>
        </div>

        {/* Driving Time */}
        <div className="p-2.5 rounded bg-[#FAFAF8] border border-[#E7E7E2]">
          <div className="text-lg font-bold text-[#164E3D] font-mono tracking-tight leading-tight">
            {summary.totalDrivingHours}
          </div>
          <div className="text-[11px] text-[#626862] font-medium mt-1">Driving Time</div>
        </div>

        {/* Total Elapsed */}
        <div className="p-2.5 rounded bg-[#FAFAF8] border border-[#E7E7E2]">
          <div className="text-lg font-bold text-[#202321] font-mono tracking-tight leading-tight">
            {summary.totalElapsedHours}
          </div>
          <div className="text-[11px] text-[#626862] font-medium mt-1">Total Elapsed</div>
        </div>

        {/* Trip Duration */}
        <div className="p-2.5 rounded bg-[#FAFAF8] border border-[#E7E7E2]">
          <div className="text-lg font-bold text-[#202321] font-mono tracking-tight leading-tight">
            {summary.daysCount} <span className="text-xs font-normal text-[#626862]">days</span>
          </div>
          <div className="text-[11px] text-[#626862] font-medium mt-1">Trip Duration</div>
        </div>

        {/* Planned Stops */}
        <div className="p-2.5 rounded bg-[#FAFAF8] border border-[#E7E7E2]">
          <div className="text-lg font-bold text-[#202321] font-mono tracking-tight leading-tight">
            {stopsCount}
          </div>
          <div className="text-[11px] text-[#626862] font-medium mt-1">Planned Stops</div>
        </div>

        {/* Cycle Used */}
        <div className="p-2.5 rounded bg-[#FAFAF8] border border-[#E7E7E2]">
          <div className="text-lg font-bold text-[#202321] font-mono tracking-tight leading-tight">
            {summary.finalCycleUsed.toFixed(1)}h <span className="text-xs font-normal text-[#626862]">/ 70h</span>
          </div>
          <div className="text-[11px] text-[#626862] font-medium mt-1">Cycle Used</div>
        </div>
      </div>

      {/* Cycle Progress Bar Summary */}
      <div className="pt-3 border-t border-[#E7E7E2] mt-auto">
        <div className="flex items-center justify-between text-xs font-mono mb-1.5">
          <span className="text-[#626862]">70-Hour Duty Cycle</span>
          <span className="font-semibold text-[#164E3D]">{summary.cycleHoursRemaining.toFixed(1)}h remaining</span>
        </div>
        <div className="w-full bg-[#E7E7E2] h-2 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-300 ${
              cyclePercent > 90 ? 'bg-[#DC2626]' : cyclePercent > 75 ? 'bg-[#D97706]' : 'bg-[#164E3D]'
            }`}
            style={{ width: `${cyclePercent}%` }}
          />
        </div>
      </div>
    </div>
  );
};
