import { TripScheduleRequest, TripSchedule, TripScheduleApiError } from '../types/tripSchedule';

const API_BASE_URL = ((import.meta as any).env?.VITE_API_BASE_URL as string) || 'http://127.0.0.1:8000';

export async function planTripSchedule(
  payload: TripScheduleRequest,
  signal?: AbortSignal
): Promise<TripSchedule> {
  const response = await fetch(`${API_BASE_URL}/api/trips/plan/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload),
    signal,
  });

  const data = await response.json();

  if (!response.ok) {
    const apiError = data as TripScheduleApiError;
    const msg = apiError.error?.message || `Trip schedule request failed with status ${response.status}`;
    const err = new Error(msg);
    (err as any).code = apiError.error?.code;
    throw err;
  }

  // Handle both direct TripSchedule or { schedule: TripSchedule } responses
  return (data.schedule || data) as TripSchedule;
}
