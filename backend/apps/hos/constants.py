"""
HOS regulatory limits and simulation constants.
All durations are also provided in minutes for precise arithmetic.
"""

# Maximum driving hours allowed per duty window
MAX_DRIVING_HOURS: float = 11.0
MAX_DRIVING_MINUTES: int = 11 * 60  # 660 mins

# Maximum duty window duration (consecutive hours from window start)
MAX_DUTY_WINDOW_HOURS: float = 14.0
MAX_DUTY_WINDOW_MINUTES: int = 14 * 60  # 840 mins

# Mandatory consecutive rest hours for daily reset
REQUIRED_OFF_DUTY_HOURS: float = 10.0
REQUIRED_OFF_DUTY_MINUTES: int = 10 * 60  # 600 mins

# Cumulative driving threshold before a 30-minute break is mandatory
BREAK_THRESHOLD_DRIVING_HOURS: float = 8.0
BREAK_THRESHOLD_DRIVING_MINUTES: int = 8 * 60  # 480 mins

# Duration of required driving break
REQUIRED_BREAK_MINUTES: int = 30

# 70-hour / 8-day cycle limit
MAX_CYCLE_HOURS: float = 70.0
MAX_CYCLE_MINUTES: int = 70 * 60  # 4200 mins
CYCLE_DAYS: int = 8

# Maximum distance in miles before a fuel stop must be performed
FUEL_INTERVAL_MILES: float = 1000.0

# Mandatory task durations
PICKUP_DURATION_MINUTES: int = 60
DROPOFF_DURATION_MINUTES: int = 60
FUEL_DURATION_MINUTES: int = 30
