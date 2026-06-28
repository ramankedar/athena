"""Business-day arithmetic utilities.

These are module-level functions rather than methods on a calendar class.
Rationale: business-day arithmetic is purely compositional — it is built
entirely from ``TradingCalendarProtocol.next_trading_day()`` and
``previous_trading_day()``. Putting this logic on every calendar implementation
would force identical code duplication; putting it here keeps implementations
minimal and the arithmetic composable.

All functions take a ``TradingCalendarProtocol`` argument, so they work with
any calendar — NSE, BSE, MCX, or a test calendar.

Usage::

    from athena.time.business_day import add_trading_days, count_trading_days
    from athena.time.calendar import NSETradingCalendar
    from athena.time.holiday import NullHolidayProvider

    cal = NSETradingCalendar(NullHolidayProvider())
    from datetime import date
    start = date(2025, 1, 13)  # Monday
    end = add_trading_days(start, 5, cal)  # 5 trading days later
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from athena.time.interfaces import TradingCalendarProtocol


def add_trading_days(d: date, n: int, calendar: TradingCalendarProtocol) -> date:
    """Return the date that is ``n`` trading days after ``d``.

    When ``n`` is zero, ``d`` itself is returned regardless of whether it is
    a trading day. When ``n`` is negative, delegates to
    ``subtract_trading_days``.

    Args:
        d:        Starting date.
        n:        Number of trading days to advance. May be negative.
        calendar: The trading calendar to use for day validation.

    Returns:
        The date ``n`` trading days after ``d``.
    """
    if n == 0:
        return d
    if n < 0:
        return subtract_trading_days(d, -n, calendar)
    result = d
    for _ in range(n):
        result = calendar.next_trading_day(result)
    return result


def subtract_trading_days(d: date, n: int, calendar: TradingCalendarProtocol) -> date:
    """Return the date that is ``n`` trading days before ``d``.

    When ``n`` is zero, ``d`` itself is returned. When ``n`` is negative,
    delegates to ``add_trading_days``.

    Args:
        d:        Starting date.
        n:        Number of trading days to go back. May be negative.
        calendar: The trading calendar to use for day validation.

    Returns:
        The date ``n`` trading days before ``d``.
    """
    if n == 0:
        return d
    if n < 0:
        return add_trading_days(d, -n, calendar)
    result = d
    for _ in range(n):
        result = calendar.previous_trading_day(result)
    return result


def count_trading_days(
    start: date,
    end: date,
    calendar: TradingCalendarProtocol,
    *,
    inclusive_start: bool = False,
    inclusive_end: bool = True,
) -> int:
    """Count the number of trading days in ``[start, end]``.

    By default, ``start`` is excluded and ``end`` is included — this counts
    the number of trading days *elapsed since* ``start``.

    Args:
        start:           Lower bound of the date range.
        end:             Upper bound of the date range.
        calendar:        The trading calendar to use.
        inclusive_start: When ``True``, include ``start`` if it is a trading
            day. Default is ``False``.
        inclusive_end:   When ``True`` (default), include ``end`` if it is a
            trading day. When ``False``, ``end`` is excluded.

    Returns:
        The count of trading days in the specified range.

    Raises:
        ValueError: If ``start > end``.
    """
    if start > end:
        raise ValueError(f"start must be <= end: {start.isoformat()} > {end.isoformat()}")

    range_start = start if inclusive_start else start + timedelta(days=1)
    range_end = end if inclusive_end else end - timedelta(days=1)

    if range_start > range_end:
        return 0

    return len(calendar.trading_days_between(range_start, range_end, inclusive=True))


def trading_days_in_month(year: int, month: int, calendar: TradingCalendarProtocol) -> list[date]:
    """Return all trading days in the given calendar month.

    Args:
        year:     Four-digit calendar year.
        month:    Calendar month (1-12).
        calendar: The trading calendar to use.

    Returns:
        A sorted list of trading dates within the month.

    Raises:
        ValueError: If ``month`` is not in 1-12.
    """
    if not 1 <= month <= 12:
        raise ValueError(f"month must be 1-12, got {month}")

    first = date(year, month, 1)
    if month == 12:
        last = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)

    return calendar.trading_days_between(first, last, inclusive=True)


def is_last_trading_day_of_week(d: date, calendar: TradingCalendarProtocol) -> bool:
    """Return ``True`` if ``d`` is the last trading day in its ISO week.

    The ISO week runs Monday-Sunday. This function finds the next trading day
    after ``d`` and checks whether it falls in a different ISO week.

    Args:
        d:        The date to test.
        calendar: The trading calendar to use.

    Returns:
        ``True`` if ``d`` is the final trading day of its week.
    """
    if not calendar.is_trading_day(d):
        return False
    next_day = calendar.next_trading_day(d)
    return next_day.isocalendar().week != d.isocalendar().week


def is_last_trading_day_of_month(d: date, calendar: TradingCalendarProtocol) -> bool:
    """Return ``True`` if ``d`` is the last trading day of its calendar month.

    Args:
        d:        The date to test.
        calendar: The trading calendar to use.

    Returns:
        ``True`` if no more trading days remain in the same month after ``d``.
    """
    if not calendar.is_trading_day(d):
        return False
    next_day = calendar.next_trading_day(d)
    return next_day.month != d.month or next_day.year != d.year
