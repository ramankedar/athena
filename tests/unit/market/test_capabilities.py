"""Unit tests for market capabilities."""

from __future__ import annotations

from decimal import Decimal

import pytest

from athena.market.capabilities import (
    NSE_EQ_CAPABILITIES,
    NSE_EQ_ORDER_CAPS,
    MarketCapabilities,
    OrderCapabilities,
    OrderType,
    OrderValidity,
)
from athena.market.exceptions import InvalidMarketIdError
from athena.market.models import MarketId


class TestOrderType:
    def test_values(self) -> None:
        assert OrderType.LIMIT == "limit"
        assert OrderType.MARKET == "market"
        assert OrderType.STOP_LIMIT == "stop_limit"
        assert OrderType.STOP_MARKET == "stop_market"
        assert OrderType.ICEBERG == "iceberg"
        assert OrderType.IOC == "ioc"
        assert OrderType.FOK == "fok"
        assert OrderType.AFTER_MARKET == "after_market"
        assert OrderType.BASKET == "basket"


class TestOrderValidity:
    def test_values(self) -> None:
        assert OrderValidity.DAY == "day"
        assert OrderValidity.GTC == "gtc"
        assert OrderValidity.GTD == "gtd"
        assert OrderValidity.AT_OPEN == "at_open"
        assert OrderValidity.AT_CLOSE == "at_close"


class TestOrderCapabilities:
    def test_nse_eq_order_caps(self) -> None:
        assert OrderType.LIMIT in NSE_EQ_ORDER_CAPS.supported_order_types
        assert NSE_EQ_ORDER_CAPS.default_order_type == OrderType.LIMIT

    def test_supports_order_type_true(self) -> None:
        assert NSE_EQ_ORDER_CAPS.supports(OrderType.LIMIT) is True

    def test_supports_order_type_false(self) -> None:
        assert NSE_EQ_ORDER_CAPS.supports(OrderType.FOK) is False

    def test_supports_validity_true(self) -> None:
        assert NSE_EQ_ORDER_CAPS.supports_validity(OrderValidity.DAY) is True

    def test_supports_validity_false(self) -> None:
        assert NSE_EQ_ORDER_CAPS.supports_validity(OrderValidity.GTC) is False

    def test_empty_supported_types_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError, match="empty"):
            OrderCapabilities(
                supported_order_types=frozenset(),
                supported_validities=frozenset({OrderValidity.DAY}),
                default_order_type=OrderType.LIMIT,
            )

    def test_default_not_in_supported_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError, match="default_order_type"):
            OrderCapabilities(
                supported_order_types=frozenset({OrderType.MARKET}),
                supported_validities=frozenset({OrderValidity.DAY}),
                default_order_type=OrderType.LIMIT,  # not in supported
            )

    def test_max_less_than_min_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError, match="max_order_value"):
            OrderCapabilities(
                supported_order_types=frozenset({OrderType.LIMIT}),
                supported_validities=frozenset({OrderValidity.DAY}),
                default_order_type=OrderType.LIMIT,
                max_order_value=Decimal("100"),
                min_order_value=Decimal("500"),
            )

    def test_with_value_limits(self) -> None:
        caps = OrderCapabilities(
            supported_order_types=frozenset({OrderType.LIMIT}),
            supported_validities=frozenset({OrderValidity.DAY}),
            default_order_type=OrderType.LIMIT,
            max_order_value=Decimal("500000"),
            min_order_value=Decimal("100"),
        )
        assert caps.max_order_value == Decimal("500000")


class TestMarketCapabilities:
    def test_nse_eq_capabilities(self) -> None:
        caps = NSE_EQ_CAPABILITIES
        assert caps.exchange_id == MarketId("NSE")
        assert caps.segment_id == MarketId("NSE_EQ")
        assert caps.supports_margin_trading is True
        assert caps.supports_short_selling is True
        assert caps.supports_algo_trading is True
        assert caps.supports_after_market is True
        assert caps.supports_block_deals is True
        assert caps.supports_derivatives is False

    def test_supports_asset_class_true(self) -> None:
        assert NSE_EQ_CAPABILITIES.supports_asset_class("equity") is True
        assert NSE_EQ_CAPABILITIES.supports_asset_class("etf") is True

    def test_supports_asset_class_false(self) -> None:
        assert NSE_EQ_CAPABILITIES.supports_asset_class("commodity") is False

    def test_supports_order_type_delegates(self) -> None:
        assert NSE_EQ_CAPABILITIES.supports_order_type(OrderType.LIMIT) is True
        assert NSE_EQ_CAPABILITIES.supports_order_type(OrderType.FOK) is False

    def test_empty_asset_classes_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError, match="empty"):
            MarketCapabilities(
                exchange_id=MarketId("TEST"),
                segment_id=None,
                supported_asset_classes=frozenset(),
                order_capabilities=NSE_EQ_ORDER_CAPS,
            )

    def test_exchange_wide_capabilities(self) -> None:
        caps = MarketCapabilities(
            exchange_id=MarketId("NSE"),
            segment_id=None,
            supported_asset_classes=frozenset({"equity", "derivative"}),
            order_capabilities=NSE_EQ_ORDER_CAPS,
        )
        assert caps.segment_id is None
        assert caps.supports_derivatives is False  # default
