"""Unit tests for adjustment factor value objects."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from athena.core.domain.primitives import Price, Symbol
from athena.market_data.adjustments import (
    AdjustedPrice,
    AdjustmentFactor,
    apply_adjustment,
    cumulative_price_factor,
)
from athena.market_data.corporate_actions import CorporateActionType
from athena.market_data.exceptions import InvalidAdjustmentError
from athena.market_data.models import AdjustmentMethodology

HDFCBANK = Symbol("NSE:HDFCBANK")
EX_DATE = date(2025, 1, 20)


def _split_factor() -> AdjustmentFactor:
    return AdjustmentFactor(
        symbol=HDFCBANK,
        effective_date=EX_DATE,
        price_factor=Decimal("0.5"),
        volume_factor=Decimal("2.0"),
        methodology=AdjustmentMethodology.BACKWARD,
        source_action_type=CorporateActionType.STOCK_SPLIT,
    )


class TestAdjustmentFactor:
    def test_valid_construction(self) -> None:
        f = _split_factor()
        assert f.price_factor == Decimal("0.5")
        assert f.volume_factor == Decimal("2.0")

    def test_zero_price_factor_raises(self) -> None:
        with pytest.raises(InvalidAdjustmentError, match="price_factor"):
            AdjustmentFactor(
                symbol=HDFCBANK,
                effective_date=EX_DATE,
                price_factor=Decimal("0"),
                volume_factor=Decimal("1"),
                methodology=AdjustmentMethodology.BACKWARD,
            )

    def test_negative_volume_factor_raises(self) -> None:
        with pytest.raises(InvalidAdjustmentError, match="volume_factor"):
            AdjustmentFactor(
                symbol=HDFCBANK,
                effective_date=EX_DATE,
                price_factor=Decimal("1"),
                volume_factor=Decimal("-1"),
                methodology=AdjustmentMethodology.BACKWARD,
            )

    def test_is_identity_true(self) -> None:
        f = AdjustmentFactor(
            symbol=HDFCBANK,
            effective_date=EX_DATE,
            price_factor=Decimal("1"),
            volume_factor=Decimal("1"),
            methodology=AdjustmentMethodology.NONE,
        )
        assert f.is_identity() is True

    def test_is_identity_false(self) -> None:
        assert _split_factor().is_identity() is False

    def test_inverse(self) -> None:
        f = _split_factor()
        inv = f.inverse()
        assert inv.price_factor == Decimal("2.0")  # 1 / 0.5
        assert inv.volume_factor == Decimal("0.5")  # 1 / 2.0

    def test_str(self) -> None:
        s = str(_split_factor())
        assert "NSE:HDFCBANK" in s
        assert "backward" in s


class TestAdjustedPrice:
    def test_valid_construction(self) -> None:
        ap = AdjustedPrice(
            original_price=Price(Decimal("200")),
            adjustment_factor=Decimal("0.5"),
            adjusted_price=Price(Decimal("100")),
            adjusted_for_date=EX_DATE,
            methodology=AdjustmentMethodology.BACKWARD,
        )
        assert ap.price_change == Decimal("-100")

    def test_zero_original_raises(self) -> None:
        with pytest.raises(InvalidAdjustmentError, match="original_price"):
            AdjustedPrice(
                original_price=Price(Decimal("0")),
                adjustment_factor=Decimal("1"),
                adjusted_price=Price(Decimal("1")),
                adjusted_for_date=EX_DATE,
                methodology=AdjustmentMethodology.BACKWARD,
            )

    def test_zero_adjusted_raises(self) -> None:
        with pytest.raises(InvalidAdjustmentError, match="adjusted_price"):
            AdjustedPrice(
                original_price=Price(Decimal("100")),
                adjustment_factor=Decimal("0.5"),
                adjusted_price=Price(Decimal("0")),
                adjusted_for_date=EX_DATE,
                methodology=AdjustmentMethodology.BACKWARD,
            )

    def test_price_change_positive(self) -> None:
        ap = AdjustedPrice(
            original_price=Price(Decimal("100")),
            adjustment_factor=Decimal("2"),
            adjusted_price=Price(Decimal("200")),
            adjusted_for_date=EX_DATE,
            methodology=AdjustmentMethodology.FORWARD,
        )
        assert ap.price_change == Decimal("100")

    def test_str(self) -> None:
        ap = AdjustedPrice(
            original_price=Price(Decimal("200")),
            adjustment_factor=Decimal("0.5"),
            adjusted_price=Price(Decimal("100")),
            adjusted_for_date=EX_DATE,
            methodology=AdjustmentMethodology.BACKWARD,
        )
        s = str(ap)
        assert "200" in s
        assert "100" in s


class TestApplyAdjustment:
    def test_apply_split_adjustment(self) -> None:
        f = _split_factor()
        result = apply_adjustment(Price(Decimal("200")), f)
        assert result.adjusted_price == Price(Decimal("100"))  # 200 * 0.5
        assert result.adjustment_factor == Decimal("0.5")

    def test_apply_identity(self) -> None:
        f = AdjustmentFactor(
            symbol=HDFCBANK,
            effective_date=EX_DATE,
            price_factor=Decimal("1"),
            volume_factor=Decimal("1"),
            methodology=AdjustmentMethodology.NONE,
        )
        result = apply_adjustment(Price(Decimal("100")), f)
        assert result.adjusted_price == Price(Decimal("100"))


class TestCumulativePriceFactor:
    def test_empty_sequence_is_identity(self) -> None:
        assert cumulative_price_factor(()) == Decimal("1")

    def test_single_factor(self) -> None:
        f = _split_factor()
        assert cumulative_price_factor((f,)) == Decimal("0.5")

    def test_two_splits(self) -> None:
        f1 = _split_factor()  # 0.5
        f2 = AdjustmentFactor(
            symbol=HDFCBANK,
            effective_date=date(2024, 6, 1),
            price_factor=Decimal("0.5"),
            volume_factor=Decimal("2.0"),
            methodology=AdjustmentMethodology.BACKWARD,
        )
        result = cumulative_price_factor((f1, f2))
        assert result == Decimal("0.25")  # 0.5 * 0.5
