"""Holiday provider implementations.

A ``HolidayProviderProtocol`` is the source of exchange holiday information.
The trading calendar (``athena.time.calendar``) depends on this protocol but
never on a specific implementation, so the data source can be swapped without
touching the calendar logic.

Two implementations are provided:

- ``NullHolidayProvider``:  Returns no holidays. Safe default when no holiday
  data has been loaded. The system operates with weekends-only exclusions.

- ``SetHolidayProvider``:   Backed by an in-memory ``frozenset[date]``. Suitable
  for unit tests, for pre-loaded static datasets, and for environments where
  holiday data is injected at startup rather than fetched from an API.

Future implementations (not in this sprint):
- ``NSEHolidayProvider``    — loads from NSE's official holiday API.
- ``DatabaseHolidayProvider`` — queries the TimescaleDB holiday table.
- ``CSVHolidayProvider``    — reads from a CSV/TOML file.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date


class NullHolidayProvider:
    """Holiday provider that recognises no holidays.

    This is the safe default: when no holiday data is available, the
    trading calendar treats all weekdays as trading days. The system
    degrades gracefully rather than refusing to operate.

    Inject this provider during development, or when holiday data has
    not yet been loaded for the current year.

    Example::

        provider = NullHolidayProvider()
        assert provider.get_holidays(2025) == frozenset()
        assert provider.is_holiday(date(2025, 1, 26)) is False
    """

    def get_holidays(self, year: int) -> frozenset[date]:
        """Return an empty set for any year.

        Args:
            year: The calendar year (ignored).

        Returns:
            An empty ``frozenset``.
        """
        return frozenset()

    def is_holiday(self, d: date) -> bool:
        """Always return ``False``.

        Args:
            d: The date to check (ignored).

        Returns:
            ``False`` unconditionally.
        """
        return False


class SetHolidayProvider:
    """Holiday provider backed by a fixed in-memory set of dates.

    Construct with any iterable of holiday dates. The provider handles
    cross-year lookups correctly via set membership testing.

    Args:
        holidays: An iterable of ``date`` objects representing exchange
            holidays. Duplicates are silently ignored.

    Example::

        from datetime import date
        provider = SetHolidayProvider(
            holidays={
                date(2025, 1, 26),  # Republic Day
                date(2025, 3, 14),  # Holi
                date(2025, 4, 14),  # Dr. Ambedkar Jayanti
            }
        )
        assert provider.is_holiday(date(2025, 1, 26)) is True
        assert provider.is_holiday(date(2025, 1, 27)) is False
        assert len(provider.get_holidays(2025)) == 3
    """

    def __init__(self, holidays: frozenset[date] | set[date]) -> None:
        self._holidays: frozenset[date] = frozenset(holidays)

    def get_holidays(self, year: int) -> frozenset[date]:
        """Return all holidays in the given calendar year.

        Args:
            year: The calendar year to filter by.

        Returns:
            A ``frozenset`` of holiday dates whose year matches ``year``.
            Empty frozenset if no holidays are recorded for that year.
        """
        return frozenset(d for d in self._holidays if d.year == year)

    def is_holiday(self, d: date) -> bool:
        """Return ``True`` if ``d`` is a recorded holiday.

        Args:
            d: The date to check.

        Returns:
            ``True`` when ``d`` is in the holiday set; ``False`` otherwise.
        """
        return d in self._holidays

    @property
    def all_holidays(self) -> frozenset[date]:
        """All holidays across all years in this provider.

        Returns:
            The complete set of holiday dates.
        """
        return self._holidays
