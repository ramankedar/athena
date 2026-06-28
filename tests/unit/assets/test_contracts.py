"""Unit tests for contract specification value objects."""

from __future__ import annotations

import dataclasses
from datetime import date
from decimal import Decimal

import pytest

from athena.assets.classification import OptionStyle, OptionType, SettlementType
from athena.assets.contracts import (
    CommoditySpec,
    CurrencySpec,
    EquitySpec,
    ETFSpec,
    FuturesSpec,
    IndexSpec,
    OptionsSpec,
)
from athena.assets.exceptions import InvalidContractSpecError
from athena.assets.identifiers import ISIN, CurrencyCode, Symbol

INR = CurrencyCode("INR")
USD = CurrencyCode("USD")
NIFTY = Symbol.parse("NSE:NIFTY50-INDEX")
EXPIRY = date(2025, 1, 30)


class TestEquitySpec:
    def test_valid_construction(self) -> None:
        spec = EquitySpec(
            lot_size=Decimal("1"),
            tick_size=Decimal("0.05"),
            currency=INR,
        )
        assert spec.lot_size == Decimal("1")
        assert spec.isin is None

    def test_with_isin(self) -> None:
        spec = EquitySpec(
            lot_size=Decimal("1"),
            tick_size=Decimal("0.05"),
            currency=INR,
            isin=ISIN("INE040A01034"),
        )
        assert spec.isin is not None

    def test_with_face_value(self) -> None:
        spec = EquitySpec(
            lot_size=Decimal("1"),
            tick_size=Decimal("0.05"),
            currency=INR,
            face_value=Decimal("10"),
        )
        assert spec.face_value == Decimal("10")

    def test_negative_face_value_raises(self) -> None:
        with pytest.raises(InvalidContractSpecError, match="face_value"):
            EquitySpec(
                lot_size=Decimal("1"),
                tick_size=Decimal("0.05"),
                currency=INR,
                face_value=Decimal("-1"),
            )

    def test_zero_lot_size_raises(self) -> None:
        with pytest.raises(InvalidContractSpecError, match="lot_size"):
            EquitySpec(lot_size=Decimal("0"), tick_size=Decimal("0.05"), currency=INR)

    def test_negative_tick_size_raises(self) -> None:
        with pytest.raises(InvalidContractSpecError, match="tick_size"):
            EquitySpec(lot_size=Decimal("1"), tick_size=Decimal("-0.05"), currency=INR)

    def test_tick_value(self) -> None:
        spec = EquitySpec(
            lot_size=Decimal("1"),
            tick_size=Decimal("0.05"),
            currency=INR,
        )
        assert spec.tick_value == Decimal("0.05")

    def test_is_frozen(self) -> None:
        spec = EquitySpec(Decimal("1"), Decimal("0.05"), INR)
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            spec.lot_size = Decimal("2")  # type: ignore[misc]


class TestIndexSpec:
    def test_valid_construction(self) -> None:
        spec = IndexSpec(
            lot_size=Decimal("1"),
            tick_size=Decimal("0.05"),
            currency=INR,
            num_components=50,
        )
        assert spec.num_components == 50

    def test_optional_fields_default_none(self) -> None:
        spec = IndexSpec(Decimal("1"), Decimal("0.05"), INR)
        assert spec.base_value is None
        assert spec.base_date is None
        assert spec.num_components is None

    def test_negative_base_value_raises(self) -> None:
        with pytest.raises(InvalidContractSpecError, match="base_value"):
            IndexSpec(Decimal("1"), Decimal("0.05"), INR, base_value=Decimal("-100"))

    def test_zero_components_raises(self) -> None:
        with pytest.raises(InvalidContractSpecError, match="num_components"):
            IndexSpec(Decimal("1"), Decimal("0.05"), INR, num_components=0)


class TestFuturesSpec:
    def test_valid_construction(self) -> None:
        spec = FuturesSpec(
            lot_size=Decimal("50"),
            tick_size=Decimal("0.05"),
            currency=INR,
            underlying=NIFTY,
            expiry=EXPIRY,
            multiplier=Decimal("1"),
            settlement=SettlementType.CASH,
        )
        assert spec.underlying == NIFTY
        assert spec.expiry == EXPIRY
        assert spec.settlement == SettlementType.CASH

    def test_negative_multiplier_raises(self) -> None:
        with pytest.raises(InvalidContractSpecError, match="multiplier"):
            FuturesSpec(
                lot_size=Decimal("50"),
                tick_size=Decimal("0.05"),
                currency=INR,
                underlying=NIFTY,
                expiry=EXPIRY,
                multiplier=Decimal("-1"),
                settlement=SettlementType.CASH,
            )

    def test_tick_value_for_futures(self) -> None:
        spec = FuturesSpec(
            lot_size=Decimal("50"),
            tick_size=Decimal("0.05"),
            currency=INR,
            underlying=NIFTY,
            expiry=EXPIRY,
            multiplier=Decimal("1"),
            settlement=SettlementType.CASH,
        )
        assert spec.tick_value == Decimal("2.50")  # 50 * 0.05


class TestOptionsSpec:
    def _make_call(self) -> OptionsSpec:
        return OptionsSpec(
            lot_size=Decimal("50"),
            tick_size=Decimal("0.05"),
            currency=INR,
            underlying=NIFTY,
            expiry=EXPIRY,
            strike=Decimal("24500"),
            option_type=OptionType.CALL,
            style=OptionStyle.EUROPEAN,
            multiplier=Decimal("1"),
            settlement=SettlementType.CASH,
        )

    def test_valid_call(self) -> None:
        spec = self._make_call()
        assert spec.is_call is True
        assert spec.is_put is False

    def test_valid_put(self) -> None:
        spec = OptionsSpec(
            lot_size=Decimal("50"),
            tick_size=Decimal("0.05"),
            currency=INR,
            underlying=NIFTY,
            expiry=EXPIRY,
            strike=Decimal("24500"),
            option_type=OptionType.PUT,
            style=OptionStyle.EUROPEAN,
            multiplier=Decimal("1"),
            settlement=SettlementType.CASH,
        )
        assert spec.is_put is True
        assert spec.is_call is False

    def test_zero_strike_raises(self) -> None:
        with pytest.raises(InvalidContractSpecError, match="strike"):
            OptionsSpec(
                lot_size=Decimal("50"),
                tick_size=Decimal("0.05"),
                currency=INR,
                underlying=NIFTY,
                expiry=EXPIRY,
                strike=Decimal("0"),
                option_type=OptionType.CALL,
                style=OptionStyle.EUROPEAN,
                multiplier=Decimal("1"),
                settlement=SettlementType.CASH,
            )

    def test_negative_strike_raises(self) -> None:
        with pytest.raises(InvalidContractSpecError, match="strike"):
            OptionsSpec(
                lot_size=Decimal("50"),
                tick_size=Decimal("0.05"),
                currency=INR,
                underlying=NIFTY,
                expiry=EXPIRY,
                strike=Decimal("-100"),
                option_type=OptionType.CALL,
                style=OptionStyle.EUROPEAN,
                multiplier=Decimal("1"),
                settlement=SettlementType.CASH,
            )


class TestETFSpec:
    def test_valid_construction(self) -> None:
        spec = ETFSpec(
            lot_size=Decimal("1"),
            tick_size=Decimal("0.01"),
            currency=INR,
            tracking_index=NIFTY,
            total_expense_ratio=Decimal("0.0007"),
        )
        assert spec.total_expense_ratio == Decimal("0.0007")

    def test_expense_ratio_one_raises(self) -> None:
        with pytest.raises(InvalidContractSpecError, match="total_expense_ratio"):
            ETFSpec(
                lot_size=Decimal("1"),
                tick_size=Decimal("0.01"),
                currency=INR,
                total_expense_ratio=Decimal("1"),  # must be < 1
            )

    def test_expense_ratio_negative_raises(self) -> None:
        with pytest.raises(InvalidContractSpecError, match="total_expense_ratio"):
            ETFSpec(
                lot_size=Decimal("1"),
                tick_size=Decimal("0.01"),
                currency=INR,
                total_expense_ratio=Decimal("-0.001"),
            )

    def test_zero_expense_ratio_valid(self) -> None:
        spec = ETFSpec(
            lot_size=Decimal("1"),
            tick_size=Decimal("0.01"),
            currency=INR,
            total_expense_ratio=Decimal("0"),
        )
        assert spec.total_expense_ratio == Decimal("0")


class TestCurrencySpec:
    def test_valid_usd_inr(self) -> None:
        spec = CurrencySpec(
            lot_size=Decimal("1000"),
            tick_size=Decimal("0.0025"),
            currency=INR,
            base_currency=USD,
            quote_currency=INR,
        )
        assert spec.pair_name == "USD/INR"

    def test_same_base_and_quote_raises(self) -> None:
        with pytest.raises(InvalidContractSpecError, match="different"):
            CurrencySpec(
                lot_size=Decimal("1000"),
                tick_size=Decimal("0.0025"),
                currency=INR,
                base_currency=INR,
                quote_currency=INR,
            )

    def test_negative_pip_size_raises(self) -> None:
        with pytest.raises(InvalidContractSpecError, match="pip_size"):
            CurrencySpec(
                lot_size=Decimal("1000"),
                tick_size=Decimal("0.0025"),
                currency=INR,
                base_currency=USD,
                quote_currency=INR,
                pip_size=Decimal("-0.0025"),
            )

    def test_pair_name(self) -> None:
        spec = CurrencySpec(
            lot_size=Decimal("1"),
            tick_size=Decimal("0.01"),
            currency=CurrencyCode("JPY"),
            base_currency=USD,
            quote_currency=CurrencyCode("JPY"),
        )
        assert spec.pair_name == "USD/JPY"


class TestCommoditySpec:
    def test_valid_gold(self) -> None:
        spec = CommoditySpec(
            lot_size=Decimal("100"),
            tick_size=Decimal("1"),
            currency=INR,
            unit_of_measure="gram",
            expiry=date(2025, 2, 5),
            settlement=SettlementType.PHYSICAL,
            quality_grade="999.9 fine gold",
        )
        assert spec.unit_of_measure == "gram"
        assert spec.quality_grade == "999.9 fine gold"

    def test_empty_unit_of_measure_raises(self) -> None:
        with pytest.raises(InvalidContractSpecError, match="unit_of_measure"):
            CommoditySpec(
                lot_size=Decimal("100"),
                tick_size=Decimal("1"),
                currency=INR,
                unit_of_measure="",
            )

    def test_negative_multiplier_raises(self) -> None:
        with pytest.raises(InvalidContractSpecError, match="multiplier"):
            CommoditySpec(
                lot_size=Decimal("100"),
                tick_size=Decimal("1"),
                currency=INR,
                unit_of_measure="barrel",
                multiplier=Decimal("-1"),
            )

    def test_optional_fields(self) -> None:
        spec = CommoditySpec(
            lot_size=Decimal("1"),
            tick_size=Decimal("1"),
            currency=INR,
            unit_of_measure="MT",
        )
        assert spec.expiry is None
        assert spec.underlying is None
        assert spec.quality_grade is None
        assert spec.delivery_location is None
