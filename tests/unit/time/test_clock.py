"""Unit tests for clock implementations."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from athena.time.clock import FrozenClock, ManualClock, OffsetClock, SystemClock
from athena.time.exceptions import NaiveDatetimeError
from athena.time.timezone import IST, UTC


class TestSystemClock:
    def test_now_is_utc_aware(self) -> None:
        clock = SystemClock()
        now = clock.now()
        assert now.tzinfo is not None

    def test_now_is_approximately_current_time(self) -> None:
        clock = SystemClock()
        before = datetime.now(UTC)
        now = clock.now()
        after = datetime.now(UTC)
        assert before <= now <= after

    def test_today_returns_date(self) -> None:
        clock = SystemClock()
        today = clock.today()
        now_ist = clock.now().astimezone(IST)
        assert today == now_ist.date()

    def test_now_returns_utc_timezone(self) -> None:
        clock = SystemClock()
        now = clock.now()
        assert now.utcoffset() == timedelta(0)


class TestFrozenClock:
    def test_now_returns_fixed_time(self) -> None:
        fixed = datetime(2025, 1, 15, 9, 15, tzinfo=UTC)
        clock = FrozenClock(fixed)
        assert clock.now() == fixed

    def test_now_is_always_same(self) -> None:
        fixed = datetime(2025, 1, 15, 9, 15, tzinfo=UTC)
        clock = FrozenClock(fixed)
        assert clock.now() == clock.now()

    def test_today_returns_ist_date(self) -> None:
        # 03:45 UTC = 09:15 IST — same date in both timezones
        fixed = datetime(2025, 1, 15, 3, 45, tzinfo=UTC)
        clock = FrozenClock(fixed)
        assert clock.today().isoformat() == "2025-01-15"

    def test_today_handles_date_boundary(self) -> None:
        # 20:00 UTC on Jan 15 = 01:30 IST on Jan 16
        fixed = datetime(2025, 1, 15, 20, 0, tzinfo=UTC)
        clock = FrozenClock(fixed)
        assert clock.today().isoformat() == "2025-01-16"

    def test_rejects_naive_datetime(self) -> None:
        with pytest.raises(NaiveDatetimeError):
            FrozenClock(datetime(2025, 1, 15, 9, 15))

    def test_fixed_time_property(self) -> None:
        fixed = datetime(2025, 1, 15, 9, 15, tzinfo=UTC)
        clock = FrozenClock(fixed)
        assert clock.fixed_time is fixed

    def test_accepts_ist_datetime(self) -> None:
        fixed_ist = datetime(2025, 1, 15, 9, 15, tzinfo=IST)
        clock = FrozenClock(fixed_ist)
        assert clock.now() == fixed_ist


class TestManualClock:
    def test_now_returns_start_time(self) -> None:
        start = datetime(2025, 1, 15, 9, 0, tzinfo=UTC)
        clock = ManualClock(start)
        assert clock.now() == start

    def test_advance_moves_clock_forward(self) -> None:
        start = datetime(2025, 1, 15, 9, 0, tzinfo=UTC)
        clock = ManualClock(start)
        clock.advance(timedelta(hours=1))
        assert clock.now() == datetime(2025, 1, 15, 10, 0, tzinfo=UTC)

    def test_advance_negative_moves_backward(self) -> None:
        start = datetime(2025, 1, 15, 9, 0, tzinfo=UTC)
        clock = ManualClock(start)
        clock.advance(timedelta(hours=-1))
        assert clock.now() == datetime(2025, 1, 15, 8, 0, tzinfo=UTC)

    def test_advance_multiple_times(self) -> None:
        start = datetime(2025, 1, 15, 9, 0, tzinfo=UTC)
        clock = ManualClock(start)
        clock.advance(timedelta(minutes=30))
        clock.advance(timedelta(minutes=15))
        assert clock.now() == datetime(2025, 1, 15, 9, 45, tzinfo=UTC)

    def test_set_changes_time(self) -> None:
        start = datetime(2025, 1, 15, 9, 0, tzinfo=UTC)
        new_time = datetime(2025, 1, 15, 15, 30, tzinfo=UTC)
        clock = ManualClock(start)
        clock.set(new_time)
        assert clock.now() == new_time

    def test_set_rejects_naive_datetime(self) -> None:
        clock = ManualClock(datetime(2025, 1, 15, 9, 0, tzinfo=UTC))
        with pytest.raises(NaiveDatetimeError):
            clock.set(datetime(2025, 1, 15, 10, 0))

    def test_rejects_naive_start(self) -> None:
        with pytest.raises(NaiveDatetimeError):
            ManualClock(datetime(2025, 1, 15, 9, 0))

    def test_today_changes_after_advance(self) -> None:
        # Start at 22:00 UTC (03:30 IST next day)
        start = datetime(2025, 1, 14, 22, 0, tzinfo=UTC)
        clock = ManualClock(start)
        assert clock.today().isoformat() == "2025-01-15"
        clock.advance(timedelta(hours=2))
        # Now 00:00 UTC = 05:30 IST, still Jan 15
        assert clock.today().isoformat() == "2025-01-15"


class TestOffsetClock:
    def test_now_is_approximately_current_plus_offset(self) -> None:
        offset = timedelta(hours=2)
        clock = OffsetClock(offset)
        before = datetime.now(UTC) + offset
        now = clock.now()
        after = datetime.now(UTC) + offset
        assert before <= now <= after

    def test_negative_offset(self) -> None:
        offset = timedelta(hours=-3)
        clock = OffsetClock(offset)
        before = datetime.now(UTC) + offset
        now = clock.now()
        after = datetime.now(UTC) + offset
        assert before <= now <= after

    def test_zero_offset_matches_system_clock(self) -> None:
        clock = OffsetClock(timedelta(0))
        system = SystemClock()
        # Allow a small margin for execution time
        assert abs((clock.now() - system.now()).total_seconds()) < 1.0

    def test_offset_property(self) -> None:
        offset = timedelta(hours=5, minutes=30)
        clock = OffsetClock(offset)
        assert clock.offset == offset

    def test_today_uses_ist_timezone(self) -> None:
        clock = OffsetClock(timedelta(0))
        system = SystemClock()
        assert clock.today() == system.today()
