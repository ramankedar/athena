"""Market data domain validation utilities.

Returns ``ValidationResult`` (structured result with failure messages) rather
than raising immediately. This lets callers batch-validate large datasets and
collect all errors in a single pass — important when validating thousands of
downloaded OHLCV bars before committing them to storage.

Note on ``ValidationResult`` instances in multiple domains:
    ``ValidationResult`` is also defined in ``athena.assets.validation``,
    ``athena.market.validation``, and ``athena.storage.validation``.
    Since these are all peer layers, each defines its own independently.
    The structure is identical; the types are separate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from athena.market_data.adjustments import AdjustmentFactor
    from athena.market_data.ohlcv import OHLCVBar, OHLCVSeries
    from athena.market_data.orderbook import OrderBookSnapshot
    from athena.market_data.quotes import Quote
    from athena.market_data.ticks import MarketTick
    from athena.market_data.trades import Trade


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of a market data validation pass.

    Attributes:
        is_valid: ``True`` when no failures were found.
        failures: Tuple of human-readable failure descriptions.
    """

    is_valid: bool
    failures: tuple[str, ...] = ()

    @classmethod
    def ok(cls) -> ValidationResult:
        """Return a result indicating no failures.

        Returns:
            A valid ``ValidationResult`` with no failures.
        """
        return cls(is_valid=True)

    @classmethod
    def failed(cls, *messages: str) -> ValidationResult:
        """Return a result indicating one or more failures.

        Args:
            *messages: Failure descriptions.

        Returns:
            An invalid ``ValidationResult`` with the provided messages.
        """
        return cls(is_valid=False, failures=tuple(messages))

    def merge(self, other: ValidationResult) -> ValidationResult:
        """Combine two results. Invalid if either input is invalid.

        Args:
            other: The other result to merge.

        Returns:
            Combined ``ValidationResult`` with all failure messages.
        """
        combined = self.failures + other.failures
        return ValidationResult(is_valid=len(combined) == 0, failures=combined)


# ── Domain validators ──────────────────────────────────────────────────────────


def validate_ohlcv_bar(bar: OHLCVBar) -> ValidationResult:
    """Validate an ``OHLCVBar`` against domain business rules.

    Checks beyond the structural validation in ``OHLCVBar.__post_init__``,
    including cross-field business rules.

    Args:
        bar: The bar to validate.

    Returns:
        A ``ValidationResult``.
    """
    failures: list[str] = []

    # Structural checks (may be bypassed via duck-typed input)
    if bar.open_time.tzinfo is None:
        failures.append("open_time must be timezone-aware")
    if bar.close_time.tzinfo is None:
        failures.append("close_time must be timezone-aware")
    # Only compare times when both are timezone-aware (avoids TypeError on mixed types)
    if (
        bar.open_time.tzinfo is not None
        and bar.close_time.tzinfo is not None
        and bar.open_time >= bar.close_time
    ):
        failures.append(f"open_time ({bar.open_time}) must be before close_time ({bar.close_time})")

    # Price structural integrity
    for name, val in (
        ("open", bar.open),
        ("high", bar.high),
        ("low", bar.low),
        ("close", bar.close),
    ):
        if val <= 0:
            failures.append(f"{name} must be > 0 (got {val})")

    if bar.high < bar.low:
        failures.append(f"high ({bar.high}) must be >= low ({bar.low})")
    if bar.volume < 0:
        failures.append(f"volume must be >= 0 (got {bar.volume})")

    # VWAP cross-field check
    if (
        bar.vwap is not None
        and bar.low is not None
        and bar.high is not None
        and not (bar.low <= bar.vwap <= bar.high)
    ):
        failures.append(f"VWAP ({bar.vwap}) must be within [low={bar.low}, high={bar.high}]")

    return ValidationResult.ok() if not failures else ValidationResult.failed(*failures)


def validate_ohlcv_series(series: OHLCVSeries) -> ValidationResult:
    """Validate an ``OHLCVSeries`` for consistency and ordering.

    Args:
        series: The series to validate.

    Returns:
        A ``ValidationResult``.
    """
    failures: list[str] = []

    for i, bar in enumerate(series.bars):
        bar_result = validate_ohlcv_bar(bar)
        if not bar_result.is_valid:
            failures.extend(f"bar[{i}]: {msg}" for msg in bar_result.failures)

        if bar.symbol != series.symbol:
            failures.append(f"bar[{i}].symbol {bar.symbol!r} != series.symbol {series.symbol!r}")
        if bar.timeframe != series.timeframe:
            failures.append(
                f"bar[{i}].timeframe {bar.timeframe!r} != series.timeframe {series.timeframe!r}"
            )

    # Check ordering
    failures.extend(
        f"bars not in ascending open_time order at index {i}"
        for i in range(len(series.bars) - 1)
        if series.bars[i].open_time >= series.bars[i + 1].open_time
    )

    return ValidationResult.ok() if not failures else ValidationResult.failed(*failures)


def validate_tick(tick: MarketTick) -> ValidationResult:
    """Validate a ``MarketTick`` record.

    Args:
        tick: The tick to validate.

    Returns:
        A ``ValidationResult``.
    """
    failures: list[str] = []

    if tick.timestamp_utc.tzinfo is None:
        failures.append("timestamp_utc must be timezone-aware")
    if tick.price <= 0:
        failures.append(f"price must be > 0 (got {tick.price})")
    if tick.volume < 0:
        failures.append(f"volume must be >= 0 (got {tick.volume})")

    return ValidationResult.ok() if not failures else ValidationResult.failed(*failures)


def validate_quote(quote: Quote) -> ValidationResult:
    """Validate a ``Quote`` snapshot.

    Args:
        quote: The quote to validate.

    Returns:
        A ``ValidationResult``.
    """
    failures: list[str] = []

    if quote.timestamp_utc.tzinfo is None:
        failures.append("timestamp_utc must be timezone-aware")

    if quote.bid_price is not None and quote.bid_price <= 0:
        failures.append(f"bid_price must be > 0 (got {quote.bid_price})")
    if quote.ask_price is not None and quote.ask_price <= 0:
        failures.append(f"ask_price must be > 0 (got {quote.ask_price})")

    if quote.is_crossed:
        failures.append(f"crossed market: bid ({quote.bid_price}) >= ask ({quote.ask_price})")

    return ValidationResult.ok() if not failures else ValidationResult.failed(*failures)


def validate_trade(trade: Trade) -> ValidationResult:
    """Validate a ``Trade`` record.

    Args:
        trade: The trade to validate.

    Returns:
        A ``ValidationResult``.
    """
    failures: list[str] = []

    if trade.timestamp_utc.tzinfo is None:
        failures.append("timestamp_utc must be timezone-aware")
    if trade.price <= 0:
        failures.append(f"price must be > 0 (got {trade.price})")
    if trade.volume <= 0:
        failures.append(f"volume must be > 0 (got {trade.volume})")

    return ValidationResult.ok() if not failures else ValidationResult.failed(*failures)


def validate_order_book(snapshot: OrderBookSnapshot) -> ValidationResult:
    """Validate an ``OrderBookSnapshot``.

    Args:
        snapshot: The order book to validate.

    Returns:
        A ``ValidationResult``.
    """
    failures: list[str] = []

    if snapshot.timestamp_utc.tzinfo is None:
        failures.append("timestamp_utc must be timezone-aware")

    if snapshot.is_crossed:
        failures.append(
            f"crossed book: best bid ({snapshot.bids.best_price}) >= "
            f"best ask ({snapshot.asks.best_price})"
        )

    return ValidationResult.ok() if not failures else ValidationResult.failed(*failures)


def validate_adjustment_factor(factor: AdjustmentFactor) -> ValidationResult:
    """Validate an ``AdjustmentFactor`` record.

    Args:
        factor: The adjustment factor to validate.

    Returns:
        A ``ValidationResult``.
    """
    failures: list[str] = []

    if factor.price_factor <= 0:
        failures.append(f"price_factor must be > 0 (got {factor.price_factor})")
    if factor.volume_factor <= 0:
        failures.append(f"volume_factor must be > 0 (got {factor.volume_factor})")

    return ValidationResult.ok() if not failures else ValidationResult.failed(*failures)
