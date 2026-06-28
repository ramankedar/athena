"""Derivative contract expiry date calculations.

``NSEExpiryCalculator`` computes expiry dates for NSE F&O instruments:

- **Monthly expiry**: Last Thursday of the calendar month. If that Thursday
  is a holiday, the expiry shifts to the previous trading day.

- **Weekly expiry**: The nearest upcoming instance of the configured expiry
  weekday (default: Thursday for NIFTY). If that weekday is a holiday, the
  expiry shifts to the previous trading day.

Common expiry days on NSE:
    - ``NIFTY 50``    — Thursday (``WeeklyExpiryDay.THURSDAY``)
    - ``SENSEX``      — Tuesday  (``WeeklyExpiryDay.TUESDAY``)

All calculations incorporate the trading calendar to guarantee that the
returned date is always a valid trading day.

Note on last-day-of-month computation:
    This module does NOT import the stdlib ``calendar`` module to avoid
    naming ambiguity with ``athena.time.calendar``. Month-end dates are
    computed via ``date(year, month+1, 1) - timedelta(days=1)`` instead.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from athena.time.exceptions import ExpiryCalculationError
from athena.time.models import ExpiryInfo, ExpiryType, WeeklyExpiryDay

if TYPE_CHECKING:
    from athena.time.interfaces import TradingCalendarProtocol

# Convenience constants for the most common NSE expiry days.
NIFTY_WEEKLY_EXPIRY_DAY: WeeklyExpiryDay = WeeklyExpiryDay.THURSDAY
SENSEX_WEEKLY_EXPIRY_DAY: WeeklyExpiryDay = WeeklyExpiryDay.TUESDAY

_MAX_HOLIDAY_ADJUSTMENT_DAYS: int = 7
"""Maximum days to search backward when adjusting an expiry date for holidays.
If an entire expiry week is closed (e.g. extended market shutdown), this limit
prevents an infinite loop and triggers ``ExpiryCalculationError`` instead.
"""


def _last_day_of_month(year: int, month: int) -> date:
    """Return the last calendar date of the given month.

    Args:
        year:  Four-digit calendar year.
        month: Calendar month (1-12).

    Returns:
        The last date of the specified month.
    """
    if month == 12:
        return date(year + 1, 1, 1) - timedelta(days=1)
    return date(year, month + 1, 1) - timedelta(days=1)


def _adjust_to_trading_day(
    nominal: date,
    calendar: TradingCalendarProtocol,
    context: str,
) -> date:
    """Adjust ``nominal`` backward to the nearest trading day.

    If ``nominal`` itself is a trading day, it is returned unchanged.
    Otherwise, the function steps backward one day at a time until a
    trading day is found.

    Args:
        nominal:  The initially computed expiry date.
        calendar: The calendar used to validate trading days.
        context:  A short description for error messages.

    Returns:
        The adjusted trading day.

    Raises:
        ExpiryCalculationError: If no trading day is found within
            ``_MAX_HOLIDAY_ADJUSTMENT_DAYS`` days.
    """
    candidate = nominal
    for _ in range(_MAX_HOLIDAY_ADJUSTMENT_DAYS + 1):
        if calendar.is_trading_day(candidate):
            return candidate
        candidate -= timedelta(days=1)

    raise ExpiryCalculationError(
        f"No trading day found within {_MAX_HOLIDAY_ADJUSTMENT_DAYS} days of {context}",
        error_code="TIM_005",
        nominal_date=nominal.isoformat(),
        context=context,
    )


class NSEExpiryCalculator:
    """Expiry date calculator for NSE F&O contracts.

    Args:
        calendar: Trading calendar used to validate and adjust expiry dates.
        exchange: Exchange name to embed in returned ``ExpiryInfo`` objects.
            Defaults to ``"NSE"``.

    Example::

        from datetime import date
        from athena.time.calendar import NSETradingCalendar
        from athena.time.holiday import NullHolidayProvider

        cal = NSETradingCalendar(NullHolidayProvider())
        calc = NSEExpiryCalculator(cal)

        # Last Thursday of January 2025
        expiry = calc.monthly_expiry(2025, 1)
        assert expiry == date(2025, 1, 30)
    """

    def __init__(
        self,
        calendar: TradingCalendarProtocol,
        exchange: str = "NSE",
    ) -> None:
        self._calendar = calendar
        self._exchange = exchange

    def monthly_expiry(self, year: int, month: int) -> date:
        """Return the monthly F&O expiry date for the given year and month.

        The nominal expiry is the last Thursday of the month. If that Thursday
        is a holiday, the expiry is moved to the previous trading day.

        Args:
            year:  Four-digit calendar year.
            month: Calendar month (1-12).

        Returns:
            The monthly expiry date.

        Raises:
            ValueError: If ``month`` is not in 1-12.
            ExpiryCalculationError: If no trading day can be found near the
                nominal expiry.
        """
        if not 1 <= month <= 12:
            raise ValueError(f"month must be 1-12, got {month}")

        last_day = _last_day_of_month(year, month)

        # Walk backward from the last day to find the last Thursday.
        days_back = (last_day.weekday() - WeeklyExpiryDay.THURSDAY) % 7
        last_thursday = last_day - timedelta(days=days_back)

        return _adjust_to_trading_day(
            last_thursday,
            self._calendar,
            context=f"monthly expiry {year}-{month:02d}",
        )

    def next_weekly_expiry(
        self,
        from_date: date,
        expiry_day: WeeklyExpiryDay = NIFTY_WEEKLY_EXPIRY_DAY,
    ) -> date:
        """Return the next weekly expiry date on or after ``from_date``.

        Finds the nearest instance of ``expiry_day`` on or after ``from_date``,
        then adjusts backward for holidays. If the adjustment moves the expiry
        to before ``from_date``, the calculator moves to the following week.

        Args:
            from_date:  Start of the search window.
            expiry_day: Weekday on which weekly expiry falls. Defaults to
                ``NIFTY_WEEKLY_EXPIRY_DAY`` (Thursday).

        Returns:
            The next weekly expiry date (always ``>= from_date``).

        Raises:
            ExpiryCalculationError: If no valid expiry is found.
        """
        target_weekday = int(expiry_day)

        # Compute days until the target weekday (0 if from_date is already that day)
        days_until_target = (target_weekday - from_date.weekday()) % 7
        candidate = from_date + timedelta(days=days_until_target)

        adjusted = _adjust_to_trading_day(
            candidate,
            self._calendar,
            context=f"weekly expiry from {from_date.isoformat()} ({expiry_day.name})",
        )

        # If holiday adjustment moved the expiry to before from_date,
        # advance to the next week's expiry.
        if adjusted < from_date:
            next_candidate = candidate + timedelta(weeks=1)
            adjusted = _adjust_to_trading_day(
                next_candidate,
                self._calendar,
                context=f"next-week expiry from {from_date.isoformat()} ({expiry_day.name})",
            )

        return adjusted

    def next_monthly_expiry(self, from_date: date) -> date:
        """Return the next monthly expiry on or after ``from_date``.

        If the current month's expiry has not yet passed, returns it.
        Otherwise, returns the following month's expiry.

        Args:
            from_date: Reference date.

        Returns:
            The next monthly expiry date (always ``>= from_date``).
        """
        candidate = self.monthly_expiry(from_date.year, from_date.month)
        if candidate >= from_date:
            return candidate

        # This month's expiry has already passed — move to next month.
        if from_date.month == 12:
            return self.monthly_expiry(from_date.year + 1, 1)
        return self.monthly_expiry(from_date.year, from_date.month + 1)

    def expiry_series(
        self,
        from_date: date,
        expiry_type: ExpiryType,
        count: int,
    ) -> list[ExpiryInfo]:
        """Return a series of consecutive expiry dates.

        Args:
            from_date:   Start date for the series (first expiry is >= this date).
            expiry_type: The expiry cadence — weekly or monthly.
            count:       Number of expiry dates to return (must be >= 1).

        Returns:
            A list of ``ExpiryInfo`` objects in ascending date order.

        Raises:
            ValueError: If ``count < 1`` or ``expiry_type`` is not supported.
        """
        if count < 1:
            raise ValueError(f"count must be >= 1, got {count}")

        results: list[ExpiryInfo] = []
        current = from_date

        for _ in range(count):
            if expiry_type == ExpiryType.WEEKLY:
                expiry_date = self.next_weekly_expiry(current)
                results.append(
                    ExpiryInfo(
                        date=expiry_date,
                        expiry_type=ExpiryType.WEEKLY,
                        exchange=self._exchange,
                    )
                )
                # Advance past this expiry to find the next distinct one.
                current = expiry_date + timedelta(days=1)

            elif expiry_type == ExpiryType.MONTHLY:
                expiry_date = self.next_monthly_expiry(current)
                results.append(
                    ExpiryInfo(
                        date=expiry_date,
                        expiry_type=ExpiryType.MONTHLY,
                        exchange=self._exchange,
                    )
                )
                # Advance to the first day of the next month.
                if expiry_date.month == 12:
                    current = date(expiry_date.year + 1, 1, 1)
                else:
                    current = date(expiry_date.year, expiry_date.month + 1, 1)

            else:
                raise ValueError(
                    f"expiry_type {expiry_type!r} is not yet supported (supported: WEEKLY, MONTHLY)"
                )

        return results
