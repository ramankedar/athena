"""Unit tests for experiment domain core model types."""

from __future__ import annotations

import pytest

from athena.experiments.exceptions import InvalidExperimentError
from athena.experiments.models import (
    VALID_EXPERIMENT_TRANSITIONS,
    VALID_RUN_TRANSITIONS,
    ExperimentId,
    ExperimentStatus,
    RunGroupId,
    RunGroupPurpose,
    RunId,
    RunStatus,
    is_valid_experiment_transition,
    is_valid_run_transition,
)


class TestExperimentStatus:
    def test_values(self) -> None:
        assert ExperimentStatus.DRAFT == "draft"
        assert ExperimentStatus.ACTIVE == "active"
        assert ExperimentStatus.ARCHIVED == "archived"
        assert ExperimentStatus.CANCELLED == "cancelled"

    def test_is_terminal(self) -> None:
        assert ExperimentStatus.ARCHIVED.is_terminal is True
        assert ExperimentStatus.CANCELLED.is_terminal is True
        assert ExperimentStatus.DRAFT.is_terminal is False
        assert ExperimentStatus.ACTIVE.is_terminal is False

    def test_accepts_runs(self) -> None:
        assert ExperimentStatus.ACTIVE.accepts_runs is True
        assert ExperimentStatus.DRAFT.accepts_runs is False
        assert ExperimentStatus.ARCHIVED.accepts_runs is False


class TestRunStatus:
    def test_values(self) -> None:
        assert RunStatus.PENDING == "pending"
        assert RunStatus.RUNNING == "running"
        assert RunStatus.COMPLETED == "completed"
        assert RunStatus.FAILED == "failed"
        assert RunStatus.CANCELLED == "cancelled"

    def test_is_terminal(self) -> None:
        assert RunStatus.COMPLETED.is_terminal is True
        assert RunStatus.FAILED.is_terminal is True
        assert RunStatus.CANCELLED.is_terminal is True
        assert RunStatus.PENDING.is_terminal is False
        assert RunStatus.RUNNING.is_terminal is False

    def test_is_active(self) -> None:
        assert RunStatus.RUNNING.is_active is True
        assert RunStatus.PENDING.is_active is False
        assert RunStatus.COMPLETED.is_active is False


class TestRunGroupPurpose:
    def test_values(self) -> None:
        assert RunGroupPurpose.HYPERPARAMETER_SWEEP == "hyperparameter_sweep"
        assert RunGroupPurpose.WALK_FORWARD == "walk_forward"
        assert RunGroupPurpose.MONTE_CARLO == "monte_carlo"
        assert RunGroupPurpose.CROSS_VALIDATION == "cross_validation"
        assert RunGroupPurpose.SENSITIVITY_ANALYSIS == "sensitivity_analysis"
        assert RunGroupPurpose.MANUAL_COMPARISON == "manual_comparison"


class TestExperimentId:
    def test_generate_unique(self) -> None:
        ids = {ExperimentId.generate() for _ in range(50)}
        assert len(ids) == 50

    def test_str(self) -> None:
        eid = ExperimentId.generate()
        assert len(str(eid)) == 36  # UUID string

    def test_from_string_valid(self) -> None:
        eid = ExperimentId.generate()
        parsed = ExperimentId.from_string(str(eid))
        assert parsed == eid

    def test_from_string_invalid(self) -> None:
        with pytest.raises(InvalidExperimentError):
            ExperimentId.from_string("not-a-uuid")

    def test_equality(self) -> None:
        from uuid import UUID

        uuid = UUID("550e8400-e29b-41d4-a716-446655440000")
        assert ExperimentId(uuid) == ExperimentId(uuid)

    def test_repr(self) -> None:
        eid = ExperimentId.generate()
        assert "ExperimentId" in repr(eid)

    def test_hashable(self) -> None:
        eid = ExperimentId.generate()
        mapping = {eid: "value"}
        assert mapping[eid] == "value"


class TestRunId:
    def test_generate_unique(self) -> None:
        ids = {RunId.generate() for _ in range(50)}
        assert len(ids) == 50

    def test_from_string_valid(self) -> None:
        rid = RunId.generate()
        assert RunId.from_string(str(rid)) == rid

    def test_from_string_invalid(self) -> None:
        with pytest.raises(InvalidExperimentError):
            RunId.from_string("invalid")

    def test_repr(self) -> None:
        assert "RunId" in repr(RunId.generate())


class TestRunGroupId:
    def test_generate_unique(self) -> None:
        ids = {RunGroupId.generate() for _ in range(50)}
        assert len(ids) == 50

    def test_from_string_valid(self) -> None:
        gid = RunGroupId.generate()
        assert RunGroupId.from_string(str(gid)) == gid

    def test_from_string_invalid(self) -> None:
        with pytest.raises(InvalidExperimentError):
            RunGroupId.from_string("bad")


class TestStatusTransitions:
    def test_valid_experiment_transitions(self) -> None:
        assert is_valid_experiment_transition(ExperimentStatus.DRAFT, ExperimentStatus.ACTIVE)
        assert is_valid_experiment_transition(ExperimentStatus.ACTIVE, ExperimentStatus.ARCHIVED)
        assert is_valid_experiment_transition(ExperimentStatus.DRAFT, ExperimentStatus.CANCELLED)

    def test_invalid_experiment_transition(self) -> None:
        assert not is_valid_experiment_transition(
            ExperimentStatus.ARCHIVED, ExperimentStatus.ACTIVE
        )
        assert not is_valid_experiment_transition(
            ExperimentStatus.CANCELLED, ExperimentStatus.ACTIVE
        )
        assert not is_valid_experiment_transition(ExperimentStatus.DRAFT, ExperimentStatus.ARCHIVED)

    def test_same_status_experiment_is_valid(self) -> None:
        assert is_valid_experiment_transition(ExperimentStatus.ACTIVE, ExperimentStatus.ACTIVE)

    def test_valid_run_transitions(self) -> None:
        assert is_valid_run_transition(RunStatus.PENDING, RunStatus.RUNNING)
        assert is_valid_run_transition(RunStatus.RUNNING, RunStatus.COMPLETED)
        assert is_valid_run_transition(RunStatus.RUNNING, RunStatus.FAILED)
        assert is_valid_run_transition(RunStatus.PENDING, RunStatus.CANCELLED)

    def test_invalid_run_transition(self) -> None:
        assert not is_valid_run_transition(RunStatus.COMPLETED, RunStatus.RUNNING)
        assert not is_valid_run_transition(RunStatus.FAILED, RunStatus.RUNNING)
        assert not is_valid_run_transition(RunStatus.PENDING, RunStatus.COMPLETED)

    def test_same_status_run_is_valid(self) -> None:
        assert is_valid_run_transition(RunStatus.RUNNING, RunStatus.RUNNING)

    def test_valid_sets_not_empty(self) -> None:
        assert len(VALID_EXPERIMENT_TRANSITIONS) > 0
        assert len(VALID_RUN_TRANSITIONS) > 0
