"""Shared fixtures for time-domain unit tests.

All market times are pinned to a concrete IST moment so tests are
deterministic regardless of when they run.

Reference market day used throughout these tests:
    Wednesday, 15 January 2025 — a normal NSE/BSE trading day.
    No holidays fall on this date with the NullHolidayProvider.

Session reference times (IST → UTC):
    08:30 IST = 03:00 UTC  — before market open (CLOSED)
    09:04 IST = 03:34 UTC  — during PRE_OPEN
    09:10 IST = 03:40 UTC  — during PRE_OPEN_MATCHING
    11:00 IST = 05:30 UTC  — during NORMAL
    15:35 IST = 10:05 UTC  — during CLOSING
    15:45 IST = 10:15 UTC  — during POST_CLOSE
    17:00 IST = 11:30 UTC  — after market close (CLOSED)
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from athena.time.calendar import NSETradingCalendar
from athena.time.clock import FrozenClock, ManualClock
from athena.time.expiry import NSEExpiryCalculator
from athena.time.holiday import NullHolidayProvider, SetHolidayProvider
from athena.time.session import NSESessionService
from athena.time.timezone import UTC

# ── Reference dates ───────────────────────────────────────────────────────────

TRADING_DATE = date(2025, 1, 15)  # Wednesday — normal trading day
WEEKEND_DATE = date(2025, 1, 18)  # Saturday  — never a trading day
HOLIDAY_DATE = date(2025, 1, 26)  # Sunday + Republic Day (both reasons)

# Datetimes in UTC corresponding to key IST moments on TRADING_DATE
BEFORE_OPEN_UTC = datetime(2025, 1, 15, 3, 0, tzinfo=UTC)  # 08:30 IST
PRE_OPEN_UTC = datetime(2025, 1, 15, 3, 34, tzinfo=UTC)  # 09:04 IST
PRE_OPEN_MATCH_UTC = datetime(2025, 1, 15, 3, 40, tzinfo=UTC)  # 09:10 IST
NORMAL_UTC = datetime(2025, 1, 15, 5, 30, tzinfo=UTC)  # 11:00 IST
CLOSING_UTC = datetime(2025, 1, 15, 10, 5, tzinfo=UTC)  # 15:35 IST
POST_CLOSE_UTC = datetime(2025, 1, 15, 10, 15, tzinfo=UTC)  # 15:45 IST
AFTER_CLOSE_UTC = datetime(2025, 1, 15, 11, 30, tzinfo=UTC)  # 17:00 IST


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def null_holiday_provider() -> NullHolidayProvider:
    """A holiday provider that records no holidays."""
    return NullHolidayProvider()


@pytest.fixture
def republic_day_provider() -> SetHolidayProvider:
    """Holiday provider with Republic Day (Jan 26) and Holi (Mar 14) 2025."""
    return SetHolidayProvider(holidays=frozenset({date(2025, 1, 26), date(2025, 3, 14)}))


@pytest.fixture
def nse_calendar(null_holiday_provider: NullHolidayProvider) -> NSETradingCalendar:
    """NSE calendar with no holidays (weekdays only)."""
    return NSETradingCalendar(holiday_provider=null_holiday_provider)


@pytest.fixture
def nse_calendar_with_holidays(
    republic_day_provider: SetHolidayProvider,
) -> NSETradingCalendar:
    """NSE calendar with Republic Day and Holi as holidays."""
    return NSETradingCalendar(holiday_provider=republic_day_provider)


@pytest.fixture
def clock_at_normal() -> FrozenClock:
    """Clock frozen at 11:00 IST on Jan 15, 2025 (during NORMAL session)."""
    return FrozenClock(NORMAL_UTC)


@pytest.fixture
def manual_clock() -> ManualClock:
    """Manual clock starting at 11:00 IST on Jan 15, 2025."""
    return ManualClock(NORMAL_UTC)


@pytest.fixture
def nse_session_service(
    nse_calendar: NSETradingCalendar,
    clock_at_normal: FrozenClock,
) -> NSESessionService:
    """NSE session service with no-holiday calendar and a clock at 11:00 IST."""
    return NSESessionService(calendar=nse_calendar, clock=clock_at_normal)


@pytest.fixture
def nse_expiry_calculator(nse_calendar: NSETradingCalendar) -> NSEExpiryCalculator:
    """NSE expiry calculator using the no-holiday calendar."""
    return NSEExpiryCalculator(calendar=nse_calendar)
