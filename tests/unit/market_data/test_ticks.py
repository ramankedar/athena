"""Unit tests for MarketTick."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from athena.core.domain.primitives import Price, Quantity, Symbol
from athena.market_data.exceptions import InvalidTickError
from athena.market_data.models import TickType
from athena.market_data.ticks import MarketTick

NIFTY = Symbol("NSE:NIFTY50-INDEX")
NOW = datetime(2025, 1, 15, 9, 15, 30, tzinfo=UTC)


class TestMarketTick:
    def test_valid_construction(self) -> None:
        tick = MarketTick(
            symbol=NIFTY,
            timestamp_utc=NOW,
            price=Price(Decimal("24500")),
            volume=Quantity(Decimal("50")),
            tick_type=TickType.TRADE,
        )
        assert tick.price == Decimal("24500")
        assert tick.tick_type == TickType.TRADE

    def test_naive_timestamp_raises(self) -> None:
        with pytest.raises(InvalidTickError, match="timezone-aware"):
            MarketTick(
                symbol=NIFTY,
                timestamp_utc=datetime(2025, 1, 15, 9, 15, 30),
                price=Price(Decimal("100")),
                volume=Quantity(Decimal("1")),
            )

    def test_zero_price_raises(self) -> None:
        with pytest.raises(InvalidTickError, match="price"):
            MarketTick(
                symbol=NIFTY,
                timestamp_utc=NOW,
                price=Price(Decimal("0")),
                volume=Quantity(Decimal("1")),
            )

    def test_negative_volume_raises(self) -> None:
        with pytest.raises(InvalidTickError, match="volume"):
            MarketTick(
                symbol=NIFTY,
                timestamp_utc=NOW,
                price=Price(Decimal("100")),
                volume=Quantity(Decimal("-1")),
            )

    def test_naive_exchange_timestamp_raises(self) -> None:
        with pytest.raises(InvalidTickError, match="exchange_timestamp"):
            MarketTick(
                symbol=NIFTY,
                timestamp_utc=NOW,
                price=Price(Decimal("100")),
                volume=Quantity(Decimal("1")),
                exchange_timestamp=datetime(2025, 1, 15, 9, 15),  # naive
            )

    def test_is_trade(self) -> None:
        tick = MarketTick(
            symbol=NIFTY,
            timestamp_utc=NOW,
            price=Price(Decimal("100")),
            volume=Quantity(Decimal("1")),
            tick_type=TickType.TRADE,
        )
        assert tick.is_trade is True
        assert tick.is_quote is False

    def test_is_quote(self) -> None:
        tick = MarketTick(
            symbol=NIFTY,
            timestamp_utc=NOW,
            price=Price(Decimal("100")),
            volume=Quantity(Decimal("0")),
            tick_type=TickType.BID,
        )
        assert tick.is_quote is True
        assert tick.is_trade is False

    def test_with_conditions(self) -> None:
        tick = MarketTick(
            symbol=NIFTY,
            timestamp_utc=NOW,
            price=Price(Decimal("100")),
            volume=Quantity(Decimal("1")),
            conditions=frozenset({"REGULAR", "ODD_LOT"}),
        )
        assert "REGULAR" in tick.conditions

    def test_default_tick_type(self) -> None:
        tick = MarketTick(
            symbol=NIFTY,
            timestamp_utc=NOW,
            price=Price(Decimal("100")),
            volume=Quantity(Decimal("1")),
        )
        assert tick.tick_type == TickType.UNKNOWN

    def test_zero_volume_is_valid(self) -> None:
        tick = MarketTick(
            symbol=NIFTY,
            timestamp_utc=NOW,
            price=Price(Decimal("100")),
            volume=Quantity(Decimal("0")),
            tick_type=TickType.BID,
        )
        assert tick.volume == Decimal("0")

    def test_str(self) -> None:
        tick = MarketTick(
            symbol=NIFTY,
            timestamp_utc=NOW,
            price=Price(Decimal("24500")),
            volume=Quantity(Decimal("50")),
            tick_type=TickType.TRADE,
        )
        s = str(tick)
        assert "NSE:NIFTY50-INDEX" in s
        assert "trade" in s
