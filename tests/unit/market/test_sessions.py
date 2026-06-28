"""Unit tests for market session schedules."""

from __future__ import annotations

import dataclasses
from datetime import time

import pytest

from athena.market.exceptions import InvalidScheduleError
from athena.market.models import MarketId, MarketTimezone, WeeklySchedule
from athena.market.sessions import (
    NSE_DAILY_SCHEDULE,
    NSE_PRE_OPEN,
    NSE_STANDARD_SCHEDULE,
    DailySchedule,
    ExchangeSchedule,
    MarketSessionType,
    SessionWindow,
)

IST = MarketTimezone("Asia/Kolkata")


class TestMarketSessionType:
    def test_values(self) -> None:
        assert MarketSessionType.PRE_OPEN == "pre_open"
        assert MarketSessionType.OPENING_AUCTION == "opening_auction"
        assert MarketSessionType.CONTINUOUS == "continuous"
        assert MarketSessionType.CLOSING_AUCTION == "closing_auction"
        assert MarketSessionType.AFTER_HOURS == "after_hours"


class TestSessionWindow:
    def test_valid_construction(self) -> None:
        w = SessionWindow(
            session_type=MarketSessionType.CONTINUOUS,
            start_time=time(9, 15),
            end_time=time(15, 30),
        )
        assert w.start_time == time(9, 15)

    def test_start_equals_end_raises(self) -> None:
        with pytest.raises(InvalidScheduleError):
            SessionWindow(MarketSessionType.CONTINUOUS, time(9, 0), time(9, 0))

    def test_start_after_end_raises(self) -> None:
        with pytest.raises(InvalidScheduleError):
            SessionWindow(MarketSessionType.CONTINUOUS, time(15, 30), time(9, 0))

    def test_duration_minutes(self) -> None:
        w = SessionWindow(MarketSessionType.CONTINUOUS, time(9, 15), time(15, 30))
        assert w.duration_minutes == 375  # 6h 15min

    def test_duration_pre_open(self) -> None:
        assert NSE_PRE_OPEN.duration_minutes == 15

    def test_contains_true(self) -> None:
        w = SessionWindow(MarketSessionType.CONTINUOUS, time(9, 15), time(15, 30))
        assert w.contains(time(12, 0)) is True

    def test_contains_at_start(self) -> None:
        w = SessionWindow(MarketSessionType.CONTINUOUS, time(9, 15), time(15, 30))
        assert w.contains(time(9, 15)) is True

    def test_contains_at_end_exclusive(self) -> None:
        w = SessionWindow(MarketSessionType.CONTINUOUS, time(9, 15), time(15, 30))
        assert w.contains(time(15, 30)) is False

    def test_str(self) -> None:
        s = str(NSE_PRE_OPEN)
        assert "pre_open" in s
        assert "09:00" in s

    def test_is_frozen(self) -> None:
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            NSE_PRE_OPEN.start_time = time(8, 0)  # type: ignore[misc]


class TestDailySchedule:
    def test_nse_daily_schedule(self) -> None:
        assert len(NSE_DAILY_SCHEDULE.sessions) == 3
        assert NSE_DAILY_SCHEDULE.market_open == time(9, 0)
        assert NSE_DAILY_SCHEDULE.market_close == time(16, 0)

    def test_total_duration(self) -> None:
        # pre_open: 15 min, continuous: 375 min, closing_auction: 30 min = 420 total
        assert NSE_DAILY_SCHEDULE.total_duration_minutes == 420

    def test_session_at_during_continuous(self) -> None:
        result = NSE_DAILY_SCHEDULE.session_at(time(12, 0))
        assert result is not None
        assert result.session_type == MarketSessionType.CONTINUOUS

    def test_session_at_before_open(self) -> None:
        result = NSE_DAILY_SCHEDULE.session_at(time(8, 0))
        assert result is None

    def test_session_at_after_close(self) -> None:
        result = NSE_DAILY_SCHEDULE.session_at(time(17, 0))
        assert result is None

    def test_has_session_type_true(self) -> None:
        assert NSE_DAILY_SCHEDULE.has_session_type(MarketSessionType.PRE_OPEN) is True
        assert NSE_DAILY_SCHEDULE.has_session_type(MarketSessionType.CONTINUOUS) is True

    def test_has_session_type_false(self) -> None:
        assert NSE_DAILY_SCHEDULE.has_session_type(MarketSessionType.AFTER_HOURS) is False

    def test_empty_sessions_raises(self) -> None:
        with pytest.raises(InvalidScheduleError, match="empty"):
            DailySchedule(sessions=(), timezone=IST)

    def test_overlapping_sessions_raises(self) -> None:
        with pytest.raises(InvalidScheduleError, match="overlap"):
            DailySchedule(
                sessions=(
                    SessionWindow(MarketSessionType.PRE_OPEN, time(9, 0), time(9, 30)),
                    SessionWindow(MarketSessionType.CONTINUOUS, time(9, 20), time(15, 30)),
                ),
                timezone=IST,
            )


class TestExchangeSchedule:
    def test_nse_standard_schedule(self) -> None:
        assert NSE_STANDARD_SCHEDULE.exchange_id == MarketId("NSE")
        assert NSE_STANDARD_SCHEDULE.segment_id is None
        assert NSE_STANDARD_SCHEDULE.weekly == WeeklySchedule.MON_FRI

    def test_trades_on_monday(self) -> None:
        assert NSE_STANDARD_SCHEDULE.trades_on_weekday(0) is True

    def test_does_not_trade_on_saturday(self) -> None:
        assert NSE_STANDARD_SCHEDULE.trades_on_weekday(5) is False

    def test_with_segment_id(self) -> None:
        schedule = ExchangeSchedule(
            exchange_id=MarketId("NSE"),
            daily=NSE_DAILY_SCHEDULE,
            weekly=WeeklySchedule.MON_FRI,
            segment_id=MarketId("NSE_FO"),
        )
        assert schedule.segment_id == MarketId("NSE_FO")

    def test_str_without_segment(self) -> None:
        s = str(NSE_STANDARD_SCHEDULE)
        assert "NSE" in s

    def test_str_with_segment(self) -> None:
        schedule = ExchangeSchedule(
            exchange_id=MarketId("NSE"),
            daily=NSE_DAILY_SCHEDULE,
            weekly=WeeklySchedule.MON_FRI,
            segment_id=MarketId("NSE_FO"),
        )
        s = str(schedule)
        assert "NSE_FO" in s
