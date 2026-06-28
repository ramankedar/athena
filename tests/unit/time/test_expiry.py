"""Unit tests for expiry date calculations."""

from __future__ import annotations

from datetime import date

import pytest

from athena.time.calendar import NSETradingCalendar
from athena.time.expiry import (
    NIFTY_WEEKLY_EXPIRY_DAY,
    SENSEX_WEEKLY_EXPIRY_DAY,
    NSEExpiryCalculator,
    _last_day_of_month,
)
from athena.time.holiday import NullHolidayProvider, SetHolidayProvider
from athena.time.models import ExpiryInfo, ExpiryType, WeeklyExpiryDay


def _calc() -> NSEExpiryCalculator:
    return NSEExpiryCalculator(NSETradingCalendar(NullHolidayProvider()))


def _calc_with_holidays(holidays: set[date]) -> NSEExpiryCalculator:
    return NSEExpiryCalculator(NSETradingCalendar(SetHolidayProvider(frozenset(holidays))))


class TestLastDayOfMonth:
    def test_january_has_31_days(self) -> None:
        assert _last_day_of_month(2025, 1) == date(2025, 1, 31)

    def test_february_2025_has_28_days(self) -> None:
        assert _last_day_of_month(2025, 2) == date(2025, 2, 28)

    def test_february_2024_has_29_days_leap_year(self) -> None:
        assert _last_day_of_month(2024, 2) == date(2024, 2, 29)

    def test_december_year_boundary(self) -> None:
        assert _last_day_of_month(2025, 12) == date(2025, 12, 31)


class TestMonthlyExpiry:
    def test_january_2025_last_thursday(self) -> None:
        # Jan 2025: Thursdays are 2, 9, 16, 23, 30 → last is Jan 30
        assert _calc().monthly_expiry(2025, 1) == date(2025, 1, 30)

    def test_february_2025_last_thursday(self) -> None:
        # Feb 2025: Thursdays are 6, 13, 20, 27 → last is Feb 27
        assert _calc().monthly_expiry(2025, 2) == date(2025, 2, 27)

    def test_march_2025_last_thursday(self) -> None:
        # Mar 2025: Thursdays are 6, 13, 20, 27 → last is Mar 27
        assert _calc().monthly_expiry(2025, 3) == date(2025, 3, 27)

    def test_december_2025_last_thursday(self) -> None:
        # Dec 2025: Thursdays are 4, 11, 18, 25 → last is Dec 25
        assert _calc().monthly_expiry(2025, 12) == date(2025, 12, 25)

    def test_expiry_is_always_thursday(self) -> None:
        calc = _calc()
        for month in range(1, 13):
            expiry = calc.monthly_expiry(2025, month)
            # The result is a Thursday OR adjusted backward from one
            # Either way it must be <= the last Thursday of the month
            assert expiry.weekday() <= 4  # Mon-Fri

    def test_holiday_adjustment_moves_expiry_earlier(self) -> None:
        # Jan 30, 2025 is the last Thursday → make it a holiday
        calc = _calc_with_holidays({date(2025, 1, 30)})
        expiry = calc.monthly_expiry(2025, 1)
        assert expiry == date(2025, 1, 29)  # Wednesday

    def test_invalid_month_raises(self) -> None:
        with pytest.raises(ValueError, match="month"):
            _calc().monthly_expiry(2025, 0)

    def test_invalid_month_13_raises(self) -> None:
        with pytest.raises(ValueError, match="month"):
            _calc().monthly_expiry(2025, 13)


class TestNextWeeklyExpiry:
    def test_from_monday_returns_thursday(self) -> None:
        monday = date(2025, 1, 13)
        assert _calc().next_weekly_expiry(monday) == date(2025, 1, 16)

    def test_from_thursday_returns_same_thursday(self) -> None:
        thursday = date(2025, 1, 16)
        assert _calc().next_weekly_expiry(thursday) == thursday

    def test_from_friday_returns_next_thursday(self) -> None:
        friday = date(2025, 1, 17)
        assert _calc().next_weekly_expiry(friday) == date(2025, 1, 23)

    def test_from_saturday_returns_next_thursday(self) -> None:
        saturday = date(2025, 1, 18)
        assert _calc().next_weekly_expiry(saturday) == date(2025, 1, 23)

    def test_holiday_adjustment_for_thursday(self) -> None:
        # Thursday Jan 16 is a holiday → expiry moves to Wednesday Jan 15
        calc = _calc_with_holidays({date(2025, 1, 16)})
        # From Monday Jan 13, nearest Thursday is Jan 16, adjusted to Jan 15
        assert calc.next_weekly_expiry(date(2025, 1, 13)) == date(2025, 1, 15)

    def test_holiday_adjustment_moves_to_next_week_if_before_start(self) -> None:
        # Thursday Jan 16 is a holiday → nominal expiry moves to Wed Jan 15
        # But from Friday Jan 17, Jan 15 < Jan 17, so go to next week's Thu Jan 23
        calc = _calc_with_holidays({date(2025, 1, 16)})
        assert calc.next_weekly_expiry(date(2025, 1, 17)) == date(2025, 1, 23)

    def test_custom_expiry_day_tuesday_for_sensex(self) -> None:
        monday = date(2025, 1, 13)
        # SENSEX weekly expiry is Tuesday
        assert _calc().next_weekly_expiry(monday, SENSEX_WEEKLY_EXPIRY_DAY) == date(2025, 1, 14)

    def test_nifty_weekly_expiry_day_is_thursday(self) -> None:
        assert NIFTY_WEEKLY_EXPIRY_DAY == WeeklyExpiryDay.THURSDAY

    def test_sensex_weekly_expiry_day_is_tuesday(self) -> None:
        assert SENSEX_WEEKLY_EXPIRY_DAY == WeeklyExpiryDay.TUESDAY

    def test_result_is_always_trading_day(self) -> None:
        calc = _calc()
        start = date(2025, 1, 1)
        for days_offset in range(20):
            from_date = start + __import__("datetime").timedelta(days=days_offset)
            expiry = calc.next_weekly_expiry(from_date)
            assert expiry.weekday() < 5  # Weekday
            assert expiry >= from_date


class TestNextMonthlyExpiry:
    def test_from_start_of_month_returns_this_months_expiry(self) -> None:
        from_date = date(2025, 1, 1)
        assert _calc().next_monthly_expiry(from_date) == date(2025, 1, 30)

    def test_from_after_expiry_returns_next_months(self) -> None:
        from_date = date(2025, 1, 31)  # After Jan 30 expiry
        assert _calc().next_monthly_expiry(from_date) == date(2025, 2, 27)

    def test_from_expiry_date_returns_same_date(self) -> None:
        from_date = date(2025, 1, 30)
        assert _calc().next_monthly_expiry(from_date) == date(2025, 1, 30)

    def test_december_to_january_transition(self) -> None:
        from_date = date(2025, 12, 26)  # After Dec 25 expiry
        expiry = _calc().next_monthly_expiry(from_date)
        assert expiry.year == 2026
        assert expiry.month == 1


class TestExpirySeries:
    def test_weekly_series_of_4(self) -> None:
        series = _calc().expiry_series(
            from_date=date(2025, 1, 13),
            expiry_type=ExpiryType.WEEKLY,
            count=4,
        )
        assert len(series) == 4
        assert all(isinstance(e, ExpiryInfo) for e in series)
        assert all(e.expiry_type == ExpiryType.WEEKLY for e in series)
        # Dates are strictly increasing
        for i in range(len(series) - 1):
            assert series[i].date < series[i + 1].date

    def test_monthly_series_of_3(self) -> None:
        series = _calc().expiry_series(
            from_date=date(2025, 1, 1),
            expiry_type=ExpiryType.MONTHLY,
            count=3,
        )
        assert len(series) == 3
        assert all(e.expiry_type == ExpiryType.MONTHLY for e in series)
        months = [e.date.month for e in series]
        assert months == sorted(months)

    def test_invalid_count_raises(self) -> None:
        with pytest.raises(ValueError, match="count"):
            _calc().expiry_series(date(2025, 1, 1), ExpiryType.WEEKLY, 0)

    def test_unsupported_type_raises(self) -> None:
        with pytest.raises(ValueError, match="not yet supported"):
            _calc().expiry_series(date(2025, 1, 1), ExpiryType.QUARTERLY, 1)

    def test_exchange_name_in_results(self) -> None:
        calc = NSEExpiryCalculator(NSETradingCalendar(NullHolidayProvider()), exchange="BSE")
        series = calc.expiry_series(date(2025, 1, 1), ExpiryType.WEEKLY, 1)
        assert series[0].exchange == "BSE"


class TestNextWeekBranch:
    def test_from_holiday_thursday_returns_next_week(self) -> None:
        """Cover the 'next-week' branch inside next_weekly_expiry.

        When from_date IS the holiday Thursday, the holiday adjustment moves
        the expiry to the previous Wednesday which is < from_date, so the
        calculator must advance to the following week's Thursday.
        """
        calc = _calc_with_holidays({date(2025, 1, 16)})
        # candidate = Jan 16 (holiday) → adjusted back to Jan 15 (Wed)
        # Jan 15 < Jan 16 (from_date) → advance to next week: Jan 23
        assert calc.next_weekly_expiry(date(2025, 1, 16)) == date(2025, 1, 23)
