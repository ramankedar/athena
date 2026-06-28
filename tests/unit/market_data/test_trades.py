"""Unit tests for Trade."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from athena.core.domain.primitives import Price, Quantity, Symbol
from athena.market_data.exceptions import InvalidTradeError
from athena.market_data.models import TradeSide
from athena.market_data.trades import Trade

NIFTY = Symbol("NSE:NIFTY50-INDEX")
NOW = datetime(2025, 1, 15, 9, 15, 30, 500000, tzinfo=UTC)


class TestTrade:
    def test_valid_trade(self) -> None:
        t = Trade(
            symbol=NIFTY,
            timestamp_utc=NOW,
            price=Price(Decimal("24500")),
            volume=Quantity(Decimal("50")),
            side=TradeSide.BUY,
        )
        assert t.notional_value == Decimal("24500") * Decimal("50")

    def test_naive_timestamp_raises(self) -> None:
        with pytest.raises(InvalidTradeError, match="timezone-aware"):
            Trade(
                symbol=NIFTY,
                timestamp_utc=datetime(2025, 1, 15),
                price=Price(Decimal("100")),
                volume=Quantity(Decimal("1")),
            )

    def test_zero_price_raises(self) -> None:
        with pytest.raises(InvalidTradeError, match="price"):
            Trade(
                symbol=NIFTY,
                timestamp_utc=NOW,
                price=Price(Decimal("0")),
                volume=Quantity(Decimal("1")),
            )

    def test_zero_volume_raises(self) -> None:
        with pytest.raises(InvalidTradeError, match="volume"):
            Trade(
                symbol=NIFTY,
                timestamp_utc=NOW,
                price=Price(Decimal("100")),
                volume=Quantity(Decimal("0")),
            )

    def test_notional_value(self) -> None:
        t = Trade(
            symbol=NIFTY,
            timestamp_utc=NOW,
            price=Price(Decimal("200")),
            volume=Quantity(Decimal("5")),
        )
        assert t.notional_value == Decimal("1000")

    def test_is_buyer_initiated(self) -> None:
        t = Trade(
            symbol=NIFTY,
            timestamp_utc=NOW,
            price=Price(Decimal("100")),
            volume=Quantity(Decimal("1")),
            side=TradeSide.BUY,
        )
        assert t.is_buyer_initiated is True

    def test_seller_initiated(self) -> None:
        t = Trade(
            symbol=NIFTY,
            timestamp_utc=NOW,
            price=Price(Decimal("100")),
            volume=Quantity(Decimal("1")),
            side=TradeSide.SELL,
        )
        assert t.is_buyer_initiated is False

    def test_default_side(self) -> None:
        t = Trade(
            symbol=NIFTY,
            timestamp_utc=NOW,
            price=Price(Decimal("100")),
            volume=Quantity(Decimal("1")),
        )
        assert t.side == TradeSide.UNKNOWN

    def test_conditions(self) -> None:
        t = Trade(
            symbol=NIFTY,
            timestamp_utc=NOW,
            price=Price(Decimal("100")),
            volume=Quantity(Decimal("1")),
            conditions=frozenset({"REGULAR"}),
        )
        assert "REGULAR" in t.conditions

    def test_str(self) -> None:
        t = Trade(
            symbol=NIFTY,
            timestamp_utc=NOW,
            price=Price(Decimal("24500")),
            volume=Quantity(Decimal("50")),
            side=TradeSide.BUY,
        )
        s = str(t)
        assert "NSE:NIFTY50-INDEX" in s
        assert "buy" in s
