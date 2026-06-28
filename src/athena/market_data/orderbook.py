"""Order book snapshot value objects.

An order book snapshot captures the state of the visible order book at a
single point in time. The model supports multi-level depth (Level 2+) as
well as single-level NBBO (Level 1).

Three types:
    ``OrderBookLevel``    — a single price level with size and order count.
    ``OrderBookSide``     — all levels on one side (bids or asks).
    ``OrderBookSnapshot`` — the complete book at one instant.

Design note on side ordering:
    Bid side levels are in DESCENDING price order (best bid first).
    Ask side levels are in ASCENDING price order (best ask first).
    ``OrderBookSide.is_bid_side`` records which semantics apply.
    This invariant is validated in ``OrderBookSide.__post_init__``.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from athena.core.domain.primitives import Price, Quantity, Symbol
from athena.market_data.exceptions import InvalidOrderBookError

if TYPE_CHECKING:
    from datetime import datetime

    from athena.market_data.metadata import DataProvenance
    from athena.market_data.quality import DataQuality


@dataclass(frozen=True)
class OrderBookLevel:
    """A single price level in the order book.

    Attributes:
        price:       Price of this level. Must be > 0.
        size:        Total quantity available at this price. Must be >= 0.
        order_count: Number of resting orders at this level. ``None`` when
            the venue does not publish order count (common for OTC markets
            and some exchange feeds).

    Raises:
        InvalidOrderBookError: If ``price <= 0`` or ``size < 0``.
    """

    price: Price
    size: Quantity
    order_count: int | None = None

    def __post_init__(self) -> None:
        if self.price <= 0:
            raise InvalidOrderBookError(f"OrderBookLevel.price must be > 0 (got {self.price})")
        if self.size < 0:
            raise InvalidOrderBookError(f"OrderBookLevel.size must be >= 0 (got {self.size})")
        if self.order_count is not None and self.order_count < 0:
            raise InvalidOrderBookError(
                f"OrderBookLevel.order_count must be >= 0 (got {self.order_count})"
            )

    def __str__(self) -> str:
        oc = f" [{self.order_count} orders]" if self.order_count is not None else ""
        return f"Level(@{self.price} x{self.size}{oc})"


@dataclass(frozen=True)
class OrderBookSide:
    """All price levels on one side (bid or ask) of the order book.

    Levels must be in the correct order:
    - Bid side: DESCENDING price (best bid first).
    - Ask side: ASCENDING price (best ask first).

    Attributes:
        levels:      Ordered tuple of price levels. May be empty (thin market).
        is_bid_side: ``True`` for the bid (buy) side; ``False`` for asks.

    Raises:
        InvalidOrderBookError: If levels are not in the correct order for
            the side.
    """

    levels: tuple[OrderBookLevel, ...]
    is_bid_side: bool

    def __post_init__(self) -> None:
        # Validate ordering
        for i in range(len(self.levels) - 1):
            current_price = self.levels[i].price
            next_price = self.levels[i + 1].price
            if self.is_bid_side:
                # Bids must be descending
                if current_price <= next_price:
                    raise InvalidOrderBookError(
                        f"Bid levels must be in descending price order: "
                        f"level[{i}]={current_price} <= level[{i + 1}]={next_price}"
                    )
            else:
                # Asks must be ascending
                if current_price >= next_price:
                    raise InvalidOrderBookError(
                        f"Ask levels must be in ascending price order: "
                        f"level[{i}]={current_price} >= level[{i + 1}]={next_price}"
                    )

    @property
    def best_price(self) -> Price | None:
        """The best (most competitive) price on this side.

        Returns:
            The first level's price (best bid for bids, best ask for asks),
            or ``None`` when the side is empty.
        """
        return self.levels[0].price if self.levels else None

    @property
    def total_size(self) -> Quantity:
        """Total quantity across all visible levels.

        Returns:
            Sum of ``size`` across all levels. ``Quantity(0)`` when empty.
        """
        return Quantity(sum(Decimal(level.size) for level in self.levels))

    @property
    def depth(self) -> int:
        """Number of distinct price levels on this side.

        Returns:
            ``len(self.levels)``.
        """
        return len(self.levels)

    @property
    def is_empty(self) -> bool:
        """Return ``True`` when no price levels are present.

        Returns:
            ``True`` when ``depth == 0``.
        """
        return len(self.levels) == 0

    def __str__(self) -> str:
        side = "bid" if self.is_bid_side else "ask"
        return f"OrderBookSide({side}, depth={self.depth}, best={self.best_price})"


@dataclass(frozen=True)
class OrderBookSnapshot:
    """A complete order book snapshot at a single point in time.

    Attributes:
        symbol:          Instrument symbol.
        timestamp_utc:   UTC timestamp. Must be timezone-aware.
        bids:            Bid-side levels in descending price order.
        asks:            Ask-side levels in ascending price order.
        sequence_number: Exchange-assigned sequence number. Used for ordering
            consecutive snapshots with identical timestamps.
        provenance:      Source metadata.
        quality:         Data quality flags.

    Raises:
        InvalidOrderBookError: If ``timestamp_utc`` is naive, ``bids`` is not
            bid-side, or ``asks`` is not ask-side.
    """

    symbol: Symbol
    timestamp_utc: datetime
    bids: OrderBookSide
    asks: OrderBookSide
    sequence_number: int | None = None
    provenance: DataProvenance | None = None
    quality: DataQuality | None = None

    def __post_init__(self) -> None:
        if self.timestamp_utc.tzinfo is None:
            raise InvalidOrderBookError("timestamp_utc must be timezone-aware")
        if not self.bids.is_bid_side:
            raise InvalidOrderBookError("bids must be an OrderBookSide with is_bid_side=True")
        if self.asks.is_bid_side:
            raise InvalidOrderBookError("asks must be an OrderBookSide with is_bid_side=False")

    @property
    def spread(self) -> Price | None:
        """Best-ask minus best-bid. ``None`` when either side is empty.

        Returns:
            ``Price(ask - bid)`` or ``None``.
        """
        best_bid = self.bids.best_price
        best_ask = self.asks.best_price
        if best_bid is not None and best_ask is not None:
            return Price(best_ask - best_bid)
        return None

    @property
    def mid_price(self) -> Price | None:
        """Midpoint of best-bid and best-ask. ``None`` when either side is empty.

        Returns:
            ``Price((bid + ask) / 2)`` or ``None``.
        """
        best_bid = self.bids.best_price
        best_ask = self.asks.best_price
        if best_bid is not None and best_ask is not None:
            return Price((best_bid + best_ask) / 2)
        return None

    @property
    def is_crossed(self) -> bool:
        """Return ``True`` when best bid >= best ask (invalid state).

        Returns:
            ``True`` when both sides have prices and bid >= ask.
        """
        best_bid = self.bids.best_price
        best_ask = self.asks.best_price
        if best_bid is not None and best_ask is not None:
            return best_bid >= best_ask
        return False

    def __str__(self) -> str:
        return (
            f"OrderBookSnapshot({self.symbol} "
            f"bid={self.bids.best_price}/{self.bids.depth} "
            f"ask={self.asks.best_price}/{self.asks.depth} "
            f"{self.timestamp_utc.isoformat()})"
        )
