"""Port: broker order management.

The concrete adapter (e.g. FyersOrderAdapter) lives in
athena.engines.trading.infrastructure and implements this protocol.

This port is the ONLY place in the entire codebase that is authorised
to submit orders to an exchange. No other module may call the broker API.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from athena.core.domain.primitives import Price, Quantity, Symbol


class OrderSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(StrEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class ProductType(StrEnum):
    """NSE/BSE product type codes as understood by Fyers."""

    INTRADAY = "INTRADAY"  # MIS - must be squared off same day
    CARRYFORWARD = "CNC"  # Delivery / positional
    MARGIN = "MARGIN"  # NRML for F&O


@dataclass(frozen=True)
class OrderRequest:
    """Fully specified order ready to be submitted to the broker.

    Constructed by the Trading Engine after all pre-trade risk checks pass.
    The idempotency_key ensures at-most-once submission even under retries.
    """

    idempotency_key: UUID
    symbol: Symbol
    side: OrderSide
    order_type: OrderType
    product_type: ProductType
    quantity: Quantity
    limit_price: Price | None = None  # Required for LIMIT and STOP_LIMIT
    stop_price: Price | None = None  # Required for STOP_LIMIT
    validity: str = "DAY"  # DAY | IOC


@dataclass(frozen=True)
class OrderAcknowledgement:
    """Broker-assigned identifiers returned on successful submission."""

    broker_order_id: str
    client_order_id: UUID  # Mirrors OrderRequest.idempotency_key
    submitted_at_utc: datetime
    status: OrderStatus


@dataclass(frozen=True)
class Position:
    """Current position for one instrument as reported by the broker."""

    symbol: Symbol
    product_type: ProductType
    quantity: Quantity  # Positive = long, negative = short
    average_price: Price
    last_price: Price


@runtime_checkable
class BrokerPort(Protocol):
    """Submit orders and query live account state from the broker."""

    async def submit_order(self, request: OrderRequest) -> OrderAcknowledgement:
        """Submit an order to the broker.

        Must be idempotent: submitting the same idempotency_key twice must
        return the original acknowledgement without creating a duplicate order.

        Raises:
            BrokerError: on any broker-side rejection or communication failure.
        """
        ...

    async def cancel_order(self, broker_order_id: str) -> bool:
        """Request cancellation of an open order.

        Returns True if the cancellation was accepted, False if the order
        was already in a terminal state.
        """
        ...

    async def get_positions(self) -> list[Position]:
        """Return all current open positions from the broker."""
        ...

    async def get_order_status(self, broker_order_id: str) -> OrderStatus:
        """Query the current status of an order by broker ID."""
        ...
