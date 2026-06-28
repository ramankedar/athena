"""Core primitive value objects for the Market Domain.

Defines the fundamental typed identifiers and value objects used throughout
``athena.market``. These types are intentionally independent of the Asset
Domain (``athena.assets``) and Time Domain (``athena.time``) to preserve
peer-layer isolation.

Types defined here:
    ``MarketId``       — Typed identifier for exchanges, segments, and venues.
    ``CountryCode``    — ISO 3166-1 alpha-2 two-letter country code.
    ``MarketCurrency`` — ISO 4217 three-letter currency code.
    ``MarketTimezone`` — IANA timezone name (validated against the tzdb).
    ``WeeklySchedule`` — Which weekdays a market operates (frozenset of ints).

Design notes:
    - ``MarketId`` uses alphanumeric-plus-underscore format to support
      identifiers like ``"NSE_FO"`` (segment) and ``"NSE"`` (exchange).
    - ``MarketCurrency`` and ``CountryCode`` are re-defined here (they also
      exist in ``athena.assets``) because peer layers must not import from
      each other. The validation logic is identical; the types are independent.
    - ``WeeklySchedule`` uses ``frozenset[int]`` with Python's ``date.weekday()``
      convention (0=Monday, 6=Sunday). This accommodates Sunday-to-Thursday
      exchanges (e.g., Tadawul) without any special-casing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from athena.market.exceptions import InvalidMarketIdError, InvalidScheduleError


@dataclass(frozen=True)
class MarketId:
    """Typed identifier for a market entity (exchange, segment, or venue).

    Accepts uppercase alphanumeric codes and underscores, matching common
    exchange and segment naming conventions.

    Attributes:
        code: The identifier string (e.g. ``"NSE"``, ``"NSE_FO"``).

    Example::

        exchange_id = MarketId("NSE")
        segment_id = MarketId("NSE_FO")
    """

    code: str

    def __post_init__(self) -> None:
        stripped = self.code.strip()
        if not stripped:
            raise InvalidMarketIdError(self.code, reason="MarketId.code must not be empty")
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
        invalid_chars = set(self.code) - allowed
        if invalid_chars:
            raise InvalidMarketIdError(
                self.code,
                reason=(
                    "MarketId.code must contain only uppercase letters, digits, "
                    f"or underscores (invalid: {sorted(invalid_chars)})"
                ),
            )

    def __str__(self) -> str:
        return self.code

    def __repr__(self) -> str:
        return f"MarketId({self.code!r})"


@dataclass(frozen=True)
class CountryCode:
    """ISO 3166-1 alpha-2 two-letter country code.

    Attributes:
        code: Exactly two uppercase letters (e.g. ``"IN"``, ``"US"``).

    Example::

        india = CountryCode("IN")
        usa = CountryCode("US")
    """

    code: str

    def __post_init__(self) -> None:
        if len(self.code) != 2 or not self.code.isalpha() or not self.code.isupper():
            raise InvalidMarketIdError(
                self.code,
                reason="CountryCode must be exactly 2 uppercase letters (ISO 3166-1 alpha-2)",
            )

    def __str__(self) -> str:
        return self.code

    def __repr__(self) -> str:
        return f"CountryCode({self.code!r})"


@dataclass(frozen=True)
class MarketCurrency:
    """ISO 4217 three-letter currency code.

    Attributes:
        code: Exactly three uppercase letters (e.g. ``"INR"``, ``"USD"``).

    Example::

        inr = MarketCurrency("INR")
        usd = MarketCurrency("USD")
    """

    code: str

    def __post_init__(self) -> None:
        if len(self.code) != 3 or not self.code.isalpha() or not self.code.isupper():
            raise InvalidMarketIdError(
                self.code,
                reason="MarketCurrency must be exactly 3 uppercase letters (ISO 4217)",
            )

    def __str__(self) -> str:
        return self.code

    def __repr__(self) -> str:
        return f"MarketCurrency({self.code!r})"


@dataclass(frozen=True)
class MarketTimezone:
    """IANA timezone identifier validated against the system timezone database.

    On construction, the timezone name is verified by attempting to instantiate
    a ``zoneinfo.ZoneInfo`` object. Invalid timezone names raise immediately.

    Attributes:
        name: IANA timezone string (e.g. ``"Asia/Kolkata"``, ``"America/New_York"``).

    Example::

        ist = MarketTimezone("Asia/Kolkata")
        et = MarketTimezone("America/New_York")
    """

    name: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidMarketIdError(self.name, reason="MarketTimezone.name must not be empty")
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        try:
            ZoneInfo(self.name)
        except (KeyError, ZoneInfoNotFoundError) as exc:
            raise InvalidMarketIdError(
                self.name,
                reason=f"Unknown IANA timezone: {self.name!r}",
            ) from exc

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"MarketTimezone({self.name!r})"


@dataclass(frozen=True)
class WeeklySchedule:
    """The set of weekdays on which a market operates.

    Uses Python's ``date.weekday()`` convention: Monday = 0, Sunday = 6.
    A frozenset representation accommodates non-standard trading weeks
    (e.g. Sunday-to-Thursday for Gulf exchanges) without special-casing.

    Attributes:
        trading_days: Frozenset of integers in ``[0, 6]`` indicating which
            days of the week the market is open.

    Class constants:
        MON_FRI: Standard Monday-to-Friday trading week.
        SUN_THU: Sunday-to-Thursday (Gulf exchange convention).
        MON_SAT: Monday-to-Saturday (some commodity markets).

    Example::

        nse_week = WeeklySchedule.MON_FRI
        tadawul_week = WeeklySchedule.SUN_THU
        custom_week = WeeklySchedule(frozenset({0, 1, 2, 3, 4, 5}))  # Mon-Sat
    """

    trading_days: frozenset[int]

    MON_FRI: ClassVar[WeeklySchedule]
    SUN_THU: ClassVar[WeeklySchedule]
    MON_SAT: ClassVar[WeeklySchedule]

    def __post_init__(self) -> None:
        invalid = self.trading_days - frozenset(range(7))
        if invalid:
            raise InvalidScheduleError(
                f"WeeklySchedule.trading_days contains invalid weekday(s): {sorted(invalid)}. "
                "Valid values are 0 (Monday) through 6 (Sunday).",
                invalid_days=sorted(invalid),
            )
        if not self.trading_days:
            raise InvalidScheduleError(
                "WeeklySchedule.trading_days must contain at least one trading day.",
            )

    def trades_on(self, weekday: int) -> bool:
        """Return ``True`` if the market trades on the given weekday.

        Args:
            weekday: Integer weekday (``date.weekday()``: 0=Monday, 6=Sunday).

        Returns:
            ``True`` when ``weekday`` is in this schedule's trading days.
        """
        return weekday in self.trading_days

    @property
    def num_trading_days(self) -> int:
        """Number of trading days per week.

        Returns:
            Count of weekdays in this schedule.
        """
        return len(self.trading_days)

    def __str__(self) -> str:
        names = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
        days = sorted(self.trading_days)
        return "-".join(names.get(d, str(d)) for d in days)


# Class constants — set after class definition
WeeklySchedule.MON_FRI = WeeklySchedule(frozenset({0, 1, 2, 3, 4}))
WeeklySchedule.SUN_THU = WeeklySchedule(frozenset({6, 0, 1, 2, 3}))
WeeklySchedule.MON_SAT = WeeklySchedule(frozenset({0, 1, 2, 3, 4, 5}))


# ── Module-level well-known identifiers ───────────────────────────────────────

#: Timezone for Indian exchanges (NSE, BSE, MCX).
INDIA_TIMEZONE: MarketTimezone = MarketTimezone("Asia/Kolkata")

#: Timezone for US Eastern markets (NYSE, NASDAQ).
US_EASTERN_TIMEZONE: MarketTimezone = MarketTimezone("America/New_York")

#: Timezone for UK markets (LSE).
UK_TIMEZONE: MarketTimezone = MarketTimezone("Europe/London")

#: Indian Rupee currency code.
INR: MarketCurrency = MarketCurrency("INR")

#: US Dollar currency code.
USD: MarketCurrency = MarketCurrency("USD")

#: Indian country code.
INDIA: CountryCode = CountryCode("IN")

#: United States country code.
UNITED_STATES: CountryCode = CountryCode("US")
