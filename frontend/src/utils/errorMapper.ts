export interface MappedError {
  title: string;
  message: string;
  suggestion?: string;
  isRetryable: boolean;
}

export function mapTripError(error: any): MappedError {
  const code = error?.code || '';
  const rawMsg = error?.message || '';

  if (error?.name === 'AbortError' || rawMsg.includes('aborted')) {
    return {
      title: 'Calculation Cancelled',
      message: 'The trip calculation was cancelled because a new request was started.',
      isRetryable: false,
    };
  }

  switch (code) {
    case 'LOCATION_NOT_FOUND':
      return {
        title: 'Location Not Found',
        message: rawMsg || 'One or more of the specified addresses could not be geocoded.',
        suggestion: 'Please verify the city, state, or address spelling (e.g. "Chicago, IL").',
        isRetryable: false,
      };

    case 'NO_ROUTE_FOUND':
      return {
        title: 'No Driving Route Found',
        message: rawMsg || 'Could not find a valid driving route between the specified locations.',
        suggestion: 'Ensure the locations are connected by public roadways.',
        isRetryable: false,
      };

    case 'INSUFFICIENT_CYCLE_HOURS':
      return {
        title: 'Insufficient Cycle Hours',
        message: rawMsg || 'The driver does not have enough remaining cycle hours to complete this trip safely.',
        suggestion: 'Reduce the starting cycle hours or plan a shorter trip segment.',
        isRetryable: false,
      };

    case 'RATE_LIMITED':
      return {
        title: 'Service Rate Limited',
        message: rawMsg || 'External geocoding or routing services are temporarily rate-limiting requests.',
        suggestion: 'Please wait a moment and try again.',
        isRetryable: true,
      };

    case 'PROVIDER_ERROR':
      return {
        title: 'Routing Provider Error',
        message: rawMsg || 'An error occurred while contacting the map or routing provider.',
        suggestion: 'Check your internet connection and try again.',
        isRetryable: true,
      };

    case 'VALIDATION_ERROR':
      return {
        title: 'Invalid Input',
        message: rawMsg || 'The submitted trip parameters failed validation.',
        suggestion: 'Please check your inputs and try again.',
        isRetryable: false,
      };

    default:
      if (rawMsg.includes('Failed to fetch') || rawMsg.includes('NetworkError')) {
        return {
          title: 'Connection Error',
          message: 'Unable to connect to the trip planning backend server.',
          suggestion: 'Ensure the backend server is running and accessible.',
          isRetryable: true,
        };
      }
      return {
        title: 'Trip Planning Error',
        message: rawMsg || 'An unexpected error occurred while planning the trip.',
        suggestion: 'Please review your trip details and try again.',
        isRetryable: true,
      };
  }
}
