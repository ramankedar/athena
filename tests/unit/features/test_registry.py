"""Unit tests for FeatureDefinition, FeatureSet, and InMemoryFeatureRegistry."""

from __future__ import annotations

import pytest

from athena.features.dependencies import ImmutableDependencyGraph
from athena.features.exceptions import (
    DuplicateFeatureError,
    FeatureNotFoundError,
    FeatureSetError,
    InvalidFeatureDefinitionError,
)
from athena.features.metadata import FeatureMetadata
from athena.features.models import (
    FeatureId,
    FeatureNamespace,
    FeatureOutputType,
    FeatureVersion,
    InputDataType,
    InputTimeframe,
)
from athena.features.registry import FeatureDefinition, FeatureSet, InMemoryFeatureRegistry
from athena.features.schemas import (
    FeatureOutputField,
    FeatureOutputSchema,
    InputRequirement,
)


def _make_def(
    name: str = "rsi_14",
    namespace: FeatureNamespace = FeatureNamespace.TECHNICAL,
    params: tuple[tuple[str, str], ...] = (("period", "14"),),
) -> FeatureDefinition:
    return FeatureDefinition(
        id=FeatureId(namespace, name),
        version=FeatureVersion(1, 0, 0),
        display_name=f"{name.upper()} feature",
        input_requirements=(
            InputRequirement(
                data_type=InputDataType.OHLCV,
                timeframe=InputTimeframe.DAY_1,
                lookback_periods=14,
            ),
        ),
        output_schema=FeatureOutputSchema(
            fields=(FeatureOutputField("value", FeatureOutputType.SCALAR),)
        ),
        dependencies=ImmutableDependencyGraph.empty(),
        metadata=FeatureMetadata(description="Test feature", author="Test"),
        parameters=params,
    )


class TestFeatureDefinition:
    def test_valid_construction(self, rsi_definition: FeatureDefinition) -> None:
        assert rsi_definition.display_name == "RSI (14-period)"
        assert rsi_definition.is_experimental is False

    def test_computation_hash_non_empty(self, rsi_definition: FeatureDefinition) -> None:
        assert len(rsi_definition.computation_hash) == 64  # SHA-256 hex

    def test_computation_hash_changes_with_version(self) -> None:
        d1 = _make_def()
        d2 = FeatureDefinition(
            id=d1.id,
            version=FeatureVersion(2, 0, 0),  # different version
            display_name=d1.display_name,
            input_requirements=d1.input_requirements,
            output_schema=d1.output_schema,
            dependencies=d1.dependencies,
            metadata=d1.metadata,
            parameters=d1.parameters,
        )
        assert d1.computation_hash != d2.computation_hash

    def test_computation_hash_same_for_same_content(self) -> None:
        d1 = _make_def()
        d2 = _make_def()
        assert d1.computation_hash == d2.computation_hash

    def test_computation_hash_unchanged_by_metadata(self) -> None:
        d1 = _make_def()
        d2 = FeatureDefinition(
            id=d1.id,
            version=d1.version,
            display_name=d1.display_name,
            input_requirements=d1.input_requirements,
            output_schema=d1.output_schema,
            dependencies=d1.dependencies,
            metadata=FeatureMetadata(
                description="DIFFERENT DESCRIPTION",
                author="DIFFERENT AUTHOR",
            ),
            parameters=d1.parameters,
        )
        assert d1.computation_hash == d2.computation_hash

    def test_empty_display_name_raises(self) -> None:
        with pytest.raises(InvalidFeatureDefinitionError, match="display_name"):
            FeatureDefinition(
                id=FeatureId(FeatureNamespace.TECHNICAL, "x"),
                version=FeatureVersion(1, 0, 0),
                display_name="   ",
                input_requirements=(InputRequirement(data_type=InputDataType.OHLCV),),
                output_schema=FeatureOutputSchema(
                    fields=(FeatureOutputField("v", FeatureOutputType.SCALAR),)
                ),
                dependencies=ImmutableDependencyGraph.empty(),
                metadata=FeatureMetadata(description="D", author="A"),
            )

    def test_empty_input_requirements_raises(self) -> None:
        with pytest.raises(InvalidFeatureDefinitionError, match="input_requirements"):
            FeatureDefinition(
                id=FeatureId(FeatureNamespace.TECHNICAL, "x"),
                version=FeatureVersion(1, 0, 0),
                display_name="Test",
                input_requirements=(),
                output_schema=FeatureOutputSchema(
                    fields=(FeatureOutputField("v", FeatureOutputType.SCALAR),)
                ),
                dependencies=ImmutableDependencyGraph.empty(),
                metadata=FeatureMetadata(description="D", author="A"),
            )

    def test_get_parameter_found(self, rsi_definition: FeatureDefinition) -> None:
        assert rsi_definition.get_parameter("period") == "14"

    def test_get_parameter_not_found(self, rsi_definition: FeatureDefinition) -> None:
        assert rsi_definition.get_parameter("nonexistent") is None

    def test_experimental_flag(self) -> None:
        d = FeatureDefinition(
            id=FeatureId(FeatureNamespace.CUSTOM, "exp_feature"),
            version=FeatureVersion(0, 1, 0),
            display_name="Experimental",
            input_requirements=(InputRequirement(data_type=InputDataType.OHLCV),),
            output_schema=FeatureOutputSchema(
                fields=(FeatureOutputField("v", FeatureOutputType.SCALAR),)
            ),
            dependencies=ImmutableDependencyGraph.empty(),
            metadata=FeatureMetadata(description="Exp", author="A"),
            is_experimental=True,
        )
        assert d.is_experimental is True

    def test_str(self, rsi_definition: FeatureDefinition) -> None:
        s = str(rsi_definition)
        assert "technical:rsi_14" in s
        assert "1.0.0" in s


class TestFeatureSet:
    def test_valid_construction(self) -> None:
        fs = FeatureSet(
            name="momentum",
            version=FeatureVersion(1, 0, 0),
            description="Momentum features",
            feature_ids=(
                FeatureId(FeatureNamespace.TECHNICAL, "rsi_14"),
                FeatureId(FeatureNamespace.TECHNICAL, "macd_12_26_9"),
            ),
        )
        assert len(fs) == 2

    def test_empty_name_raises(self) -> None:
        with pytest.raises(InvalidFeatureDefinitionError, match="name"):
            FeatureSet(
                name="",
                version=FeatureVersion(1, 0, 0),
                description="Desc",
                feature_ids=(FeatureId(FeatureNamespace.TECHNICAL, "rsi"),),
            )

    def test_empty_description_raises(self) -> None:
        with pytest.raises(InvalidFeatureDefinitionError, match="description"):
            FeatureSet(
                name="set",
                version=FeatureVersion(1, 0, 0),
                description="",
                feature_ids=(FeatureId(FeatureNamespace.TECHNICAL, "rsi"),),
            )

    def test_empty_feature_ids_raises(self) -> None:
        with pytest.raises(FeatureSetError, match="empty"):
            FeatureSet(
                name="set",
                version=FeatureVersion(1, 0, 0),
                description="Desc",
                feature_ids=(),
            )

    def test_duplicate_ids_raises(self) -> None:
        fid = FeatureId(FeatureNamespace.TECHNICAL, "rsi")
        with pytest.raises(FeatureSetError, match="duplicate"):
            FeatureSet(
                name="set",
                version=FeatureVersion(1, 0, 0),
                description="Desc",
                feature_ids=(fid, fid),
            )

    def test_contains_true(self) -> None:
        fid = FeatureId(FeatureNamespace.TECHNICAL, "rsi")
        fs = FeatureSet(
            name="s", version=FeatureVersion(1, 0, 0), description="D", feature_ids=(fid,)
        )
        assert fs.contains(fid) is True

    def test_contains_false(self) -> None:
        fs = FeatureSet(
            name="s",
            version=FeatureVersion(1, 0, 0),
            description="D",
            feature_ids=(FeatureId(FeatureNamespace.TECHNICAL, "rsi"),),
        )
        assert fs.contains(FeatureId(FeatureNamespace.TECHNICAL, "macd")) is False

    def test_str(self) -> None:
        fs = FeatureSet(
            name="test_set",
            version=FeatureVersion(1, 0, 0),
            description="D",
            feature_ids=(FeatureId(FeatureNamespace.TECHNICAL, "rsi"),),
        )
        s = str(fs)
        assert "test_set" in s
        assert "1 features" in s


class TestInMemoryFeatureRegistry:
    def test_empty_registry(self) -> None:
        r = InMemoryFeatureRegistry()
        assert len(r) == 0
        assert repr(r).startswith("InMemoryFeatureRegistry")

    def test_register_and_get(self, rsi_definition: FeatureDefinition) -> None:
        r = InMemoryFeatureRegistry()
        r.register(rsi_definition)
        result = r.get(rsi_definition.id)
        assert result is rsi_definition

    def test_register_duplicate_raises(self, rsi_definition: FeatureDefinition) -> None:
        r = InMemoryFeatureRegistry()
        r.register(rsi_definition)
        with pytest.raises(DuplicateFeatureError):
            r.register(rsi_definition)

    def test_register_or_replace(self, rsi_definition: FeatureDefinition) -> None:
        r = InMemoryFeatureRegistry()
        r.register(rsi_definition)
        updated = FeatureDefinition(
            id=rsi_definition.id,
            version=FeatureVersion(2, 0, 0),
            display_name="RSI v2",
            input_requirements=rsi_definition.input_requirements,
            output_schema=rsi_definition.output_schema,
            dependencies=rsi_definition.dependencies,
            metadata=rsi_definition.metadata,
        )
        r.register_or_replace(updated)
        assert r.get(rsi_definition.id).version == FeatureVersion(2, 0, 0)

    def test_get_not_found_raises(self) -> None:
        r = InMemoryFeatureRegistry()
        with pytest.raises(FeatureNotFoundError):
            r.get(FeatureId(FeatureNamespace.TECHNICAL, "unknown"))

    def test_get_or_none_found(self, rsi_definition: FeatureDefinition) -> None:
        r = InMemoryFeatureRegistry()
        r.register(rsi_definition)
        assert r.get_or_none(rsi_definition.id) is rsi_definition

    def test_get_or_none_not_found(self) -> None:
        r = InMemoryFeatureRegistry()
        assert r.get_or_none(FeatureId(FeatureNamespace.TECHNICAL, "x")) is None

    def test_exists(self, rsi_definition: FeatureDefinition) -> None:
        r = InMemoryFeatureRegistry()
        assert r.exists(rsi_definition.id) is False
        r.register(rsi_definition)
        assert r.exists(rsi_definition.id) is True

    def test_remove(self, rsi_definition: FeatureDefinition) -> None:
        r = InMemoryFeatureRegistry()
        r.register(rsi_definition)
        assert r.remove(rsi_definition.id) is True
        assert len(r) == 0

    def test_remove_not_found(self) -> None:
        r = InMemoryFeatureRegistry()
        assert r.remove(FeatureId(FeatureNamespace.TECHNICAL, "x")) is False

    def test_find_by_namespace(self) -> None:
        r = InMemoryFeatureRegistry()
        r.register(_make_def("rsi_14", FeatureNamespace.TECHNICAL))
        r.register(_make_def("iv_rank", FeatureNamespace.VOLATILITY))
        tech = r.find_by_namespace(FeatureNamespace.TECHNICAL)
        assert len(tech) == 1

    def test_find_by_tag(self, rsi_definition: FeatureDefinition) -> None:
        r = InMemoryFeatureRegistry()
        r.register(rsi_definition)
        results = r.find_by_tag("test")
        assert len(results) == 1

    def test_find_by_hash(self, rsi_definition: FeatureDefinition) -> None:
        r = InMemoryFeatureRegistry()
        r.register(rsi_definition)
        result = r.find_by_hash(rsi_definition.computation_hash)
        assert result is rsi_definition

    def test_find_by_hash_not_found(self) -> None:
        r = InMemoryFeatureRegistry()
        assert r.find_by_hash("nonexistent") is None

    def test_all_features(self, rsi_definition: FeatureDefinition) -> None:
        r = InMemoryFeatureRegistry()
        r.register(rsi_definition)
        all_f = r.all_features()
        assert len(all_f) == 1

    def test_count(self) -> None:
        r = InMemoryFeatureRegistry()
        r.register(_make_def("a", FeatureNamespace.TECHNICAL))
        r.register(_make_def("b", FeatureNamespace.VOLATILITY))
        assert r.count() == 2
        assert r.count(FeatureNamespace.TECHNICAL) == 1
        assert r.count(FeatureNamespace.VOLATILITY) == 1

    def test_register_set_and_get(self, rsi_definition: FeatureDefinition) -> None:
        r = InMemoryFeatureRegistry()
        r.register(rsi_definition)
        fs = FeatureSet(
            name="my_set",
            version=FeatureVersion(1, 0, 0),
            description="My feature set",
            feature_ids=(rsi_definition.id,),
        )
        r.register_set(fs)
        result = r.get_set("my_set")
        assert result is fs

    def test_get_set_not_found(self) -> None:
        r = InMemoryFeatureRegistry()
        with pytest.raises(FeatureNotFoundError):
            r.get_set("nonexistent")

    def test_resolve_set(self, rsi_definition: FeatureDefinition) -> None:
        r = InMemoryFeatureRegistry()
        r.register(rsi_definition)
        fs = FeatureSet(
            name="my_set",
            version=FeatureVersion(1, 0, 0),
            description="Desc",
            feature_ids=(rsi_definition.id,),
        )
        r.register_set(fs)
        resolved = r.resolve_set("my_set")
        assert len(resolved) == 1
        assert resolved[0] is rsi_definition

    def test_duplicate_set_raises(self, rsi_definition: FeatureDefinition) -> None:
        r = InMemoryFeatureRegistry()
        fs = FeatureSet(
            name="s",
            version=FeatureVersion(1, 0, 0),
            description="D",
            feature_ids=(rsi_definition.id,),
        )
        r.register_set(fs)
        with pytest.raises(DuplicateFeatureError):
            r.register_set(fs)
