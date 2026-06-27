"""Unit tests for primitive value types.

Uses hypothesis for property-based testing: the invariants tested here
must hold for any valid Decimal input, not just the examples we thought of.
"""

from __future__ import annotations

from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from athena.core.domain.primitives import Currency, Price, Quantity, price, quantity

# ── Price ─────────────────────────────────────────────────────────────────────


class TestPrice:
    def test_is_decimal_at_runtime(self) -> None:
        p = Price(Decimal("24500.50"))
        assert isinstance(p, Decimal)

    def test_preserves_exact_value(self) -> None:
        raw = Decimal("24500.05")
        assert Price(raw) == raw

    def test_decimal_arithmetic_is_exact(self) -> None:
        # This is the core reason we use Decimal over float.
        p1 = Price(Decimal("0.1"))
        p2 = Price(Decimal("0.2"))
        assert p1 + p2 == Decimal("0.3")

    def test_constructor_helper(self) -> None:
        assert price("24500.50") == Decimal("24500.50")
        assert price(24500) == Decimal("24500")
        assert price(Decimal("100.25")) == Decimal("100.25")

    @given(
        st.decimals(
            min_value=0,
            max_value=Decimal("1e6"),
            allow_nan=False,
            allow_infinity=False,
        )
    )
    @settings(max_examples=200)
    def test_price_preserves_arbitrary_value(self, value: Decimal) -> None:
        assert Price(value) == value

    def test_two_prices_are_comparable(self) -> None:
        low = Price(Decimal("100"))
        high = Price(Decimal("200"))
        assert low < high
        assert high > low
        assert low != high


# ── Quantity ──────────────────────────────────────────────────────────────────


class TestQuantity:
    def test_is_decimal_at_runtime(self) -> None:
        q = Quantity(Decimal("50"))
        assert isinstance(q, Decimal)

    def test_lot_size_multiplication(self) -> None:
        lot = Quantity(Decimal("50"))
        contracts = Decimal("3")
        total = lot * contracts
        assert total == Decimal("150")

    def test_constructor_helper(self) -> None:
        assert quantity("50") == Decimal("50")
        assert quantity(50) == Decimal("50")

    @given(
        st.decimals(
            min_value=0,
            max_value=Decimal("1e9"),
            allow_nan=False,
            allow_infinity=False,
        )
    )
    def test_quantity_preserves_arbitrary_value(self, value: Decimal) -> None:
        assert Quantity(value) == value


# ── Currency ──────────────────────────────────────────────────────────────────


class TestCurrency:
    def test_is_str_at_runtime(self) -> None:
        assert isinstance(Currency("INR"), str)

    def test_equality(self) -> None:
        assert Currency("INR") == Currency("INR")
        assert Currency("INR") != Currency("USD")
