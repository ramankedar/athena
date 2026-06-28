"""Market capability value objects.

``MarketCapabilities`` describes what an exchange or segment can do:
which asset classes it supports, which order types it accepts, and what
special features are available (margin, short-selling, algorithmic trading).

Capabilities are modelled at the segment level because different segments
of the same exchange have different capabilities. NSE's equity segment
supports LIMIT and MARKET orders; NSE's F&O segment supports LIMIT and
STOP_LIMIT orders but not (typically) MARKET orders for options.

``OrderType`` and ``OrderValidity`` are defined here rather than in the Asset
Domain because they are properties of the market's rule book, not of the
traded instrument itself. An option contract does not carry information about
whether its exchange supports stop-limit orders.

Design note on ``supported_asset_classes``:
    This field stores string tags (e.g. ``"equity"``, ``"derivative"``) rather
    than importing ``AssetClass`` from ``athena.assets``. This preserves
    peer-layer isolation — the Market Domain does not import from the Asset
    Domain. The strings match ``AssetClass`` enum values so engines can
    cross-reference them.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from athena.market.exceptions import InvalidMarketIdError
from athena.market.models import MarketId

if TYPE_CHECKING:
    from decimal import Decimal


class OrderType(StrEnum):
    """Types of orders supported by an exchange or segment.

    Attributes:
        LIMIT:        Order to buy/sell at a specified price or better.
        MARKET:       Order to buy/sell immediately at the best available price.
        STOP_LIMIT:   Stop order that converts to a limit order when triggered
            (``SL`` in NSE terminology).
        STOP_MARKET:  Stop order that converts to a market order when triggered
            (``SL-M`` in NSE terminology).
        ICEBERG:      Large order split into smaller disclosed lots to reduce
            market impact (``Disclosed Quantity`` in NSE terminology).
        IOC:          Immediate-Or-Cancel: fill what is possible immediately,
            cancel the remainder.
        FOK:          Fill-Or-Kill: fill the entire order immediately or cancel.
        AFTER_MARKET: Orders placed outside market hours, queued for the next
            session (``AMO`` in NSE terminology).
        BASKET:       A group of orders submitted together as a single unit.
    """

    LIMIT = "limit"
    MARKET = "market"
    STOP_LIMIT = "stop_limit"
    STOP_MARKET = "stop_market"
    ICEBERG = "iceberg"
    IOC = "ioc"
    FOK = "fok"
    AFTER_MARKET = "after_market"
    BASKET = "basket"


class OrderValidity(StrEnum):
    """Time-in-force rules for orders.

    Attributes:
        DAY:  Order is valid for the current trading day only.
        GTC:  Good Till Cancelled — valid until filled or explicitly cancelled.
        GTD:  Good Till Date — valid until a specified date.
        IOC:  Immediate or Cancel (also an ``OrderType``; validity and type
            overlap for IOC).
        FOK:  Fill or Kill (same overlap as IOC).
        AT_OPEN:  Execute only at the opening auction.
        AT_CLOSE: Execute only at the closing auction.
    """

    DAY = "day"
    GTC = "gtc"
    GTD = "gtd"
    IOC = "ioc"
    FOK = "fok"
    AT_OPEN = "at_open"
    AT_CLOSE = "at_close"


@dataclass(frozen=True)
class OrderCapabilities:
    """The set of order-related capabilities for an exchange or segment.

    Attributes:
        supported_order_types:     Frozenset of supported ``OrderType`` values.
        supported_validities:      Frozenset of supported ``OrderValidity`` values.
        default_order_type:        The order type assumed when none is specified.
        supports_fractional_qty:   Whether fractional share quantities are
            accepted (uncommon for Indian markets; relevant for US fractional
            share trading).
        max_order_value:           Maximum monetary value of a single order.
            ``None`` if no explicit cap applies.
        min_order_value:           Minimum monetary value of a single order.
            ``None`` if no minimum applies.

    Example::

        nse_order_caps = OrderCapabilities(
            supported_order_types=frozenset({
                OrderType.LIMIT, OrderType.MARKET, OrderType.STOP_LIMIT,
                OrderType.STOP_MARKET, OrderType.ICEBERG, OrderType.IOC,
                OrderType.AFTER_MARKET,
            }),
            supported_validities=frozenset({OrderValidity.DAY, OrderValidity.IOC}),
            default_order_type=OrderType.LIMIT,
        )
    """

    supported_order_types: frozenset[OrderType]
    supported_validities: frozenset[OrderValidity]
    default_order_type: OrderType
    supports_fractional_qty: bool = False
    max_order_value: Decimal | None = None
    min_order_value: Decimal | None = None

    def __post_init__(self) -> None:
        if not self.supported_order_types:
            raise InvalidMarketIdError(
                self.default_order_type.value,
                reason="OrderCapabilities.supported_order_types must not be empty",
            )
        if self.default_order_type not in self.supported_order_types:
            raise InvalidMarketIdError(
                self.default_order_type.value,
                reason=(
                    f"default_order_type {self.default_order_type.value!r} is not "
                    "in supported_order_types"
                ),
            )
        if (
            self.max_order_value is not None
            and self.min_order_value is not None
            and self.max_order_value < self.min_order_value
        ):
            raise InvalidMarketIdError(
                self.default_order_type.value,
                reason="max_order_value must be >= min_order_value",
            )

    def supports(self, order_type: OrderType) -> bool:
        """Return ``True`` if the given order type is supported.

        Args:
            order_type: The order type to check.

        Returns:
            ``True`` when ``order_type`` is in ``supported_order_types``.
        """
        return order_type in self.supported_order_types

    def supports_validity(self, validity: OrderValidity) -> bool:
        """Return ``True`` if the given order validity is supported.

        Args:
            validity: The time-in-force to check.

        Returns:
            ``True`` when ``validity`` is in ``supported_validities``.
        """
        return validity in self.supported_validities


@dataclass(frozen=True)
class MarketCapabilities:
    """Complete capability description for an exchange or segment.

    Attributes:
        exchange_id:               The exchange these capabilities describe.
        segment_id:                Optional segment scope. ``None`` means the
            capabilities apply exchange-wide (as defaults for all segments).
        supported_asset_classes:   Frozenset of asset class strings supported.
            Values match ``athena.assets.AssetClass`` enum values.
        order_capabilities:        Order types and validities available.
        supports_derivatives:      Whether futures and options can be traded.
        supports_margin_trading:   Whether leveraged margin positions are supported.
        supports_short_selling:    Whether selling borrowed securities is permitted.
        supports_algo_trading:     Whether algorithmic / DMA order flow is accepted.
        supports_after_market:     Whether after-market orders (AMO) are accepted.
        supports_block_deals:      Whether block deal windows are available.
        supports_bulk_deals:       Whether bulk deal reporting is applicable.

    Example::

        nse_eq_caps = MarketCapabilities(
            exchange_id=MarketId("NSE"),
            segment_id=MarketId("NSE_EQ"),
            supported_asset_classes=frozenset({"equity", "etf"}),
            order_capabilities=OrderCapabilities(...),
            supports_margin_trading=True,
            supports_short_selling=True,
            supports_algo_trading=True,
            supports_after_market=True,
        )
    """

    exchange_id: MarketId
    segment_id: MarketId | None
    supported_asset_classes: frozenset[str]
    order_capabilities: OrderCapabilities
    supports_derivatives: bool = False
    supports_margin_trading: bool = False
    supports_short_selling: bool = False
    supports_algo_trading: bool = True
    supports_after_market: bool = False
    supports_block_deals: bool = False
    supports_bulk_deals: bool = False

    def __post_init__(self) -> None:
        if not self.supported_asset_classes:
            raise InvalidMarketIdError(
                str(self.exchange_id),
                reason="MarketCapabilities.supported_asset_classes must not be empty",
            )

    def supports_asset_class(self, asset_class: str) -> bool:
        """Return ``True`` if the given asset class is supported.

        Args:
            asset_class: Asset class string (e.g. ``"equity"``, ``"derivative"``).

        Returns:
            ``True`` when ``asset_class`` is in ``supported_asset_classes``.
        """
        return asset_class in self.supported_asset_classes

    def supports_order_type(self, order_type: OrderType) -> bool:
        """Return ``True`` if the given order type is supported.

        Args:
            order_type: The ``OrderType`` to check.

        Returns:
            Delegates to ``self.order_capabilities.supports(order_type)``.
        """
        return self.order_capabilities.supports(order_type)


# ── Well-known capability constants ────────────────────────────────────────────

#: Standard NSE equity segment order capabilities.
NSE_EQ_ORDER_CAPS: OrderCapabilities = OrderCapabilities(
    supported_order_types=frozenset(
        {
            OrderType.LIMIT,
            OrderType.MARKET,
            OrderType.STOP_LIMIT,
            OrderType.STOP_MARKET,
            OrderType.ICEBERG,
            OrderType.IOC,
            OrderType.AFTER_MARKET,
        }
    ),
    supported_validities=frozenset(
        {
            OrderValidity.DAY,
            OrderValidity.IOC,
        }
    ),
    default_order_type=OrderType.LIMIT,
)

#: NSE Equity segment market capabilities.
NSE_EQ_CAPABILITIES: MarketCapabilities = MarketCapabilities(
    exchange_id=MarketId("NSE"),
    segment_id=MarketId("NSE_EQ"),
    supported_asset_classes=frozenset({"equity", "etf", "index"}),
    order_capabilities=NSE_EQ_ORDER_CAPS,
    supports_margin_trading=True,
    supports_short_selling=True,
    supports_algo_trading=True,
    supports_after_market=True,
    supports_block_deals=True,
    supports_bulk_deals=True,
)
