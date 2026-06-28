"""Executed trade (print) value object."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING

from athena.market_data.exceptions import InvalidTradeError
from athena.market_data.models import TradeSide

if TYPE_CHECKING:
    from datetime import datetime

    from athena.core.domain.primitives import Price, Quantity, Symbol
    from athena.market_data.metadata import DataProvenance
    from athena.market_data.quality import DataQuality


@dataclass(frozen=True)
class Trade:
    """A single executed trade (tape print) with full metadata.

    Attributes:
        symbol:          Instrument symbol.
        timestamp_utc:   UTC timestamp of the trade. Must be timezone-aware.
        price:           Execution price. Must be > 0.
        volume:          Number of units traded. Must be > 0.
        side:            Aggressor side (BUY, SELL, or UNKNOWN).
        trade_id:        Vendor-assigned trade identifier. ``None`` when not
            provided.
        sequence_number: Exchange sequence number. Used for ordering when
            multiple trades share the same timestamp.
        conditions:      Exchange condition codes as a frozenset (e.g.
            ``{"REGULAR"}`` or ``{"ODD_LOT", "DELAYED"}``).
        provenance:      Source metadata.
        quality:         Data quality flags.

    Raises:
        InvalidTradeError: If ``timestamp_utc`` is naive, ``price <= 0``,
            or ``volume <= 0``.
    """

    symbol: Symbol
    timestamp_utc: datetime
    price: Price
    volume: Quantity
    side: TradeSide = TradeSide.UNKNOWN
    trade_id: str | None = None
    sequence_number: int | None = None
    conditions: frozenset[str] = field(default_factory=frozenset)
    provenance: DataProvenance | None = None
    quality: DataQuality | None = None

    def __post_init__(self) -> None:
        if self.timestamp_utc.tzinfo is None:
            raise InvalidTradeError("timestamp_utc must be timezone-aware")
        if self.price <= 0:
            raise InvalidTradeError(f"price must be > 0 (got {self.price})")
        if self.volume <= 0:
            raise InvalidTradeError(f"volume must be > 0 (got {self.volume})")

    @property
    def notional_value(self) -> Decimal:
        """Total value of the trade (price x volume).

        Returns:
            ``Decimal`` representing ``price * volume``.
        """
        return Decimal(self.price) * Decimal(self.volume)

    @property
    def is_buyer_initiated(self) -> bool:
        """Return ``True`` when the aggressor was the buyer.

        Returns:
            ``True`` when ``side == TradeSide.BUY``.
        """
        return self.side == TradeSide.BUY

    def __str__(self) -> str:
        return (
            f"Trade({self.symbol} {self.side.value} "
            f"@{self.price} x{self.volume} {self.timestamp_utc.isoformat()})"
        )
