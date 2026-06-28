"""Market tick value object.

``MarketTick`` is the richer sibling of ``athena.core.domain.tick.Tick``.
Where the core type is a minimal transport used in event streams, ``MarketTick``
carries vendor provenance, exchange condition codes, type classification,
sequence numbers for ordering, and data quality metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from athena.market_data.exceptions import InvalidTickError
from athena.market_data.models import TickType

if TYPE_CHECKING:
    from datetime import datetime

    from athena.core.domain.primitives import Price, Quantity, Symbol
    from athena.market_data.metadata import DataProvenance
    from athena.market_data.quality import DataQuality


@dataclass(frozen=True)
class MarketTick:
    """A single market tick (trade print or quote update) with rich metadata.

    Attributes:
        symbol:             Instrument symbol.
        timestamp_utc:      UTC timestamp of the tick. Must be timezone-aware.
        price:              Price at which the tick occurred. Must be > 0.
        volume:             Volume associated with the tick. Must be >= 0.
        tick_type:          Classification: TRADE, BID, ASK, or UNKNOWN.
        exchange_timestamp: Exchange-assigned timestamp (may differ from
            ``timestamp_utc`` due to processing delay). ``None`` when not
            provided by the vendor.
        conditions:         Exchange condition codes as a frozenset of strings
            (e.g. ``{"REGULAR", "ODD_LOT"}``). Vendor-specific; interpret
            using the exchange's condition code legend.
        sequence_number:    Vendor-assigned sequence number. Used to order
            ticks with identical timestamps. ``None`` when not provided.
        provenance:         Source metadata. ``None`` for in-process ticks.
        quality:            Quality flags and confidence score.

    Raises:
        InvalidTickError: If ``timestamp_utc`` is naive, ``price <= 0``,
            or ``volume < 0``.
    """

    symbol: Symbol
    timestamp_utc: datetime
    price: Price
    volume: Quantity
    tick_type: TickType = TickType.UNKNOWN
    exchange_timestamp: datetime | None = None
    conditions: frozenset[str] = field(default_factory=frozenset)
    sequence_number: int | None = None
    provenance: DataProvenance | None = None
    quality: DataQuality | None = None

    def __post_init__(self) -> None:
        if self.timestamp_utc.tzinfo is None:
            raise InvalidTickError("timestamp_utc must be timezone-aware")
        if self.price <= 0:
            raise InvalidTickError(f"price must be > 0 (got {self.price})")
        if self.volume < 0:
            raise InvalidTickError(f"volume must be >= 0 (got {self.volume})")
        if self.exchange_timestamp is not None and self.exchange_timestamp.tzinfo is None:
            raise InvalidTickError("exchange_timestamp must be timezone-aware when provided")

    @property
    def is_trade(self) -> bool:
        """Return ``True`` when this tick represents an executed trade.

        Returns:
            ``True`` when ``tick_type == TickType.TRADE``.
        """
        return self.tick_type == TickType.TRADE

    @property
    def is_quote(self) -> bool:
        """Return ``True`` when this tick represents a quote update (BID or ASK).

        Returns:
            ``True`` when ``tick_type`` is ``BID`` or ``ASK``.
        """
        return self.tick_type in (TickType.BID, TickType.ASK)

    def __str__(self) -> str:
        return (
            f"MarketTick({self.symbol} {self.tick_type.value} "
            f"@{self.price} x{self.volume} {self.timestamp_utc.isoformat()})"
        )
