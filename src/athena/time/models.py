"""Immutable value objects for the time domain.

All models are frozen dataclasses: once constructed they cannot be mutated.
This makes them safe to pass between engines without defensive copying and
allows them to be used as dictionary keys or set members.

Design notes:
    - ``TimeRange`` stores UTC datetimes internally and validates on construction.
    - ``ExpiryInfo`` is a value object representing a single expiry event.
    - ``ExpiryType`` and ``WeeklyExpiryDay`` are pure domain enumerations with
      no behaviour beyond their values.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import TYPE_CHECKING

from athena.time.exceptions import NaiveDatetimeError

if TYPE_CHECKING:
    from datetime import date, datetime, timedelta


class ExpiryType(StrEnum):
    """Classification of a derivative contract expiry.

    Attributes:
        WEEKLY:    Expires on a fixed weekday each week (e.g. NIFTY — Thursday).
        MONTHLY:   Expires on the last Thursday of each calendar month.
        QUARTERLY: Expires at the end of each calendar quarter (planned).
        YEARLY:    Annual expiry (planned — commodity and long-dated options).
    """

    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class WeeklyExpiryDay(IntEnum):
    """Day of the week on which weekly derivatives expire.

    Values match Python's ``date.weekday()`` convention (Monday = 0).

    Attributes:
        MONDAY:    ``date.weekday() == 0``
        TUESDAY:   ``date.weekday() == 1`` — SENSEX weekly expiry day.
        WEDNESDAY: ``date.weekday() == 2``
        THURSDAY:  ``date.weekday() == 3`` — NIFTY weekly expiry day.
        FRIDAY:    ``date.weekday() == 4``
    """

    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4


@dataclass(frozen=True)
class TimeRange:
    """An inclusive time range bounded by two timezone-aware UTC datetimes.

    ``start`` and ``end`` are stored as-is; callers are responsible for
    providing consistent timezones. Both bounds must be timezone-aware.

    Attributes:
        start: Inclusive lower bound of the range (timezone-aware).
        end:   Inclusive upper bound of the range (timezone-aware).

    Raises:
        NaiveDatetimeError: If either ``start`` or ``end`` is timezone-naive.
        ValueError: If ``start`` is after ``end``.

    Example::

        from datetime import UTC, datetime
        r = TimeRange(
            start=datetime(2025, 1, 15, 9, 15, tzinfo=UTC),
            end=datetime(2025, 1, 15, 15, 30, tzinfo=UTC),
        )
        assert r.contains(datetime(2025, 1, 15, 12, 0, tzinfo=UTC))
    """

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start.tzinfo is None:
            raise NaiveDatetimeError(str(self.start), field="start")
        if self.end.tzinfo is None:
            raise NaiveDatetimeError(str(self.end), field="end")
        if self.start > self.end:
            raise ValueError(f"TimeRange.start must be <= end: {self.start!r} > {self.end!r}")

    def contains(self, dt: datetime) -> bool:
        """Return ``True`` if ``dt`` falls within this range (inclusive on both ends).

        Args:
            dt: The datetime to test. Must be timezone-aware.

        Returns:
            ``True`` when ``self.start <= dt <= self.end``.
        """
        return self.start <= dt <= self.end

    @property
    def duration(self) -> timedelta:
        """Elapsed time between ``start`` and ``end``.

        Returns:
            A ``timedelta`` representing ``end - start``.
        """
        return self.end - self.start

    def overlaps(self, other: TimeRange) -> bool:
        """Return ``True`` if this range overlaps with ``other``.

        Two ranges overlap when one starts before the other ends and
        vice versa.

        Args:
            other: The other ``TimeRange`` to test against.

        Returns:
            ``True`` when the ranges share at least one instant.
        """
        return self.start <= other.end and other.start <= self.end


@dataclass(frozen=True)
class ExpiryInfo:
    """A single derivative contract expiry event.

    Attributes:
        date:            The expiry date (calendar date, not datetime).
        expiry_type:     Weekly, monthly, quarterly, or yearly.
        exchange:        Exchange on which the instrument is listed (e.g. ``"NSE"``).
        instrument_name: Optional human-readable name (e.g. ``"NIFTY"``).

    Example::

        from datetime import date
        expiry = ExpiryInfo(
            date=date(2025, 1, 30),
            expiry_type=ExpiryType.MONTHLY,
            exchange="NSE",
            instrument_name="NIFTY",
        )
    """

    date: date
    expiry_type: ExpiryType
    exchange: str
    instrument_name: str | None = None

    def __str__(self) -> str:
        name = f" ({self.instrument_name})" if self.instrument_name else ""
        return f"{self.exchange} {self.expiry_type.value} expiry{name}: {self.date.isoformat()}"
