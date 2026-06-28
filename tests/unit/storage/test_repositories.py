"""Unit tests for domain-specific repository Protocol definitions."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from athena.core.domain.instrument import Exchange, Instrument, Segment
from athena.core.domain.ohlcv import OHLCV, BarInterval
from athena.core.domain.primitives import Currency, Price, Quantity, Symbol
from athena.core.domain.tick import Tick
from athena.storage.models import Page, QuerySpec, StorageKey
from athena.storage.repositories import (
    InstrumentRepositoryProtocol,
    OHLCVRepositoryProtocol,
    TickRepositoryProtocol,
)

NOW = datetime(2025, 1, 15, 9, 15, tzinfo=UTC)
LATER = datetime(2025, 1, 15, 15, 30, tzinfo=UTC)

_NIFTY_SYMBOL = Symbol("NSE:NIFTY50-INDEX")
_NIFTY = Instrument(
    symbol=_NIFTY_SYMBOL,
    exchange=Exchange.NSE,
    segment=Segment.INDEX,
    name="Nifty 50",
    lot_size=Quantity(Decimal("50")),
    tick_size=Price(Decimal("0.05")),
    currency=Currency("INR"),
)

_TICK = Tick(
    symbol=_NIFTY_SYMBOL,
    timestamp_utc=NOW,
    last_price=Price(Decimal("24500.50")),
    volume=Quantity(Decimal("1000")),
)


def _empty_page() -> Page[object]:
    return Page(items=(), total=0, offset=0, limit=100, has_next=False, has_previous=False)


# ── Minimal mock implementations ──────────────────────────────────────────────


class _MockInstrumentRepo:
    async def get_instrument(self, symbol: Symbol) -> Instrument:
        if symbol == _NIFTY_SYMBOL:
            return _NIFTY
        from athena.storage.exceptions import RecordNotFoundError

        raise RecordNotFoundError(symbol)

    async def get_instrument_or_none(self, symbol: Symbol) -> Instrument | None:
        if symbol == _NIFTY_SYMBOL:
            return _NIFTY
        return None

    async def find_instruments(
        self,
        exchange: Exchange | None = None,
        segment: Segment | None = None,
        spec: QuerySpec | None = None,
    ) -> Page[Instrument]:
        return Page(
            items=(_NIFTY,), total=1, offset=0, limit=100, has_next=False, has_previous=False
        )

    async def upsert_instrument(self, instrument: Instrument) -> StorageKey:
        return instrument.symbol

    async def upsert_many(self, instruments: list[Instrument]) -> int:
        return len(instruments)

    async def count_instruments(
        self,
        exchange: Exchange | None = None,
        segment: Segment | None = None,
    ) -> int:
        return 1


class _MockTickRepo:
    async def get_tick(self, symbol: Symbol, timestamp_utc: datetime) -> Tick:
        return _TICK

    async def get_latest_tick(self, symbol: Symbol) -> Tick | None:
        return _TICK

    async def find_ticks(
        self,
        symbol: Symbol,
        from_utc: datetime,
        to_utc: datetime,
        spec: QuerySpec | None = None,
    ) -> Page[Tick]:
        return Page(
            items=(_TICK,), total=1, offset=0, limit=100, has_next=False, has_previous=False
        )

    async def add_tick(self, tick: Tick) -> StorageKey:
        return f"{tick.symbol}::{tick.timestamp_utc.isoformat()}"

    async def add_ticks(self, ticks: list[Tick]) -> int:
        return len(ticks)

    async def delete_ticks_before(self, symbol: Symbol, cutoff_utc: datetime) -> int:
        return 0

    async def count_ticks(
        self,
        symbol: Symbol,
        from_utc: datetime | None = None,
        to_utc: datetime | None = None,
    ) -> int:
        return 1


class _MockOHLCVRepo:
    def _bar(self) -> OHLCV:
        return OHLCV(
            symbol=_NIFTY_SYMBOL,
            interval=BarInterval.ONE_MINUTE,
            open_time=NOW,
            close_time=LATER,
            open=Price(Decimal("24490")),
            high=Price(Decimal("24510")),
            low=Price(Decimal("24480")),
            close=Price(Decimal("24500")),
            volume=Quantity(Decimal("5000")),
        )

    async def get_bar(
        self,
        symbol: Symbol,
        interval: BarInterval,
        open_time_utc: datetime,
    ) -> OHLCV:
        return self._bar()

    async def find_bars(
        self,
        symbol: Symbol,
        interval: BarInterval,
        from_utc: datetime,
        to_utc: datetime,
        spec: QuerySpec | None = None,
    ) -> Page[OHLCV]:
        return Page(
            items=(self._bar(),), total=1, offset=0, limit=100, has_next=False, has_previous=False
        )

    async def get_latest_bar(self, symbol: Symbol, interval: BarInterval) -> OHLCV | None:
        return self._bar()

    async def add_bar(self, bar: OHLCV) -> StorageKey:
        return f"{bar.symbol}::{bar.interval}::{bar.open_time.isoformat()}"

    async def add_bars(self, bars: list[OHLCV]) -> int:
        return len(bars)

    async def count_bars(
        self,
        symbol: Symbol,
        interval: BarInterval,
        from_utc: datetime | None = None,
        to_utc: datetime | None = None,
    ) -> int:
        return 1

    async def delete_bars_before(
        self,
        symbol: Symbol,
        interval: BarInterval,
        cutoff_utc: datetime,
    ) -> int:
        return 0


class _EmptyClass:
    pass


# ── Tests ──────────────────────────────────────────────────────────────────────


class TestInstrumentRepositoryProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockInstrumentRepo(), InstrumentRepositoryProtocol)

    def test_empty_class_does_not_satisfy(self) -> None:
        assert not isinstance(_EmptyClass(), InstrumentRepositoryProtocol)

    async def test_get_instrument(self) -> None:
        repo = _MockInstrumentRepo()
        result = await repo.get_instrument(_NIFTY_SYMBOL)
        assert result == _NIFTY

    async def test_get_instrument_or_none_found(self) -> None:
        result = await _MockInstrumentRepo().get_instrument_or_none(_NIFTY_SYMBOL)
        assert result == _NIFTY

    async def test_get_instrument_or_none_missing(self) -> None:
        result = await _MockInstrumentRepo().get_instrument_or_none(Symbol("UNKNOWN"))
        assert result is None

    async def test_upsert_returns_key(self) -> None:
        key = await _MockInstrumentRepo().upsert_instrument(_NIFTY)
        assert key == _NIFTY_SYMBOL

    async def test_upsert_many_returns_count(self) -> None:
        count = await _MockInstrumentRepo().upsert_many([_NIFTY, _NIFTY])
        assert count == 2

    async def test_count_instruments(self) -> None:
        assert await _MockInstrumentRepo().count_instruments() == 1


class TestTickRepositoryProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockTickRepo(), TickRepositoryProtocol)

    def test_empty_class_does_not_satisfy(self) -> None:
        assert not isinstance(_EmptyClass(), TickRepositoryProtocol)

    async def test_get_tick(self) -> None:
        result = await _MockTickRepo().get_tick(_NIFTY_SYMBOL, NOW)
        assert result == _TICK

    async def test_get_latest_tick(self) -> None:
        result = await _MockTickRepo().get_latest_tick(_NIFTY_SYMBOL)
        assert result is not None

    async def test_find_ticks_returns_page(self) -> None:
        page = await _MockTickRepo().find_ticks(_NIFTY_SYMBOL, NOW, LATER)
        assert isinstance(page, Page)
        assert len(page.items) == 1

    async def test_add_tick_returns_key(self) -> None:
        key = await _MockTickRepo().add_tick(_TICK)
        assert "NSE:NIFTY50-INDEX" in key

    async def test_add_ticks_returns_count(self) -> None:
        count = await _MockTickRepo().add_ticks([_TICK, _TICK])
        assert count == 2

    async def test_delete_ticks_before(self) -> None:
        deleted = await _MockTickRepo().delete_ticks_before(_NIFTY_SYMBOL, NOW)
        assert deleted == 0

    async def test_count_ticks(self) -> None:
        assert await _MockTickRepo().count_ticks(_NIFTY_SYMBOL) == 1


class TestOHLCVRepositoryProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockOHLCVRepo(), OHLCVRepositoryProtocol)

    def test_empty_class_does_not_satisfy(self) -> None:
        assert not isinstance(_EmptyClass(), OHLCVRepositoryProtocol)

    async def test_get_bar_returns_ohlcv(self) -> None:
        result = await _MockOHLCVRepo().get_bar(_NIFTY_SYMBOL, BarInterval.ONE_MINUTE, NOW)
        assert isinstance(result, OHLCV)

    async def test_get_latest_bar(self) -> None:
        result = await _MockOHLCVRepo().get_latest_bar(_NIFTY_SYMBOL, BarInterval.ONE_MINUTE)
        assert result is not None

    async def test_find_bars_returns_page(self) -> None:
        page = await _MockOHLCVRepo().find_bars(_NIFTY_SYMBOL, BarInterval.ONE_MINUTE, NOW, LATER)
        assert isinstance(page, Page)
        assert len(page.items) == 1

    async def test_add_bar_returns_key(self) -> None:
        repo = _MockOHLCVRepo()
        bar = (await repo.find_bars(_NIFTY_SYMBOL, BarInterval.ONE_MINUTE, NOW, LATER)).items[0]
        key = await repo.add_bar(bar)
        assert "NSE:NIFTY50-INDEX" in key

    async def test_add_bars_returns_count(self) -> None:
        repo = _MockOHLCVRepo()
        bars = list((await repo.find_bars(_NIFTY_SYMBOL, BarInterval.ONE_MINUTE, NOW, LATER)).items)
        count = await repo.add_bars(bars)
        assert count == 1

    async def test_count_bars(self) -> None:
        count = await _MockOHLCVRepo().count_bars(_NIFTY_SYMBOL, BarInterval.ONE_MINUTE)
        assert count == 1

    async def test_delete_bars_before(self) -> None:
        deleted = await _MockOHLCVRepo().delete_bars_before(
            _NIFTY_SYMBOL, BarInterval.ONE_MINUTE, NOW
        )
        assert deleted == 0
