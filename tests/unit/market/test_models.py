"""Unit tests for market domain primitive value objects."""

from __future__ import annotations

import dataclasses

import pytest

from athena.market.exceptions import InvalidMarketIdError, InvalidScheduleError
from athena.market.models import (
    INDIA,
    INDIA_TIMEZONE,
    INR,
    UNITED_STATES,
    US_EASTERN_TIMEZONE,
    USD,
    CountryCode,
    MarketCurrency,
    MarketId,
    MarketTimezone,
    WeeklySchedule,
)


class TestMarketId:
    def test_valid_construction(self) -> None:
        mid = MarketId("NSE")
        assert mid.code == "NSE"

    def test_valid_with_underscore(self) -> None:
        mid = MarketId("NSE_FO")
        assert mid.code == "NSE_FO"

    def test_valid_with_digits(self) -> None:
        mid = MarketId("MCX2")
        assert mid.code == "MCX2"

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError, match="empty"):
            MarketId("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError):
            MarketId("   ")

    def test_lowercase_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError, match="uppercase"):
            MarketId("nse")

    def test_hyphen_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError):
            MarketId("NSE-FO")

    def test_str(self) -> None:
        assert str(MarketId("NSE")) == "NSE"

    def test_repr(self) -> None:
        assert "'NSE'" in repr(MarketId("NSE"))

    def test_equality(self) -> None:
        assert MarketId("NSE") == MarketId("NSE")
        assert MarketId("NSE") != MarketId("BSE")

    def test_is_frozen(self) -> None:
        mid = MarketId("NSE")
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            mid.code = "BSE"  # type: ignore[misc]

    def test_hashable(self) -> None:
        mapping = {MarketId("NSE"): "nse"}
        assert mapping[MarketId("NSE")] == "nse"


class TestCountryCode:
    def test_valid_india(self) -> None:
        cc = CountryCode("IN")
        assert cc.code == "IN"

    def test_valid_us(self) -> None:
        assert CountryCode("US").code == "US"

    def test_str(self) -> None:
        assert str(CountryCode("IN")) == "IN"

    def test_too_short_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError):
            CountryCode("I")

    def test_too_long_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError):
            CountryCode("IND")

    def test_lowercase_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError):
            CountryCode("in")

    def test_is_frozen(self) -> None:
        cc = CountryCode("IN")
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            cc.code = "US"  # type: ignore[misc]


class TestMarketCurrency:
    def test_valid_inr(self) -> None:
        assert MarketCurrency("INR").code == "INR"

    def test_str(self) -> None:
        assert str(MarketCurrency("USD")) == "USD"

    def test_too_short_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError):
            MarketCurrency("IN")

    def test_too_long_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError):
            MarketCurrency("INRR")

    def test_lowercase_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError):
            MarketCurrency("inr")

    def test_digits_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError):
            MarketCurrency("1NR")


class TestMarketTimezone:
    def test_valid_ist(self) -> None:
        tz = MarketTimezone("Asia/Kolkata")
        assert tz.name == "Asia/Kolkata"

    def test_valid_us_eastern(self) -> None:
        tz = MarketTimezone("America/New_York")
        assert tz.name == "America/New_York"

    def test_str(self) -> None:
        assert str(MarketTimezone("Asia/Kolkata")) == "Asia/Kolkata"

    def test_repr(self) -> None:
        assert "Asia/Kolkata" in repr(MarketTimezone("Asia/Kolkata"))

    def test_invalid_timezone_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError, match="Unknown IANA"):
            MarketTimezone("Invalid/Timezone")

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError, match="empty"):
            MarketTimezone("")


class TestWeeklySchedule:
    def test_mon_fri_constant(self) -> None:
        assert WeeklySchedule.MON_FRI.trading_days == frozenset({0, 1, 2, 3, 4})

    def test_sun_thu_constant(self) -> None:
        assert WeeklySchedule.SUN_THU.trading_days == frozenset({6, 0, 1, 2, 3})

    def test_mon_sat_constant(self) -> None:
        assert WeeklySchedule.MON_SAT.num_trading_days == 6

    def test_trades_on_true(self) -> None:
        assert WeeklySchedule.MON_FRI.trades_on(0) is True  # Monday

    def test_trades_on_false(self) -> None:
        assert WeeklySchedule.MON_FRI.trades_on(5) is False  # Saturday

    def test_num_trading_days(self) -> None:
        assert WeeklySchedule.MON_FRI.num_trading_days == 5

    def test_invalid_weekday_raises(self) -> None:
        with pytest.raises(InvalidScheduleError, match="invalid weekday"):
            WeeklySchedule(frozenset({0, 1, 7}))

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidScheduleError, match="at least one"):
            WeeklySchedule(frozenset())

    def test_str_representation(self) -> None:
        s = str(WeeklySchedule.MON_FRI)
        assert "Mon" in s
        assert "Fri" in s


class TestModuleLevelConstants:
    def test_india_country(self) -> None:
        assert INDIA.code == "IN"

    def test_united_states_country(self) -> None:
        assert UNITED_STATES.code == "US"

    def test_inr(self) -> None:
        assert INR.code == "INR"

    def test_usd(self) -> None:
        assert USD.code == "USD"

    def test_india_timezone(self) -> None:
        assert INDIA_TIMEZONE.name == "Asia/Kolkata"

    def test_us_eastern_timezone(self) -> None:
        assert US_EASTERN_TIMEZONE.name == "America/New_York"
