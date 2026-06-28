"""Unit tests for NSETradingCalendar."""

from __future__ import annotations

from datetime import date, timedelta

from hypothesis import given
from hypothesis import strategies as st
import pytest

from athena.time.calendar import NSETradingCalendar
from athena.time.holiday import NullHolidayProvider, SetHolidayProvider

MONDAY = date(2025, 1, 13)
TUESDAY = date(2025, 1, 14)
WEDNESDAY = date(2025, 1, 15)
THURSDAY = date(2025, 1, 16)
FRIDAY = date(2025, 1, 17)
SATURDAY = date(2025, 1, 18)
SUNDAY = date(2025, 1, 19)
REPUBLIC_DAY = date(2025, 1, 26)  # A Sunday — doubly non-trading


def _null_cal() -> NSETradingCalendar:
    return NSETradingCalendar(NullHolidayProvider())


def _holiday_cal(holidays: set[date]) -> NSETradingCalendar:
    return NSETradingCalendar(SetHolidayProvider(frozenset(holidays)))


class TestIsTradingDay:
    def test_monday_is_trading_day(self) -> None:
        assert _null_cal().is_trading_day(MONDAY) is True

    def test_friday_is_trading_day(self) -> None:
        assert _null_cal().is_trading_day(FRIDAY) is True

    def test_saturday_is_not_trading_day(self) -> None:
        assert _null_cal().is_trading_day(SATURDAY) is False

    def test_sunday_is_not_trading_day(self) -> None:
        assert _null_cal().is_trading_day(SUNDAY) is False

    def test_holiday_weekday_is_not_trading_day(self) -> None:
        # Jan 26, 2025 is a Sunday, but Jan 27, 2025 (Monday) is a normal day
        # Use a Wednesday holiday instead
        wednesday_holiday = date(2025, 1, 29)  # Wednesday
        cal = _holiday_cal({wednesday_holiday})
        assert cal.is_trading_day(wednesday_holiday) is False

    def test_non_holiday_weekday_is_trading_day(self) -> None:
        cal = _holiday_cal({date(2025, 1, 29)})
        # Jan 28 (Tuesday) is not a holiday
        assert cal.is_trading_day(date(2025, 1, 28)) is True


class TestNextTradingDay:
    def test_next_day_when_tomorrow_is_weekday(self) -> None:
        assert _null_cal().next_trading_day(MONDAY) == TUESDAY

    def test_skips_weekend(self) -> None:
        # Friday → next Monday (skips Sat + Sun)
        assert _null_cal().next_trading_day(FRIDAY) == date(2025, 1, 20)

    def test_skips_saturday(self) -> None:
        assert _null_cal().next_trading_day(SATURDAY) == SUNDAY + timedelta(days=1)

    def test_skips_holiday(self) -> None:
        # Make Monday Jan 20 a holiday
        monday_holiday = date(2025, 1, 20)
        cal = _holiday_cal({monday_holiday})
        # Friday's next trading day should be Tuesday Jan 21
        assert cal.next_trading_day(FRIDAY) == date(2025, 1, 21)

    def test_skips_multiple_consecutive_holidays(self) -> None:
        # Declare Mon-Wed (Jan 20-22) as holidays
        cal = _holiday_cal({date(2025, 1, 20), date(2025, 1, 21), date(2025, 1, 22)})
        # Friday Jan 17 → next trading day is Thursday Jan 23
        assert cal.next_trading_day(FRIDAY) == date(2025, 1, 23)


class TestPreviousTradingDay:
    def test_previous_day_when_yesterday_is_weekday(self) -> None:
        assert _null_cal().previous_trading_day(TUESDAY) == MONDAY

    def test_skips_weekend_going_backward(self) -> None:
        # Monday Jan 13 → previous is Friday Jan 10 (skips Sat Jan 11, Sun Jan 12)
        assert _null_cal().previous_trading_day(MONDAY) == date(2025, 1, 10)

    def test_skips_holiday(self) -> None:
        # Make Friday Jan 17 a holiday.
        # From Monday Jan 20, stepping backward:
        #   Jan 19 = Sunday, Jan 18 = Saturday, Jan 17 = Friday (holiday) → skip
        #   Jan 16 = Thursday → trading day ✓
        cal = _holiday_cal({FRIDAY})
        assert cal.previous_trading_day(date(2025, 1, 20)) == THURSDAY

    def test_skips_multiple_consecutive_holidays(self) -> None:
        # Declare Wed-Fri (Jan 15-17) as holidays
        cal = _holiday_cal({WEDNESDAY, THURSDAY, FRIDAY})
        # Monday Jan 20 → previous is Tuesday Jan 14
        assert cal.previous_trading_day(date(2025, 1, 20)) == TUESDAY


class TestTradingDaysBetween:
    def test_single_trading_day(self) -> None:
        result = _null_cal().trading_days_between(WEDNESDAY, WEDNESDAY)
        assert result == [WEDNESDAY]

    def test_full_week_mon_to_fri(self) -> None:
        result = _null_cal().trading_days_between(MONDAY, FRIDAY)
        assert result == [MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY]

    def test_excludes_weekends(self) -> None:
        # Fri to following Mon: only Fri and Mon
        result = _null_cal().trading_days_between(FRIDAY, date(2025, 1, 20))
        assert result == [FRIDAY, date(2025, 1, 20)]

    def test_excludes_holidays(self) -> None:
        cal = _holiday_cal({THURSDAY})
        result = cal.trading_days_between(MONDAY, FRIDAY)
        assert result == [MONDAY, TUESDAY, WEDNESDAY, FRIDAY]

    def test_empty_range_no_trading_days(self) -> None:
        result = _null_cal().trading_days_between(SATURDAY, SUNDAY)
        assert result == []

    def test_start_equals_end_on_weekend(self) -> None:
        result = _null_cal().trading_days_between(SATURDAY, SATURDAY)
        assert result == []

    def test_exclusive_end(self) -> None:
        result = _null_cal().trading_days_between(MONDAY, FRIDAY, inclusive=False)
        assert FRIDAY not in result
        assert MONDAY in result

    def test_start_after_end_raises(self) -> None:
        with pytest.raises(ValueError, match="start must be"):
            _null_cal().trading_days_between(FRIDAY, MONDAY)

    def test_result_is_sorted(self) -> None:
        result = _null_cal().trading_days_between(MONDAY, FRIDAY)
        assert result == sorted(result)


class TestPropertyBased:
    @given(st.dates(min_value=date(2024, 1, 1), max_value=date(2025, 12, 31)))
    def test_next_previous_are_inverses_on_trading_day(self, d: date) -> None:
        cal = _null_cal()
        if cal.is_trading_day(d):
            assert cal.previous_trading_day(cal.next_trading_day(d)) == d

    @given(st.dates(min_value=date(2024, 1, 1), max_value=date(2025, 12, 31)))
    def test_next_trading_day_is_always_strictly_after(self, d: date) -> None:
        cal = _null_cal()
        assert cal.next_trading_day(d) > d

    @given(st.dates(min_value=date(2024, 1, 1), max_value=date(2025, 12, 31)))
    def test_previous_trading_day_is_always_strictly_before(self, d: date) -> None:
        cal = _null_cal()
        assert cal.previous_trading_day(d) < d
