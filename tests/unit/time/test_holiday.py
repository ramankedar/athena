"""Unit tests for holiday provider implementations."""

from __future__ import annotations

from datetime import date

from hypothesis import given
from hypothesis import strategies as st

from athena.time.holiday import NullHolidayProvider, SetHolidayProvider

REPUBLIC_DAY = date(2025, 1, 26)
HOLI_2025 = date(2025, 3, 14)
HOLI_2024 = date(2024, 3, 25)


class TestNullHolidayProvider:
    def test_get_holidays_returns_empty_frozenset(self) -> None:
        provider = NullHolidayProvider()
        assert provider.get_holidays(2025) == frozenset()

    def test_get_holidays_empty_for_any_year(self) -> None:
        provider = NullHolidayProvider()
        for year in (2020, 2025, 2030, 9999):
            assert provider.get_holidays(year) == frozenset()

    def test_is_holiday_always_false(self) -> None:
        provider = NullHolidayProvider()
        assert provider.is_holiday(REPUBLIC_DAY) is False
        assert provider.is_holiday(HOLI_2025) is False
        assert provider.is_holiday(date(2025, 12, 31)) is False

    @given(st.dates(min_value=date(2000, 1, 1), max_value=date(2050, 12, 31)))
    def test_is_holiday_always_false_property(self, d: date) -> None:
        provider = NullHolidayProvider()
        assert provider.is_holiday(d) is False


class TestSetHolidayProvider:
    def _provider(self) -> SetHolidayProvider:
        return SetHolidayProvider(holidays=frozenset({REPUBLIC_DAY, HOLI_2025, HOLI_2024}))

    def test_is_holiday_true_for_recorded_date(self) -> None:
        assert self._provider().is_holiday(REPUBLIC_DAY) is True

    def test_is_holiday_false_for_unrecorded_date(self) -> None:
        assert self._provider().is_holiday(date(2025, 1, 27)) is False

    def test_get_holidays_filters_by_year(self) -> None:
        provider = self._provider()
        holidays_2025 = provider.get_holidays(2025)
        assert REPUBLIC_DAY in holidays_2025
        assert HOLI_2025 in holidays_2025
        assert HOLI_2024 not in holidays_2025

    def test_get_holidays_2024(self) -> None:
        provider = self._provider()
        holidays_2024 = provider.get_holidays(2024)
        assert HOLI_2024 in holidays_2024
        assert REPUBLIC_DAY not in holidays_2024

    def test_get_holidays_empty_for_unknown_year(self) -> None:
        provider = self._provider()
        assert provider.get_holidays(1990) == frozenset()

    def test_all_holidays_property(self) -> None:
        provider = self._provider()
        assert provider.all_holidays == frozenset({REPUBLIC_DAY, HOLI_2025, HOLI_2024})

    def test_accepts_set_input(self) -> None:
        provider = SetHolidayProvider(holidays={REPUBLIC_DAY, HOLI_2025})
        assert provider.is_holiday(REPUBLIC_DAY) is True

    def test_duplicates_are_deduplicated(self) -> None:
        provider = SetHolidayProvider(holidays=frozenset({REPUBLIC_DAY, REPUBLIC_DAY}))
        assert len(provider.get_holidays(2025)) == 1

    def test_empty_provider(self) -> None:
        provider = SetHolidayProvider(holidays=frozenset())
        assert provider.get_holidays(2025) == frozenset()
        assert provider.is_holiday(REPUBLIC_DAY) is False
