"""Unit tests for time-domain exception types."""

from __future__ import annotations

from athena.platform.exceptions import AthenaError
from athena.time.exceptions import (
    ExpiryCalculationError,
    InvalidTimezoneError,
    NaiveDatetimeError,
    NonTradingDayError,
    NoSessionError,
    TimeError,
)


class TestTimeError:
    def test_is_athena_error(self) -> None:
        assert issubclass(TimeError, AthenaError)

    def test_construction_and_message(self) -> None:
        exc = TimeError("time went wrong", component="clock")
        assert "time went wrong" in str(exc)
        assert exc.context["component"] == "clock"


class TestNaiveDatetimeError:
    def test_construction_without_repr(self) -> None:
        exc = NaiveDatetimeError()
        assert "timezone-aware" in str(exc)
        assert exc.error_code == "TIM_001"

    def test_construction_with_repr(self) -> None:
        exc = NaiveDatetimeError("2025-01-15 09:00:00")
        assert "2025-01-15" in str(exc)
        assert exc.context["dt_repr"] == "2025-01-15 09:00:00"

    def test_is_time_error(self) -> None:
        assert issubclass(NaiveDatetimeError, TimeError)

    def test_additional_context(self) -> None:
        exc = NaiveDatetimeError("2025-01-15", clock="FrozenClock")
        assert exc.context["clock"] == "FrozenClock"


class TestInvalidTimezoneError:
    def test_message_contains_timezone_name(self) -> None:
        exc = InvalidTimezoneError("Atlantis/Deep_Sea")
        assert "Atlantis/Deep_Sea" in str(exc)

    def test_error_code(self) -> None:
        exc = InvalidTimezoneError("Bad/Zone")
        assert exc.error_code == "TIM_002"

    def test_timezone_name_in_context(self) -> None:
        exc = InvalidTimezoneError("Foo/Bar")
        assert exc.context["timezone_name"] == "Foo/Bar"

    def test_is_time_error(self) -> None:
        assert issubclass(InvalidTimezoneError, TimeError)


class TestNonTradingDayError:
    def test_message_contains_date(self) -> None:
        exc = NonTradingDayError("2025-01-18")
        assert "2025-01-18" in str(exc)

    def test_default_exchange_is_nse(self) -> None:
        exc = NonTradingDayError("2025-01-18")
        assert exc.context["exchange"] == "NSE"
        assert "NSE" in str(exc)

    def test_custom_exchange(self) -> None:
        exc = NonTradingDayError("2025-01-18", exchange="BSE")
        assert exc.context["exchange"] == "BSE"

    def test_error_code(self) -> None:
        assert NonTradingDayError("2025-01-18").error_code == "TIM_003"

    def test_is_time_error(self) -> None:
        assert issubclass(NonTradingDayError, TimeError)


class TestNoSessionError:
    def test_message_contains_search_from(self) -> None:
        exc = NoSessionError("2025-01-15T03:00:00+00:00")
        assert "2025-01-15" in str(exc)

    def test_default_max_days(self) -> None:
        exc = NoSessionError("2025-01-15")
        assert exc.context["max_days"] == 30

    def test_custom_max_days(self) -> None:
        exc = NoSessionError("2025-01-15", max_days=7)
        assert exc.context["max_days"] == 7

    def test_error_code(self) -> None:
        assert NoSessionError("2025-01-15").error_code == "TIM_004"

    def test_is_time_error(self) -> None:
        assert issubclass(NoSessionError, TimeError)


class TestExpiryCalculationError:
    def test_is_time_error(self) -> None:
        assert issubclass(ExpiryCalculationError, TimeError)

    def test_construction(self) -> None:
        exc = ExpiryCalculationError("could not find expiry", year=2025, month=1)
        assert "could not find expiry" in str(exc)
        assert exc.context["year"] == 2025
