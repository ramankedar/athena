"""Unit tests for Experiment, ExperimentRun, ExperimentRunGroup, and registry."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from athena.experiments.exceptions import (
    DuplicateExperimentError,
    ExperimentNotFoundError,
    InvalidExperimentError,
    InvalidRunStatusTransitionError,
    RunNotFoundError,
)
from athena.experiments.metrics import ExperimentMetric, MetricDirection, MetricSnapshot
from athena.experiments.models import (
    ExperimentId,
    ExperimentStatus,
    RunGroupId,
    RunGroupPurpose,
    RunId,
    RunStatus,
)
from athena.experiments.parameters import ParameterSnapshot
from athena.experiments.registry import (
    Experiment,
    ExperimentRun,
    ExperimentRunGroup,
    InMemoryExperimentRegistry,
)

NOW = datetime(2025, 1, 15, 10, 0, tzinfo=UTC)
LATER = datetime(2025, 1, 15, 11, 0, tzinfo=UTC)


class TestExperiment:
    def test_valid_construction(self, basic_experiment: Experiment) -> None:
        assert basic_experiment.name == "RSI Momentum Backtest"
        assert basic_experiment.status == ExperimentStatus.ACTIVE

    def test_empty_name_raises(self, basic_metadata: object) -> None:
        from athena.experiments.exceptions import InvalidExperimentError
        from athena.experiments.metadata import ExperimentMetadata

        meta = ExperimentMetadata(author="A", description="D")
        with pytest.raises(InvalidExperimentError, match="name"):
            Experiment(
                id=ExperimentId.generate(),
                name="   ",
                status=ExperimentStatus.DRAFT,
                metadata=meta,
            )

    def test_accepts_runs_active(self, basic_experiment: Experiment) -> None:
        assert basic_experiment.accepts_runs is True

    def test_accepts_runs_draft(self, basic_metadata: object) -> None:
        from athena.experiments.metadata import ExperimentMetadata

        meta = ExperimentMetadata(author="A", description="D")
        exp = Experiment(
            id=ExperimentId.generate(),
            name="Draft Exp",
            status=ExperimentStatus.DRAFT,
            metadata=meta,
        )
        assert exp.accepts_runs is False

    def test_template_does_not_accept_runs(self, basic_metadata: object) -> None:
        from athena.experiments.metadata import ExperimentMetadata

        meta = ExperimentMetadata(author="A", description="D")
        exp = Experiment(
            id=ExperimentId.generate(),
            name="Template",
            status=ExperimentStatus.ACTIVE,
            metadata=meta,
            is_template=True,
        )
        assert exp.accepts_runs is False

    def test_str(self, basic_experiment: Experiment) -> None:
        s = str(basic_experiment)
        assert "RSI Momentum Backtest" in s
        assert "active" in s


class TestExperimentRun:
    def test_valid_pending_run(self, pending_run: ExperimentRun) -> None:
        assert pending_run.status == RunStatus.PENDING
        assert pending_run.is_running is False

    def test_naive_started_at_raises(
        self,
        run_id: RunId,
        exp_id: ExperimentId,
        rsi_param_snapshot: ParameterSnapshot,
        empty_metrics: MetricSnapshot,
    ) -> None:
        with pytest.raises(InvalidExperimentError, match="started_at"):
            ExperimentRun(
                run_id=run_id,
                experiment_id=exp_id,
                status=RunStatus.RUNNING,
                parameter_snapshot=rsi_param_snapshot,
                metric_snapshot=empty_metrics,
                started_at=datetime(2025, 1, 15, 10),  # naive
            )

    def test_duration_seconds(
        self,
        run_id: RunId,
        exp_id: ExperimentId,
        rsi_param_snapshot: ParameterSnapshot,
        empty_metrics: MetricSnapshot,
    ) -> None:
        run = ExperimentRun(
            run_id=run_id,
            experiment_id=exp_id,
            status=RunStatus.COMPLETED,
            parameter_snapshot=rsi_param_snapshot,
            metric_snapshot=empty_metrics,
            started_at=NOW,
            completed_at=LATER,
        )
        assert run.duration_seconds == 3600.0

    def test_duration_none_when_not_started(self, pending_run: ExperimentRun) -> None:
        assert pending_run.duration_seconds is None

    def test_str(self, pending_run: ExperimentRun) -> None:
        s = str(pending_run)
        assert "pending" in s


class TestExperimentRunGroup:
    def test_valid_construction(self, exp_id: ExperimentId) -> None:
        run_ids = tuple(RunId.generate() for _ in range(3))
        group = ExperimentRunGroup(
            group_id=RunGroupId.generate(),
            experiment_id=exp_id,
            name="sweep_v1",
            purpose=RunGroupPurpose.HYPERPARAMETER_SWEEP,
            run_ids=run_ids,
        )
        assert group.size == 3

    def test_empty_name_raises(self, exp_id: ExperimentId) -> None:
        with pytest.raises(InvalidExperimentError, match="name"):
            ExperimentRunGroup(
                group_id=RunGroupId.generate(),
                experiment_id=exp_id,
                name="",
                purpose=RunGroupPurpose.WALK_FORWARD,
                run_ids=(RunId.generate(),),
            )

    def test_duplicate_run_ids_raises(self, exp_id: ExperimentId) -> None:
        rid = RunId.generate()
        with pytest.raises(InvalidExperimentError, match="duplicate"):
            ExperimentRunGroup(
                group_id=RunGroupId.generate(),
                experiment_id=exp_id,
                name="sweep",
                purpose=RunGroupPurpose.MONTE_CARLO,
                run_ids=(rid, rid),
            )

    def test_contains(self, exp_id: ExperimentId) -> None:
        rid = RunId.generate()
        group = ExperimentRunGroup(
            group_id=RunGroupId.generate(),
            experiment_id=exp_id,
            name="g",
            purpose=RunGroupPurpose.WALK_FORWARD,
            run_ids=(rid,),
        )
        assert group.contains(rid) is True
        assert group.contains(RunId.generate()) is False

    def test_str(self, exp_id: ExperimentId) -> None:
        group = ExperimentRunGroup(
            group_id=RunGroupId.generate(),
            experiment_id=exp_id,
            name="test_group",
            purpose=RunGroupPurpose.HYPERPARAMETER_SWEEP,
            run_ids=(RunId.generate(),),
        )
        s = str(group)
        assert "test_group" in s
        assert "hyperparameter_sweep" in s


class TestInMemoryExperimentRegistry:
    def test_empty_registry(self) -> None:
        r = InMemoryExperimentRegistry()
        assert len(r) == 0
        assert "experiments=0" in repr(r)

    def test_register_and_get(self, basic_experiment: Experiment) -> None:
        r = InMemoryExperimentRegistry()
        r.register(basic_experiment)
        found = r.get_experiment(basic_experiment.id)
        assert found is basic_experiment

    def test_register_duplicate_raises(self, basic_experiment: Experiment) -> None:
        r = InMemoryExperimentRegistry()
        r.register(basic_experiment)
        with pytest.raises(DuplicateExperimentError):
            r.register(basic_experiment)

    def test_get_not_found_raises(self) -> None:
        r = InMemoryExperimentRegistry()
        with pytest.raises(ExperimentNotFoundError):
            r.get_experiment(ExperimentId.generate())

    def test_get_or_none(self, basic_experiment: Experiment) -> None:
        r = InMemoryExperimentRegistry()
        r.register(basic_experiment)
        assert r.get_experiment_or_none(basic_experiment.id) is basic_experiment
        assert r.get_experiment_or_none(ExperimentId.generate()) is None

    def test_update_experiment_status(self, basic_experiment: Experiment) -> None:
        r = InMemoryExperimentRegistry()
        r.register(basic_experiment)
        updated = r.update_experiment_status(basic_experiment.id, ExperimentStatus.ARCHIVED)
        assert updated.status == ExperimentStatus.ARCHIVED

    def test_invalid_status_transition_raises(self, basic_experiment: Experiment) -> None:
        r = InMemoryExperimentRegistry()
        r.register(basic_experiment)
        with pytest.raises(InvalidExperimentError):
            r.update_experiment_status(basic_experiment.id, ExperimentStatus.DRAFT)

    def test_find_by_status(self, basic_experiment: Experiment) -> None:
        r = InMemoryExperimentRegistry()
        r.register(basic_experiment)
        active = r.find_by_status(ExperimentStatus.ACTIVE)
        assert basic_experiment in active

    def test_find_by_tag(self, basic_experiment: Experiment) -> None:
        r = InMemoryExperimentRegistry()
        r.register(basic_experiment)
        found = r.find_by_tag("test")
        assert basic_experiment in found
        assert r.find_by_tag("nonexistent") == ()

    def test_all_experiments(self, basic_experiment: Experiment) -> None:
        r = InMemoryExperimentRegistry()
        r.register(basic_experiment)
        assert len(r.all_experiments()) == 1

    def test_register_run(self, basic_experiment: Experiment, pending_run: ExperimentRun) -> None:
        r = InMemoryExperimentRegistry()
        r.register(basic_experiment)
        r.register_run(pending_run)
        found = r.get_run(pending_run.run_id)
        assert found is pending_run

    def test_register_run_missing_experiment_raises(self, pending_run: ExperimentRun) -> None:
        r = InMemoryExperimentRegistry()
        with pytest.raises(ExperimentNotFoundError):
            r.register_run(pending_run)

    def test_register_run_duplicate_raises(
        self, basic_experiment: Experiment, pending_run: ExperimentRun
    ) -> None:
        r = InMemoryExperimentRegistry()
        r.register(basic_experiment)
        r.register_run(pending_run)
        with pytest.raises(InvalidExperimentError):
            r.register_run(pending_run)

    def test_get_run_not_found_raises(self) -> None:
        r = InMemoryExperimentRegistry()
        with pytest.raises(RunNotFoundError):
            r.get_run(RunId.generate())

    def test_advance_run_status(
        self, basic_experiment: Experiment, pending_run: ExperimentRun
    ) -> None:
        r = InMemoryExperimentRegistry()
        r.register(basic_experiment)
        r.register_run(pending_run)
        updated = r.advance_run_status(pending_run.run_id, RunStatus.RUNNING, started_at=NOW)
        assert updated.status == RunStatus.RUNNING
        assert updated.started_at == NOW

    def test_invalid_run_transition_raises(
        self, basic_experiment: Experiment, pending_run: ExperimentRun
    ) -> None:
        r = InMemoryExperimentRegistry()
        r.register(basic_experiment)
        r.register_run(pending_run)
        with pytest.raises(InvalidRunStatusTransitionError):
            r.advance_run_status(pending_run.run_id, RunStatus.COMPLETED)

    def test_record_metrics(self, basic_experiment: Experiment, pending_run: ExperimentRun) -> None:
        r = InMemoryExperimentRegistry()
        r.register(basic_experiment)
        r.register_run(pending_run)
        metric = ExperimentMetric("sharpe", 1.5, MetricDirection.HIGHER_IS_BETTER)
        updated = r.record_metrics(pending_run.run_id, (metric,))
        assert updated.metric_snapshot.get("sharpe") is not None

    def test_record_artifact(
        self, basic_experiment: Experiment, pending_run: ExperimentRun
    ) -> None:
        from athena.experiments.artifacts import ArtifactLocation, ArtifactType, ExperimentArtifact

        r = InMemoryExperimentRegistry()
        r.register(basic_experiment)
        r.register_run(pending_run)
        art = ExperimentArtifact.create(
            run_id=pending_run.run_id,
            name="results",
            artifact_type=ArtifactType.BACKTEST_RESULTS,
            location=ArtifactLocation("s3://bucket/results.parquet", "s3"),
        )
        updated = r.record_artifact(pending_run.run_id, art)
        assert len(updated.artifacts) == 1

    def test_runs_for_experiment(
        self, basic_experiment: Experiment, pending_run: ExperimentRun
    ) -> None:
        r = InMemoryExperimentRegistry()
        r.register(basic_experiment)
        r.register_run(pending_run)
        runs = r.runs_for_experiment(basic_experiment.id)
        assert len(runs) == 1

    def test_runs_by_status(self, basic_experiment: Experiment, pending_run: ExperimentRun) -> None:
        r = InMemoryExperimentRegistry()
        r.register(basic_experiment)
        r.register_run(pending_run)
        pending = r.runs_by_status(RunStatus.PENDING)
        assert pending_run in pending
        assert r.runs_by_status(RunStatus.RUNNING) == ()

    def test_run_group(self, basic_experiment: Experiment, pending_run: ExperimentRun) -> None:
        r = InMemoryExperimentRegistry()
        r.register(basic_experiment)
        r.register_run(pending_run)
        group = ExperimentRunGroup(
            group_id=RunGroupId.generate(),
            experiment_id=basic_experiment.id,
            name="sweep",
            purpose=RunGroupPurpose.HYPERPARAMETER_SWEEP,
            run_ids=(pending_run.run_id,),
        )
        r.register_run_group(group)
        found = r.get_run_group(group.group_id)
        assert found is group

    def test_get_run_group_not_found(self) -> None:
        r = InMemoryExperimentRegistry()
        with pytest.raises(RunNotFoundError):
            r.get_run_group(RunGroupId.generate())

    def test_duplicate_run_group_raises(self, basic_experiment: Experiment) -> None:
        r = InMemoryExperimentRegistry()
        r.register(basic_experiment)
        group = ExperimentRunGroup(
            group_id=RunGroupId.generate(),
            experiment_id=basic_experiment.id,
            name="g",
            purpose=RunGroupPurpose.WALK_FORWARD,
            run_ids=(RunId.generate(),),
        )
        r.register_run_group(group)
        with pytest.raises(InvalidExperimentError):
            r.register_run_group(group)

    def test_groups_for_experiment(self, basic_experiment: Experiment) -> None:
        r = InMemoryExperimentRegistry()
        r.register(basic_experiment)
        group = ExperimentRunGroup(
            group_id=RunGroupId.generate(),
            experiment_id=basic_experiment.id,
            name="g",
            purpose=RunGroupPurpose.MONTE_CARLO,
            run_ids=(RunId.generate(),),
        )
        r.register_run_group(group)
        groups = r.groups_for_experiment(basic_experiment.id)
        assert len(groups) == 1

    def test_run_count(self, basic_experiment: Experiment, pending_run: ExperimentRun) -> None:
        r = InMemoryExperimentRegistry()
        r.register(basic_experiment)
        r.register_run(pending_run)
        assert r.run_count() == 1
