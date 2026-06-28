"""Athena Time Domain — Sprint 2.

Single source of truth for all temporal logic across the Athena platform.
No engine should call ``datetime.now()`` directly or compute trading days,
sessions, or expiries inline. All temporal operations must go through this
domain.

Public API::

    from athena.time import (
        # Timezone constants
        UTC, IST, to_utc, to_ist, require_aware,

        # Clock implementations
        SystemClock, FrozenClock, ManualClock, OffsetClock,

        # Holiday providers
        NullHolidayProvider, SetHolidayProvider,

        # Calendar
        NSETradingCalendar,

        # Session service
        NSESessionService,

        # Business-day arithmetic
        add_trading_days, subtract_trading_days, count_trading_days,
        trading_days_in_month,

        # Expiry calculations
        NSEExpiryCalculator, NIFTY_WEEKLY_EXPIRY_DAY, SENSEX_WEEKLY_EXPIRY_DAY,

        # Models
        ExpiryType, WeeklyExpiryDay, ExpiryInfo, TimeRange,

        # Interfaces (type hints)
        ClockProtocol, HolidayProviderProtocol, TradingCalendarProtocol,
        SessionServiceProtocol, ExpiryCalculatorProtocol,

        # Exceptions
        TimeError, NaiveDatetimeError, NonTradingDayError,
        NoSessionError, ExpiryCalculationError,
    )
"""

from athena.time.business_day import (
    add_trading_days,
    count_trading_days,
    is_last_trading_day_of_month,
    is_last_trading_day_of_week,
    subtract_trading_days,
    trading_days_in_month,
)
from athena.time.calendar import NSETradingCalendar
from athena.time.clock import FrozenClock, ManualClock, OffsetClock, SystemClock
from athena.time.exceptions import (
    ExpiryCalculationError,
    InvalidTimezoneError,
    NaiveDatetimeError,
    NonTradingDayError,
    NoSessionError,
    TimeError,
)
from athena.time.expiry import (
    NIFTY_WEEKLY_EXPIRY_DAY,
    SENSEX_WEEKLY_EXPIRY_DAY,
    NSEExpiryCalculator,
)
from athena.time.holiday import NullHolidayProvider, SetHolidayProvider
from athena.time.interfaces import (
    ClockProtocol,
    ExpiryCalculatorProtocol,
    HolidayProviderProtocol,
    SessionServiceProtocol,
    TradingCalendarProtocol,
)
from athena.time.models import ExpiryInfo, ExpiryType, TimeRange, WeeklyExpiryDay
from athena.time.session import NSE_SESSION_SCHEDULE, NSESessionService
from athena.time.timezone import IST, UTC, is_aware, require_aware, to_ist, to_utc

__all__ = [
    "IST",
    "NIFTY_WEEKLY_EXPIRY_DAY",
    "NSE_SESSION_SCHEDULE",
    "SENSEX_WEEKLY_EXPIRY_DAY",
    "UTC",
    "ClockProtocol",
    "ExpiryCalculationError",
    "ExpiryCalculatorProtocol",
    "ExpiryInfo",
    "ExpiryType",
    "FrozenClock",
    "HolidayProviderProtocol",
    "InvalidTimezoneError",
    "ManualClock",
    "NSEExpiryCalculator",
    "NSESessionService",
    "NSETradingCalendar",
    "NaiveDatetimeError",
    "NoSessionError",
    "NonTradingDayError",
    "NullHolidayProvider",
    "OffsetClock",
    "SessionServiceProtocol",
    "SetHolidayProvider",
    "SystemClock",
    "TimeError",
    "TimeRange",
    "TradingCalendarProtocol",
    "WeeklyExpiryDay",
    "add_trading_days",
    "count_trading_days",
    "is_aware",
    "is_last_trading_day_of_month",
    "is_last_trading_day_of_week",
    "require_aware",
    "subtract_trading_days",
    "to_ist",
    "to_utc",
    "trading_days_in_month",
]
