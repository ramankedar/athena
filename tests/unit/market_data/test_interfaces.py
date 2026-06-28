"""Unit tests for market data Protocol interfaces."""

from __future__ import annotations

from datetime import UTC, date, datetime

from athena.core.domain.primitives import Symbol
from athena.market_data.adjustments import AdjustmentFactor
from athena.market_data.corporate_actions import CorporateAction
from athena.market_data.interfaces import (
    CorporateActionProviderProtocol,
    HistoricalDataProviderProtocol,
    LiveDataProviderProtocol,
    MarketDataRepositoryProtocol,
)
from athena.market_data.models import Timeframe
from athena.market_data.ohlcv import OHLCVBar
from athena.market_data.quotes import Quote
from athena.market_data.ticks import MarketTick
from athena.market_data.trades import Trade

NOW = datetime(2025, 1, 15, 9, 15, tzinfo=UTC)
NIFTY = Symbol("NSE:NIFTY50-INDEX")


class _MockHistoricalProvider:
    @property
    def vendor_name(self) -> str:
        return "mock"

    @property
    def supported_timeframes(self) -> frozenset[Timeframe]:
        return frozenset({Timeframe.MINUTE_1, Timeframe.DAY_1})

    async def fetch_ohlcv(
        self, symbol: Symbol, timeframe: Timeframe, from_utc: datetime, to_utc: datetime
    ) -> tuple[OHLCVBar, ...]:
        return ()

    async def fetch_ticks(
        self, symbol: Symbol, from_utc: datetime, to_utc: datetime
    ) -> tuple[MarketTick, ...]:
        return ()

    async def fetch_trades(
        self, symbol: Symbol, from_utc: datetime, to_utc: datetime
    ) -> tuple[Trade, ...]:
        return ()

    async def fetch_quotes(
        self, symbol: Symbol, from_utc: datetime, to_utc: datetime
    ) -> tuple[Quote, ...]:
        return ()

    async def fetch_corporate_actions(
        self, symbol: Symbol, from_date: date, to_date: date
    ) -> tuple[CorporateAction, ...]:
        return ()


class _MockLiveProvider:
    @property
    def vendor_name(self) -> str:
        return "mock_live"

    @property
    def is_connected(self) -> bool:
        return True

    async def subscribe_ticks(self, symbols: frozenset[Symbol]) -> None:
        pass

    async def subscribe_quotes(self, symbols: frozenset[Symbol]) -> None:
        pass

    async def unsubscribe(self, symbols: frozenset[Symbol]) -> None:
        pass

    async def get_subscribed_symbols(self) -> frozenset[Symbol]:
        return frozenset()

    async def get_latest_quote(self, symbol: Symbol) -> Quote | None:
        return None

    async def get_latest_trade(self, symbol: Symbol) -> Trade | None:
        return None


class _MockCorporateActionProvider:
    @property
    def vendor_name(self) -> str:
        return "mock_ca"

    async def fetch_corporate_actions(
        self, symbol: Symbol, from_date: date, to_date: date
    ) -> tuple[CorporateAction, ...]:
        return ()

    async def compute_adjustment_factors(
        self, symbol: Symbol, from_date: date, to_date: date
    ) -> tuple[AdjustmentFactor, ...]:
        return ()


class _MockRepository:
    async def store_ohlcv_bars(self, bars: tuple[OHLCVBar, ...]) -> int:
        return len(bars)

    async def fetch_ohlcv_bars(
        self, symbol: Symbol, timeframe: Timeframe, from_utc: datetime, to_utc: datetime
    ) -> tuple[OHLCVBar, ...]:
        return ()

    async def store_ticks(self, ticks: tuple[MarketTick, ...]) -> int:
        return len(ticks)

    async def fetch_ticks(
        self, symbol: Symbol, from_utc: datetime, to_utc: datetime
    ) -> tuple[MarketTick, ...]:
        return ()

    async def store_corporate_actions(self, actions: tuple[CorporateAction, ...]) -> int:
        return len(actions)

    async def fetch_corporate_actions(
        self, symbol: Symbol, from_date: date, to_date: date
    ) -> tuple[CorporateAction, ...]:
        return ()


class _EmptyClass:
    pass


class TestHistoricalDataProviderProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockHistoricalProvider(), HistoricalDataProviderProtocol)

    def test_empty_class_does_not_satisfy(self) -> None:
        assert not isinstance(_EmptyClass(), HistoricalDataProviderProtocol)

    def test_vendor_name(self) -> None:
        assert _MockHistoricalProvider().vendor_name == "mock"

    def test_supported_timeframes(self) -> None:
        tfs = _MockHistoricalProvider().supported_timeframes
        assert Timeframe.MINUTE_1 in tfs


class TestLiveDataProviderProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockLiveProvider(), LiveDataProviderProtocol)

    def test_is_connected(self) -> None:
        assert _MockLiveProvider().is_connected is True


class TestCorporateActionProviderProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockCorporateActionProvider(), CorporateActionProviderProtocol)


class TestMarketDataRepositoryProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockRepository(), MarketDataRepositoryProtocol)

    def test_empty_class_does_not_satisfy(self) -> None:
        assert not isinstance(_EmptyClass(), MarketDataRepositoryProtocol)
