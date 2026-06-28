"""Unit tests for order book value objects."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from athena.core.domain.primitives import Price, Quantity, Symbol
from athena.market_data.exceptions import InvalidOrderBookError
from athena.market_data.orderbook import OrderBookLevel, OrderBookSide, OrderBookSnapshot

NIFTY = Symbol("NSE:NIFTY50-INDEX")
NOW = datetime(2025, 1, 15, 9, 15, tzinfo=UTC)


class TestOrderBookLevel:
    def test_valid_construction(self) -> None:
        level = OrderBookLevel(price=Price(Decimal("24500")), size=Quantity(Decimal("100")))
        assert level.price == Decimal("24500")
        assert level.order_count is None

    def test_zero_price_raises(self) -> None:
        with pytest.raises(InvalidOrderBookError, match="price"):
            OrderBookLevel(price=Price(Decimal("0")), size=Quantity(Decimal("10")))

    def test_negative_size_raises(self) -> None:
        with pytest.raises(InvalidOrderBookError, match="size"):
            OrderBookLevel(price=Price(Decimal("100")), size=Quantity(Decimal("-1")))

    def test_negative_order_count_raises(self) -> None:
        with pytest.raises(InvalidOrderBookError, match="order_count"):
            OrderBookLevel(
                price=Price(Decimal("100")),
                size=Quantity(Decimal("10")),
                order_count=-1,
            )

    def test_str(self) -> None:
        level = OrderBookLevel(
            price=Price(Decimal("24500")),
            size=Quantity(Decimal("100")),
            order_count=5,
        )
        s = str(level)
        assert "24500" in s
        assert "5 orders" in s


class TestOrderBookSide:
    def _bid_side(self) -> OrderBookSide:
        return OrderBookSide(
            levels=(
                OrderBookLevel(Price(Decimal("24500")), Quantity(Decimal("100"))),
                OrderBookLevel(Price(Decimal("24490")), Quantity(Decimal("200"))),
            ),
            is_bid_side=True,
        )

    def _ask_side(self) -> OrderBookSide:
        return OrderBookSide(
            levels=(
                OrderBookLevel(Price(Decimal("24510")), Quantity(Decimal("150"))),
                OrderBookLevel(Price(Decimal("24520")), Quantity(Decimal("300"))),
            ),
            is_bid_side=False,
        )

    def test_bid_side_best_price(self) -> None:
        side = self._bid_side()
        assert side.best_price == Price(Decimal("24500"))

    def test_ask_side_best_price(self) -> None:
        side = self._ask_side()
        assert side.best_price == Price(Decimal("24510"))

    def test_total_size(self) -> None:
        side = self._bid_side()
        assert side.total_size == Quantity(Decimal("300"))

    def test_depth(self) -> None:
        assert self._bid_side().depth == 2

    def test_empty_side(self) -> None:
        side = OrderBookSide(levels=(), is_bid_side=True)
        assert side.is_empty is True
        assert side.best_price is None
        assert side.total_size == Quantity(Decimal("0"))

    def test_bid_out_of_order_raises(self) -> None:
        with pytest.raises(InvalidOrderBookError, match="descending"):
            OrderBookSide(
                levels=(
                    OrderBookLevel(Price(Decimal("24490")), Quantity(Decimal("100"))),
                    OrderBookLevel(Price(Decimal("24500")), Quantity(Decimal("200"))),  # wrong
                ),
                is_bid_side=True,
            )

    def test_ask_out_of_order_raises(self) -> None:
        with pytest.raises(InvalidOrderBookError, match="ascending"):
            OrderBookSide(
                levels=(
                    OrderBookLevel(Price(Decimal("24520")), Quantity(Decimal("100"))),  # wrong
                    OrderBookLevel(Price(Decimal("24510")), Quantity(Decimal("200"))),
                ),
                is_bid_side=False,
            )

    def test_str(self) -> None:
        s = str(self._bid_side())
        assert "bid" in s
        assert "depth=2" in s


class TestOrderBookSnapshot:
    def _snapshot(self) -> OrderBookSnapshot:
        bids = OrderBookSide(
            levels=(OrderBookLevel(Price(Decimal("24490")), Quantity(Decimal("100"))),),
            is_bid_side=True,
        )
        asks = OrderBookSide(
            levels=(OrderBookLevel(Price(Decimal("24510")), Quantity(Decimal("150"))),),
            is_bid_side=False,
        )
        return OrderBookSnapshot(symbol=NIFTY, timestamp_utc=NOW, bids=bids, asks=asks)

    def test_spread(self) -> None:
        snap = self._snapshot()
        assert snap.spread == Price(Decimal("20"))  # 24510 - 24490

    def test_mid_price(self) -> None:
        snap = self._snapshot()
        assert snap.mid_price == Price(Decimal("24500"))

    def test_is_crossed_false(self) -> None:
        assert self._snapshot().is_crossed is False

    def test_is_crossed_true(self) -> None:
        bids = OrderBookSide(
            levels=(OrderBookLevel(Price(Decimal("24520")), Quantity(Decimal("100"))),),
            is_bid_side=True,
        )
        asks = OrderBookSide(
            levels=(OrderBookLevel(Price(Decimal("24510")), Quantity(Decimal("100"))),),
            is_bid_side=False,
        )
        snap = OrderBookSnapshot(symbol=NIFTY, timestamp_utc=NOW, bids=bids, asks=asks)
        assert snap.is_crossed is True

    def test_naive_timestamp_raises(self) -> None:
        bids = OrderBookSide(levels=(), is_bid_side=True)
        asks = OrderBookSide(levels=(), is_bid_side=False)
        with pytest.raises(InvalidOrderBookError, match="timezone-aware"):
            OrderBookSnapshot(
                symbol=NIFTY,
                timestamp_utc=datetime(2025, 1, 15, 9, 15),
                bids=bids,
                asks=asks,
            )

    def test_wrong_bid_side_raises(self) -> None:
        ask_side = OrderBookSide(levels=(), is_bid_side=False)
        with pytest.raises(InvalidOrderBookError, match="bid"):
            OrderBookSnapshot(
                symbol=NIFTY,
                timestamp_utc=NOW,
                bids=ask_side,  # wrong
                asks=ask_side,
            )

    def test_spread_none_when_empty(self) -> None:
        bids = OrderBookSide(levels=(), is_bid_side=True)
        asks = OrderBookSide(levels=(), is_bid_side=False)
        snap = OrderBookSnapshot(symbol=NIFTY, timestamp_utc=NOW, bids=bids, asks=asks)
        assert snap.spread is None
        assert snap.mid_price is None
        assert snap.is_crossed is False

    def test_str(self) -> None:
        s = str(self._snapshot())
        assert "NSE:NIFTY50-INDEX" in s
