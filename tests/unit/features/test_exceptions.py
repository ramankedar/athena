"""Unit tests for feature domain exceptions."""

from __future__ import annotations

import pytest

from athena.features.exceptions import (
    CyclicDependencyError,
    DuplicateFeatureError,
    FeatureError,
    FeatureNotFoundError,
    FeatureSetError,
    InvalidFeatureDefinitionError,
    InvalidInputRequirementError,
    VersionConflictError,
)
from athena.platform.exceptions import AthenaError


class TestFeatureError:
    def test_is_athena_error(self) -> None:
        assert issubclass(FeatureError, AthenaError)


class TestFeatureNotFoundError:
    def test_attributes(self) -> None:
        exc = FeatureNotFoundError("technical:rsi_14")
        assert exc.feature_id == "technical:rsi_14"
        assert exc.error_code == "FTR_001"
        assert "rsi_14" in str(exc)

    def test_caught_as_feature_error(self) -> None:
        with pytest.raises(FeatureError):
            raise FeatureNotFoundError("x")


class TestDuplicateFeatureError:
    def test_attributes(self) -> None:
        exc = DuplicateFeatureError("technical:rsi_14")
        assert exc.feature_id == "technical:rsi_14"
        assert exc.error_code == "FTR_002"


class TestInvalidFeatureDefinitionError:
    def test_attributes(self) -> None:
        exc = InvalidFeatureDefinitionError("name must not be empty", field="name")
        assert "name" in str(exc)
        assert exc.error_code == "FTR_003"


class TestCyclicDependencyError:
    def test_attributes(self) -> None:
        exc = CyclicDependencyError("a -> b -> a")
        assert exc.cycle_path == "a -> b -> a"
        assert exc.error_code == "FTR_004"
        assert "->" in str(exc)


class TestVersionConflictError:
    def test_attributes(self) -> None:
        exc = VersionConflictError("technical:rsi", ">=2.0.0", "1.5.0")
        assert exc.feature_id == "technical:rsi"
        assert exc.required_constraint == ">=2.0.0"
        assert exc.actual_version == "1.5.0"
        assert exc.error_code == "FTR_005"


class TestInvalidInputRequirementError:
    def test_attributes(self) -> None:
        exc = InvalidInputRequirementError("lookback must be >= 1")
        assert exc.error_code == "FTR_006"


class TestFeatureSetError:
    def test_attributes(self) -> None:
        exc = FeatureSetError("feature set is empty")
        assert exc.error_code == "FTR_007"

    def test_caught_as_feature_error(self) -> None:
        with pytest.raises(FeatureError):
            raise FeatureSetError("empty")
