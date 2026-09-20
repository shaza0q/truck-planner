import { DutySegment, DailyLog, DailySchedule, ValidationResult, Stop } from './hos';
import { RoutePlanResponse } from './routing';

export interface TripScheduleSummary {
  totalDistanceMiles: number;
  totalDrivingMinutes: number;
  totalDrivingHours: number;
  totalElapsedMinutes: number;
  totalElapsedHours: number;
  totalOnDutyHours: number;
  totalOffDutyHours: number;
  totalSleeperHours: number;
  startingCycleUsed: number;
  finalCycleUsed: number;
  cycleHoursRemaining: number;
  cycleHoursAdded: number;
  daysCount: number;
  isValid: boolean;
}

export interface TripSchedule {
  route: RoutePlanResponse;
  stops: Stop[];
  segments: DutySegment[];
  dailyLogs: DailyLog[];
  dailySchedules: DailySchedule[];
  summary: TripScheduleSummary;
  validationResult: ValidationResult | null;
}

export interface TripScheduleRequest {
  currentLocation: string;
  pickupLocation: string;
  dropoffLocation: string;
  currentCycleUsed: number;
  fuelIntervalMiles?: number;
}

export type TripScheduleResponse = TripSchedule | { schedule: TripSchedule };

export interface TripScheduleApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, any>;
  };
}
