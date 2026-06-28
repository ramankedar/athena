"""Unit tests for experiment domain exceptions."""

from __future__ import annotations

import pytest

from athena.experiments.exceptions import (
    DuplicateExperimentError,
    ExperimentError,
    ExperimentLineageCycleError,
    ExperimentNotFoundError,
    InvalidExperimentError,
    InvalidParameterError,
    InvalidRunStatusTransitionError,
    RunNotFoundError,
)
from athena.platform.exceptions import AthenaError


class TestExperimentError:
    def test_is_athena_error(self) -> None:
        assert issubclass(ExperimentError, AthenaError)


class TestExperimentNotFoundError:
    def test_attributes(self) -> None:
        exc = ExperimentNotFoundError("exp-id-123")
        assert exc.experiment_id == "exp-id-123"
        assert exc.error_code == "EXP_001"
        assert "exp-id-123" in str(exc)


class TestDuplicateExperimentError:
    def test_attributes(self) -> None:
        exc = DuplicateExperimentError("exp-id-123")
        assert exc.experiment_id == "exp-id-123"
        assert exc.error_code == "EXP_002"


class TestRunNotFoundError:
    def test_attributes(self) -> None:
        exc = RunNotFoundError("run-id-456")
        assert exc.run_id == "run-id-456"
        assert exc.error_code == "EXP_003"


class TestInvalidExperimentError:
    def test_attributes(self) -> None:
        exc = InvalidExperimentError("name must not be empty")
        assert exc.error_code == "EXP_004"

    def test_caught_as_experiment_error(self) -> None:
        with pytest.raises(ExperimentError):
            raise InvalidExperimentError("test")


class TestInvalidRunStatusTransitionError:
    def test_attributes(self) -> None:
        exc = InvalidRunStatusTransitionError("completed", "running", run_id="run-1")
        assert exc.from_status == "completed"
        assert exc.to_status == "running"
        assert exc.run_id == "run-1"
        assert exc.error_code == "EXP_005"

    def test_without_run_id(self) -> None:
        exc = InvalidRunStatusTransitionError("completed", "running")
        assert exc.run_id == ""


class TestExperimentLineageCycleError:
    def test_attributes(self) -> None:
        exc = ExperimentLineageCycleError("a -> b -> a")
        assert exc.cycle_path == "a -> b -> a"
        assert exc.error_code == "EXP_006"
        assert "->" in str(exc)


class TestInvalidParameterError:
    def test_attributes(self) -> None:
        exc = InvalidParameterError("period", "must be >= 1")
        assert exc.parameter_name == "period"
        assert exc.reason == "must be >= 1"
        assert exc.error_code == "EXP_007"
        assert "period" in str(exc)
