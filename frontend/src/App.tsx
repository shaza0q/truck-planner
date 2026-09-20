import React, { useState, useEffect, useRef } from 'react';
import { TripSchedule } from './types/tripSchedule';
import { planTripSchedule } from './services/tripScheduleApi';
import { mapTripError, MappedError } from './utils/errorMapper';
import { TripScheduleSummaryCard } from './components/TripScheduleSummaryCard';
import { StopsList } from './components/StopsList';
import { DriverDailyLog } from './components/daily-log/DriverDailyLog';
import { RouteMap } from './components/map/RouteMap';
import { SegmentTimeline } from './components/SegmentTimeline';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import {
  Compass,
  Clock,
  X,
  Navigation,
  KeyRound,
  AlertCircle,
  RefreshCw,
  Layers,
  SlidersHorizontal,
} from 'lucide-react';

import { SidebarMotif } from './components/SidebarMotif';
import { EditTripModal } from './components/EditTripModal';
import { TripPdfReport } from './components/pdf/TripPdfReport';
import { exportElementToPdf } from './utils/pdfExport';

export const App: React.FC = () => {
  const [showTimelineModal, setShowTimelineModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [isExportingPdf, setIsExportingPdf] = useState(false);

  // PDF report container ref
  const pdfReportRef = useRef<HTMLDivElement>(null);

  // Form Inputs
  const [currentLoc, setCurrentLoc] = useState('Dallas, TX');
  const [pickupLoc, setPickupLoc] = useState('Houston, TX');
  const [dropoffLoc, setDropoffLoc] = useState('Atlanta, GA');
  const [cycleHoursUsed, setCycleHoursUsed] = useState<number>(10.0);
  const [fuelIntervalMiles, setFuelIntervalMiles] = useState<number>(1000);

  // Trip Schedule State
  const [tripScheduleLoading, setTripScheduleLoading] = useState(false);
  const [tripSchedule, setTripSchedule] = useState<TripSchedule | null>(null);
  const [mappedError, setMappedError] = useState<MappedError | null>(null);

  // Abort controller ref
  const abortControllerRef = useRef<AbortController | null>(null);

  // PDF Export Handler
  const handleExportPdf = async () => {
    if (!pdfReportRef.current || !tripSchedule) return;
    try {
      setIsExportingPdf(true);
      const originSlug = currentLoc.split(',')[0].replace(/\s+/g, '-');
      const destSlug = dropoffLoc.split(',')[0].replace(/\s+/g, '-');
      const filename = `FMCSA-Trip-Plan-${originSlug}-to-${destSlug}.pdf`;
      await exportElementToPdf({
        element: pdfReportRef.current,
        filename,
      });
    } catch (e) {
      console.error('PDF Export Error:', e);
    } finally {
      setIsExportingPdf(false);
    }
  };

  // Plan trip function
  const handlePlanTrip = async (
    customCurrent?: string,
    customPickup?: string,
    customDropoff?: string,
    customCycle?: number
  ) => {
    const c = (customCurrent ?? currentLoc).trim();
    const p = (customPickup ?? pickupLoc).trim();
    const d = (customDropoff ?? dropoffLoc).trim();
    const cycle = customCycle !== undefined ? customCycle : cycleHoursUsed;

    if (!c || !p || !d) {
      setMappedError({
        title: 'Missing Required Locations',
        message: 'Current, Pickup, and Dropoff locations are all required.',
        suggestion: 'Please fill in all three location fields before planning.',
        isRetryable: false,
      });
      return;
    }

    if (cycle < 0 || cycle > 70) {
      setMappedError({
        title: 'Invalid Cycle Hours',
        message: 'Current cycle hours used must be between 0.0 and 70.0 hours.',
        suggestion: 'Enter a valid number between 0 and 70.',
        isRetryable: false,
      });
      return;
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setTripScheduleLoading(true);
    setMappedError(null);

    try {
      const response = await planTripSchedule(
        {
          currentLocation: c,
          pickupLocation: p,
          dropoffLocation: d,
          currentCycleUsed: Number(cycle),
        },
        controller.signal
      );

      setTripSchedule(response);
    } catch (err: any) {
      if (err?.name === 'AbortError') return;
      setMappedError(mapTripError(err));
    } finally {
      setTripScheduleLoading(false);
    }
  };

  // Initial plan on mount
  useEffect(() => {
    handlePlanTrip('Dallas, TX', 'Houston, TX', 'Atlanta, GA', 10.0);
  }, []);

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-[#F4F4F0] text-[#202321] flex flex-col font-sans selection:bg-[#164E3D]/15 selection:text-[#164E3D]">
        {/* Main Grid Wrapper (Sidebar + Main Content) */}
        <div className="flex-1 flex flex-col md:flex-row">
          {/* ========================================================================= */}
          {/* LEFT SIDEBAR (STICKY ON DESKTOP) */}
          {/* ========================================================================= */}
          <aside className="w-full md:w-60 md:h-screen md:sticky md:top-0 shrink-0 bg-[#F4F4F0] border-r border-[#E2E3DE] p-5 flex flex-col justify-between overflow-y-auto">
            {/* Brand Logo & Title */}
            <div>
              <div className="flex items-center gap-2.5 mb-6">
                <div className="w-7 h-7 rounded bg-[#164E3D] text-white flex items-center justify-center shadow-xs">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <div>
                  <h1 className="text-sm font-extrabold text-[#164E3D] tracking-tight leading-tight uppercase">
                    Truck Planner
                  </h1>
                  <p className="text-[10px] text-[#626862] font-mono font-medium">HOS & Route Engine</p>
                </div>
              </div>

              {/* Navigation Items */}
              <nav className="space-y-1.5">
                <div
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-xs font-semibold bg-[#E2ECE6] text-[#164E3D] relative before:absolute before:left-0 before:top-1.5 before:bottom-1.5 before:w-1 before:bg-[#164E3D] before:rounded-r"
                >
                  <Compass className="w-4 h-4 text-[#164E3D]" />
                  <span>Trip Planner</span>
                </div>
              </nav>
            </div>

            {/* Bottom Sidebar Motif (Seamless integration matching Reference 2) */}
            <div className="mt-auto pt-6 space-y-3">
              <SidebarMotif />
              <div className="px-1">
                <h4 className="text-base font-bold text-[#202321] leading-tight tracking-tight">
                  Keep<br />
                  drivers moving<br />
                  safely.
                </h4>
                <div className="text-[11px] text-[#626862] mt-2.5 space-y-0.5 leading-snug">
                  <p>Compliant planning.</p>
                  <p>Clear visibility.</p>
                  <p>More miles ahead.</p>
                </div>
              </div>
            </div>
          </aside>

          {/* ========================================================================= */}
          {/* MAIN CONTENT AREA */}
          {/* ========================================================================= */}
          <main className="flex-1 p-4 md:p-6 space-y-4 max-w-7xl mx-auto w-full">
            {/* Top Banner / Slogan */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-[#E2E3DE]">
              <div>
                <h2 className="text-xl md:text-2xl font-bold text-[#202321] tracking-tight">
                  Plan the road. Respect the clock.
                </h2>
                <p className="text-xs text-[#626862] mt-0.5">
                  Real routes. HOS-compliant schedules. FMCSA-style daily logs.
                </p>
              </div>

              {/* Highway truck illustration / slogan on right */}
              <div className="flex items-center gap-3 self-end md:self-auto">
                <div className="text-right hidden sm:block">
                  <span className="text-[10px] font-mono text-[#858A84] block uppercase">Safety & Logistics</span>
                  <span className="text-xs font-semibold text-[#164E3D]">Safer drivers. Stronger supply chains.</span>
                </div>
                <div className="h-10 w-24 relative overflow-hidden rounded flex items-center justify-center bg-transparent">
                  <img
                    src="/images/truck_silhouette.png"
                    alt="Truck on highway"
                    className="h-9 object-contain opacity-85"
                  />
                </div>
              </div>
            </div>

            {/* Error Message if any */}
            {mappedError && (
              <div className="p-3.5 bg-[#FEF2F2] border border-[#FCA5A5] rounded-lg text-xs flex items-start gap-3">
                <AlertCircle className="w-4 h-4 text-[#DC2626] shrink-0 mt-0.5" />
                <div className="flex-1">
                  <strong className="font-bold text-[#991B1B]">{mappedError.title}: </strong>
                  <span className="text-[#B91C1C]">{mappedError.message}</span>
                  {mappedError.suggestion && (
                    <p className="text-[#991B1B] mt-0.5 text-[11px]">{mappedError.suggestion}</p>
                  )}
                </div>
                <button
                  onClick={() => setMappedError(null)}
                  className="text-[#991B1B] hover:text-black cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}

            {/* ===================================================================== */}
            {/* ROW 1: PLAN A TRIP CARD */}
            {/* ===================================================================== */}
            <div className="bg-white border border-[#E2E3DE] rounded-lg p-4 shadow-xs">
              {/* Card Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[#E7E7E2]">
                <div className="flex items-center gap-2">
                  <div className="w-5 h-5 rounded-full bg-[#164E3D]/10 text-[#164E3D] flex items-center justify-center">
                    <KeyRound className="w-3 h-3" />
                  </div>
                  <div>
                    <h3 className="text-xs font-bold text-[#202321] tracking-tight">Plan a Trip</h3>
                    <p className="text-[11px] text-[#626862]">
                      Enter your locations and available cycle hours to generate a route and HOS-compliant schedule.
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setShowEditModal(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[11px] font-semibold bg-[#FAFAF8] hover:bg-[#EAEAE5] text-[#164E3D] border border-[#D9DAD5] transition cursor-pointer self-start sm:self-auto shadow-2xs"
                  title="Open detailed trip editing form"
                >
                  <SlidersHorizontal className="w-3.5 h-3.5" />
                  <span>Customize Trip & Rules</span>
                </button>
              </div>

              {/* Form Input Row */}
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handlePlanTrip();
                }}
                className="mt-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-12 gap-3 items-end"
              >
                {/* Current Location */}
                <div className="lg:col-span-3">
                  <label className="block text-[11px] font-semibold text-[#202321] mb-1 flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-[#164E3D]" />
                    Current Location
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      value={currentLoc}
                      onChange={(e) => setCurrentLoc(e.target.value)}
                      placeholder="e.g. Dallas, TX"
                      required
                      className="w-full bg-white border border-[#D9DAD5] rounded-md px-3 py-1.5 text-xs text-[#202321] focus:outline-none focus:border-[#164E3D] pr-7 font-medium"
                    />
                    {currentLoc && (
                      <button
                        type="button"
                        onClick={() => setCurrentLoc('')}
                        className="absolute right-2 top-2 text-[#858A84] hover:text-[#202321] cursor-pointer"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>

                {/* Pickup Location */}
                <div className="lg:col-span-3">
                  <label className="block text-[11px] font-semibold text-[#202321] mb-1 flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-sm bg-[#164E3D]" />
                    Pickup Location (1h stop)
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      value={pickupLoc}
                      onChange={(e) => setPickupLoc(e.target.value)}
                      placeholder="e.g. Houston, TX"
                      required
                      className="w-full bg-white border border-[#D9DAD5] rounded-md px-3 py-1.5 text-xs text-[#202321] focus:outline-none focus:border-[#164E3D] pr-7 font-medium"
                    />
                    {pickupLoc && (
                      <button
                        type="button"
                        onClick={() => setPickupLoc('')}
                        className="absolute right-2 top-2 text-[#858A84] hover:text-[#202321] cursor-pointer"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>

                {/* Dropoff Location */}
                <div className="lg:col-span-3">
                  <label className="block text-[11px] font-semibold text-[#202321] mb-1 flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-sm bg-[#DC2626]" />
                    Dropoff Location (1h stop)
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      value={dropoffLoc}
                      onChange={(e) => setDropoffLoc(e.target.value)}
                      placeholder="e.g. Atlanta, GA"
                      required
                      className="w-full bg-white border border-[#D9DAD5] rounded-md px-3 py-1.5 text-xs text-[#202321] focus:outline-none focus:border-[#164E3D] pr-7 font-medium"
                    />
                    {dropoffLoc && (
                      <button
                        type="button"
                        onClick={() => setDropoffLoc('')}
                        className="absolute right-2 top-2 text-[#858A84] hover:text-[#202321] cursor-pointer"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>

                {/* Current Cycle Used */}
                <div className="lg:col-span-2">
                  <label className="block text-[11px] font-semibold text-[#202321] mb-1 flex items-center gap-1.5">
                    <Clock className="w-3 h-3 text-[#626862]" />
                    Current Cycle Used
                  </label>
                  <div className="relative">
                    <input
                      type="number"
                      step="0.5"
                      min="0"
                      max="70"
                      value={cycleHoursUsed}
                      onChange={(e) => setCycleHoursUsed(Number(e.target.value))}
                      placeholder="10"
                      required
                      className="w-full bg-white border border-[#D9DAD5] rounded-md px-3 py-1.5 text-xs text-[#202321] font-mono focus:outline-none focus:border-[#164E3D] pr-7 font-medium"
                    />
                    {cycleHoursUsed !== undefined && (
                      <button
                        type="button"
                        onClick={() => setCycleHoursUsed(0)}
                        className="absolute right-2 top-2 text-[#858A84] hover:text-[#202321] cursor-pointer"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>

                {/* Submit Action Button */}
                <div className="lg:col-span-1">
                  <button
                    type="submit"
                    disabled={tripScheduleLoading}
                    className="w-full flex items-center justify-center gap-1.5 px-3 py-2 bg-[#164E3D] hover:bg-[#123F31] text-white rounded-md text-xs font-bold transition shadow-xs disabled:opacity-50 cursor-pointer"
                  >
                    {tripScheduleLoading ? (
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <>
                        <Navigation className="w-3.5 h-3.5 rotate-45" />
                        <span>Plan Trip</span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>

            {/* ===================================================================== */}
            {/* ROW 2: MAP & TRIP OVERVIEW */}
            {/* ===================================================================== */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-stretch">
              {/* Left Column: Route & Stops Map (7 columns) */}
              <div className="lg:col-span-7 flex flex-col">
                <RouteMap
                  routePlan={tripSchedule?.route || null}
                  stops={tripSchedule?.stops || []}
                  summary={tripSchedule?.summary || null}
                  loading={tripScheduleLoading}
                />
              </div>

              {/* Right Column: Trip Overview (5 columns) */}
              <div className="lg:col-span-5 flex flex-col">
                {tripSchedule?.summary ? (
                  <TripScheduleSummaryCard
                    summary={tripSchedule.summary}
                    stopsCount={tripSchedule.stops.length}
                    onDownloadPdf={handleExportPdf}
                    isDownloadingPdf={isExportingPdf}
                  />
                ) : (
                  <div className="bg-white border border-[#E2E3DE] rounded-lg p-6 text-center text-xs text-[#858A84] flex-1 flex items-center justify-center">
                    Trip Overview will populate once calculated.
                  </div>
                )}
              </div>
            </div>

            {/* ===================================================================== */}
            {/* ROW 3: SCHEDULED STOPS (FULL WIDTH) */}
            {/* ===================================================================== */}
            <div className="w-full">
              <StopsList
                stops={tripSchedule?.stops || []}
                onViewTimeline={() => setShowTimelineModal(true)}
              />
            </div>

            {/* ===================================================================== */}
            {/* ROW 4: DRIVER'S DAILY LOG (FULL WIDTH) */}
            {/* ===================================================================== */}
            <div className="w-full">
              <DriverDailyLog
                dailyLogs={tripSchedule?.dailyLogs || []}
                onDownloadPdf={handleExportPdf}
                isDownloadingPdf={isExportingPdf}
              />
            </div>

            {/* Off-screen PDF Printable Document Generator */}
            <TripPdfReport
              reportRef={pdfReportRef}
              summary={tripSchedule?.summary || null}
              stops={tripSchedule?.stops || []}
              dailyLogs={tripSchedule?.dailyLogs || []}
              routePlan={tripSchedule?.route || null}
            />

            {/* ===================================================================== */}
            {/* FULL TIMELINE MODAL (DRAWER) */}
            {/* ===================================================================== */}
            {showTimelineModal && tripSchedule && (
              <div className="fixed inset-0 bg-black/40 backdrop-blur-xs z-50 flex items-center justify-center p-4">
                <div className="bg-white border border-[#E2E3DE] rounded-xl max-w-2xl w-full max-h-[85vh] flex flex-col shadow-xl overflow-hidden">
                  <div className="p-4 border-b border-[#E7E7E2] flex items-center justify-between bg-[#FAFAF8]">
                    <div className="flex items-center gap-2">
                      <Layers className="w-4 h-4 text-[#164E3D]" />
                      <h3 className="text-sm font-bold text-[#202321]">Full Trip Segment Timeline</h3>
                    </div>
                    <button
                      onClick={() => setShowTimelineModal(false)}
                      className="p-1 rounded hover:bg-[#EAEAE5] text-[#626862] cursor-pointer"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                  <div className="p-4 overflow-y-auto flex-1">
                    <SegmentTimeline segments={tripSchedule.segments} />
                  </div>
                </div>
              </div>
            )}

            {/* ===================================================================== */}
            {/* EDIT TRIP PARAMETERS MODAL */}
            {/* ===================================================================== */}
            <EditTripModal
              isOpen={showEditModal}
              onClose={() => setShowEditModal(false)}
              initialValues={{
                currentLocation: currentLoc,
                pickupLocation: pickupLoc,
                dropoffLocation: dropoffLoc,
                currentCycleUsed: cycleHoursUsed,
                fuelIntervalMiles: fuelIntervalMiles,
              }}
              loading={tripScheduleLoading}
              onSubmit={(params) => {
                setCurrentLoc(params.currentLocation);
                setPickupLoc(params.pickupLocation);
                setDropoffLoc(params.dropoffLocation);
                setCycleHoursUsed(params.currentCycleUsed);
                if (params.fuelIntervalMiles) setFuelIntervalMiles(params.fuelIntervalMiles);
                handlePlanTrip(
                  params.currentLocation,
                  params.pickupLocation,
                  params.dropoffLocation,
                  params.currentCycleUsed
                );
                setShowEditModal(false);
              }}
            />
          </main>
        </div>

        {/* ========================================================================= */}
        {/* GLOBAL FOOTER */}
        {/* ========================================================================= */}
        <footer className="border-t border-[#E2E3DE] bg-[#F4F4F0] py-2.5 px-4 text-[10px] text-[#858A84] font-mono flex flex-col sm:flex-row items-center justify-between gap-2">
          <div>
            <strong className="text-[#202321] font-sans font-semibold">Truck Trip Planner</strong> • Complies with FMCSA 49 CFR Part 395 (11h driving / 14h duty window / 30m rest break / 10h sleeper / 70h cycle)
          </div>
          <div className="flex items-center gap-4">
            <span>OpenStreetMap • OpenFreeMap • OSRM</span>
            <span className="px-1.5 py-0.5 rounded bg-white border border-[#E2E3DE] text-[#202321]">v1.0.0</span>
          </div>
        </footer>
      </div>
    </ErrorBoundary>
  );
};
export default App;
