"""Market data domain exception hierarchy.

All market data exceptions inherit from ``MarketDataError`` which inherits
from ``AthenaError``, preserving the platform-wide catch clause while
allowing fine-grained discrimination by subtype.

Hierarchy::

    AthenaError
    └── MarketDataError
        ├── InvalidBarError           — OHLCV bar fails structural rules
        ├── InvalidTickError          — tick data fails validation
        ├── InvalidQuoteError         — bid/ask quote fails validation
        ├── InvalidTradeError         — trade record fails validation
        ├── InvalidOrderBookError     — order book snapshot fails validation
        ├── InvalidSeriesError        — time-series collection fails ordering
        ├── DataGapError              — unacceptable gap detected in series
        ├── InvalidAdjustmentError    — adjustment factor fails constraints
        └── ProviderError             — external data provider returned bad data
"""

from __future__ import annotations

from athena.platform.exceptions import AthenaError


class MarketDataError(AthenaError):
    """Root exception for all market data domain errors.

    Args:
        message: Human-readable description.
        error_code: Optional machine-readable code (prefix: ``MDT``).
        **context: Diagnostic key-value pairs.
    """


class InvalidBarError(MarketDataError):
    """Raised when an OHLCV bar fails structural validation.

    Common causes: high < low, open or close outside [low, high], negative
    volume, or naive (timezone-unaware) timestamps.

    Args:
        field: Name of the field that is invalid.
        value: The offending value.
        reason: Description of the constraint violated.
        **context: Additional diagnostic context.
    """

    def __init__(
        self, field: str, value: object = None, reason: str = "", **context: object
    ) -> None:
        msg = f"Invalid OHLCV bar — {field}"
        if value is not None:
            msg += f"={value!r}"
        if reason:
            msg += f": {reason}"
        super().__init__(msg, error_code="MDT_001", field=field, reason=reason, **context)
        self.field = field
        self.reason = reason


class InvalidTickError(MarketDataError):
    """Raised when a tick record fails validation.

    Args:
        reason: Description of the validation failure.
        **context: Additional diagnostic context.
    """

    def __init__(self, reason: str, **context: object) -> None:
        super().__init__(f"Invalid tick: {reason}", error_code="MDT_002", reason=reason, **context)
        self.reason = reason


class InvalidQuoteError(MarketDataError):
    """Raised when a bid/ask quote fails validation (e.g. crossed market).

    Args:
        reason: Description of the validation failure.
        **context: Additional diagnostic context.
    """

    def __init__(self, reason: str, **context: object) -> None:
        super().__init__(f"Invalid quote: {reason}", error_code="MDT_003", reason=reason, **context)
        self.reason = reason


class InvalidTradeError(MarketDataError):
    """Raised when a trade record fails validation.

    Args:
        reason: Description of the validation failure.
        **context: Additional diagnostic context.
    """

    def __init__(self, reason: str, **context: object) -> None:
        super().__init__(f"Invalid trade: {reason}", error_code="MDT_004", reason=reason, **context)
        self.reason = reason


class InvalidOrderBookError(MarketDataError):
    """Raised when an order book snapshot fails validation.

    Args:
        reason: Description of the validation failure.
        **context: Additional diagnostic context.
    """

    def __init__(self, reason: str, **context: object) -> None:
        super().__init__(
            f"Invalid order book: {reason}", error_code="MDT_005", reason=reason, **context
        )
        self.reason = reason


class InvalidSeriesError(MarketDataError):
    """Raised when a time-series collection (OHLCVSeries) fails consistency checks.

    Common causes: bars not sorted by time, bars with mismatched symbols or
    timeframes, or empty series where non-empty is expected.

    Args:
        reason: Description of the consistency violation.
        **context: Additional diagnostic context.
    """

    def __init__(self, reason: str, **context: object) -> None:
        super().__init__(
            f"Invalid series: {reason}", error_code="MDT_006", reason=reason, **context
        )
        self.reason = reason


class DataGapError(MarketDataError):
    """Raised when a series has an unacceptable gap in its time sequence.

    Args:
        gap_start: ISO string of the gap's start time.
        gap_end: ISO string of the gap's end time.
        expected_bars: Number of bars expected to exist in the gap.
        **context: Additional diagnostic context.
    """

    def __init__(
        self,
        gap_start: str,
        gap_end: str,
        expected_bars: int = 0,
        **context: object,
    ) -> None:
        super().__init__(
            f"Data gap from {gap_start} to {gap_end} ({expected_bars} expected bars)",
            error_code="MDT_007",
            gap_start=gap_start,
            gap_end=gap_end,
            expected_bars=expected_bars,
            **context,
        )
        self.gap_start = gap_start
        self.gap_end = gap_end
        self.expected_bars = expected_bars


class InvalidAdjustmentError(MarketDataError):
    """Raised when an adjustment factor fails its constraints.

    Args:
        field: The adjustment field that is invalid.
        value: The invalid value.
        reason: Description of the constraint violated.
        **context: Additional diagnostic context.
    """

    def __init__(self, field: str, value: object, reason: str, **context: object) -> None:
        super().__init__(
            f"Invalid adjustment — {field}={value!r}: {reason}",
            error_code="MDT_008",
            field=field,
            reason=reason,
            **context,
        )
        self.field = field
        self.reason = reason


class ProviderError(MarketDataError):
    """Raised when an external data provider returns unexpected or invalid data.

    Args:
        vendor: Name of the data vendor.
        reason: Description of the problem.
        **context: Additional diagnostic context (status code, response body, etc.).
    """

    def __init__(self, vendor: str, reason: str, **context: object) -> None:
        super().__init__(
            f"Provider {vendor!r} error: {reason}",
            error_code="MDT_009",
            vendor=vendor,
            reason=reason,
            **context,
        )
        self.vendor = vendor
        self.reason = reason
