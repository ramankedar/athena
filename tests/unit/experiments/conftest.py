"""Shared fixtures for experiment domain unit tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from athena.experiments.metadata import (
    ExperimentMetadata,
    ReproducibilitySnapshot,
)
from athena.experiments.metrics import MetricSnapshot
from athena.experiments.models import (
    ExperimentId,
    ExperimentStatus,
    RunId,
    RunStatus,
)
from athena.experiments.parameters import (
    ParameterSnapshot,
)
from athena.experiments.registry import Experiment, ExperimentRun

NOW = datetime(2025, 1, 15, 10, 0, tzinfo=UTC)


@pytest.fixture
def exp_id() -> ExperimentId:
    return ExperimentId.generate()


@pytest.fixture
def run_id() -> RunId:
    return RunId.generate()


@pytest.fixture
def basic_metadata() -> ExperimentMetadata:
    return ExperimentMetadata(
        author="Test Suite",
        description="Test experiment.",
        tags=frozenset({"test", "unit"}),
        created_at=NOW,
    )


@pytest.fixture
def empty_param_snapshot() -> ParameterSnapshot:
    return ParameterSnapshot.from_mapping({})


@pytest.fixture
def rsi_param_snapshot() -> ParameterSnapshot:
    return ParameterSnapshot.from_mapping({"period": "14"})


@pytest.fixture
def empty_metrics() -> MetricSnapshot:
    return MetricSnapshot.empty()


@pytest.fixture
def basic_experiment(exp_id: ExperimentId, basic_metadata: ExperimentMetadata) -> Experiment:
    return Experiment(
        id=exp_id,
        name="RSI Momentum Backtest",
        status=ExperimentStatus.ACTIVE,
        metadata=basic_metadata,
    )


@pytest.fixture
def pending_run(
    run_id: RunId,
    exp_id: ExperimentId,
    rsi_param_snapshot: ParameterSnapshot,
    empty_metrics: MetricSnapshot,
) -> ExperimentRun:
    return ExperimentRun(
        run_id=run_id,
        experiment_id=exp_id,
        status=RunStatus.PENDING,
        parameter_snapshot=rsi_param_snapshot,
        metric_snapshot=empty_metrics,
    )


@pytest.fixture
def reproducibility_snapshot() -> ReproducibilitySnapshot:
    return ReproducibilitySnapshot(
        git_commit_hash="abc1234def5678",
        git_branch="main",
        git_is_dirty=False,
        random_seed=42,
        python_version="3.12.3",
    )
