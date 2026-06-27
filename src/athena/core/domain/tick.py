"""Tick domain model - the atomic unit of market data.

A Tick represents a single market update: either a trade print or a
best-bid/ask quote update. Once created from a raw exchange payload it
is immutable. The Data Engine normalises exchange-specific formats into
this canonical representation before any other engine sees the data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from athena.core.domain.primitives import Price  # needed at runtime for property returns

if TYPE_CHECKING:
    from datetime import datetime

    from athena.core.domain.primitives import Quantity, Symbol


@dataclass(frozen=True)
class Tick:
    """A single market data update for one instrument.

    Fields:
        symbol:         Fully-qualified instrument symbol.
        timestamp_utc:  Exchange timestamp converted to UTC. Microsecond precision.
        last_price:     Last traded price (LTP).
        volume:         Cumulative day volume at this tick.
        bid:            Best bid price. None if not available in the feed.
        ask:            Best ask price. None if not available in the feed.
        bid_size:       Quantity available at best bid.
        ask_size:       Quantity available at best ask.
        open_interest:  Open interest for derivatives. None for cash instruments.
    """

    symbol: Symbol
    timestamp_utc: datetime
    last_price: Price
    volume: Quantity
    bid: Price | None = None
    ask: Price | None = None
    bid_size: Quantity | None = None
    ask_size: Quantity | None = None
    open_interest: Quantity | None = None

    def __post_init__(self) -> None:
        if self.timestamp_utc.tzinfo is None:
            raise ValueError("Tick.timestamp_utc must be timezone-aware (UTC expected)")

    @property
    def spread(self) -> Price | None:
        """Bid-ask spread. None if either side is unavailable."""
        if self.bid is not None and self.ask is not None:
            return Price(self.ask - self.bid)
        return None

    @property
    def mid_price(self) -> Price | None:
        """Mid-point of the bid-ask spread."""
        if self.bid is not None and self.ask is not None:
            return Price((self.bid + self.ask) / 2)
        return None
