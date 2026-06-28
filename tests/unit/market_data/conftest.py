"""Shared fixtures for market data unit tests."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from athena.core.domain.primitives import Price, Quantity, Symbol
from athena.market_data.metadata import DataProvenance
from athena.market_data.models import Timeframe
from athena.market_data.ohlcv import OHLCVBar
from athena.market_data.quality import DataQuality

NOW = datetime(2025, 1, 15, 9, 15, tzinfo=UTC)
CLOSE = datetime(2025, 1, 15, 9, 16, tzinfo=UTC)
NIFTY = Symbol("NSE:NIFTY50-INDEX")


@pytest.fixture
def nifty() -> Symbol:
    return NIFTY


@pytest.fixture
def sample_provenance() -> DataProvenance:
    return DataProvenance(
        vendor="fyers",
        vendor_symbol="NSE:NIFTY50-INDEX",
        retrieved_at=NOW,
    )


@pytest.fixture
def good_quality() -> DataQuality:
    return DataQuality.good()


@pytest.fixture
def sample_bar() -> OHLCVBar:
    return OHLCVBar(
        symbol=NIFTY,
        timeframe=Timeframe.MINUTE_1,
        open_time=NOW,
        close_time=CLOSE,
        open=Price(Decimal("24490")),
        high=Price(Decimal("24510")),
        low=Price(Decimal("24480")),
        close=Price(Decimal("24500")),
        volume=Quantity(Decimal("5000")),
    )
