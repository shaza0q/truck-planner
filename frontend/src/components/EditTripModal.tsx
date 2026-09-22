import React, { useState } from 'react';
import { X, Clock, Fuel, RotateCcw, Navigation } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (params: {
    currentLocation: string;
    pickupLocation: string;
    dropoffLocation: string;
    currentCycleUsed: number;
    fuelIntervalMiles?: number;
  }) => void;
  initialValues: {
    currentLocation: string;
    pickupLocation: string;
    dropoffLocation: string;
    currentCycleUsed: number;
    fuelIntervalMiles?: number;
  };
  loading?: boolean;
}

const DEFAULT_VALUES = {
  currentLocation: 'Dallas, TX',
  pickupLocation: 'Houston, TX',
  dropoffLocation: 'Atlanta, GA',
  currentCycleUsed: 10.0,
  fuelIntervalMiles: 1000,
};

export const EditTripModal: React.FC<Props> = ({
  isOpen,
  onClose,
  onSubmit,
  initialValues,
  loading = false,
}) => {
  const [currentLocation, setCurrentLocation] = useState(initialValues.currentLocation || DEFAULT_VALUES.currentLocation);
  const [pickupLocation, setPickupLocation] = useState(initialValues.pickupLocation || DEFAULT_VALUES.pickupLocation);
  const [dropoffLocation, setDropoffLocation] = useState(initialValues.dropoffLocation || DEFAULT_VALUES.dropoffLocation);
  const [currentCycleUsed, setCurrentCycleUsed] = useState(initialValues.currentCycleUsed ?? DEFAULT_VALUES.currentCycleUsed);
  const [fuelIntervalMiles, setFuelIntervalMiles] = useState(initialValues.fuelIntervalMiles ?? DEFAULT_VALUES.fuelIntervalMiles);

  if (!isOpen) return null;

  const handleResetDefaults = () => {
    setCurrentLocation(DEFAULT_VALUES.currentLocation);
    setPickupLocation(DEFAULT_VALUES.pickupLocation);
    setDropoffLocation(DEFAULT_VALUES.dropoffLocation);
    setCurrentCycleUsed(DEFAULT_VALUES.currentCycleUsed);
    setFuelIntervalMiles(DEFAULT_VALUES.fuelIntervalMiles);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      currentLocation: currentLocation.trim(),
      pickupLocation: pickupLocation.trim(),
      dropoffLocation: dropoffLocation.trim(),
      currentCycleUsed: Number(currentCycleUsed),
      fuelIntervalMiles: Number(fuelIntervalMiles) || 1000,
    });
  };

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-xs z-[9999] flex items-center justify-center p-4">
      <div className="bg-white border border-[#E2E3DE] rounded-xl max-w-lg w-full shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Modal Header */}
        <div className="p-4 sm:p-5 border-b border-[#E7E7E2] flex items-center justify-between bg-[#FAFAF8]">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-full bg-[#164E3D]/10 text-[#164E3D] flex items-center justify-center shadow-xs">
              <Navigation className="w-3.5 h-3.5 rotate-45" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-[#202321] tracking-tight">
                Edit Trip & HOS Parameters
              </h3>
              <p className="text-[11px] text-[#626862]">
                Configure origin, stops, and driver cycle hours for routing calculation.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md hover:bg-[#EAEAE5] text-[#626862] hover:text-[#202321] transition cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Form */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {/* Current Location */}
          <div>
            <label className="block text-xs font-semibold text-[#202321] mb-1.5 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#164E3D]" />
              Current Location (Origin)
            </label>
            <div className="relative">
              <input
                type="text"
                value={currentLocation}
                onChange={(e) => setCurrentLocation(e.target.value)}
                placeholder="e.g. Dallas, TX"
                required
                className="w-full bg-[#FAFAF8] focus:bg-white border border-[#D9DAD5] rounded-md px-3 py-2 text-xs text-[#202321] focus:outline-none focus:border-[#164E3D] pr-8 font-medium transition"
              />
              {currentLocation && (
                <button
                  type="button"
                  onClick={() => setCurrentLocation('')}
                  className="absolute right-2.5 top-2.5 text-[#858A84] hover:text-[#202321] cursor-pointer"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
            <p className="text-[10px] text-[#858A84] mt-1">Starting point where driver departs.</p>
          </div>

          {/* Pickup & Dropoff 2-Column Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            {/* Pickup Location */}
            <div>
              <label className="block text-xs font-semibold text-[#202321] mb-1.5 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-sm bg-[#164E3D]" />
                Pickup Location (1h Stop)
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={pickupLocation}
                  onChange={(e) => setPickupLocation(e.target.value)}
                  placeholder="e.g. Houston, TX"
                  required
                  className="w-full bg-[#FAFAF8] focus:bg-white border border-[#D9DAD5] rounded-md px-3 py-2 text-xs text-[#202321] focus:outline-none focus:border-[#164E3D] pr-8 font-medium transition"
                />
                {pickupLocation && (
                  <button
                    type="button"
                    onClick={() => setPickupLocation('')}
                    className="absolute right-2.5 top-2.5 text-[#858A84] hover:text-[#202321] cursor-pointer"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>

            {/* Dropoff Location */}
            <div>
              <label className="block text-xs font-semibold text-[#202321] mb-1.5 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-sm bg-[#DC2626]" />
                Dropoff Location (1h Stop)
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={dropoffLocation}
                  onChange={(e) => setDropoffLocation(e.target.value)}
                  placeholder="e.g. Atlanta, GA"
                  required
                  className="w-full bg-[#FAFAF8] focus:bg-white border border-[#D9DAD5] rounded-md px-3 py-2 text-xs text-[#202321] focus:outline-none focus:border-[#164E3D] pr-8 font-medium transition"
                />
                {dropoffLocation && (
                  <button
                    type="button"
                    onClick={() => setDropoffLocation('')}
                    className="absolute right-2.5 top-2.5 text-[#858A84] hover:text-[#202321] cursor-pointer"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* HOS Cycle & Fuel Interval 2-Column Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-1">
            {/* Current Cycle Used */}
            <div>
              <label className="block text-xs font-semibold text-[#202321] mb-1.5 flex items-center gap-1.5 font-mono">
                <Clock className="w-3.5 h-3.5 text-[#626862]" />
                Starting 70h Cycle Used
              </label>
              <div className="relative">
                <input
                  type="number"
                  step="0.5"
                  min="0"
                  max="70"
                  value={currentCycleUsed}
                  onChange={(e) => setCurrentCycleUsed(Number(e.target.value))}
                  placeholder="10.0"
                  required
                  className="w-full bg-[#FAFAF8] focus:bg-white border border-[#D9DAD5] rounded-md px-3 py-2 text-xs text-[#202321] font-mono focus:outline-none focus:border-[#164E3D] pr-12 font-semibold transition"
                />
                <span className="absolute right-3 top-2.5 text-[11px] font-mono text-[#858A84]">/ 70h</span>
              </div>
              <p className="text-[10px] text-[#858A84] mt-1 font-mono">
                {(70 - currentCycleUsed).toFixed(1)}h available before 70h cap
              </p>
            </div>

            {/* Fuel Stop Interval */}
            <div>
              <label className="block text-xs font-semibold text-[#202321] mb-1.5 flex items-center gap-1.5 font-mono">
                <Fuel className="w-3.5 h-3.5 text-[#D97706]" />
                Fueling Interval (Miles)
              </label>
              <div className="relative">
                <input
                  type="number"
                  step="50"
                  min="300"
                  max="2000"
                  value={fuelIntervalMiles}
                  onChange={(e) => setFuelIntervalMiles(Number(e.target.value))}
                  placeholder="1000"
                  required
                  className="w-full bg-[#FAFAF8] focus:bg-white border border-[#D9DAD5] rounded-md px-3 py-2 text-xs text-[#202321] font-mono focus:outline-none focus:border-[#164E3D] pr-10 font-semibold transition"
                />
                <span className="absolute right-3 top-2.5 text-[11px] font-mono text-[#858A84]">mi</span>
              </div>
              <p className="text-[10px] text-[#858A84] mt-1">
                Standard tank range (default: 1,000 mi)
              </p>
            </div>
          </div>

          {/* Modal Actions */}
          <div className="pt-3 border-t border-[#E7E7E2] flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={handleResetDefaults}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium text-[#626862] hover:bg-[#F4F4F0] hover:text-[#202321] transition cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset Defaults</span>
            </button>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-3.5 py-1.5 rounded-md text-xs font-medium text-[#626862] hover:bg-[#F4F4F0] transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex items-center gap-1.5 px-4 py-2 bg-[#164E3D] hover:bg-[#123F31] text-white rounded-md text-xs font-bold transition shadow-xs disabled:opacity-50 cursor-pointer"
              >
                <Navigation className="w-3.5 h-3.5 rotate-45" />
                <span>{loading ? 'Calculating...' : 'Plan Trip'}</span>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
