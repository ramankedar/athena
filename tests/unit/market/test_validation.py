"""Unit tests for market domain validation utilities."""

from __future__ import annotations

from datetime import time
from decimal import Decimal

import pytest

from athena.market.capabilities import (
    NSE_EQ_CAPABILITIES,
    NSE_EQ_ORDER_CAPS,
    OrderCapabilities,
    OrderType,
    OrderValidity,
)
from athena.market.exchange import NSE
from athena.market.models import MarketId, MarketTimezone
from athena.market.rules import (
    SEBI_NSE_CIRCUIT_BREAKER,
    CircuitBreakerLevel,
    CircuitBreakerThreshold,
    PriceBandConfig,
    PriceBandType,
)
from athena.market.sessions import DailySchedule, MarketSessionType, SessionWindow
from athena.market.validation import (
    ValidationResult,
    validate_circuit_breaker_config,
    validate_circuit_breaker_threshold,
    validate_daily_schedule,
    validate_exchange_metadata,
    validate_market_capabilities,
    validate_order_capabilities,
    validate_price_band_config,
    validate_session_window,
)

IST = MarketTimezone("Asia/Kolkata")


class TestValidationResult:
    def test_ok(self) -> None:
        r = ValidationResult.ok()
        assert r.is_valid is True
        assert r.failures == ()

    def test_failed(self) -> None:
        r = ValidationResult.failed("msg1", "msg2")
        assert r.is_valid is False
        assert len(r.failures) == 2

    def test_merge_ok_ok(self) -> None:
        assert ValidationResult.ok().merge(ValidationResult.ok()).is_valid is True

    def test_merge_ok_failed(self) -> None:
        merged = ValidationResult.ok().merge(ValidationResult.failed("err"))
        assert not merged.is_valid
        assert "err" in merged.failures

    def test_merge_failed_failed(self) -> None:
        r1 = ValidationResult.failed("err1")
        r2 = ValidationResult.failed("err2")
        merged = r1.merge(r2)
        assert not merged.is_valid
        assert len(merged.failures) == 2


class TestValidateExchangeMetadata:
    def test_valid_nse(self) -> None:
        assert validate_exchange_metadata(NSE).is_valid

    def test_implausible_year_caught_at_construction(self) -> None:
        from athena.market.exceptions import InvalidMarketIdError
        from athena.market.exchange import ExchangeMetadata
        from athena.market.models import CountryCode, MarketCurrency

        with pytest.raises(InvalidMarketIdError, match="predates"):
            ExchangeMetadata(
                id=MarketId("OLD"),
                name="Old Exchange",
                short_name="OE",
                country=CountryCode("IN"),
                primary_currency=MarketCurrency("INR"),
                timezone=IST,
                regulator="SEBI",
                established_year=1000,
            )


class TestValidateSessionWindow:
    def test_valid_window(self) -> None:
        w = SessionWindow(MarketSessionType.CONTINUOUS, time(9, 15), time(15, 30))
        assert validate_session_window(w).is_valid

    def test_one_minute_window(self) -> None:
        w = SessionWindow(MarketSessionType.PRE_OPEN, time(9, 0), time(9, 1))
        assert validate_session_window(w).is_valid

    def test_invalid_zero_duration_via_duck_type(self) -> None:
        """Bypasses frozen dataclass to test validator failure path."""

        class FakeWindow:
            session_type = MarketSessionType.CONTINUOUS
            start_time = time(9, 0)
            end_time = time(9, 0)  # equal → zero duration
            duration_minutes = 0

        result = validate_session_window(FakeWindow())  # type: ignore[arg-type]
        assert not result.is_valid


class TestValidateDailySchedule:
    def test_valid_nse_schedule(self, nse_daily_schedule: DailySchedule) -> None:
        assert validate_daily_schedule(nse_daily_schedule).is_valid

    def test_single_session_valid(self) -> None:
        schedule = DailySchedule(
            sessions=(SessionWindow(MarketSessionType.CONTINUOUS, time(9, 0), time(15, 30)),),
            timezone=IST,
        )
        assert validate_daily_schedule(schedule).is_valid

    def test_schedule_with_invalid_window_via_duck_type(self) -> None:
        """Exercise the per-window failure path in validate_daily_schedule."""

        class FakeWindow:
            session_type = MarketSessionType.CONTINUOUS
            start_time = time(15, 30)
            end_time = time(9, 0)  # invalid order
            duration_minutes = -1

        class FakeSchedule:
            sessions = (FakeWindow(),)
            timezone = IST

        result = validate_daily_schedule(FakeSchedule())  # type: ignore[arg-type]
        assert not result.is_valid


class TestValidatePriceBandConfig:
    def test_valid_static(self) -> None:
        config = PriceBandConfig(
            band_type=PriceBandType.STATIC,
            upper_limit_pct=Decimal("20"),
            lower_limit_pct=Decimal("20"),
        )
        assert validate_price_band_config(config).is_valid

    def test_valid_none_type(self) -> None:
        config = PriceBandConfig(band_type=PriceBandType.NONE)
        assert validate_price_band_config(config).is_valid

    def test_static_with_no_limits_caught_at_construction(self) -> None:
        from athena.market.exceptions import InvalidMarketIdError

        with pytest.raises(InvalidMarketIdError):
            PriceBandConfig(band_type=PriceBandType.STATIC)

    def test_validator_failure_via_duck_type(self) -> None:
        """Exercise validate_price_band_config failure path."""

        class FakeConfig:
            band_type = PriceBandType.STATIC
            upper_limit_pct = None
            lower_limit_pct = None
            reference_price_field = "previous_close"

        result = validate_price_band_config(FakeConfig())  # type: ignore[arg-type]
        assert not result.is_valid

    def test_validator_negative_limit_via_duck_type(self) -> None:
        class FakeConfig:
            band_type = PriceBandType.STATIC
            upper_limit_pct = Decimal("-5")
            lower_limit_pct = None
            reference_price_field = "previous_close"

        result = validate_price_band_config(FakeConfig())  # type: ignore[arg-type]
        assert not result.is_valid


class TestValidateCircuitBreakerThreshold:
    def test_valid_threshold(self) -> None:
        t = CircuitBreakerThreshold(CircuitBreakerLevel.LEVEL_1, Decimal("10"), 45)
        assert validate_circuit_breaker_threshold(t).is_valid

    def test_valid_rest_of_day_threshold(self) -> None:
        t = CircuitBreakerThreshold(CircuitBreakerLevel.LEVEL_3, Decimal("20"), None)
        assert validate_circuit_breaker_threshold(t).is_valid

    def test_failure_via_duck_type_negative_pct(self) -> None:
        class FakeThreshold:
            level = CircuitBreakerLevel.LEVEL_1
            trigger_decline_pct = Decimal("0")
            halt_duration_minutes = 45

        result = validate_circuit_breaker_threshold(FakeThreshold())  # type: ignore[arg-type]
        assert not result.is_valid

    def test_failure_via_duck_type_zero_halt(self) -> None:
        class FakeThreshold:
            level = CircuitBreakerLevel.LEVEL_1
            trigger_decline_pct = Decimal("10")
            halt_duration_minutes = 0

        result = validate_circuit_breaker_threshold(FakeThreshold())  # type: ignore[arg-type]
        assert not result.is_valid


class TestValidateCircuitBreakerConfig:
    def test_valid_sebi_config_is_valid(self) -> None:
        assert validate_circuit_breaker_config(SEBI_NSE_CIRCUIT_BREAKER).is_valid

    def test_non_ascending_via_duck_type(self) -> None:
        from athena.market.rules import CircuitBreakerLevel

        class FakeThresholdHigh:
            level = CircuitBreakerLevel.LEVEL_1
            trigger_decline_pct = Decimal("20")
            halt_duration_minutes = 45

        class FakeThresholdLow:
            level = CircuitBreakerLevel.LEVEL_2
            trigger_decline_pct = Decimal("10")
            halt_duration_minutes = 90

        class FakeConfig:
            exchange_id = MarketId("TEST")
            reference_index_id = MarketId("IDX")
            thresholds = (FakeThresholdHigh(), FakeThresholdLow())

        result = validate_circuit_breaker_config(FakeConfig())  # type: ignore[arg-type]
        assert not result.is_valid


class TestValidateMarketCapabilities:
    def test_valid_nse_eq_caps(self) -> None:
        assert validate_market_capabilities(NSE_EQ_CAPABILITIES).is_valid

    def test_empty_asset_classes_via_duck_type(self) -> None:
        class FakeCaps:
            exchange_id = MarketId("NSE")
            supported_asset_classes: frozenset[str] = frozenset()
            order_capabilities = NSE_EQ_ORDER_CAPS

        result = validate_market_capabilities(FakeCaps())  # type: ignore[arg-type]
        assert not result.is_valid


class TestValidateOrderCapabilities:
    def test_valid_nse_order_caps(self) -> None:
        assert validate_order_capabilities(NSE_EQ_ORDER_CAPS).is_valid

    def test_invalid_default_not_in_supported(self) -> None:
        from athena.market.exceptions import InvalidMarketIdError

        with pytest.raises(InvalidMarketIdError):
            OrderCapabilities(
                supported_order_types=frozenset({OrderType.MARKET}),
                supported_validities=frozenset({OrderValidity.DAY}),
                default_order_type=OrderType.LIMIT,
            )

    def test_empty_types_via_duck_type(self) -> None:
        class FakeCaps:
            supported_order_types: frozenset[OrderType] = frozenset()
            supported_validities: frozenset[OrderValidity] = frozenset({OrderValidity.DAY})
            default_order_type = OrderType.LIMIT
            max_order_value = None
            min_order_value = None

        result = validate_order_capabilities(FakeCaps())  # type: ignore[arg-type]
        assert not result.is_valid

    def test_default_not_in_supported_via_duck_type(self) -> None:
        class FakeCaps:
            supported_order_types = frozenset({OrderType.MARKET})
            supported_validities = frozenset({OrderValidity.DAY})
            default_order_type = OrderType.LIMIT  # not in supported
            max_order_value = None
            min_order_value = None

        result = validate_order_capabilities(FakeCaps())  # type: ignore[arg-type]
        assert not result.is_valid
