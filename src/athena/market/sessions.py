"""Market session schedule value objects.

Defines the recurring daily and weekly session schedule for an exchange or
segment. This is the PATTERN of when a market operates — not the computation
of specific dates (which is the Time Domain's responsibility).

Distinction from ``athena.time.session``:
    ``athena.time.session.NSESessionService`` computes actual session datetimes
    for a given date using a clock and calendar. This module defines the
    SCHEDULE from which such computations derive — the "business rules" about
    what the schedule looks like, not the calculations on top of it.

    ``ExchangeSchedule`` says: "NSE has a pre-open session from 09:00 to 09:15."
    ``NSESessionService`` says: "On 2025-01-15, the pre-open starts at
    2025-01-15T03:30:00Z and ends at 2025-01-15T03:45:00Z."

``MarketSessionType`` uses different names than ``athena.core.domain.market.SessionType``
to reflect the broader exchange-agnostic perspective:
    - ``OPENING_AUCTION`` covers both pre-open order collection and call matching.
    - ``CONTINUOUS`` is the primary lit market (NORMAL in core).
    - ``CLOSING_AUCTION`` replaces CLOSING + POST_CLOSE.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from enum import StrEnum

from athena.market.exceptions import InvalidScheduleError
from athena.market.models import MarketId, MarketTimezone, WeeklySchedule


class MarketSessionType(StrEnum):
    """The type of trading session for a session window.

    Attributes:
        PRE_OPEN:        Pre-market order collection period. Orders may be
            placed but not yet matched. Prices not yet determined.
        OPENING_AUCTION: Call auction phase determining the opening price.
            Orders from PRE_OPEN are matched at a single clearing price.
        CONTINUOUS:      Primary continuous (order-book) trading. Orders
            are matched in real time as they arrive.
        CLOSING_AUCTION: Call auction phase determining the closing price.
            Ensures orderly market close with price discovery.
        AFTER_HOURS:     Post-close trading with limited order types and
            reduced liquidity. Typically restricted to institutional.
    """

    PRE_OPEN = "pre_open"
    OPENING_AUCTION = "opening_auction"
    CONTINUOUS = "continuous"
    CLOSING_AUCTION = "closing_auction"
    AFTER_HOURS = "after_hours"


@dataclass(frozen=True)
class SessionWindow:
    """A single named session phase within a trading day.

    All times are expressed in the exchange's local timezone (stored
    separately in ``DailySchedule.timezone``).

    Attributes:
        session_type: Classification of this trading phase.
        start_time:   Start of the session window (inclusive, local time).
        end_time:     End of the session window (exclusive, local time).

    Raises:
        InvalidScheduleError: If ``start_time >= end_time``.

    Example::

        pre_open = SessionWindow(
            session_type=MarketSessionType.PRE_OPEN,
            start_time=time(9, 0),
            end_time=time(9, 15),
        )
    """

    session_type: MarketSessionType
    start_time: time
    end_time: time

    def __post_init__(self) -> None:
        if self.start_time >= self.end_time:
            raise InvalidScheduleError(
                f"SessionWindow.start_time ({self.start_time}) must be "
                f"before end_time ({self.end_time})",
                session_type=self.session_type.value,
            )

    @property
    def duration_minutes(self) -> int:
        """Duration of this session window in whole minutes.

        Returns:
            Integer number of minutes from start to end.
        """
        start_min = self.start_time.hour * 60 + self.start_time.minute
        end_min = self.end_time.hour * 60 + self.end_time.minute
        return end_min - start_min

    def contains(self, t: time) -> bool:
        """Return ``True`` if ``t`` falls within this window (inclusive start, exclusive end).

        Args:
            t: The local time to check.

        Returns:
            ``True`` when ``start_time <= t < end_time``.
        """
        return self.start_time <= t < self.end_time

    def __str__(self) -> str:
        return f"{self.session_type.value}[{self.start_time}-{self.end_time}]"


@dataclass(frozen=True)
class DailySchedule:
    """The ordered set of trading session windows for a single day.

    Sessions must be in strictly chronological order with no gaps or overlaps.
    The schedule does not handle midnight-spanning sessions; 24-hour markets
    are represented with two separate daily schedules.

    Attributes:
        sessions:  Ordered tuple of session windows for the day.
        timezone:  IANA timezone in which ``sessions`` times are expressed.

    Raises:
        InvalidScheduleError: If ``sessions`` is empty, contains overlapping
            windows, or is not in chronological order.

    Example::

        nse_daily = DailySchedule(
            sessions=(
                SessionWindow(MarketSessionType.PRE_OPEN, time(9, 0), time(9, 15)),
                SessionWindow(MarketSessionType.CONTINUOUS, time(9, 15), time(15, 30)),
                SessionWindow(MarketSessionType.CLOSING_AUCTION, time(15, 30), time(16, 0)),
            ),
            timezone=MarketTimezone("Asia/Kolkata"),
        )
    """

    sessions: tuple[SessionWindow, ...]
    timezone: MarketTimezone

    def __post_init__(self) -> None:
        if not self.sessions:
            raise InvalidScheduleError("DailySchedule.sessions must not be empty")
        # Verify sessions are ordered and non-overlapping
        for i in range(len(self.sessions) - 1):
            current = self.sessions[i]
            next_session = self.sessions[i + 1]
            if current.end_time > next_session.start_time:
                raise InvalidScheduleError(
                    f"Session windows overlap or are out of order: "
                    f"{current} ends at {current.end_time} but "
                    f"{next_session} starts at {next_session.start_time}",
                )

    @property
    def market_open(self) -> time:
        """The start of the first session window.

        Returns:
            The local time at which the first session begins.
        """
        return self.sessions[0].start_time

    @property
    def market_close(self) -> time:
        """The end of the last session window.

        Returns:
            The local time at which the last session ends.
        """
        return self.sessions[-1].end_time

    @property
    def total_duration_minutes(self) -> int:
        """Total trading time across all sessions in minutes.

        Returns:
            Sum of durations of all session windows.
        """
        return sum(s.duration_minutes for s in self.sessions)

    def session_at(self, t: time) -> SessionWindow | None:
        """Return the session window active at local time ``t``, or ``None``.

        Args:
            t: Local time to query.

        Returns:
            The active ``SessionWindow``, or ``None`` if outside all windows.
        """
        for session in self.sessions:
            if session.contains(t):
                return session
        return None

    def has_session_type(self, session_type: MarketSessionType) -> bool:
        """Return ``True`` if this schedule includes the given session type.

        Args:
            session_type: The session type to check for.

        Returns:
            ``True`` when at least one window has this type.
        """
        return any(s.session_type == session_type for s in self.sessions)


@dataclass(frozen=True)
class ExchangeSchedule:
    """Complete recurring schedule for an exchange or specific segment.

    Combines a ``DailySchedule`` (intraday session windows) with a
    ``WeeklySchedule`` (which days of the week the market operates).

    Attributes:
        exchange_id: The exchange this schedule applies to.
        daily:       The intraday session windows and timezone.
        weekly:      Which days of the week the market operates.
        segment_id:  When not ``None``, this schedule applies to a specific
            segment within the exchange. ``None`` means exchange-wide default.

    Example::

        nse_schedule = ExchangeSchedule(
            exchange_id=MarketId("NSE"),
            daily=DailySchedule(...),
            weekly=WeeklySchedule.MON_FRI,
        )
    """

    exchange_id: MarketId
    daily: DailySchedule
    weekly: WeeklySchedule
    segment_id: MarketId | None = None

    def trades_on_weekday(self, weekday: int) -> bool:
        """Return ``True`` if the market operates on the given weekday.

        Args:
            weekday: Integer weekday (``date.weekday()``: 0=Monday, 6=Sunday).

        Returns:
            ``True`` when this exchange trades on the given weekday.
        """
        return self.weekly.trades_on(weekday)

    def __str__(self) -> str:
        scope = f"{self.exchange_id}" + (f"/{self.segment_id}" if self.segment_id else "")
        return f"ExchangeSchedule({scope}: {self.weekly!s})"


# ── Well-known NSE schedule ────────────────────────────────────────────────────
#
# These are domain facts about NSE's session structure, not configuration.
# The actual UTC datetimes for a specific date are computed by athena.time.

#: NSE pre-open session (09:00-09:15 IST).
NSE_PRE_OPEN: SessionWindow = SessionWindow(
    session_type=MarketSessionType.PRE_OPEN,
    start_time=time(9, 0),
    end_time=time(9, 15),
)

#: NSE continuous trading session (09:15-15:30 IST).
NSE_CONTINUOUS: SessionWindow = SessionWindow(
    session_type=MarketSessionType.CONTINUOUS,
    start_time=time(9, 15),
    end_time=time(15, 30),
)

#: NSE closing session / post-close (15:30-16:00 IST).
NSE_CLOSING: SessionWindow = SessionWindow(
    session_type=MarketSessionType.CLOSING_AUCTION,
    start_time=time(15, 30),
    end_time=time(16, 0),
)

#: Standard NSE equity and F&O daily schedule.
NSE_DAILY_SCHEDULE: DailySchedule = DailySchedule(
    sessions=(NSE_PRE_OPEN, NSE_CONTINUOUS, NSE_CLOSING),
    timezone=MarketTimezone("Asia/Kolkata"),
)

#: Full NSE schedule for equity and F&O (Mon-Fri).
NSE_STANDARD_SCHEDULE: ExchangeSchedule = ExchangeSchedule(
    exchange_id=MarketId("NSE"),
    daily=NSE_DAILY_SCHEDULE,
    weekly=WeeklySchedule.MON_FRI,
)
