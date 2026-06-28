"""Timezone constants and conversion utilities.

Defines the two timezones used throughout Athena:

- ``UTC``: ``datetime.timezone.utc`` — the canonical internal representation.
  All datetimes stored in the database, passed between engines, and logged
  are in UTC.

- ``IST``: ``zoneinfo.ZoneInfo("Asia/Kolkata")`` — Indian Standard Time,
  UTC+05:30. Used only at the presentation layer and when computing session
  times from their IST-based definitions.

Why ``zoneinfo`` over ``pytz`` or ``dateutil``?
    ``zoneinfo`` is Python 3.9+ stdlib. ``pytz`` is deprecated. ``dateutil``
    adds external dependency weight. ``zoneinfo`` handles DST correctly
    (irrelevant for IST, which has no DST, but matters for future multi-exchange
    support). ``tzdata`` is added as a runtime dependency to ensure the IANA
    timezone database is available in environments without a system tzdb
    (e.g. minimal Alpine Linux images, Windows).
"""

from __future__ import annotations

from datetime import UTC, datetime, timezone
from zoneinfo import ZoneInfo

from athena.time.exceptions import NaiveDatetimeError

UTC: timezone = UTC
"""``datetime.timezone.utc`` — canonical internal timezone for all Athena datetimes."""

IST: ZoneInfo = ZoneInfo("Asia/Kolkata")
"""``ZoneInfo("Asia/Kolkata")`` — Indian Standard Time (UTC+05:30)."""


def is_aware(dt: datetime) -> bool:
    """Return ``True`` if ``dt`` is timezone-aware.

    A datetime is aware when its ``tzinfo`` attribute is set and
    ``tzinfo.utcoffset(dt)`` returns a non-``None`` value.

    Args:
        dt: The datetime to inspect.

    Returns:
        ``True`` for timezone-aware datetimes; ``False`` for naive ones.
    """
    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None


def require_aware(dt: datetime) -> datetime:
    """Assert that ``dt`` is timezone-aware and return it unchanged.

    This is the standard boundary check: every public function in the time
    domain calls this on any incoming ``datetime`` before doing any work.

    Args:
        dt: The datetime to validate.

    Returns:
        ``dt`` unchanged when it is timezone-aware.

    Raises:
        NaiveDatetimeError: If ``dt`` is timezone-naive.
    """
    if not is_aware(dt):
        raise NaiveDatetimeError(str(dt))
    return dt


def to_utc(dt: datetime) -> datetime:
    """Convert a timezone-aware datetime to UTC.

    Args:
        dt: A timezone-aware datetime in any timezone.

    Returns:
        An equivalent ``datetime`` with ``tzinfo == datetime.timezone.utc``.

    Raises:
        NaiveDatetimeError: If ``dt`` is timezone-naive.
    """
    require_aware(dt)
    return dt.astimezone(UTC)


def to_ist(dt: datetime) -> datetime:
    """Convert a timezone-aware datetime to IST (Asia/Kolkata).

    Args:
        dt: A timezone-aware datetime in any timezone.

    Returns:
        An equivalent ``datetime`` with ``tzinfo == ZoneInfo("Asia/Kolkata")``.

    Raises:
        NaiveDatetimeError: If ``dt`` is timezone-naive.
    """
    require_aware(dt)
    return dt.astimezone(IST)


def now_utc() -> datetime:
    """Return the current time as a UTC-aware datetime.

    This function is a thin convenience wrapper used only in contexts where
    dependency injection of a clock is impractical (e.g. log timestamps).
    All business logic must use a ``ClockProtocol`` instead.

    Returns:
        The current UTC datetime.
    """
    return datetime.now(UTC)


def now_ist() -> datetime:
    """Return the current time as an IST-aware datetime.

    Returns:
        The current IST datetime.
    """
    return datetime.now(IST)
