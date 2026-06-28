"""Unit tests for business-day arithmetic utilities."""

from __future__ import annotations

from datetime import date

from hypothesis import assume, given, settings
from hypothesis import strategies as st
import pytest

from athena.time.business_day import (
    add_trading_days,
    count_trading_days,
    is_last_trading_day_of_month,
    is_last_trading_day_of_week,
    subtract_trading_days,
    trading_days_in_month,
)
from athena.time.calendar import NSETradingCalendar
from athena.time.holiday import NullHolidayProvider

MONDAY = date(2025, 1, 13)  # Monday 13-Jan
TUESDAY = date(2025, 1, 14)
WEDNESDAY = date(2025, 1, 15)
THURSDAY = date(2025, 1, 16)
FRIDAY = date(2025, 1, 17)
SATURDAY = date(2025, 1, 18)


def _cal() -> NSETradingCalendar:
    return NSETradingCalendar(NullHolidayProvider())


class TestAddTradingDays:
    def test_add_zero_returns_same_date(self) -> None:
        assert add_trading_days(WEDNESDAY, 0, _cal()) == WEDNESDAY

    def test_add_one_returns_next_trading_day(self) -> None:
        assert add_trading_days(MONDAY, 1, _cal()) == TUESDAY

    def test_add_five_from_monday_is_next_monday(self) -> None:
        # Mon → Tue → Wed → Thu → Fri → Mon
        assert add_trading_days(MONDAY, 5, _cal()) == date(2025, 1, 20)

    def test_add_from_friday_skips_weekend(self) -> None:
        assert add_trading_days(FRIDAY, 1, _cal()) == date(2025, 1, 20)

    def test_add_two_from_friday(self) -> None:
        # Fri + 2: Mon, Tue
        assert add_trading_days(FRIDAY, 2, _cal()) == date(2025, 1, 21)

    def test_add_negative_delegates_to_subtract(self) -> None:
        assert add_trading_days(FRIDAY, -1, _cal()) == THURSDAY

    def test_add_zero_from_weekend(self) -> None:
        # Adding zero days to a weekend returns the weekend date unchanged
        assert add_trading_days(SATURDAY, 0, _cal()) == SATURDAY


class TestSubtractTradingDays:
    def test_subtract_zero_returns_same_date(self) -> None:
        assert subtract_trading_days(WEDNESDAY, 0, _cal()) == WEDNESDAY

    def test_subtract_one_returns_previous_trading_day(self) -> None:
        assert subtract_trading_days(FRIDAY, 1, _cal()) == THURSDAY

    def test_subtract_from_monday_skips_weekend(self) -> None:
        # Monday Jan 13 - 1 trading day = Friday Jan 10 (skips Sat Jan 11, Sun Jan 12)
        assert subtract_trading_days(MONDAY, 1, _cal()) == date(2025, 1, 10)

    def test_subtract_five_from_monday(self) -> None:
        # Mon - 5: Fri → Thu → Wed → Tue → Mon (of previous week)
        assert subtract_trading_days(MONDAY, 5, _cal()) == date(2025, 1, 6)

    def test_subtract_negative_delegates_to_add(self) -> None:
        assert subtract_trading_days(MONDAY, -1, _cal()) == TUESDAY

    def test_add_and_subtract_are_inverses(self) -> None:
        for n in range(1, 10):
            assert subtract_trading_days(add_trading_days(MONDAY, n, _cal()), n, _cal()) == MONDAY


class TestCountTradingDays:
    def test_same_day_with_inclusive_end(self) -> None:
        # start=MONDAY, end=MONDAY, inclusive_start=False, inclusive_end=True
        assert count_trading_days(MONDAY, MONDAY, _cal()) == 0

    def test_one_day_elapsed(self) -> None:
        # Mon to Tue (exclusive Mon, inclusive Tue) = 1
        assert count_trading_days(MONDAY, TUESDAY, _cal()) == 1

    def test_full_week(self) -> None:
        # Mon to Fri (exclusive Mon, inclusive Fri) = 4
        assert count_trading_days(MONDAY, FRIDAY, _cal()) == 4

    def test_inclusive_start(self) -> None:
        # Mon to Fri (inclusive both) = 5
        assert count_trading_days(MONDAY, FRIDAY, _cal(), inclusive_start=True) == 5

    def test_exclusive_end(self) -> None:
        # Mon to Fri (exclusive Mon, exclusive Fri) = 3
        assert count_trading_days(MONDAY, FRIDAY, _cal(), inclusive_end=False) == 3

    def test_spans_weekend(self) -> None:
        # Fri to following Mon (exclusive Fri, inclusive Mon) = 1
        monday_after = date(2025, 1, 20)
        assert count_trading_days(FRIDAY, monday_after, _cal()) == 1

    def test_start_after_end_raises(self) -> None:
        with pytest.raises(ValueError, match="start must be"):
            count_trading_days(FRIDAY, MONDAY, _cal())

    def test_range_of_only_weekend(self) -> None:
        assert count_trading_days(FRIDAY, SATURDAY, _cal(), inclusive_end=False) == 0


class TestTradingDaysInMonth:
    def test_january_2025_has_correct_count(self) -> None:
        # Jan 2025: 1 is Wed, 31 is Fri
        # Weekends: 4+5 (Sat/Sun), 11+12, 18+19, 25+26
        # All weekdays = 31 - 8 weekend days = 23
        days = trading_days_in_month(2025, 1, _cal())
        assert len(days) == 23
        assert all(d.month == 1 for d in days)

    def test_all_days_are_weekdays(self) -> None:
        days = trading_days_in_month(2025, 1, _cal())
        assert all(d.weekday() < 5 for d in days)

    def test_february_2025(self) -> None:
        days = trading_days_in_month(2025, 2, _cal())
        assert all(d.month == 2 for d in days)
        assert all(d.weekday() < 5 for d in days)

    def test_december_year_boundary(self) -> None:
        days = trading_days_in_month(2025, 12, _cal())
        assert all(d.month == 12 and d.year == 2025 for d in days)

    def test_invalid_month_raises(self) -> None:
        with pytest.raises(ValueError, match="month"):
            trading_days_in_month(2025, 0, _cal())

    def test_invalid_month_13_raises(self) -> None:
        with pytest.raises(ValueError, match="month"):
            trading_days_in_month(2025, 13, _cal())


class TestIsLastTradingDayOfWeek:
    def test_friday_is_last_of_week(self) -> None:
        assert is_last_trading_day_of_week(FRIDAY, _cal()) is True

    def test_monday_is_not_last_of_week(self) -> None:
        assert is_last_trading_day_of_week(MONDAY, _cal()) is False

    def test_saturday_returns_false(self) -> None:
        # Non-trading day
        assert is_last_trading_day_of_week(SATURDAY, _cal()) is False


class TestIsLastTradingDayOfMonth:
    def test_last_weekday_of_jan_2025(self) -> None:
        # Jan 31, 2025 is a Friday
        assert is_last_trading_day_of_month(date(2025, 1, 31), _cal()) is True

    def test_not_last_day_of_month(self) -> None:
        assert is_last_trading_day_of_month(MONDAY, _cal()) is False

    def test_saturday_returns_false(self) -> None:
        assert is_last_trading_day_of_month(SATURDAY, _cal()) is False


class TestPropertyBased:
    @given(
        st.integers(min_value=1, max_value=20),
        st.dates(min_value=date(2024, 1, 1), max_value=date(2025, 12, 31)),
    )
    @settings(max_examples=50)
    def test_add_subtract_are_inverses(self, n: int, d: date) -> None:
        cal = NSETradingCalendar(NullHolidayProvider())
        # add/subtract are only exact inverses when d is itself a trading day.
        # For a non-trading day (e.g. Saturday), add(d, n) jumps to the nth
        # trading day after d, and subtract brings back to a trading day —
        # not necessarily back to d.
        assume(cal.is_trading_day(d))
        assert subtract_trading_days(add_trading_days(d, n, cal), n, cal) == d
