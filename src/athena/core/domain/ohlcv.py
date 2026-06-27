"""OHLCV bar domain model.

An OHLCV bar aggregates all ticks within a fixed time window into five
canonical values: Open, High, Low, Close, Volume. Bars are the primary
unit consumed by signal computation and backtesting.

Bars are immutable once closed. An open (in-progress) bar is a mutable
aggregate maintained by the Data Engine's aggregator; only the closed
bar is published as a domain event.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

from athena.core.domain.primitives import Price  # needed at runtime for property returns

if TYPE_CHECKING:
    from datetime import datetime

    from athena.core.domain.primitives import Quantity, Symbol


class BarInterval(IntEnum):
    """Bar duration in seconds. Matches Fyers API resolution identifiers."""

    ONE_MINUTE = 60
    THREE_MINUTES = 180
    FIVE_MINUTES = 300
    FIFTEEN_MINUTES = 900
    THIRTY_MINUTES = 1800
    ONE_HOUR = 3600
    ONE_DAY = 86400


@dataclass(frozen=True)
class OHLCV:
    """A single closed OHLCV bar for one instrument.

    Fields:
        symbol:       Fully-qualified instrument symbol.
        interval:     Bar duration.
        open_time:    UTC timestamp of the bar's first tick (inclusive).
        close_time:   UTC timestamp of the bar's last tick (inclusive).
        open:         Price of the first tick in the bar.
        high:         Highest price within the bar.
        low:          Lowest price within the bar.
        close:        Price of the last tick in the bar.
        volume:       Total traded volume within the bar.
        open_interest: Open interest at bar close (derivatives only).
    """

    symbol: Symbol
    interval: BarInterval
    open_time: datetime
    close_time: datetime
    open: Price
    high: Price
    low: Price
    close: Price
    volume: Quantity
    open_interest: Quantity | None = None

    def __post_init__(self) -> None:
        if self.open_time.tzinfo is None or self.close_time.tzinfo is None:
            raise ValueError("OHLCV timestamps must be timezone-aware (UTC expected)")
        if self.open_time >= self.close_time:
            raise ValueError("OHLCV open_time must be before close_time")
        if self.high < self.low:
            raise ValueError(f"OHLCV high {self.high} cannot be less than low {self.low}")
        if not (self.low <= self.open <= self.high):
            raise ValueError(
                f"OHLCV open {self.open} must be within [low={self.low}, high={self.high}]"
            )
        if not (self.low <= self.close <= self.high):
            raise ValueError(
                f"OHLCV close {self.close} must be within [low={self.low}, high={self.high}]"
            )

    @property
    def range(self) -> Price:
        """High - Low for the bar."""
        return Price(self.high - self.low)

    @property
    def is_bullish(self) -> bool:
        return self.close >= self.open

    @property
    def body_size(self) -> Price:
        """Absolute difference between open and close."""
        return Price(abs(self.close - self.open))
