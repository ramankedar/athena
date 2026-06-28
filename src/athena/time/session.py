"""Market session computation for the NSE/BSE trading day.

``NSESessionService`` computes ``MarketSession`` objects on demand from:
1. A static schedule (``NSE_SESSION_SCHEDULE``) — the IST-based definition
   of each session's start and end time.
2. A ``TradingCalendarProtocol`` — determines which dates are trading days.
3. A ``ClockProtocol`` — provides the current moment when ``at`` is not given.

Design notes:

Session definitions are compile-time constants (``NSE_SESSION_SCHEDULE``),
not service state. Adding a new exchange means defining a new schedule tuple
and passing it to the service — no subclassing required.

Session querying uses ``opens_at_utc <= at < closes_at_utc`` (inclusive start,
exclusive end). This avoids the ambiguity of two adjacent sessions both matching
at their shared boundary. The previous session's close is always strictly before
the next session's open (they share the same instant, but only the opening
session claims it).

All stored and returned datetimes are UTC. IST is used only internally when
mapping session definitions (which are in IST) to calendar dates.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING, ClassVar

from athena.core.domain.market import MarketSession, SessionType
from athena.time.exceptions import NoSessionError
from athena.time.timezone import IST, UTC, require_aware

if TYPE_CHECKING:
    from athena.time.interfaces import ClockProtocol, TradingCalendarProtocol

# ── NSE session schedule (times in IST) ──────────────────────────────────────
# Each entry: (SessionType, start_time_ist, end_time_ist)
# Times are exclusive on the right: a tick at exactly 09:15 IST enters NORMAL,
# not PRE_OPEN_MATCHING.
NSE_SESSION_SCHEDULE: tuple[tuple[SessionType, time, time], ...] = (
    (SessionType.PRE_OPEN, time(9, 0), time(9, 8)),
    (SessionType.PRE_OPEN_MATCHING, time(9, 8), time(9, 15)),
    (SessionType.NORMAL, time(9, 15), time(15, 30)),
    (SessionType.CLOSING, time(15, 30), time(15, 40)),
    (SessionType.POST_CLOSE, time(15, 40), time(16, 0)),
)

_MAX_SESSION_SEARCH_DAYS: int = 30
"""Maximum number of calendar days to search for the next/previous session."""


class NSESessionService:
    """Computes market sessions for the NSE/BSE trading day.

    Args:
        calendar: Trading calendar used to determine valid trading days.
        clock:    Clock used when ``at`` is not specified on query methods.

    Example::

        from datetime import datetime, UTC
        from athena.time.clock import FrozenClock
        from athena.time.calendar import NSETradingCalendar
        from athena.time.holiday import NullHolidayProvider

        clock = FrozenClock(datetime(2025, 1, 15, 5, 0, tzinfo=UTC))
        cal = NSETradingCalendar(NullHolidayProvider())
        svc = NSESessionService(calendar=cal, clock=clock)
        # 05:00 UTC = 10:30 IST → NORMAL session
        session = svc.get_session()
        assert session is not None
        assert session.session_type == SessionType.NORMAL
    """

    _schedule: ClassVar[tuple[tuple[SessionType, time, time], ...]] = NSE_SESSION_SCHEDULE

    def __init__(
        self,
        calendar: TradingCalendarProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._calendar = calendar
        self._clock = clock

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _build_sessions(self, trading_date: date) -> list[MarketSession]:
        """Construct ``MarketSession`` objects for a specific trading date.

        Args:
            trading_date: The date for which to build sessions.

        Returns:
            A list of ``MarketSession`` objects in chronological order.
        """
        sessions: list[MarketSession] = []
        for session_type, start_ist, end_ist in self._schedule:
            opens_ist = datetime.combine(trading_date, start_ist).replace(tzinfo=IST)
            closes_ist = datetime.combine(trading_date, end_ist).replace(tzinfo=IST)
            sessions.append(
                MarketSession(
                    session_type=session_type,
                    opens_at_utc=opens_ist.astimezone(UTC),
                    closes_at_utc=closes_ist.astimezone(UTC),
                )
            )
        return sessions

    # ── Public API ────────────────────────────────────────────────────────────

    def get_session_type(self, at: datetime | None = None) -> SessionType:
        """Return the session type active at the given moment.

        Args:
            at: A UTC-aware datetime to query. When ``None``, uses the
                injected clock.

        Returns:
            The active ``SessionType``. Returns ``SessionType.CLOSED`` when
            ``at`` falls outside all trading sessions or on a non-trading day.

        Raises:
            NaiveDatetimeError: If ``at`` is timezone-naive.
        """
        now = at if at is not None else self._clock.now()
        require_aware(now)

        trading_date = now.astimezone(IST).date()
        if not self._calendar.is_trading_day(trading_date):
            return SessionType.CLOSED

        for session in self._build_sessions(trading_date):
            if session.opens_at_utc <= now < session.closes_at_utc:
                return session.session_type

        return SessionType.CLOSED

    def get_session(self, at: datetime | None = None) -> MarketSession | None:
        """Return the active ``MarketSession`` at the given moment, or ``None``.

        Args:
            at: A UTC-aware datetime to query. When ``None``, uses the clock.

        Returns:
            The ``MarketSession`` containing ``at``, or ``None`` when the
            market is closed (non-trading day or outside session hours).

        Raises:
            NaiveDatetimeError: If ``at`` is timezone-naive.
        """
        now = at if at is not None else self._clock.now()
        require_aware(now)

        trading_date = now.astimezone(IST).date()
        if not self._calendar.is_trading_day(trading_date):
            return None

        for session in self._build_sessions(trading_date):
            if session.opens_at_utc <= now < session.closes_at_utc:
                return session

        return None

    def next_session(self, after: datetime) -> MarketSession:
        """Return the next market session that begins strictly after ``after``.

        Searches forward day by day until a session is found. On non-trading
        days, all sessions for that day are skipped.

        Args:
            after: A UTC-aware reference datetime.

        Returns:
            The next upcoming ``MarketSession``.

        Raises:
            NaiveDatetimeError: If ``after`` is timezone-naive.
            NoSessionError: If no session is found within
                ``_MAX_SESSION_SEARCH_DAYS`` calendar days.
        """
        require_aware(after)

        search_date = after.astimezone(IST).date()
        for _ in range(_MAX_SESSION_SEARCH_DAYS):
            if self._calendar.is_trading_day(search_date):
                for session in self._build_sessions(search_date):
                    if session.opens_at_utc > after:
                        return session
            search_date += timedelta(days=1)

        raise NoSessionError(
            str(after),
            max_days=_MAX_SESSION_SEARCH_DAYS,
            direction="forward",
        )

    def previous_session(self, before: datetime) -> MarketSession:
        """Return the most recent market session that ended before ``before``.

        Searches backward day by day until a session is found.

        Args:
            before: A UTC-aware reference datetime.

        Returns:
            The most recently completed ``MarketSession`` before ``before``.

        Raises:
            NaiveDatetimeError: If ``before`` is timezone-naive.
            NoSessionError: If no session is found within
                ``_MAX_SESSION_SEARCH_DAYS`` calendar days.
        """
        require_aware(before)

        search_date = before.astimezone(IST).date()
        for _ in range(_MAX_SESSION_SEARCH_DAYS):
            if self._calendar.is_trading_day(search_date):
                # Check sessions in reverse order (POST_CLOSE → PRE_OPEN)
                for session in reversed(self._build_sessions(search_date)):
                    if session.closes_at_utc < before:
                        return session
            search_date -= timedelta(days=1)

        raise NoSessionError(
            str(before),
            max_days=_MAX_SESSION_SEARCH_DAYS,
            direction="backward",
        )

    def sessions_for_date(self, trading_date: date) -> list[MarketSession]:
        """Return all market sessions for a given date.

        Args:
            trading_date: The calendar date to query.

        Returns:
            An ordered list of ``MarketSession`` objects for the date, or an
            empty list if ``trading_date`` is not a trading day.
        """
        if not self._calendar.is_trading_day(trading_date):
            return []
        return self._build_sessions(trading_date)
