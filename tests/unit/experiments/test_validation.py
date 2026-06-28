"""Unit tests for experiment domain validation utilities."""

from __future__ import annotations

from datetime import UTC, datetime

from athena.experiments.metadata import ReproducibilitySnapshot
from athena.experiments.models import ExperimentId, RunId, RunStatus
from athena.experiments.parameters import ParameterDefinition, ParameterSnapshot, ParameterValueType
from athena.experiments.registry import Experiment, ExperimentRun, ExperimentRunGroup
from athena.experiments.validation import (
    ValidationResult,
    validate_experiment,
    validate_parameter_snapshot,
    validate_reproducibility_snapshot,
    validate_run,
    validate_run_group,
)

NOW = datetime(2025, 1, 15, tzinfo=UTC)
LATER = datetime(2025, 1, 15, 11, 0, tzinfo=UTC)


class TestValidationResult:
    def test_ok(self) -> None:
        r = ValidationResult.ok()
        assert r.is_valid is True
        assert r.failures == ()

    def test_failed(self) -> None:
        r = ValidationResult.failed("err1", "err2")
        assert not r.is_valid
        assert len(r.failures) == 2

    def test_merge_ok_ok(self) -> None:
        assert ValidationResult.ok().merge(ValidationResult.ok()).is_valid

    def test_merge_ok_failed(self) -> None:
        merged = ValidationResult.ok().merge(ValidationResult.failed("bad"))
        assert not merged.is_valid


class TestValidateExperiment:
    def test_valid(self, basic_experiment: Experiment) -> None:
        result = validate_experiment(basic_experiment)
        assert result.is_valid

    def test_empty_name_via_duck_type(self) -> None:
        class FakeExp:
            name = ""

        result = validate_experiment(FakeExp())  # type: ignore[arg-type]
        assert not result.is_valid


class TestValidateRun:
    def test_valid_pending_run(self, pending_run: ExperimentRun) -> None:
        result = validate_run(pending_run)
        assert result.is_valid

    def test_started_after_completed_fails(
        self,
        run_id: RunId,
        exp_id: ExperimentId,
        rsi_param_snapshot: ParameterSnapshot,
        empty_metrics: object,
    ) -> None:

        class FakeRun:
            started_at = LATER
            completed_at = NOW  # earlier than started_at
            status = RunStatus.COMPLETED

        result = validate_run(FakeRun())  # type: ignore[arg-type]
        assert not result.is_valid

    def test_terminal_without_completed_at(self) -> None:
        class FakeRun:
            started_at = NOW
            completed_at = None
            status = RunStatus.COMPLETED  # terminal with no completed_at

        result = validate_run(FakeRun())  # type: ignore[arg-type]
        assert not result.is_valid


class TestValidateParameterSnapshot:
    def test_valid_all_present(self) -> None:
        snap = ParameterSnapshot.from_mapping({"period": "14"})
        defn = ParameterDefinition("period", ParameterValueType.INTEGER)
        result = validate_parameter_snapshot(snap, (defn,))
        assert result.is_valid

    def test_missing_required_fails(self) -> None:
        snap = ParameterSnapshot.from_mapping({})
        defn = ParameterDefinition("period", ParameterValueType.INTEGER, is_required=True)
        result = validate_parameter_snapshot(snap, (defn,))
        assert not result.is_valid
        assert "period" in result.failures[0]

    def test_optional_missing_is_ok(self) -> None:
        snap = ParameterSnapshot.from_mapping({})
        defn = ParameterDefinition("smoothing", ParameterValueType.STRING, is_required=False)
        result = validate_parameter_snapshot(snap, (defn,))
        assert result.is_valid

    def test_disallowed_value_fails(self) -> None:
        snap = ParameterSnapshot.from_mapping({"smoothing": "WMA"})
        defn = ParameterDefinition(
            "smoothing",
            ParameterValueType.STRING,
            allowed_values=("SMA", "EMA"),
        )
        result = validate_parameter_snapshot(snap, (defn,))
        assert not result.is_valid


class TestValidateReproducibilitySnapshot:
    def test_clean_snapshot_warns_about_nothing(
        self, reproducibility_snapshot: ReproducibilitySnapshot
    ) -> None:
        result = validate_reproducibility_snapshot(reproducibility_snapshot)
        assert result.is_valid

    def test_missing_commit_warns(self) -> None:
        snap = ReproducibilitySnapshot(random_seed=42)
        result = validate_reproducibility_snapshot(snap)
        assert not result.is_valid
        assert any("commit" in f.lower() for f in result.failures)

    def test_dirty_state_warns(self) -> None:
        snap = ReproducibilitySnapshot(git_commit_hash="abc", git_is_dirty=True)
        result = validate_reproducibility_snapshot(snap)
        assert not result.is_valid
        assert any("uncommitted" in f.lower() for f in result.failures)

    def test_missing_seed_warns(self) -> None:
        snap = ReproducibilitySnapshot(git_commit_hash="abc123")
        result = validate_reproducibility_snapshot(snap)
        assert not result.is_valid
        assert any("seed" in f.lower() for f in result.failures)


class TestValidateRunGroup:
    def test_valid_group(self, exp_id: ExperimentId) -> None:
        from athena.experiments.models import RunGroupId, RunGroupPurpose

        group = ExperimentRunGroup(
            group_id=RunGroupId.generate(),
            experiment_id=exp_id,
            name="valid_group",
            purpose=RunGroupPurpose.WALK_FORWARD,
            run_ids=(RunId.generate(),),
        )
        result = validate_run_group(group)
        assert result.is_valid

    def test_empty_name_via_duck_type(self, exp_id: ExperimentId) -> None:
        class FakeGroup:
            name = ""
            description = "D"
            feature_ids: tuple[()] = ()
            run_ids = (RunId.generate(),)

        result = validate_run_group(FakeGroup())  # type: ignore[arg-type]
        assert not result.is_valid

    def test_empty_run_ids_via_duck_type(self) -> None:
        class FakeGroup:
            name = "group"
            description = "D"
            run_ids: tuple[()] = ()

        result = validate_run_group(FakeGroup())  # type: ignore[arg-type]
        assert not result.is_valid
