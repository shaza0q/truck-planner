"""
Domain exceptions for HOS Engine.
"""


class HOSError(Exception):
    """Base exception for HOS domain errors."""
    def __init__(self, message: str, code: str = "HOS_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class InvalidTripInputError(HOSError):
    """Raised when trip input parameters violate basic constraints."""
    def __init__(self, message: str, code: str = "INVALID_TRIP_INPUT"):
        super().__init__(message, code=code)


class InsufficientCycleHoursError(HOSError):
    """Raised when the driver does not have enough cycle hours remaining to perform the trip."""
    def __init__(self, message: str = "Insufficient 70-hour cycle remaining to complete required duties.", code: str = "INSUFFICIENT_CYCLE_HOURS"):
        super().__init__(message, code=code)


class ImpossibleRouteError(HOSError):
    """Raised when the given route parameters are impossible."""
    def __init__(self, message: str = "Impossible route parameters provided.", code: str = "IMPOSSIBLE_ROUTE"):
        super().__init__(message, code=code)
