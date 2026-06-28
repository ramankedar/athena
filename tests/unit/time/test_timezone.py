"""Unit tests for timezone utilities."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hypothesis import given
from hypothesis import strategies as st
import pytest

from athena.time.exceptions import NaiveDatetimeError
from athena.time.timezone import IST, UTC, is_aware, require_aware, to_ist, to_utc


class TestConstants:
    def test_utc_is_zero_offset(self) -> None:
        dt = datetime(2025, 1, 15, 9, 0, tzinfo=UTC)
        assert dt.utcoffset() == timedelta(0)

    def test_ist_is_plus_5_30(self) -> None:
        dt = datetime(2025, 1, 15, 9, 0, tzinfo=IST)
        assert dt.utcoffset() == timedelta(hours=5, minutes=30)

    def test_ist_zoneinfo_name(self) -> None:
        assert IST.key == "Asia/Kolkata"  # type: ignore[union-attr]


class TestIsAware:
    def test_returns_true_for_utc_datetime(self) -> None:
        assert is_aware(datetime(2025, 1, 15, tzinfo=UTC)) is True

    def test_returns_true_for_ist_datetime(self) -> None:
        assert is_aware(datetime(2025, 1, 15, tzinfo=IST)) is True

    def test_returns_false_for_naive_datetime(self) -> None:
        assert is_aware(datetime(2025, 1, 15)) is False

    def test_fixed_offset_is_aware(self) -> None:
        tz = timezone(timedelta(hours=5, minutes=30))
        assert is_aware(datetime(2025, 1, 15, tzinfo=tz)) is True


class TestRequireAware:
    def test_returns_aware_datetime_unchanged(self) -> None:
        dt = datetime(2025, 1, 15, 9, 15, tzinfo=UTC)
        assert require_aware(dt) is dt

    def test_raises_on_naive_datetime(self) -> None:
        with pytest.raises(NaiveDatetimeError):
            require_aware(datetime(2025, 1, 15, 9, 15))

    def test_error_contains_datetime_string(self) -> None:
        naive = datetime(2025, 1, 15, 9, 15)
        with pytest.raises(NaiveDatetimeError) as exc_info:
            require_aware(naive)
        assert "2025-01-15" in str(exc_info.value)


class TestToUtc:
    def test_utc_datetime_unchanged(self) -> None:
        dt = datetime(2025, 1, 15, 3, 45, tzinfo=UTC)
        result = to_utc(dt)
        assert result == dt
        assert result.tzinfo == UTC

    def test_converts_ist_to_utc(self) -> None:
        # 09:15 IST = 03:45 UTC
        ist_dt = datetime(2025, 1, 15, 9, 15, tzinfo=IST)
        utc_dt = to_utc(ist_dt)
        assert utc_dt == datetime(2025, 1, 15, 3, 45, tzinfo=UTC)
        assert utc_dt.tzinfo == UTC

    def test_raises_on_naive_datetime(self) -> None:
        with pytest.raises(NaiveDatetimeError):
            to_utc(datetime(2025, 1, 15, 9, 15))

    def test_ist_to_utc_offset_is_5h30m(self) -> None:
        from datetime import timedelta

        ist_dt = datetime(2025, 1, 15, 12, 0, tzinfo=IST)
        utc_dt = to_utc(ist_dt)
        # Compare the naive components; IST = UTC + 5:30
        naive_diff = ist_dt.replace(tzinfo=None) - utc_dt.replace(tzinfo=None)
        assert naive_diff == timedelta(hours=5, minutes=30)


class TestToIst:
    def test_utc_converts_to_ist(self) -> None:
        # 03:45 UTC = 09:15 IST
        utc_dt = datetime(2025, 1, 15, 3, 45, tzinfo=UTC)
        ist_dt = to_ist(utc_dt)
        assert ist_dt.hour == 9
        assert ist_dt.minute == 15
        assert ist_dt.tzinfo == IST

    def test_raises_on_naive_datetime(self) -> None:
        with pytest.raises(NaiveDatetimeError):
            to_ist(datetime(2025, 1, 15, 9, 15))

    def test_roundtrip_utc_to_ist_to_utc(self) -> None:
        original = datetime(2025, 6, 15, 10, 30, tzinfo=UTC)
        assert to_utc(to_ist(original)) == original

    def test_roundtrip_ist_to_utc_to_ist(self) -> None:
        original = datetime(2025, 6, 15, 10, 30, tzinfo=IST)
        assert to_ist(to_utc(original)) == original


class TestPropertyBased:
    @given(
        st.datetimes(
            min_value=datetime(2000, 1, 1),
            max_value=datetime(2050, 12, 31),
            timezones=st.just(UTC),
        )
    )
    def test_to_utc_roundtrip(self, dt: datetime) -> None:
        assert to_utc(to_ist(dt)) == dt

    @given(
        st.datetimes(
            min_value=datetime(2000, 1, 1),
            max_value=datetime(2050, 12, 31),
            timezones=st.just(IST),
        )
    )
    def test_to_ist_roundtrip(self, dt: datetime) -> None:
        assert to_ist(to_utc(dt)) == dt
