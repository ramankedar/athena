"""Unit tests for market domain Protocol interfaces."""

from __future__ import annotations

from datetime import UTC, date, datetime

from athena.market.capabilities import NSE_EQ_CAPABILITIES, MarketCapabilities
from athena.market.exchange import InMemoryExchangeRepository
from athena.market.interfaces import (
    ExchangeRepositoryProtocol,
    MarketCalendarPort,
    MarketRulesRepositoryProtocol,
    MarketStateServiceProtocol,
    ScheduleRepositoryProtocol,
    SegmentRepositoryProtocol,
)
from athena.market.market_state import MarketState, MarketStateSnapshot
from athena.market.models import MarketId
from athena.market.rules import (
    IndexCircuitBreakerConfig,
    PriceBandConfig,
    TradingRestriction,
)
from athena.market.segments import InMemorySegmentRepository
from athena.market.sessions import NSE_STANDARD_SCHEDULE, ExchangeSchedule

# ── Mock implementations ───────────────────────────────────────────────────────


class _MockCalendar:
    def is_trading_day(self, exchange_id: MarketId, d: date) -> bool:
        return d.weekday() < 5

    def next_trading_day(self, exchange_id: MarketId, d: date) -> date:
        from datetime import timedelta

        candidate = d + timedelta(days=1)
        while candidate.weekday() >= 5:
            candidate += timedelta(days=1)
        return candidate

    def previous_trading_day(self, exchange_id: MarketId, d: date) -> date:
        from datetime import timedelta

        candidate = d - timedelta(days=1)
        while candidate.weekday() >= 5:
            candidate -= timedelta(days=1)
        return candidate

    def trading_days_in_range(
        self, exchange_id: MarketId, start: date, end: date
    ) -> tuple[date, ...]:
        from datetime import timedelta

        result = []
        current = start
        while current <= end:
            if current.weekday() < 5:
                result.append(current)
            current += timedelta(days=1)
        return tuple(result)


class _MockStateService:
    def get_state(
        self, exchange_id: MarketId, segment_id: MarketId | None = None
    ) -> MarketStateSnapshot:
        return MarketStateSnapshot(
            exchange_id=exchange_id,
            state=MarketState.OPEN,
            as_of=datetime(2025, 1, 15, 5, 30, tzinfo=UTC),
        )

    def is_open(self, exchange_id: MarketId, segment_id: MarketId | None = None) -> bool:
        return True

    def is_halted(self, exchange_id: MarketId, segment_id: MarketId | None = None) -> bool:
        return False


class _MockScheduleRepo:
    def get_schedule(
        self, exchange_id: MarketId, segment_id: MarketId | None = None
    ) -> ExchangeSchedule:
        return NSE_STANDARD_SCHEDULE

    def get_capabilities(
        self, exchange_id: MarketId, segment_id: MarketId | None = None
    ) -> MarketCapabilities:
        return NSE_EQ_CAPABILITIES


class _MockRulesRepo:
    def get_price_band_config(
        self, exchange_id: MarketId, instrument_symbol: str | None = None
    ) -> PriceBandConfig | None:
        return None

    def get_circuit_breaker_config(self, exchange_id: MarketId) -> IndexCircuitBreakerConfig | None:
        return None

    def get_restrictions(self, exchange_id: MarketId, d: date) -> tuple[TradingRestriction, ...]:
        return ()


class _EmptyClass:
    pass


# ── Tests ──────────────────────────────────────────────────────────────────────


class TestExchangeRepositoryProtocol:
    def test_in_memory_repo_satisfies(self) -> None:
        assert isinstance(InMemoryExchangeRepository(), ExchangeRepositoryProtocol)

    def test_empty_class_does_not_satisfy(self) -> None:
        assert not isinstance(_EmptyClass(), ExchangeRepositoryProtocol)


class TestSegmentRepositoryProtocol:
    def test_in_memory_satisfies(self) -> None:
        assert isinstance(InMemorySegmentRepository(), SegmentRepositoryProtocol)

    def test_empty_does_not_satisfy(self) -> None:
        assert not isinstance(_EmptyClass(), SegmentRepositoryProtocol)


class TestMarketCalendarPort:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockCalendar(), MarketCalendarPort)

    def test_empty_does_not_satisfy(self) -> None:
        assert not isinstance(_EmptyClass(), MarketCalendarPort)

    def test_is_trading_day(self) -> None:
        cal = _MockCalendar()
        # Wednesday
        assert cal.is_trading_day(MarketId("NSE"), date(2025, 1, 15)) is True
        # Saturday
        assert cal.is_trading_day(MarketId("NSE"), date(2025, 1, 18)) is False

    def test_trading_days_in_range(self) -> None:
        cal = _MockCalendar()
        days = cal.trading_days_in_range(
            MarketId("NSE"),
            date(2025, 1, 13),  # Monday
            date(2025, 1, 17),  # Friday
        )
        assert len(days) == 5


class TestMarketStateServiceProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockStateService(), MarketStateServiceProtocol)

    def test_is_open(self) -> None:
        assert _MockStateService().is_open(MarketId("NSE")) is True

    def test_is_halted(self) -> None:
        assert _MockStateService().is_halted(MarketId("NSE")) is False


class TestScheduleRepositoryProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockScheduleRepo(), ScheduleRepositoryProtocol)


class TestMarketRulesRepositoryProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockRulesRepo(), MarketRulesRepositoryProtocol)

    def test_no_restrictions(self) -> None:
        repo = _MockRulesRepo()
        result = repo.get_restrictions(MarketId("NSE"), date(2025, 1, 15))
        assert result == ()
