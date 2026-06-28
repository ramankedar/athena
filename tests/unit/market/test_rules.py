"""Unit tests for market rules: price bands, circuit breakers, restrictions."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from athena.market.exceptions import InvalidMarketIdError
from athena.market.models import MarketId
from athena.market.rules import (
    SEBI_NSE_CIRCUIT_BREAKER,
    CircuitBreakerLevel,
    CircuitBreakerRuleProtocol,
    CircuitBreakerThreshold,
    IndexCircuitBreakerConfig,
    PriceBandConfig,
    PriceBandRuleProtocol,
    PriceBandType,
    RestrictionType,
    TradingRestriction,
)


class TestPriceBandType:
    def test_values(self) -> None:
        assert PriceBandType.STATIC == "static"
        assert PriceBandType.DYNAMIC == "dynamic"
        assert PriceBandType.NONE == "none"


class TestPriceBandConfig:
    def test_valid_static_symmetric(self) -> None:
        config = PriceBandConfig(
            band_type=PriceBandType.STATIC,
            upper_limit_pct=Decimal("20"),
            lower_limit_pct=Decimal("20"),
        )
        assert config.is_symmetric is True

    def test_valid_asymmetric(self) -> None:
        config = PriceBandConfig(
            band_type=PriceBandType.STATIC,
            upper_limit_pct=Decimal("20"),
            lower_limit_pct=Decimal("10"),
        )
        assert config.is_symmetric is False

    def test_valid_upper_only(self) -> None:
        config = PriceBandConfig(
            band_type=PriceBandType.STATIC,
            upper_limit_pct=Decimal("20"),
        )
        assert config.upper_limit_pct == Decimal("20")
        assert config.lower_limit_pct is None
        assert config.is_symmetric is False

    def test_none_band_with_no_limits_valid(self) -> None:
        config = PriceBandConfig(band_type=PriceBandType.NONE)
        assert config.upper_limit_pct is None
        assert config.lower_limit_pct is None

    def test_static_with_no_limits_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError, match="at least one"):
            PriceBandConfig(band_type=PriceBandType.STATIC)

    def test_negative_upper_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError, match="upper_limit_pct"):
            PriceBandConfig(
                band_type=PriceBandType.STATIC,
                upper_limit_pct=Decimal("-5"),
            )

    def test_zero_lower_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError, match="lower_limit_pct"):
            PriceBandConfig(
                band_type=PriceBandType.STATIC,
                lower_limit_pct=Decimal("0"),
            )


class TestCircuitBreakerThreshold:
    def test_valid_level1(self) -> None:
        t = CircuitBreakerThreshold(
            level=CircuitBreakerLevel.LEVEL_1,
            trigger_decline_pct=Decimal("10"),
            halt_duration_minutes=45,
        )
        assert t.halts_for_day is False

    def test_level3_halts_for_day(self) -> None:
        t = CircuitBreakerThreshold(
            level=CircuitBreakerLevel.LEVEL_3,
            trigger_decline_pct=Decimal("20"),
            halt_duration_minutes=None,
        )
        assert t.halts_for_day is True

    def test_zero_trigger_pct_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError, match="trigger_decline_pct"):
            CircuitBreakerThreshold(
                level=CircuitBreakerLevel.LEVEL_1,
                trigger_decline_pct=Decimal("0"),
                halt_duration_minutes=45,
            )

    def test_zero_halt_duration_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError, match="halt_duration_minutes"):
            CircuitBreakerThreshold(
                level=CircuitBreakerLevel.LEVEL_1,
                trigger_decline_pct=Decimal("10"),
                halt_duration_minutes=0,
            )


class TestIndexCircuitBreakerConfig:
    def test_sebi_nse_constant(self) -> None:
        cb = SEBI_NSE_CIRCUIT_BREAKER
        assert cb.exchange_id == MarketId("NSE")
        assert len(cb.thresholds) == 3

    def test_threshold_levels_ascending(self) -> None:
        for i in range(len(SEBI_NSE_CIRCUIT_BREAKER.thresholds) - 1):
            assert (
                SEBI_NSE_CIRCUIT_BREAKER.thresholds[i].trigger_decline_pct
                < SEBI_NSE_CIRCUIT_BREAKER.thresholds[i + 1].trigger_decline_pct
            )

    def test_threshold_for_level(self) -> None:
        t = SEBI_NSE_CIRCUIT_BREAKER.threshold_for_level(CircuitBreakerLevel.LEVEL_1)
        assert t is not None
        assert t.trigger_decline_pct == Decimal("10")

    def test_threshold_for_nonexistent_level(self) -> None:
        config = IndexCircuitBreakerConfig(
            exchange_id=MarketId("TEST"),
            reference_index_id=MarketId("IDX"),
            thresholds=(CircuitBreakerThreshold(CircuitBreakerLevel.LEVEL_1, Decimal("10"), 45),),
        )
        assert config.threshold_for_level(CircuitBreakerLevel.LEVEL_3) is None

    def test_empty_thresholds_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError, match="empty"):
            IndexCircuitBreakerConfig(
                exchange_id=MarketId("TEST"),
                reference_index_id=MarketId("IDX"),
                thresholds=(),
            )

    def test_non_ascending_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError, match="ascending"):
            IndexCircuitBreakerConfig(
                exchange_id=MarketId("TEST"),
                reference_index_id=MarketId("IDX"),
                thresholds=(
                    CircuitBreakerThreshold(CircuitBreakerLevel.LEVEL_1, Decimal("20"), 45),
                    CircuitBreakerThreshold(CircuitBreakerLevel.LEVEL_2, Decimal("10"), 90),
                ),
            )


class TestTradingRestriction:
    def _make(self) -> TradingRestriction:
        return TradingRestriction(
            restriction_id="TEST-001",
            exchange_id=MarketId("NSE"),
            restriction_type=RestrictionType.TRADING_BAN,
            reason="Regulatory investigation",
            effective_date=date(2025, 1, 15),
        )

    def test_valid_construction(self) -> None:
        r = self._make()
        assert r.restriction_id == "TEST-001"
        assert r.expiry_date is None

    def test_is_active_on_effective_date(self) -> None:
        assert self._make().is_active_on(date(2025, 1, 15)) is True

    def test_is_not_active_before_effective(self) -> None:
        assert self._make().is_active_on(date(2025, 1, 14)) is False

    def test_indefinite_restriction_always_active_after_effective(self) -> None:
        r = self._make()
        assert r.is_active_on(date(2030, 12, 31)) is True

    def test_with_expiry_date(self) -> None:
        r = TradingRestriction(
            restriction_id="TEST-002",
            exchange_id=MarketId("NSE"),
            restriction_type=RestrictionType.TRADING_BAN,
            reason="Test",
            effective_date=date(2025, 1, 15),
            expiry_date=date(2025, 1, 30),
        )
        assert r.is_active_on(date(2025, 1, 30)) is True
        assert r.is_active_on(date(2025, 1, 31)) is False

    def test_expiry_before_effective_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError, match="expiry_date"):
            TradingRestriction(
                restriction_id="TEST-003",
                exchange_id=MarketId("NSE"),
                restriction_type=RestrictionType.TRADING_BAN,
                reason="Test",
                effective_date=date(2025, 1, 15),
                expiry_date=date(2025, 1, 14),
            )

    def test_empty_restriction_id_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError, match="restriction_id"):
            TradingRestriction(
                restriction_id="",
                exchange_id=MarketId("NSE"),
                restriction_type=RestrictionType.TRADING_BAN,
                reason="Test",
                effective_date=date(2025, 1, 15),
            )

    def test_empty_reason_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError, match="reason"):
            TradingRestriction(
                restriction_id="TEST-004",
                exchange_id=MarketId("NSE"),
                restriction_type=RestrictionType.TRADING_BAN,
                reason="",
                effective_date=date(2025, 1, 15),
            )


class TestRuleProtocols:
    def test_pricebandrulemock_satisfies_protocol(self) -> None:
        class MockPriceBandRule:
            def compute_upper_band(self, reference_price: Decimal) -> Decimal | None:
                return reference_price * Decimal("1.2")

            def compute_lower_band(self, reference_price: Decimal) -> Decimal | None:
                return reference_price * Decimal("0.8")

            def is_within_band(self, price: Decimal, reference_price: Decimal) -> bool:
                upper = self.compute_upper_band(reference_price)
                lower = self.compute_lower_band(reference_price)
                if upper is None or lower is None:
                    return True
                return lower <= price <= upper

        assert isinstance(MockPriceBandRule(), PriceBandRuleProtocol)

    def test_circuit_breaker_mock_satisfies_protocol(self) -> None:
        class MockCBRule:
            def is_triggered(self, current: Decimal, reference: Decimal) -> bool:
                decline = (reference - current) / reference * 100
                return decline >= Decimal("10")

            def get_halt_duration_minutes(self, current: Decimal, reference: Decimal) -> int | None:
                if not self.is_triggered(current, reference):
                    return 0
                return 45

        assert isinstance(MockCBRule(), CircuitBreakerRuleProtocol)
