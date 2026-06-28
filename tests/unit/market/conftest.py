"""Shared fixtures for market domain unit tests."""

from __future__ import annotations

from datetime import time

import pytest

from athena.market.capabilities import OrderCapabilities, OrderType, OrderValidity
from athena.market.exchange import NSE, ExchangeMetadata
from athena.market.models import (
    CountryCode,
    MarketCurrency,
    MarketId,
    MarketTimezone,
)
from athena.market.sessions import DailySchedule, MarketSessionType, SessionWindow


@pytest.fixture
def nse_id() -> MarketId:
    return MarketId("NSE")


@pytest.fixture
def india() -> CountryCode:
    return CountryCode("IN")


@pytest.fixture
def inr() -> MarketCurrency:
    return MarketCurrency("INR")


@pytest.fixture
def ist() -> MarketTimezone:
    return MarketTimezone("Asia/Kolkata")


@pytest.fixture
def nse_metadata() -> ExchangeMetadata:
    return NSE


@pytest.fixture
def basic_order_caps() -> OrderCapabilities:
    return OrderCapabilities(
        supported_order_types=frozenset({OrderType.LIMIT, OrderType.MARKET}),
        supported_validities=frozenset({OrderValidity.DAY}),
        default_order_type=OrderType.LIMIT,
    )


@pytest.fixture
def nse_daily_schedule(ist: MarketTimezone) -> DailySchedule:
    return DailySchedule(
        sessions=(
            SessionWindow(MarketSessionType.PRE_OPEN, time(9, 0), time(9, 15)),
            SessionWindow(MarketSessionType.CONTINUOUS, time(9, 15), time(15, 30)),
            SessionWindow(MarketSessionType.CLOSING_AUCTION, time(15, 30), time(16, 0)),
        ),
        timezone=ist,
    )
