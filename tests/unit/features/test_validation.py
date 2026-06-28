"""Unit tests for feature domain validation utilities."""

from __future__ import annotations

from athena.features.dependencies import DependencyGraph, ImmutableDependencyGraph
from athena.features.models import FeatureId, FeatureNamespace, FeatureVersion
from athena.features.registry import FeatureDefinition, FeatureSet
from athena.features.validation import (
    ValidationResult,
    validate_dependency_graph,
    validate_feature_definition,
    validate_feature_set,
)


class TestValidationResult:
    def test_ok(self) -> None:
        r = ValidationResult.ok()
        assert r.is_valid is True
        assert r.failures == ()

    def test_failed(self) -> None:
        r = ValidationResult.failed("err1", "err2")
        assert r.is_valid is False
        assert len(r.failures) == 2

    def test_merge_ok_ok(self) -> None:
        assert ValidationResult.ok().merge(ValidationResult.ok()).is_valid

    def test_merge_ok_failed(self) -> None:
        merged = ValidationResult.ok().merge(ValidationResult.failed("bad"))
        assert not merged.is_valid
        assert "bad" in merged.failures

    def test_merge_two_failed(self) -> None:
        r1 = ValidationResult.failed("e1")
        r2 = ValidationResult.failed("e2")
        merged = r1.merge(r2)
        assert not merged.is_valid
        assert len(merged.failures) == 2


class TestValidateFeatureDefinition:
    def test_valid_definition(self, rsi_definition: FeatureDefinition) -> None:
        result = validate_feature_definition(rsi_definition)
        assert result.is_valid

    def test_unsorted_params_warning(self, rsi_definition: FeatureDefinition) -> None:
        """Unsorted parameters should produce a validation failure."""
        from athena.features.dependencies import ImmutableDependencyGraph
        from athena.features.metadata import FeatureMetadata
        from athena.features.models import FeatureOutputType, InputDataType
        from athena.features.schemas import (
            FeatureOutputField,
            FeatureOutputSchema,
            InputRequirement,
        )

        d = FeatureDefinition(
            id=FeatureId(FeatureNamespace.TECHNICAL, "x"),
            version=FeatureVersion(1, 0, 0),
            display_name="X",
            input_requirements=(InputRequirement(data_type=InputDataType.OHLCV),),
            output_schema=FeatureOutputSchema(
                fields=(FeatureOutputField("v", FeatureOutputType.SCALAR),)
            ),
            dependencies=ImmutableDependencyGraph.empty(),
            metadata=FeatureMetadata(description="D", author="A"),
            parameters=(("z", "last"), ("a", "first")),  # unsorted keys
        )
        result = validate_feature_definition(d)
        assert not result.is_valid


class TestValidateDependencyGraph:
    def test_valid_empty_graph(self) -> None:
        g = DependencyGraph()
        result = validate_dependency_graph(g)
        assert result.is_valid

    def test_valid_with_dependencies(self) -> None:
        g = DependencyGraph()
        g.add_dependency(
            FeatureId(FeatureNamespace.TECHNICAL, "b"),
            __import__(
                "athena.features.dependencies",
                fromlist=["FeatureDependency"],
            ).FeatureDependency(feature_id=FeatureId(FeatureNamespace.TECHNICAL, "a")),
        )
        result = validate_dependency_graph(g)
        assert result.is_valid

    def test_valid_immutable_graph(self) -> None:
        g = ImmutableDependencyGraph.empty()
        result = validate_dependency_graph(g)
        assert result.is_valid


class TestValidateFeatureSet:
    def test_valid_set(self) -> None:
        fs = FeatureSet(
            name="test",
            version=FeatureVersion(1, 0, 0),
            description="Test set",
            feature_ids=(FeatureId(FeatureNamespace.TECHNICAL, "rsi"),),
        )
        result = validate_feature_set(fs)
        assert result.is_valid

    def test_duplicate_feature_ids_via_duck_type(self) -> None:
        """Test the validator's own duplicate check."""

        class FakeFeatureSet:
            name = "s"
            description = "D"
            feature_ids = (
                FeatureId(FeatureNamespace.TECHNICAL, "rsi"),
                FeatureId(FeatureNamespace.TECHNICAL, "rsi"),  # duplicate
            )

        result = validate_feature_set(FakeFeatureSet())  # type: ignore[arg-type]
        assert not result.is_valid

    def test_empty_name_via_duck_type(self) -> None:
        class FakeSet:
            name = ""
            description = "D"
            feature_ids = (FeatureId(FeatureNamespace.TECHNICAL, "rsi"),)

        result = validate_feature_set(FakeSet())  # type: ignore[arg-type]
        assert not result.is_valid

    def test_empty_feature_ids_via_duck_type(self) -> None:
        class FakeSet:
            name = "s"
            description = "D"
            feature_ids: tuple[()] = ()

        result = validate_feature_set(FakeSet())  # type: ignore[arg-type]
        assert not result.is_valid
