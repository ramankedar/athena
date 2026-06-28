"""Unit tests for input requirements and output schemas."""

from __future__ import annotations

import pytest

from athena.features.exceptions import (
    InvalidFeatureDefinitionError,
    InvalidInputRequirementError,
)
from athena.features.models import FeatureOutputType, InputDataType, InputTimeframe
from athena.features.schemas import (
    FeatureOutputField,
    FeatureOutputSchema,
    InputRequirement,
)


class TestInputRequirement:
    def test_valid_ohlcv(self) -> None:
        req = InputRequirement(
            data_type=InputDataType.OHLCV,
            timeframe=InputTimeframe.DAY_1,
            lookback_periods=14,
            min_periods=2,
        )
        assert req.lookback_periods == 14
        assert req.effective_min_periods == 2

    def test_valid_no_lookback(self) -> None:
        req = InputRequirement(data_type=InputDataType.OHLCV)
        assert req.lookback_periods is None
        assert req.effective_min_periods is None

    def test_zero_lookback_raises(self) -> None:
        with pytest.raises(InvalidInputRequirementError, match="lookback_periods"):
            InputRequirement(data_type=InputDataType.OHLCV, lookback_periods=0)

    def test_zero_min_periods_raises(self) -> None:
        with pytest.raises(InvalidInputRequirementError, match="min_periods"):
            InputRequirement(
                data_type=InputDataType.OHLCV,
                lookback_periods=14,
                min_periods=0,
            )

    def test_min_periods_exceeds_lookback_raises(self) -> None:
        with pytest.raises(InvalidInputRequirementError, match="min_periods"):
            InputRequirement(
                data_type=InputDataType.OHLCV,
                lookback_periods=5,
                min_periods=10,
            )

    def test_effective_min_periods_fallback(self) -> None:
        req = InputRequirement(
            data_type=InputDataType.OHLCV,
            lookback_periods=20,
        )
        assert req.effective_min_periods == 20

    def test_option_chain_no_timeframe(self) -> None:
        req = InputRequirement(data_type=InputDataType.OPTION_CHAIN)
        assert req.timeframe is None

    def test_str(self) -> None:
        req = InputRequirement(
            data_type=InputDataType.OHLCV,
            timeframe=InputTimeframe.DAY_1,
            lookback_periods=14,
        )
        s = str(req)
        assert "ohlcv" in s
        assert "1D" in s


class TestFeatureOutputField:
    def test_valid_scalar(self) -> None:
        f = FeatureOutputField("rsi", FeatureOutputType.SCALAR)
        assert f.name == "rsi"
        assert f.output_type == FeatureOutputType.SCALAR

    def test_empty_name_raises(self) -> None:
        with pytest.raises(InvalidFeatureDefinitionError, match="name"):
            FeatureOutputField("", FeatureOutputType.SCALAR)

    def test_with_units(self) -> None:
        f = FeatureOutputField("return", FeatureOutputType.SCALAR, units="percent")
        assert f.units == "percent"

    def test_str(self) -> None:
        f = FeatureOutputField("macd_line", FeatureOutputType.SCALAR)
        s = str(f)
        assert "macd_line" in s
        assert "scalar" in s


class TestFeatureOutputSchema:
    def test_single_scalar(self) -> None:
        schema = FeatureOutputSchema(fields=(FeatureOutputField("rsi", FeatureOutputType.SCALAR),))
        assert schema.is_scalar is True
        assert len(schema) == 1

    def test_multi_field_vector(self) -> None:
        schema = FeatureOutputSchema(
            fields=(
                FeatureOutputField("macd_line", FeatureOutputType.SCALAR),
                FeatureOutputField("signal_line", FeatureOutputType.SCALAR),
                FeatureOutputField("histogram", FeatureOutputType.SCALAR),
            )
        )
        assert schema.is_scalar is False
        assert len(schema) == 3

    def test_field_names(self) -> None:
        schema = FeatureOutputSchema(
            fields=(
                FeatureOutputField("a", FeatureOutputType.SCALAR),
                FeatureOutputField("b", FeatureOutputType.SCALAR),
            )
        )
        assert schema.field_names == ("a", "b")

    def test_empty_fields_raises(self) -> None:
        with pytest.raises(InvalidFeatureDefinitionError, match="at least one"):
            FeatureOutputSchema(fields=())

    def test_duplicate_names_raises(self) -> None:
        with pytest.raises(InvalidFeatureDefinitionError, match="duplicate"):
            FeatureOutputSchema(
                fields=(
                    FeatureOutputField("x", FeatureOutputType.SCALAR),
                    FeatureOutputField("x", FeatureOutputType.SCALAR),
                )
            )

    def test_get_field_found(self) -> None:
        schema = FeatureOutputSchema(
            fields=(
                FeatureOutputField("line", FeatureOutputType.SCALAR),
                FeatureOutputField("signal", FeatureOutputType.SCALAR),
            )
        )
        f = schema.get_field("line")
        assert f is not None
        assert f.name == "line"

    def test_get_field_not_found(self) -> None:
        schema = FeatureOutputSchema(
            fields=(FeatureOutputField("value", FeatureOutputType.SCALAR),)
        )
        assert schema.get_field("nonexistent") is None

    def test_str(self) -> None:
        schema = FeatureOutputSchema(fields=(FeatureOutputField("rsi", FeatureOutputType.SCALAR),))
        assert "rsi" in str(schema)

    def test_boolean_output_not_scalar(self) -> None:
        schema = FeatureOutputSchema(
            fields=(FeatureOutputField("signal", FeatureOutputType.BOOLEAN),)
        )
        assert schema.is_scalar is False
