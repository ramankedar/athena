"""Unit tests for corporate actions."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from athena.core.domain.primitives import Symbol
from athena.market_data.corporate_actions import CorporateAction, CorporateActionType
from athena.market_data.exceptions import InvalidBarError

HDFCBANK = Symbol("NSE:HDFCBANK")


class TestCorporateActionType:
    def test_values(self) -> None:
        assert CorporateActionType.CASH_DIVIDEND == "cash_dividend"
        assert CorporateActionType.STOCK_SPLIT == "stock_split"
        assert CorporateActionType.BONUS_ISSUE == "bonus_issue"
        assert CorporateActionType.REVERSE_SPLIT == "reverse_split"


class TestCorporateAction:
    def _split_2_1(self) -> CorporateAction:
        return CorporateAction(
            symbol=HDFCBANK,
            action_type=CorporateActionType.STOCK_SPLIT,
            announcement_date=date(2025, 1, 10),
            ex_date=date(2025, 1, 20),
            ratio_numerator=Decimal("2"),
            ratio_denominator=Decimal("1"),
        )

    def test_valid_construction(self) -> None:
        ca = self._split_2_1()
        assert ca.symbol == HDFCBANK
        assert ca.action_type == CorporateActionType.STOCK_SPLIT

    def test_split_factor_2_to_1(self) -> None:
        ca = self._split_2_1()
        # 2:1 split → price halved → factor = 1/2
        assert ca.split_factor == Decimal("0.5")

    def test_volume_factor_2_to_1(self) -> None:
        ca = self._split_2_1()
        # 2:1 split → volume doubled → factor = 2
        assert ca.volume_factor == Decimal("2")

    def test_split_factor_none_when_no_ratio(self) -> None:
        ca = CorporateAction(
            symbol=HDFCBANK,
            action_type=CorporateActionType.CASH_DIVIDEND,
            announcement_date=date(2025, 1, 10),
            ex_date=date(2025, 1, 20),
            amount=Decimal("5.0"),
        )
        assert ca.split_factor is None
        assert ca.volume_factor is None

    def test_reverse_split_factor(self) -> None:
        ca = CorporateAction(
            symbol=HDFCBANK,
            action_type=CorporateActionType.REVERSE_SPLIT,
            announcement_date=date(2025, 1, 10),
            ex_date=date(2025, 1, 20),
            ratio_numerator=Decimal("1"),
            ratio_denominator=Decimal("2"),
        )
        # 1:2 reverse → price doubled → factor = 2
        assert ca.split_factor == Decimal("2")

    def test_affects_price_dividend(self) -> None:
        ca = CorporateAction(
            symbol=HDFCBANK,
            action_type=CorporateActionType.CASH_DIVIDEND,
            announcement_date=date(2025, 1, 10),
            ex_date=date(2025, 1, 20),
            amount=Decimal("5.0"),
        )
        assert ca.affects_price is True

    def test_affects_price_name_change(self) -> None:
        ca = CorporateAction(
            symbol=HDFCBANK,
            action_type=CorporateActionType.NAME_CHANGE,
            announcement_date=date(2025, 1, 10),
            ex_date=date(2025, 1, 20),
        )
        assert ca.affects_price is False

    def test_negative_ratio_numerator_raises(self) -> None:
        with pytest.raises(InvalidBarError, match="ratio_numerator"):
            CorporateAction(
                symbol=HDFCBANK,
                action_type=CorporateActionType.STOCK_SPLIT,
                announcement_date=date(2025, 1, 10),
                ex_date=date(2025, 1, 20),
                ratio_numerator=Decimal("-1"),
                ratio_denominator=Decimal("1"),
            )

    def test_negative_amount_raises(self) -> None:
        with pytest.raises(InvalidBarError, match="amount"):
            CorporateAction(
                symbol=HDFCBANK,
                action_type=CorporateActionType.CASH_DIVIDEND,
                announcement_date=date(2025, 1, 10),
                ex_date=date(2025, 1, 20),
                amount=Decimal("-5"),
            )

    def test_str(self) -> None:
        s = str(self._split_2_1())
        assert "NSE:HDFCBANK" in s
        assert "stock_split" in s
