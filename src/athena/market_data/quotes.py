"""Bid/ask quote snapshot value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from athena.core.domain.primitives import Price, Quantity, Symbol
from athena.market_data.exceptions import InvalidQuoteError
from athena.market_data.quality import DataQuality, QualityFlag

if TYPE_CHECKING:
    from datetime import datetime

    from athena.market_data.metadata import DataProvenance


@dataclass(frozen=True)
class Quote:
    """A best-bid/best-ask (NBBO) quote snapshot at a single moment in time.

    Attributes:
        symbol:        Instrument symbol.
        timestamp_utc: UTC timestamp of the quote. Must be timezone-aware.
        bid_price:     Best bid price. ``None`` if not available.
        ask_price:     Best ask price. ``None`` if not available.
        bid_size:      Quantity available at the best bid. ``None`` if not
            provided.
        ask_size:      Quantity available at the best ask. ``None`` if not
            provided.
        exchange:      Exchange or venue from which the quote originated.
            ``None`` when the quote is a consolidated NBBO.
        provenance:    Source metadata.
        quality:       Quality flags.

    Raises:
        InvalidQuoteError: If ``timestamp_utc`` is naive, either price is
            not positive when provided, or either size is negative.
    """

    symbol: Symbol
    timestamp_utc: datetime
    bid_price: Price | None = None
    ask_price: Price | None = None
    bid_size: Quantity | None = None
    ask_size: Quantity | None = None
    exchange: str | None = None
    provenance: DataProvenance | None = None
    quality: DataQuality | None = None

    def __post_init__(self) -> None:
        if self.timestamp_utc.tzinfo is None:
            raise InvalidQuoteError("timestamp_utc must be timezone-aware")
        if self.bid_price is not None and self.bid_price <= 0:
            raise InvalidQuoteError(f"bid_price must be > 0 (got {self.bid_price})")
        if self.ask_price is not None and self.ask_price <= 0:
            raise InvalidQuoteError(f"ask_price must be > 0 (got {self.ask_price})")
        if self.bid_size is not None and self.bid_size < 0:
            raise InvalidQuoteError(f"bid_size must be >= 0 (got {self.bid_size})")
        if self.ask_size is not None and self.ask_size < 0:
            raise InvalidQuoteError(f"ask_size must be >= 0 (got {self.ask_size})")

    @property
    def spread(self) -> Price | None:
        """Bid-ask spread (ask - bid). ``None`` when either side is absent.

        Returns:
            ``Price(ask - bid)`` or ``None``.
        """
        if self.bid_price is not None and self.ask_price is not None:
            return Price(self.ask_price - self.bid_price)
        return None

    @property
    def mid_price(self) -> Price | None:
        """Midpoint of the bid-ask spread. ``None`` when either side is absent.

        Returns:
            ``Price((bid + ask) / 2)`` or ``None``.
        """
        if self.bid_price is not None and self.ask_price is not None:
            return Price((self.bid_price + self.ask_price) / 2)
        return None

    @property
    def is_crossed(self) -> bool:
        """Return ``True`` when bid >= ask (invalid market state).

        Returns:
            ``True`` when both prices are set and bid >= ask.
        """
        if self.bid_price is not None and self.ask_price is not None:
            return self.bid_price >= self.ask_price
        return False

    @property
    def effective_quality(self) -> DataQuality:
        """Return the quality record, auto-flagging crossed markets.

        Returns:
            The attached ``quality``, or a newly constructed one that
            includes ``CROSSED_MARKET`` if ``is_crossed`` is ``True``.
        """
        if self.is_crossed:
            if self.quality is not None:
                return DataQuality.with_flags(
                    *self.quality.flags,
                    QualityFlag.CROSSED_MARKET,
                    confidence=min(self.quality.confidence, 0.1),
                )
            return DataQuality.with_flags(QualityFlag.CROSSED_MARKET, confidence=0.1)
        return self.quality or DataQuality.good()

    def __str__(self) -> str:
        return (
            f"Quote({self.symbol} bid={self.bid_price} ask={self.ask_price} "
            f"{self.timestamp_utc.isoformat()})"
        )
