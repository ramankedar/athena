"""Unit tests for Feature Domain core model types."""

from __future__ import annotations

import dataclasses

import pytest

from athena.features.exceptions import InvalidFeatureDefinitionError
from athena.features.models import (
    FeatureId,
    FeatureNamespace,
    FeatureOutputType,
    FeatureVersion,
    InputDataType,
    InputTimeframe,
)


class TestFeatureNamespace:
    def test_values(self) -> None:
        assert FeatureNamespace.TECHNICAL == "technical"
        assert FeatureNamespace.VOLATILITY == "volatility"
        assert FeatureNamespace.OPTIONS == "options"
        assert FeatureNamespace.MARKET_MICROSTRUCTURE == "market_microstructure"
        assert FeatureNamespace.MACRO == "macro"
        assert FeatureNamespace.FUNDAMENTAL == "fundamental"
        assert FeatureNamespace.CUSTOM == "custom"

    def test_is_str(self) -> None:
        assert isinstance(FeatureNamespace.TECHNICAL, str)

    def test_count(self) -> None:
        assert len(FeatureNamespace) == 7


class TestFeatureOutputType:
    def test_values(self) -> None:
        assert FeatureOutputType.SCALAR == "scalar"
        assert FeatureOutputType.VECTOR == "vector"
        assert FeatureOutputType.BOOLEAN == "boolean"
        assert FeatureOutputType.CATEGORICAL == "categorical"
        assert FeatureOutputType.RANKING == "ranking"
        assert FeatureOutputType.SERIES == "series"


class TestInputDataType:
    def test_values(self) -> None:
        assert InputDataType.OHLCV == "ohlcv"
        assert InputDataType.TICK == "tick"
        assert InputDataType.ORDER_BOOK == "order_book"
        assert InputDataType.OPTION_CHAIN == "option_chain"
        assert InputDataType.FUNDAMENTAL == "fundamental"

    def test_count(self) -> None:
        assert len(InputDataType) == 8


class TestInputTimeframe:
    def test_values_match_market_data_codes(self) -> None:
        assert InputTimeframe.MINUTE_1 == "1T"
        assert InputTimeframe.HOUR_1 == "1H"
        assert InputTimeframe.DAY_1 == "1D"
        assert InputTimeframe.WEEK_1 == "1W"
        assert InputTimeframe.MONTH_1 == "1M"

    def test_tick_value(self) -> None:
        assert InputTimeframe.TICK == "tick"


class TestFeatureVersion:
    def test_valid_construction(self) -> None:
        v = FeatureVersion(1, 2, 3)
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_str(self) -> None:
        assert str(FeatureVersion(1, 2, 3)) == "1.2.3"

    def test_is_frozen(self) -> None:
        v = FeatureVersion(1, 0, 0)
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            v.major = 2  # type: ignore[misc]

    def test_negative_major_raises(self) -> None:
        with pytest.raises(InvalidFeatureDefinitionError, match="major"):
            FeatureVersion(-1, 0, 0)

    def test_negative_minor_raises(self) -> None:
        with pytest.raises(InvalidFeatureDefinitionError, match="minor"):
            FeatureVersion(1, -1, 0)

    def test_negative_patch_raises(self) -> None:
        with pytest.raises(InvalidFeatureDefinitionError, match="patch"):
            FeatureVersion(1, 0, -1)

    def test_ordering_major(self) -> None:
        assert FeatureVersion(2, 0, 0) > FeatureVersion(1, 0, 0)

    def test_ordering_minor(self) -> None:
        assert FeatureVersion(1, 2, 0) > FeatureVersion(1, 1, 0)

    def test_ordering_patch(self) -> None:
        assert FeatureVersion(1, 0, 1) > FeatureVersion(1, 0, 0)

    def test_equality(self) -> None:
        assert FeatureVersion(1, 0, 0) == FeatureVersion(1, 0, 0)

    def test_satisfies_gte(self) -> None:
        assert FeatureVersion(1, 2, 0).satisfies(">=1.0.0") is True
        assert FeatureVersion(0, 9, 0).satisfies(">=1.0.0") is False

    def test_satisfies_eq(self) -> None:
        assert FeatureVersion(1, 0, 0).satisfies("==1.0.0") is True
        assert FeatureVersion(1, 0, 1).satisfies("==1.0.0") is False

    def test_satisfies_gt(self) -> None:
        assert FeatureVersion(1, 1, 0).satisfies(">1.0.0") is True
        assert FeatureVersion(1, 0, 0).satisfies(">1.0.0") is False

    def test_satisfies_lte(self) -> None:
        assert FeatureVersion(1, 0, 0).satisfies("<=1.0.0") is True
        assert FeatureVersion(1, 1, 0).satisfies("<=1.0.0") is False

    def test_satisfies_lt(self) -> None:
        assert FeatureVersion(0, 9, 0).satisfies("<1.0.0") is True
        assert FeatureVersion(1, 0, 0).satisfies("<1.0.0") is False

    def test_satisfies_neq(self) -> None:
        assert FeatureVersion(1, 1, 0).satisfies("!=1.0.0") is True
        assert FeatureVersion(1, 0, 0).satisfies("!=1.0.0") is False

    def test_satisfies_invalid_constraint(self) -> None:
        with pytest.raises(ValueError, match="Unsupported"):
            FeatureVersion(1, 0, 0).satisfies("~1.0.0")

    def test_from_string_valid(self) -> None:
        v = FeatureVersion.from_string("2.4.1")
        assert v.major == 2
        assert v.minor == 4
        assert v.patch == 1

    def test_from_string_invalid_format(self) -> None:
        with pytest.raises(InvalidFeatureDefinitionError, match=r"major\.minor\.patch"):
            FeatureVersion.from_string("1.2")

    def test_from_string_non_integer(self) -> None:
        with pytest.raises(InvalidFeatureDefinitionError, match="integers"):
            FeatureVersion.from_string("a.b.c")

    def test_zero_version_valid(self) -> None:
        v = FeatureVersion.from_string("0.0.0")
        assert v == FeatureVersion(0, 0, 0)


class TestFeatureId:
    def test_valid_construction(self) -> None:
        fid = FeatureId(FeatureNamespace.TECHNICAL, "rsi_14")
        assert fid.namespace == FeatureNamespace.TECHNICAL
        assert fid.name == "rsi_14"

    def test_str(self) -> None:
        fid = FeatureId(FeatureNamespace.TECHNICAL, "rsi_14")
        assert str(fid) == "technical:rsi_14"

    def test_repr(self) -> None:
        fid = FeatureId(FeatureNamespace.TECHNICAL, "rsi_14")
        r = repr(fid)
        assert "technical" in r
        assert "rsi_14" in r

    def test_empty_name_raises(self) -> None:
        with pytest.raises(InvalidFeatureDefinitionError, match="empty"):
            FeatureId(FeatureNamespace.TECHNICAL, "")

    def test_uppercase_raises(self) -> None:
        with pytest.raises(InvalidFeatureDefinitionError, match="invalid characters"):
            FeatureId(FeatureNamespace.TECHNICAL, "RSI_14")

    def test_hyphen_raises(self) -> None:
        with pytest.raises(InvalidFeatureDefinitionError, match="invalid characters"):
            FeatureId(FeatureNamespace.TECHNICAL, "rsi-14")

    def test_valid_with_digits(self) -> None:
        fid = FeatureId(FeatureNamespace.TECHNICAL, "macd_12_26_9")
        assert fid.name == "macd_12_26_9"

    def test_is_frozen(self) -> None:
        fid = FeatureId(FeatureNamespace.TECHNICAL, "rsi_14")
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            fid.name = "other"  # type: ignore[misc]

    def test_equality(self) -> None:
        a = FeatureId(FeatureNamespace.TECHNICAL, "rsi_14")
        b = FeatureId(FeatureNamespace.TECHNICAL, "rsi_14")
        assert a == b

    def test_different_namespaces_not_equal(self) -> None:
        a = FeatureId(FeatureNamespace.TECHNICAL, "rsi_14")
        b = FeatureId(FeatureNamespace.VOLATILITY, "rsi_14")
        assert a != b

    def test_hashable(self) -> None:
        fid = FeatureId(FeatureNamespace.TECHNICAL, "rsi_14")
        mapping = {fid: "rsi"}
        assert mapping[fid] == "rsi"

    def test_parse_valid(self) -> None:
        fid = FeatureId.parse("technical:rsi_14")
        assert fid.namespace == FeatureNamespace.TECHNICAL
        assert fid.name == "rsi_14"

    def test_parse_no_separator_raises(self) -> None:
        with pytest.raises(InvalidFeatureDefinitionError, match="namespace:name"):
            FeatureId.parse("technical_rsi_14")

    def test_parse_unknown_namespace_raises(self) -> None:
        with pytest.raises(InvalidFeatureDefinitionError, match="Unknown feature namespace"):
            FeatureId.parse("unknown:rsi_14")

    def test_parse_roundtrip(self) -> None:
        fid = FeatureId(FeatureNamespace.OPTIONS, "iv_rank")
        assert FeatureId.parse(str(fid)) == fid
