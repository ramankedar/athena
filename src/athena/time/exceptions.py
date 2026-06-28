"""Time-domain exceptions.

All exceptions inherit from ``TimeError``, which itself inherits from
``AthenaError``, ensuring that any code catching ``AthenaError`` also catches
time-domain failures without requiring changes.

Hierarchy::

    AthenaError
    └── TimeError
        ├── NaiveDatetimeError       — naive datetime received where aware required
        ├── InvalidTimezoneError     — unrecognised IANA timezone name
        ├── NonTradingDayError       — operation requires a trading day
        ├── NoSessionError           — no session found within the search window
        └── ExpiryCalculationError   — expiry date cannot be determined
"""

from __future__ import annotations

from athena.platform.exceptions import AthenaError


class TimeError(AthenaError):
    """Root exception for all time-domain errors.

    Args:
        message: Human-readable description of the problem.
        error_code: Optional machine-readable code (prefix: ``TIM``).
        **context: Diagnostic key-value pairs.
    """


class NaiveDatetimeError(TimeError):
    """Raised when a naive (timezone-unaware) datetime is passed to a function
    that requires a timezone-aware value.

    All datetimes within the Athena time domain must carry timezone information.
    Naive datetimes are rejected at the boundary to prevent silent offset bugs.

    Args:
        dt_repr: String representation of the offending datetime.
        **context: Additional diagnostic context.
    """

    def __init__(self, dt_repr: str = "", **context: object) -> None:
        super().__init__(
            "Naive datetime received — all datetimes must be timezone-aware"
            + (f": {dt_repr}" if dt_repr else ""),
            error_code="TIM_001",
            dt_repr=dt_repr,
            **context,
        )


class InvalidTimezoneError(TimeError):
    """Raised when an unrecognised IANA timezone name is requested.

    Args:
        timezone_name: The unrecognised timezone string.
        **context: Additional diagnostic context.
    """

    def __init__(self, timezone_name: str, **context: object) -> None:
        super().__init__(
            f"Unknown timezone: {timezone_name!r}",
            error_code="TIM_002",
            timezone_name=timezone_name,
            **context,
        )


class NonTradingDayError(TimeError):
    """Raised when an operation requires a trading day but a non-trading day
    is supplied (weekend or exchange holiday).

    Args:
        date_repr: ISO-formatted date string for the offending date.
        exchange: Exchange name (e.g. ``"NSE"``).
        **context: Additional diagnostic context.
    """

    def __init__(self, date_repr: str, exchange: str = "NSE", **context: object) -> None:
        super().__init__(
            f"{date_repr} is not a trading day on {exchange}",
            error_code="TIM_003",
            date_repr=date_repr,
            exchange=exchange,
            **context,
        )


class NoSessionError(TimeError):
    """Raised when no market session can be found within a reasonable search window.

    This typically indicates a misconfiguration or an unexpectedly large gap in
    the trading calendar (e.g. an extended market closure).

    Args:
        search_from: ISO-formatted datetime string for the start of the search.
        max_days: Number of days searched before giving up.
        **context: Additional diagnostic context.
    """

    def __init__(self, search_from: str, max_days: int = 30, **context: object) -> None:
        super().__init__(
            f"No market session found within {max_days} days of {search_from}",
            error_code="TIM_004",
            search_from=search_from,
            max_days=max_days,
            **context,
        )


class ExpiryCalculationError(TimeError):
    """Raised when an expiry date cannot be determined.

    This can occur when an entire expiry week is composed of holidays, or
    when the requested year/month combination is invalid.

    Args:
        message: Description of why calculation failed.
        **context: Additional diagnostic context (year, month, exchange, etc.).
    """
