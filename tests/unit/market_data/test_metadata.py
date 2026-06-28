"""Unit tests for DataProvenance and SymbolMapping."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime

import pytest

from athena.market_data.exceptions import InvalidBarError
from athena.market_data.metadata import DataProvenance, SymbolMapping

NOW = datetime(2025, 1, 15, 10, 0, tzinfo=UTC)


class TestDataProvenance:
    def test_valid_construction(self) -> None:
        p = DataProvenance(vendor="fyers", vendor_symbol="NSE:NIFTY", retrieved_at=NOW)
        assert p.vendor == "fyers"
        assert p.is_delayed is False

    def test_with_delay(self) -> None:
        p = DataProvenance(
            vendor="yahoo",
            vendor_symbol="^NSEI",
            retrieved_at=NOW,
            is_delayed=True,
            delay_minutes=15,
        )
        assert p.is_delayed is True
        assert p.delay_minutes == 15

    def test_empty_vendor_raises(self) -> None:
        with pytest.raises(InvalidBarError, match="vendor"):
            DataProvenance(vendor="", vendor_symbol="X", retrieved_at=NOW)

    def test_empty_symbol_raises(self) -> None:
        with pytest.raises(InvalidBarError, match="vendor_symbol"):
            DataProvenance(vendor="fyers", vendor_symbol="", retrieved_at=NOW)

    def test_naive_retrieved_at_raises(self) -> None:
        with pytest.raises(InvalidBarError, match="retrieved_at"):
            DataProvenance(
                vendor="fyers",
                vendor_symbol="X",
                retrieved_at=datetime(2025, 1, 15, 10, 0),
            )

    def test_negative_delay_raises(self) -> None:
        with pytest.raises(InvalidBarError, match="delay_minutes"):
            DataProvenance(
                vendor="fyers",
                vendor_symbol="X",
                retrieved_at=NOW,
                delay_minutes=-1,
            )

    def test_str(self) -> None:
        p = DataProvenance(vendor="fyers", vendor_symbol="NSE:NIFTY", retrieved_at=NOW)
        assert "fyers" in str(p)

    def test_is_frozen(self) -> None:
        p = DataProvenance(vendor="fyers", vendor_symbol="X", retrieved_at=NOW)
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            p.vendor = "other"  # type: ignore[misc]


class TestSymbolMapping:
    def test_valid_construction(self) -> None:
        m = SymbolMapping(
            internal_symbol="NSE:NIFTY50-INDEX",
            vendor="fyers",
            vendor_symbol="NSE:NIFTY50-INDEX",
        )
        assert m.is_active is True

    def test_inactive_mapping(self) -> None:
        m = SymbolMapping(
            internal_symbol="NSE:NIFTY50-INDEX",
            vendor="yahoo",
            vendor_symbol="^NSEI",
            is_active=False,
        )
        assert m.is_active is False

    def test_empty_internal_symbol_raises(self) -> None:
        with pytest.raises(InvalidBarError, match="internal_symbol"):
            SymbolMapping(internal_symbol="", vendor="fyers", vendor_symbol="X")

    def test_empty_vendor_raises(self) -> None:
        with pytest.raises(InvalidBarError, match="vendor"):
            SymbolMapping(internal_symbol="NSE:X", vendor="", vendor_symbol="X")

    def test_empty_vendor_symbol_raises(self) -> None:
        with pytest.raises(InvalidBarError, match="vendor_symbol"):
            SymbolMapping(internal_symbol="NSE:X", vendor="fyers", vendor_symbol="")

    def test_str_active(self) -> None:
        m = SymbolMapping(
            internal_symbol="NSE:NIFTY50-INDEX",
            vendor="fyers",
            vendor_symbol="NSE:NIFTY50",
        )
        s = str(m)
        assert "active" in s
        assert "fyers" in s

    def test_str_inactive(self) -> None:
        m = SymbolMapping(
            internal_symbol="NSE:X",
            vendor="yahoo",
            vendor_symbol="^X",
            is_active=False,
        )
        assert "inactive" in str(m)
