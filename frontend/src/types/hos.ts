export type DutyStatus = 'OFF_DUTY' | 'SLEEPER_BERTH' | 'DRIVING' | 'ON_DUTY_NOT_DRIVING';
export type StopType = 'PICKUP' | 'DROPOFF' | 'FUEL' | 'REST' | 'BREAK';

export interface MockRoute {
  distanceMiles: number;
  drivingMinutes: number;
}

export interface TripPlanRequest {
  currentLocation: string;
  pickupLocation: string;
  dropoffLocation: string;
  currentCycleUsed: number;
  mockRoute: MockRoute;
}

export interface DutySegment {
  status: DutyStatus;
  start: string;
  end: string;
  startTime?: string;
  endTime?: string;
  durationMinutes: number;
  durationHours: number;
  startMinute?: number;
  endMinute?: number;
  eventType?: string | null;
  location: string;
  miles: number;
  reason: string | null;
  coordinate?: { latitude: number; longitude: number } | null;
  leg?: string | null;
}

export interface Stop {
  type: StopType;
  start: string;
  end: string;
  durationMinutes: number;
  reason: string;
  location: string;
  milesFromStart: number;
  coordinate?: { latitude: number; longitude: number } | null;
}

export interface Remark {
  time: string;
  location: string;
  description: string;
  eventType?: string | null;
  coordinate?: { latitude: number; longitude: number } | null;
}

export interface DailyTotals {
  offDuty: number;
  sleeperBerth: number;
  driving: number;
  onDutyNotDriving: number;
  totalHours: number;
  offDutyMinutes?: number;
  sleeperBerthMinutes?: number;
  drivingMinutes?: number;
  onDutyNotDrivingMinutes?: number;
  totalMinutes?: number;
}

export interface DailyLog {
  date: string;
  dayNumber?: number;
  totalMiles: number;
  segments: DutySegment[];
  remarks: Remark[];
  totals: DailyTotals;
}

export interface DailySchedule {
  date: string;
  segments: DutySegment[];
  totalDrivingHours: number;
  totalOnDutyHours: number;
  totalOffDutyHours: number;
  totalSleeperHours: number;
  totalHours: number;
}

export interface TripSummary {
  totalDurationHours: number;
  totalDrivingHours: number;
  totalOnDutyHours: number;
  totalOffDutyHours: number;
  totalSleeperHours: number;
  totalDistanceMiles: number;
  startingCycleUsed: number;
  finalCycleUsed: number;
  cycleHoursAdded: number;
  daysCount: number;
  isValid: boolean;
}

export interface Violation {
  code: string;
  message: string;
  segmentIndex?: number;
  details?: Record<string, any>;
}

export interface ValidationResult {
  valid: boolean;
  violations: Violation[];
  warnings: string[];
}

export interface TripPlan {
  segments: DutySegment[];
  stops: Stop[];
  dailySchedules: DailySchedule[];
  dailyLogs: DailyLog[];
  summary: TripSummary;
  validationResult: ValidationResult | null;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, any>;
  };
}
