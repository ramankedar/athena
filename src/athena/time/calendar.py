"""Trading calendar implementation.

The ``NSETradingCalendar`` is the concrete implementation of
``TradingCalendarProtocol`` for the National Stock Exchange (and BSE, which
shares the same trading calendar for equity and derivatives).

Calendar logic:
    A day is a trading day when ALL of the following are true:
    1. It is a weekday (Monday-Friday, ``date.weekday() <= 4``).
    2. It is NOT a holiday according to the configured ``HolidayProviderProtocol``.

The calendar never hard-codes holidays — it delegates entirely to the injected
provider. This means:
    - ``NullHolidayProvider`` → weekdays only (correct for backtesting with
      no holiday data).
    - ``SetHolidayProvider``  → weekdays minus the provided holiday set.
    - Future providers        → weekdays minus API/database holidays.

Note on the ``calendar`` module name:
    This module is named ``calendar.py``. Python 3 uses absolute imports by
    default, so ``import calendar`` anywhere in the codebase resolves to the
    stdlib ``calendar`` module, not to this file. There is no naming conflict.
    To avoid any ambiguity, this module does NOT import the stdlib ``calendar``
    module; month-end calculations use ``date`` arithmetic instead.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from athena.time.exceptions import NonTradingDayError

if TYPE_CHECKING:
    from athena.time.interfaces import HolidayProviderProtocol

_MAX_SEARCH_DAYS: int = 365
"""Safety limit for forward/backward trading-day searches.

If no trading day is found within this many calendar days, the calendar raises
rather than looping indefinitely. In practice, the longest known continuous
market closure is under 30 days, making 365 a very conservative bound.
"""


class NSETradingCalendar:
    """Trading calendar for the National Stock Exchange (NSE).

    Also valid for BSE (Bombay Stock Exchange), MCX equity sessions, and NSE
    CDS, as all share the same trading day schedule.

    Args:
        holiday_provider: Source of exchange holiday dates. Defaults are NOT
            applied here — callers must supply a provider. Use
            ``NullHolidayProvider()`` when no holiday data is available.

    Example::

        from athena.time.holiday import SetHolidayProvider
        from datetime import date

        cal = NSETradingCalendar(
            holiday_provider=SetHolidayProvider({date(2025, 1, 26)})
        )
        assert cal.is_trading_day(date(2025, 1, 26)) is False  # Republic Day
        assert cal.is_trading_day(date(2025, 1, 27)) is True   # Monday
    """

    def __init__(self, holiday_provider: HolidayProviderProtocol) -> None:
        self._holidays = holiday_provider

    def is_trading_day(self, d: date) -> bool:
        """Return ``True`` if ``d`` is a valid NSE trading day.

        A trading day is any Monday-Friday that is NOT a recorded holiday.

        Args:
            d: The date to test.

        Returns:
            ``True`` for weekday non-holidays; ``False`` for weekends and
            holidays.
        """
        if d.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        return not self._holidays.is_holiday(d)

    def next_trading_day(self, d: date) -> date:
        """Return the first trading day strictly after ``d``.

        Args:
            d: Reference date. The returned date is always ``> d``.

        Returns:
            The next trading day after ``d``.

        Raises:
            NonTradingDayError: If no trading day is found within
                ``_MAX_SEARCH_DAYS`` calendar days (indicates a calendar
                misconfiguration rather than a normal market closure).
        """
        candidate = d + timedelta(days=1)
        for _ in range(_MAX_SEARCH_DAYS):
            if self.is_trading_day(candidate):
                return candidate
            candidate += timedelta(days=1)
        raise NonTradingDayError(
            d.isoformat(),
            reason=f"no trading day found within {_MAX_SEARCH_DAYS} days",
        )

    def previous_trading_day(self, d: date) -> date:
        """Return the most recent trading day strictly before ``d``.

        Args:
            d: Reference date. The returned date is always ``< d``.

        Returns:
            The previous trading day before ``d``.

        Raises:
            NonTradingDayError: If no trading day is found within
                ``_MAX_SEARCH_DAYS`` calendar days.
        """
        candidate = d - timedelta(days=1)
        for _ in range(_MAX_SEARCH_DAYS):
            if self.is_trading_day(candidate):
                return candidate
            candidate -= timedelta(days=1)
        raise NonTradingDayError(
            d.isoformat(),
            reason=f"no trading day found within {_MAX_SEARCH_DAYS} days looking backward",
        )

    def trading_days_between(
        self,
        start: date,
        end: date,
        *,
        inclusive: bool = True,
    ) -> list[date]:
        """Return all trading days in the range ``[start, end]``.

        Args:
            start:     First date of the range (always included in the search).
            end:       Last date of the range.
            inclusive: When ``True`` (default), includes ``end`` if it is a
                trading day. When ``False``, ``end`` is excluded even if it is
                a trading day.

        Returns:
            A list of trading dates in ascending order. May be empty when no
            trading days fall in the range (e.g. a week-long holiday).

        Raises:
            ValueError: If ``start > end``.
        """
        if start > end:
            raise ValueError(f"start must be <= end: {start.isoformat()} > {end.isoformat()}")

        result: list[date] = []
        current = start
        limit = end if inclusive else end - timedelta(days=1)

        while current <= limit:
            if self.is_trading_day(current):
                result.append(current)
            current += timedelta(days=1)

        return result
