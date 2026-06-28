"""Unit tests for the asset domain exception hierarchy."""

from __future__ import annotations

import pytest

from athena.assets.exceptions import (
    AssetError,
    DuplicateInstrumentError,
    InstrumentExpiredError,
    InstrumentNotFoundError,
    InvalidContractSpecError,
    InvalidIdentifierError,
    InvalidInstrumentError,
    UnsupportedAssetClassError,
)
from athena.platform.exceptions import AthenaError


class TestAssetError:
    def test_is_athena_error(self) -> None:
        assert issubclass(AssetError, AthenaError)

    def test_construction(self) -> None:
        exc = AssetError("asset failed", component="registry")
        assert "asset failed" in str(exc)
        assert exc.context["component"] == "registry"


class TestInvalidIdentifierError:
    def test_is_asset_error(self) -> None:
        assert issubclass(InvalidIdentifierError, AssetError)

    def test_message_and_attributes(self) -> None:
        exc = InvalidIdentifierError("bad-isin", reason="wrong length")
        assert "bad-isin" in str(exc)
        assert "wrong length" in str(exc)
        assert exc.identifier == "bad-isin"
        assert exc.reason == "wrong length"
        assert exc.error_code == "AST_001"


class TestInvalidInstrumentError:
    def test_is_asset_error(self) -> None:
        assert issubclass(InvalidInstrumentError, AssetError)

    def test_construction(self) -> None:
        exc = InvalidInstrumentError("name cannot be empty", field="name")
        assert "name cannot be empty" in str(exc)
        assert exc.error_code == "AST_002"


class TestInvalidContractSpecError:
    def test_is_asset_error(self) -> None:
        assert issubclass(InvalidContractSpecError, AssetError)

    def test_attributes(self) -> None:
        exc = InvalidContractSpecError(field="lot_size", value=-1, reason="must be positive")
        assert exc.field == "lot_size"
        assert exc.value == -1
        assert exc.reason == "must be positive"
        assert exc.error_code == "AST_003"
        assert "lot_size" in str(exc)
        assert "must be positive" in str(exc)


class TestInstrumentNotFoundError:
    def test_is_asset_error(self) -> None:
        assert issubclass(InstrumentNotFoundError, AssetError)

    def test_default_lookup_type(self) -> None:
        exc = InstrumentNotFoundError("some-uuid")
        assert exc.lookup_type == "id"
        assert exc.error_code == "AST_004"

    def test_custom_lookup_type(self) -> None:
        exc = InstrumentNotFoundError("NSE:NIFTY50", lookup_type="symbol")
        assert exc.lookup_type == "symbol"
        assert "symbol" in str(exc)


class TestDuplicateInstrumentError:
    def test_is_asset_error(self) -> None:
        assert issubclass(DuplicateInstrumentError, AssetError)

    def test_message(self) -> None:
        exc = DuplicateInstrumentError("some-uuid-value")
        assert "some-uuid-value" in str(exc)
        assert exc.instrument_id == "some-uuid-value"
        assert exc.error_code == "AST_005"


class TestInstrumentExpiredError:
    def test_is_asset_error(self) -> None:
        assert issubclass(InstrumentExpiredError, AssetError)

    def test_attributes(self) -> None:
        exc = InstrumentExpiredError(
            symbol="NSE:NIFTY25JAN24500CE",
            expiry="2025-01-30",
        )
        assert exc.symbol == "NSE:NIFTY25JAN24500CE"
        assert exc.expiry == "2025-01-30"
        assert exc.error_code == "AST_006"
        assert "NSE:NIFTY25JAN24500CE" in str(exc)
        assert "2025-01-30" in str(exc)

    def test_caught_as_asset_error(self) -> None:
        with pytest.raises(AssetError):
            raise InstrumentExpiredError("NSE:EXPIRED", "2024-12-31")


class TestUnsupportedAssetClassError:
    def test_is_asset_error(self) -> None:
        assert issubclass(UnsupportedAssetClassError, AssetError)

    def test_attributes(self) -> None:
        exc = UnsupportedAssetClassError(
            asset_class="fixed_income",
            operation="compute_duration",
        )
        assert exc.asset_class == "fixed_income"
        assert exc.operation == "compute_duration"
        assert exc.error_code == "AST_007"
        assert "fixed_income" in str(exc)
        assert "compute_duration" in str(exc)

    def test_caught_as_asset_error(self) -> None:
        with pytest.raises(AssetError):
            raise UnsupportedAssetClassError("crypto", "price_feed")
