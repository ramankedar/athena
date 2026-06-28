"""Clock service implementations.

The rule: ``datetime.now()`` is called in exactly one place in the entire
Athena codebase — inside ``SystemClock.now()``. All other time-dependent code
accepts a ``ClockProtocol`` and delegates to it.

Four implementations are provided:

- ``SystemClock``   — wraps the real wall clock; used in production.
- ``FrozenClock``   — returns a fixed instant; the standard test double.
- ``ManualClock``   — can be advanced step-by-step; for scenario testing.
- ``OffsetClock``   — applies a fixed timedelta to the system clock; useful
  for testing future-date scenarios without modifying test fixtures.

All implementations return UTC-aware datetimes from ``now()`` and IST-based
calendar dates from ``today()``.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from athena.time.exceptions import NaiveDatetimeError
from athena.time.timezone import IST, UTC


class SystemClock:
    """Production clock backed by the system wall clock.

    ``now()`` delegates to ``datetime.now(UTC)`` — this is the only place
    in the codebase that is permitted to call ``datetime.now()``.
    """

    def now(self) -> datetime:
        """Return the current UTC moment.

        Returns:
            ``datetime.now(UTC)`` — a timezone-aware UTC datetime.
        """
        return datetime.now(UTC)

    def today(self) -> date:
        """Return today's date in IST (Asia/Kolkata).

        The date is resolved in IST rather than UTC to match the exchange's
        local date, which may differ from the UTC date between 18:30-24:00 UTC.

        Returns:
            Today's date in the IST timezone.
        """
        return self.now().astimezone(IST).date()


class FrozenClock:
    """Test double that returns a fixed, predetermined instant.

    Use this in unit tests to make all time-dependent assertions deterministic.

    Args:
        fixed_time: The datetime this clock always returns. Must be
            timezone-aware.

    Raises:
        NaiveDatetimeError: If ``fixed_time`` is timezone-naive.

    Example::

        from datetime import datetime, UTC
        clock = FrozenClock(datetime(2025, 1, 15, 9, 15, tzinfo=UTC))
        assert clock.now() == datetime(2025, 1, 15, 9, 15, tzinfo=UTC)
    """

    def __init__(self, fixed_time: datetime) -> None:
        if fixed_time.tzinfo is None:
            raise NaiveDatetimeError(str(fixed_time), clock="FrozenClock")
        self._fixed_time = fixed_time

    def now(self) -> datetime:
        """Return the fixed datetime this clock was constructed with.

        Returns:
            The immutable ``fixed_time`` passed at construction.
        """
        return self._fixed_time

    def today(self) -> date:
        """Return the IST date of the frozen instant.

        Returns:
            The date component of ``fixed_time`` in the IST timezone.
        """
        return self._fixed_time.astimezone(IST).date()

    @property
    def fixed_time(self) -> datetime:
        """The datetime this clock is frozen at.

        Returns:
            The fixed datetime.
        """
        return self._fixed_time


class ManualClock:
    """A clock whose current time can be advanced or set manually.

    Unlike ``FrozenClock``, this clock's time is mutable — it can be
    advanced with ``advance()`` or jumped to an exact moment with ``set()``.
    This enables tests that need to observe how the system behaves as time
    progresses through multiple states.

    Args:
        start: The initial datetime. Must be timezone-aware.

    Raises:
        NaiveDatetimeError: If ``start`` is timezone-naive.

    Example::

        clock = ManualClock(datetime(2025, 1, 15, 9, 0, tzinfo=UTC))
        assert clock.now().hour == 9
        clock.advance(timedelta(hours=1))
        assert clock.now().hour == 10
    """

    def __init__(self, start: datetime) -> None:
        if start.tzinfo is None:
            raise NaiveDatetimeError(str(start), clock="ManualClock")
        self._current = start

    def now(self) -> datetime:
        """Return the clock's current time.

        Returns:
            The current datetime of this manual clock.
        """
        return self._current

    def today(self) -> date:
        """Return the IST date of the current clock time.

        Returns:
            The date in IST corresponding to the current clock time.
        """
        return self._current.astimezone(IST).date()

    def advance(self, delta: timedelta) -> None:
        """Advance the clock by the given duration.

        Args:
            delta: Amount of time to move the clock forward. Negative values
                move the clock backward.
        """
        self._current += delta

    def set(self, dt: datetime) -> None:
        """Set the clock to a specific datetime.

        Args:
            dt: The new current time. Must be timezone-aware.

        Raises:
            NaiveDatetimeError: If ``dt`` is timezone-naive.
        """
        if dt.tzinfo is None:
            raise NaiveDatetimeError(str(dt), clock="ManualClock")
        self._current = dt


class OffsetClock:
    """A clock that applies a fixed offset to the system wall clock.

    Useful for testing scenarios where you need time to flow naturally
    (unlike ``FrozenClock``) but offset from the current moment — for
    example, simulating a system running 6 hours ahead.

    Args:
        offset: The timedelta to add to the real wall clock on every call.
            Positive values produce a clock ahead of real time; negative
            values produce one behind.

    Example::

        # Clock that always reports 2 hours into the future
        clock = OffsetClock(timedelta(hours=2))
    """

    def __init__(self, offset: timedelta) -> None:
        self._offset = offset

    def now(self) -> datetime:
        """Return the current wall-clock time plus the configured offset.

        Returns:
            The current UTC datetime adjusted by ``offset``.
        """
        return datetime.now(UTC) + self._offset

    def today(self) -> date:
        """Return the IST date of the offset moment.

        Returns:
            The date in IST corresponding to ``now()``.
        """
        return self.now().astimezone(IST).date()

    @property
    def offset(self) -> timedelta:
        """The timedelta applied to the system clock.

        Returns:
            The configured offset.
        """
        return self._offset
