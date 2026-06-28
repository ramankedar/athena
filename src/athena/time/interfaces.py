"""Protocol interfaces for the time domain.

Every service in ``athena.time`` exposes a ``Protocol`` here. Implementations
are in their respective modules. Callers type-hint against these protocols,
not against concrete classes, keeping the dependency graph clean and
implementations swappable without touching calling code.

Usage::

    from athena.time.interfaces import ClockProtocol, TradingCalendarProtocol

    def some_service(clock: ClockProtocol, cal: TradingCalendarProtocol) -> None:
        today = clock.today()
        next_day = cal.next_trading_day(today)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from datetime import date, datetime

    from athena.core.domain.market import MarketSession, SessionType
    from athena.time.models import ExpiryInfo, ExpiryType, WeeklyExpiryDay


@runtime_checkable
class ClockProtocol(Protocol):
    """Abstraction over the system clock.

    All time-dependent code must accept a ``ClockProtocol`` rather than
    calling ``datetime.now()`` directly. This enables deterministic testing
    with ``FrozenClock`` or ``ManualClock`` without monkeypatching.
    """

    def now(self) -> datetime:
        """Return the current UTC-aware datetime.

        Returns:
            The current moment as a UTC timezone-aware ``datetime``.
        """
        ...

    def today(self) -> date:
        """Return the current calendar date in IST (the exchange's local timezone).

        The date is resolved in IST rather than UTC because a date change in
        UTC may not yet have occurred in IST — especially relevant for
        operations between 18:30-00:00 UTC (00:00-05:30 IST next day).

        Returns:
            Today's date in Asia/Kolkata.
        """
        ...


@runtime_checkable
class HolidayProviderProtocol(Protocol):
    """Source of exchange holiday information.

    Implementations may load holidays from a static dataset, an API,
    a database, or a CSV file. The interface is intentionally minimal
    to make implementations easy to write and test.
    """

    def get_holidays(self, year: int) -> frozenset[date]:
        """Return all exchange holidays in the given calendar year.

        Args:
            year: Four-digit calendar year (e.g. ``2025``).

        Returns:
            A frozenset of dates that are exchange holidays. Empty frozenset
            when the provider has no data for the requested year.
        """
        ...

    def is_holiday(self, d: date) -> bool:
        """Return ``True`` if ``d`` is an exchange holiday.

        Args:
            d: The date to check.

        Returns:
            ``True`` if ``d`` is a recorded holiday, ``False`` otherwise.
        """
        ...


@runtime_checkable
class TradingCalendarProtocol(Protocol):
    """Determines which dates are valid trading days and navigates between them.

    The calendar combines two sources of truth: weekends (always non-trading)
    and exchange holidays (from a ``HolidayProviderProtocol``).
    """

    def is_trading_day(self, d: date) -> bool:
        """Return ``True`` if ``d`` is a trading day on this exchange.

        Args:
            d: The date to check.

        Returns:
            ``False`` for weekends and exchange holidays; ``True`` otherwise.
        """
        ...

    def next_trading_day(self, d: date) -> date:
        """Return the first trading day strictly after ``d``.

        Args:
            d: Reference date. The returned date is always ``> d``.

        Returns:
            The next trading day after ``d``.
        """
        ...

    def previous_trading_day(self, d: date) -> date:
        """Return the most recent trading day strictly before ``d``.

        Args:
            d: Reference date. The returned date is always ``< d``.

        Returns:
            The previous trading day before ``d``.
        """
        ...

    def trading_days_between(self, start: date, end: date, *, inclusive: bool = True) -> list[date]:
        """Return all trading days in the range ``[start, end]``.

        Args:
            start: First date in the search range (inclusive).
            end:   Last date in the search range.
            inclusive: When ``True`` (default), includes ``end`` if it is a
                trading day. When ``False``, ``end`` is excluded.

        Returns:
            Sorted list of trading days in the range. Empty list when no
            trading days fall within the range.

        Raises:
            ValueError: If ``start > end``.
        """
        ...


@runtime_checkable
class SessionServiceProtocol(Protocol):
    """Queries market session information for a specific exchange.

    Sessions are computed on demand from a fixed schedule and a trading
    calendar. The service never caches session state.
    """

    def get_session_type(self, at: datetime | None = None) -> SessionType:
        """Return the session type active at the given moment.

        Args:
            at: A UTC-aware datetime to query. When ``None``, the service's
                clock is used to determine the current moment.

        Returns:
            The ``SessionType`` active at ``at``. Returns
            ``SessionType.CLOSED`` when ``at`` falls outside all trading
            sessions or on a non-trading day.
        """
        ...

    def get_session(self, at: datetime | None = None) -> MarketSession | None:
        """Return the active ``MarketSession`` at the given moment, or ``None``.

        Args:
            at: A UTC-aware datetime to query. When ``None``, uses the clock.

        Returns:
            The ``MarketSession`` containing ``at``, or ``None`` if the market
            is closed at that moment.
        """
        ...

    def next_session(self, after: datetime) -> MarketSession:
        """Return the next market session that begins after ``after``.

        Searches forward through trading days until a session is found.

        Args:
            after: A UTC-aware reference datetime. The returned session
                opens strictly after this moment.

        Returns:
            The next upcoming ``MarketSession``.

        Raises:
            NoSessionError: If no session is found within the search window.
        """
        ...

    def previous_session(self, before: datetime) -> MarketSession:
        """Return the most recent market session that ended before ``before``.

        Searches backward through trading days until a session is found.

        Args:
            before: A UTC-aware reference datetime. The returned session
                closes strictly before this moment.

        Returns:
            The most recently completed ``MarketSession``.

        Raises:
            NoSessionError: If no session is found within the search window.
        """
        ...

    def sessions_for_date(self, trading_date: date) -> list[MarketSession]:
        """Return all market sessions for a given trading date.

        Args:
            trading_date: The date to query. Must be a trading day.

        Returns:
            Ordered list of ``MarketSession`` objects for the day.
            Returns an empty list if ``trading_date`` is not a trading day.
        """
        ...


@runtime_checkable
class ExpiryCalculatorProtocol(Protocol):
    """Computes derivative contract expiry dates.

    Expiry calculations incorporate the trading calendar to ensure that
    expiry dates are always valid trading days — if the computed expiry
    falls on a holiday, the calculator moves to the previous trading day.
    """

    def monthly_expiry(self, year: int, month: int) -> date:
        """Return the monthly expiry date for the given year and month.

        For NSE, this is the last Thursday of the month, adjusted backward
        to the nearest trading day if the Thursday is a holiday.

        Args:
            year:  Four-digit calendar year.
            month: Calendar month (1-12).

        Returns:
            The monthly expiry date.

        Raises:
            ExpiryCalculationError: If the expiry date cannot be determined.
        """
        ...

    def next_weekly_expiry(
        self,
        from_date: date,
        expiry_day: WeeklyExpiryDay = ...,
    ) -> date:
        """Return the next weekly expiry on or after ``from_date``.

        The returned date is always a valid trading day: if the nominal
        expiry weekday falls on a holiday, the calculator steps backward
        to the previous trading day.

        Args:
            from_date:  Start of the search window.
            expiry_day: The day of the week on which weekly expiry falls.
                Defaults to ``WeeklyExpiryDay.THURSDAY`` (NIFTY).

        Returns:
            The next weekly expiry date.
        """
        ...

    def next_monthly_expiry(self, from_date: date) -> date:
        """Return the next monthly expiry strictly after ``from_date``.

        Args:
            from_date: Reference date. The returned date is always ``>= from_date``.

        Returns:
            The next monthly expiry date.
        """
        ...

    def expiry_series(
        self,
        from_date: date,
        expiry_type: ExpiryType,
        count: int,
    ) -> list[ExpiryInfo]:
        """Return a series of consecutive expiry dates.

        Args:
            from_date:   Start date for the series.
            expiry_type: The type of expiry to generate (weekly, monthly, etc.).
            count:       Number of expiry dates to return (must be >= 1).

        Returns:
            A list of ``ExpiryInfo`` objects in ascending date order.

        Raises:
            ValueError: If ``count < 1``.
        """
        ...
