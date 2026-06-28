"""Unit tests for time-domain value objects."""

from __future__ import annotations

import dataclasses
from datetime import date, datetime, timedelta

import pytest

from athena.time.exceptions import NaiveDatetimeError
from athena.time.models import ExpiryInfo, ExpiryType, TimeRange, WeeklyExpiryDay
from athena.time.timezone import UTC


class TestExpiryType:
    def test_weekly_value(self) -> None:
        assert ExpiryType.WEEKLY == "weekly"

    def test_monthly_value(self) -> None:
        assert ExpiryType.MONTHLY == "monthly"

    def test_quarterly_value(self) -> None:
        assert ExpiryType.QUARTERLY == "quarterly"

    def test_yearly_value(self) -> None:
        assert ExpiryType.YEARLY == "yearly"

    def test_is_str(self) -> None:
        assert isinstance(ExpiryType.WEEKLY, str)

    def test_all_members_present(self) -> None:
        members = {e.value for e in ExpiryType}
        assert members == {"weekly", "monthly", "quarterly", "yearly"}


class TestWeeklyExpiryDay:
    def test_thursday_is_3(self) -> None:
        assert int(WeeklyExpiryDay.THURSDAY) == 3

    def test_tuesday_is_1(self) -> None:
        assert int(WeeklyExpiryDay.TUESDAY) == 1

    def test_matches_date_weekday_convention(self) -> None:
        # 2025-01-16 is a Thursday
        thursday = date(2025, 1, 16)
        assert thursday.weekday() == int(WeeklyExpiryDay.THURSDAY)

    def test_all_members_present(self) -> None:
        assert set(WeeklyExpiryDay) == {
            WeeklyExpiryDay.MONDAY,
            WeeklyExpiryDay.TUESDAY,
            WeeklyExpiryDay.WEDNESDAY,
            WeeklyExpiryDay.THURSDAY,
            WeeklyExpiryDay.FRIDAY,
        }


class TestTimeRange:
    def _range(
        self,
        hours_start: int = 9,
        hours_end: int = 15,
    ) -> TimeRange:
        return TimeRange(
            start=datetime(2025, 1, 15, hours_start, 0, tzinfo=UTC),
            end=datetime(2025, 1, 15, hours_end, 0, tzinfo=UTC),
        )

    def test_valid_construction(self) -> None:
        r = self._range()
        assert r.start.hour == 9
        assert r.end.hour == 15

    def test_equal_start_end_is_valid(self) -> None:
        dt = datetime(2025, 1, 15, 9, 0, tzinfo=UTC)
        r = TimeRange(start=dt, end=dt)
        assert r.start == r.end

    def test_start_after_end_raises(self) -> None:
        with pytest.raises(ValueError, match="must be"):
            TimeRange(
                start=datetime(2025, 1, 15, 15, 0, tzinfo=UTC),
                end=datetime(2025, 1, 15, 9, 0, tzinfo=UTC),
            )

    def test_naive_start_raises(self) -> None:
        with pytest.raises(NaiveDatetimeError):
            TimeRange(
                start=datetime(2025, 1, 15, 9, 0),
                end=datetime(2025, 1, 15, 15, 0, tzinfo=UTC),
            )

    def test_naive_end_raises(self) -> None:
        with pytest.raises(NaiveDatetimeError):
            TimeRange(
                start=datetime(2025, 1, 15, 9, 0, tzinfo=UTC),
                end=datetime(2025, 1, 15, 15, 0),
            )

    def test_is_frozen(self) -> None:
        r = self._range()
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            r.start = datetime(2025, 1, 15, 10, 0, tzinfo=UTC)  # type: ignore[misc]

    def test_contains_midpoint(self) -> None:
        r = self._range(9, 15)
        midpoint = datetime(2025, 1, 15, 12, 0, tzinfo=UTC)
        assert r.contains(midpoint) is True

    def test_contains_start_boundary(self) -> None:
        r = self._range(9, 15)
        assert r.contains(r.start) is True

    def test_contains_end_boundary(self) -> None:
        r = self._range(9, 15)
        assert r.contains(r.end) is True

    def test_does_not_contain_before_start(self) -> None:
        r = self._range(9, 15)
        before = datetime(2025, 1, 15, 8, 59, tzinfo=UTC)
        assert r.contains(before) is False

    def test_does_not_contain_after_end(self) -> None:
        r = self._range(9, 15)
        after = datetime(2025, 1, 15, 15, 1, tzinfo=UTC)
        assert r.contains(after) is False

    def test_duration(self) -> None:
        r = self._range(9, 15)
        assert r.duration == timedelta(hours=6)

    def test_zero_duration(self) -> None:
        dt = datetime(2025, 1, 15, 9, 0, tzinfo=UTC)
        r = TimeRange(start=dt, end=dt)
        assert r.duration == timedelta(0)

    def test_overlaps_with_overlapping_range(self) -> None:
        r1 = self._range(9, 12)
        r2 = TimeRange(
            start=datetime(2025, 1, 15, 11, 0, tzinfo=UTC),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=UTC),
        )
        assert r1.overlaps(r2) is True
        assert r2.overlaps(r1) is True

    def test_overlaps_touching_ranges(self) -> None:
        r1 = self._range(9, 12)
        r2 = TimeRange(
            start=datetime(2025, 1, 15, 12, 0, tzinfo=UTC),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=UTC),
        )
        assert r1.overlaps(r2) is True

    def test_non_overlapping_ranges(self) -> None:
        r1 = self._range(9, 12)
        r2 = TimeRange(
            start=datetime(2025, 1, 15, 13, 0, tzinfo=UTC),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=UTC),
        )
        assert r1.overlaps(r2) is False


class TestExpiryInfo:
    def test_construction(self) -> None:
        info = ExpiryInfo(
            date=date(2025, 1, 30),
            expiry_type=ExpiryType.MONTHLY,
            exchange="NSE",
        )
        assert info.date == date(2025, 1, 30)
        assert info.expiry_type == ExpiryType.MONTHLY
        assert info.exchange == "NSE"
        assert info.instrument_name is None

    def test_with_instrument_name(self) -> None:
        info = ExpiryInfo(
            date=date(2025, 1, 30),
            expiry_type=ExpiryType.MONTHLY,
            exchange="NSE",
            instrument_name="NIFTY",
        )
        assert info.instrument_name == "NIFTY"

    def test_is_frozen(self) -> None:
        info = ExpiryInfo(
            date=date(2025, 1, 30),
            expiry_type=ExpiryType.MONTHLY,
            exchange="NSE",
        )
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            info.exchange = "BSE"  # type: ignore[misc]

    def test_is_hashable(self) -> None:
        info = ExpiryInfo(
            date=date(2025, 1, 30),
            expiry_type=ExpiryType.MONTHLY,
            exchange="NSE",
        )
        assert hash(info) is not None

    def test_str_contains_key_fields(self) -> None:
        info = ExpiryInfo(
            date=date(2025, 1, 30),
            expiry_type=ExpiryType.MONTHLY,
            exchange="NSE",
            instrument_name="NIFTY",
        )
        s = str(info)
        assert "NSE" in s
        assert "monthly" in s
        assert "2025-01-30" in s
        assert "NIFTY" in s

    def test_str_without_instrument(self) -> None:
        info = ExpiryInfo(
            date=date(2025, 1, 30),
            expiry_type=ExpiryType.WEEKLY,
            exchange="NSE",
        )
        s = str(info)
        assert "NSE" in s
        assert "weekly" in s
