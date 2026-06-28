"""Shared fixtures for feature domain unit tests."""

from __future__ import annotations

import pytest

from athena.features.dependencies import ImmutableDependencyGraph
from athena.features.metadata import FeatureMetadata
from athena.features.models import (
    FeatureId,
    FeatureNamespace,
    FeatureOutputType,
    FeatureVersion,
    InputDataType,
    InputTimeframe,
)
from athena.features.registry import FeatureDefinition
from athena.features.schemas import (
    FeatureOutputField,
    FeatureOutputSchema,
    InputRequirement,
)


@pytest.fixture
def v1() -> FeatureVersion:
    return FeatureVersion(1, 0, 0)


@pytest.fixture
def rsi_id() -> FeatureId:
    return FeatureId(FeatureNamespace.TECHNICAL, "rsi_14")


@pytest.fixture
def macd_id() -> FeatureId:
    return FeatureId(FeatureNamespace.TECHNICAL, "macd_12_26_9")


@pytest.fixture
def basic_metadata() -> FeatureMetadata:
    return FeatureMetadata(
        description="Test feature for unit tests.",
        author="Test Suite",
        tags=frozenset({"test", "unit"}),
    )


@pytest.fixture
def scalar_schema() -> FeatureOutputSchema:
    return FeatureOutputSchema(fields=(FeatureOutputField("value", FeatureOutputType.SCALAR),))


@pytest.fixture
def ohlcv_requirement() -> InputRequirement:
    return InputRequirement(
        data_type=InputDataType.OHLCV,
        timeframe=InputTimeframe.DAY_1,
        lookback_periods=14,
        min_periods=2,
    )


@pytest.fixture
def rsi_definition(
    rsi_id: FeatureId,
    v1: FeatureVersion,
    basic_metadata: FeatureMetadata,
    scalar_schema: FeatureOutputSchema,
    ohlcv_requirement: InputRequirement,
) -> FeatureDefinition:
    return FeatureDefinition(
        id=rsi_id,
        version=v1,
        display_name="RSI (14-period)",
        input_requirements=(ohlcv_requirement,),
        output_schema=scalar_schema,
        dependencies=ImmutableDependencyGraph.empty(),
        metadata=basic_metadata,
        parameters=(("period", "14"),),
    )
