"""Experiment, ExperimentRun, ExperimentRunGroup, and InMemoryExperimentRegistry.

``Experiment``
    The specification of what is being studied. Immutable once defined.

``ExperimentRun``
    A single execution of an experiment. Fully immutable — status changes
    produce new ``ExperimentRun`` instances via ``dataclasses.replace()``.

``ExperimentRunGroup``
    A named collection of related runs (e.g. a hyperparameter sweep or
    walk-forward series). Tracks the common purpose that spawned the group.

``InMemoryExperimentRegistry``
    Pure in-memory implementation of ``ExperimentRegistryProtocol``. No I/O.
    Suitable for unit tests, research notebooks, and startup before a database-
    backed registry is available.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from athena.experiments.exceptions import (
    DuplicateExperimentError,
    ExperimentNotFoundError,
    InvalidExperimentError,
    InvalidRunStatusTransitionError,
    RunNotFoundError,
)
from athena.experiments.models import (
    ExperimentId,
    ExperimentStatus,
    RunGroupId,
    RunGroupPurpose,
    RunId,
    RunStatus,
    is_valid_run_transition,
)

if TYPE_CHECKING:
    from datetime import datetime

    from athena.experiments.artifacts import ExperimentArtifact
    from athena.experiments.metadata import ExperimentMetadata, ReproducibilitySnapshot
    from athena.experiments.metrics import ExperimentMetric, MetricSnapshot
    from athena.experiments.parameters import ParameterDefinition, ParameterSnapshot


@dataclass(frozen=True)
class Experiment:
    """Specification of a research experiment.

    An experiment defines WHAT is being studied — parameter schema, status,
    metadata, and lineage. Individual runs hold the actual parameter values,
    metrics, and artifacts.

    Attributes:
        id:                    Unique experiment identifier.
        name:                  Human-readable experiment name.
        status:                Current lifecycle status.
        metadata:              Author, description, hypothesis, and tags.
        parameter_definitions: Declared parameter schema. Runs supply values
            conforming to this schema.
        parent_id:             Optional direct parent experiment (for derived
            experiments). Use the lineage graph for multi-parent tracking.
        is_template:           When ``True``, this experiment defines a reusable
            specification. Template experiments themselves do not have runs.

    Raises:
        InvalidExperimentError: If ``name`` is empty.
    """

    id: ExperimentId
    name: str
    status: ExperimentStatus
    metadata: ExperimentMetadata
    parameter_definitions: tuple[ParameterDefinition, ...] = ()
    parent_id: ExperimentId | None = None
    is_template: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidExperimentError("Experiment.name must not be empty")

    @property
    def accepts_runs(self) -> bool:
        """Return ``True`` when new runs can be created.

        Returns:
            ``True`` when status is ACTIVE and the experiment is not a template.
        """
        return self.status.accepts_runs and not self.is_template

    @property
    def is_active(self) -> bool:
        """Return ``True`` when the experiment is in ACTIVE status.

        Returns:
            ``True`` when ``status == ExperimentStatus.ACTIVE``.
        """
        return self.status == ExperimentStatus.ACTIVE

    def __str__(self) -> str:
        return f"Experiment({self.name!r} [{self.status.value}])"


@dataclass(frozen=True)
class ExperimentRun:
    """A single immutable execution of an experiment.

    Status transitions produce new ``ExperimentRun`` instances; the registry
    replaces the old instance. Use ``dataclasses.replace()`` for updates.

    Attributes:
        run_id:                  Unique run identifier.
        experiment_id:           Parent experiment.
        status:                  Current run lifecycle status.
        parameter_snapshot:      Immutable record of parameter values used.
        metric_snapshot:         All metrics recorded during this run.
        artifacts:               Tuple of artifacts produced.
        reproducibility:         Provenance snapshot for exact reproducibility.
        started_at:              UTC timestamp when the run started.
        completed_at:            UTC timestamp when the run ended (any terminal).
        error_message:           Error description when status is FAILED.
        tags:                    Optional run-level tags.
        run_group_id:            Optional run group this run belongs to.

    Raises:
        InvalidExperimentError: If any timestamp is timezone-naive.
    """

    run_id: RunId
    experiment_id: ExperimentId
    status: RunStatus
    parameter_snapshot: ParameterSnapshot
    metric_snapshot: MetricSnapshot
    artifacts: tuple[ExperimentArtifact, ...] = ()
    reproducibility: ReproducibilitySnapshot | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    tags: frozenset[str] = field(default_factory=frozenset)
    run_group_id: RunGroupId | None = None

    def __post_init__(self) -> None:
        for ts_name, ts_val in (
            ("started_at", self.started_at),
            ("completed_at", self.completed_at),
        ):
            if ts_val is not None and ts_val.tzinfo is None:
                raise InvalidExperimentError(
                    f"ExperimentRun.{ts_name} must be timezone-aware when provided"
                )

    @property
    def is_complete(self) -> bool:
        """Return ``True`` when the run has finished successfully.

        Returns:
            ``True`` when ``status == RunStatus.COMPLETED``.
        """
        return self.status == RunStatus.COMPLETED

    @property
    def is_running(self) -> bool:
        """Return ``True`` when the run is currently executing.

        Returns:
            ``True`` when ``status == RunStatus.RUNNING``.
        """
        return self.status == RunStatus.RUNNING

    @property
    def duration_seconds(self) -> float | None:
        """Wall-clock duration of the run in seconds.

        Returns:
            Float seconds between started_at and completed_at, or ``None``
            when either timestamp is absent.
        """
        if self.started_at is not None and self.completed_at is not None:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def __str__(self) -> str:
        return f"ExperimentRun({self.run_id!s} [{self.status.value}])"


@dataclass(frozen=True)
class ExperimentRunGroup:
    """A named collection of related experiment runs.

    Captures sets of runs that were created together with a common purpose:
    hyperparameter sweeps, walk-forward series, Monte Carlo batches, etc.

    Attributes:
        group_id:      Unique run group identifier.
        experiment_id: The parent experiment all runs belong to.
        name:          Human-readable group name.
        purpose:       Why this group of runs was created.
        run_ids:       Ordered tuple of run identifiers in the group.
        description:   Optional description of the group.
        tags:          Optional tags for discovery.

    Raises:
        InvalidExperimentError: If ``name`` is empty or ``run_ids`` has duplicates.
    """

    group_id: RunGroupId
    experiment_id: ExperimentId
    name: str
    purpose: RunGroupPurpose
    run_ids: tuple[RunId, ...]
    description: str | None = None
    tags: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidExperimentError("ExperimentRunGroup.name must not be empty")
        seen: set[str] = set()
        for rid in self.run_ids:
            s = str(rid)
            if s in seen:
                raise InvalidExperimentError(f"ExperimentRunGroup contains duplicate run_id: {s!r}")
            seen.add(s)

    @property
    def size(self) -> int:
        """Number of runs in this group.

        Returns:
            ``len(self.run_ids)``.
        """
        return len(self.run_ids)

    def contains(self, run_id: RunId) -> bool:
        """Return ``True`` if the given run is in this group.

        Args:
            run_id: The run to check.

        Returns:
            ``True`` when present.
        """
        return run_id in self.run_ids

    def __str__(self) -> str:
        return f"ExperimentRunGroup({self.name!r} [{self.purpose.value}], {self.size} runs)"


# ── In-memory registry ─────────────────────────────────────────────────────────


class InMemoryExperimentRegistry:
    """Pure in-memory experiment registry with no persistence.

    Stores experiments, runs, and run groups in plain dictionaries.
    All state-changing methods (``advance_run_status``, ``record_metric``,
    etc.) produce new immutable value objects via ``dataclasses.replace()``
    and replace the stored instance.

    Suitable for:
    - Unit tests
    - Research notebooks
    - Platform startup before database is available
    """

    def __init__(self) -> None:
        self._experiments: dict[ExperimentId, Experiment] = {}
        self._runs: dict[RunId, ExperimentRun] = {}
        self._run_groups: dict[RunGroupId, ExperimentRunGroup] = {}
        self._runs_by_experiment: dict[ExperimentId, list[RunId]] = {}

    # ── Experiment operations ─────────────────────────────────────────────────

    def register(self, experiment: Experiment) -> None:
        """Register a new experiment.

        Args:
            experiment: The experiment to register.

        Raises:
            DuplicateExperimentError: If already registered.
        """
        if experiment.id in self._experiments:
            raise DuplicateExperimentError(str(experiment.id))
        self._experiments[experiment.id] = experiment
        self._runs_by_experiment.setdefault(experiment.id, [])

    def get_experiment(self, experiment_id: ExperimentId) -> Experiment:
        """Return the experiment for the given id.

        Args:
            experiment_id: The experiment to retrieve.

        Returns:
            The matching ``Experiment``.

        Raises:
            ExperimentNotFoundError: If not registered.
        """
        exp = self._experiments.get(experiment_id)
        if exp is None:
            raise ExperimentNotFoundError(str(experiment_id))
        return exp

    def get_experiment_or_none(self, experiment_id: ExperimentId) -> Experiment | None:
        """Return the experiment, or ``None`` if not found.

        Args:
            experiment_id: The experiment to retrieve.

        Returns:
            The matching ``Experiment``, or ``None``.
        """
        return self._experiments.get(experiment_id)

    def update_experiment_status(
        self, experiment_id: ExperimentId, new_status: ExperimentStatus
    ) -> Experiment:
        """Transition an experiment's status, returning the updated instance.

        Args:
            experiment_id: The experiment to update.
            new_status:    The target status.

        Returns:
            The updated ``Experiment`` with ``status == new_status``.

        Raises:
            ExperimentNotFoundError: If not registered.
            InvalidExperimentError: If the transition is not permitted.
        """
        from athena.experiments.models import is_valid_experiment_transition

        exp = self.get_experiment(experiment_id)
        if not is_valid_experiment_transition(exp.status, new_status):
            raise InvalidExperimentError(
                f"Invalid experiment status transition: "
                f"{exp.status.value!r} -> {new_status.value!r}",
                experiment_id=str(experiment_id),
            )
        updated = dataclasses.replace(exp, status=new_status)
        self._experiments[experiment_id] = updated
        return updated

    def find_by_status(self, status: ExperimentStatus) -> tuple[Experiment, ...]:
        """Return all experiments with the given status.

        Args:
            status: The status to filter by.

        Returns:
            Tuple of matching experiments.
        """
        return tuple(e for e in self._experiments.values() if e.status == status)

    def find_by_tag(self, tag: str) -> tuple[Experiment, ...]:
        """Return all experiments tagged with the given tag.

        Args:
            tag: The tag to filter by.

        Returns:
            Tuple of matching experiments.
        """
        return tuple(e for e in self._experiments.values() if e.metadata.has_tag(tag))

    def all_experiments(self) -> tuple[Experiment, ...]:
        """Return all registered experiments.

        Returns:
            Tuple of all registered experiments.
        """
        return tuple(self._experiments.values())

    def experiment_count(self) -> int:
        """Return the number of registered experiments.

        Returns:
            Total count.
        """
        return len(self._experiments)

    # ── Run operations ────────────────────────────────────────────────────────

    def register_run(self, run: ExperimentRun) -> None:
        """Register a new experiment run.

        Args:
            run: The run to register.

        Raises:
            ExperimentNotFoundError: If the parent experiment is not registered.
            InvalidExperimentError: If a run with the same id already exists.
        """
        if run.experiment_id not in self._experiments:
            raise ExperimentNotFoundError(str(run.experiment_id))
        if run.run_id in self._runs:
            raise InvalidExperimentError(f"Run already registered: {run.run_id!s}")
        self._runs[run.run_id] = run
        self._runs_by_experiment.setdefault(run.experiment_id, []).append(run.run_id)

    def get_run(self, run_id: RunId) -> ExperimentRun:
        """Return the run for the given id.

        Args:
            run_id: The run to retrieve.

        Returns:
            The matching ``ExperimentRun``.

        Raises:
            RunNotFoundError: If not registered.
        """
        run = self._runs.get(run_id)
        if run is None:
            raise RunNotFoundError(str(run_id))
        return run

    def get_run_or_none(self, run_id: RunId) -> ExperimentRun | None:
        """Return the run, or ``None`` if not found.

        Args:
            run_id: The run to retrieve.

        Returns:
            The matching ``ExperimentRun``, or ``None``.
        """
        return self._runs.get(run_id)

    def advance_run_status(
        self,
        run_id: RunId,
        new_status: RunStatus,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        error_message: str | None = None,
    ) -> ExperimentRun:
        """Transition a run's status, returning the updated instance.

        Args:
            run_id:        The run to update.
            new_status:    The target status.
            started_at:    Set when transitioning to RUNNING.
            completed_at:  Set when transitioning to a terminal status.
            error_message: Set when transitioning to FAILED.

        Returns:
            The updated ``ExperimentRun`` with ``status == new_status``.

        Raises:
            RunNotFoundError: If not registered.
            InvalidRunStatusTransitionError: If the transition is not allowed.
        """
        run = self.get_run(run_id)
        if not is_valid_run_transition(run.status, new_status):
            raise InvalidRunStatusTransitionError(
                from_status=run.status.value,
                to_status=new_status.value,
                run_id=str(run_id),
            )
        updated = dataclasses.replace(
            run,
            status=new_status,
            started_at=started_at if started_at is not None else run.started_at,
            completed_at=completed_at if completed_at is not None else run.completed_at,
            error_message=error_message if error_message is not None else run.error_message,
        )
        self._runs[run_id] = updated
        return updated

    def record_metrics(self, run_id: RunId, metrics: tuple[ExperimentMetric, ...]) -> ExperimentRun:
        """Add metrics to a run's snapshot, returning the updated instance.

        Args:
            run_id:  The run to update.
            metrics: Metrics to add (merged with existing).

        Returns:
            The updated ``ExperimentRun`` with new metrics included.

        Raises:
            RunNotFoundError: If not registered.
        """
        from athena.experiments.metrics import MetricSnapshot

        run = self.get_run(run_id)
        combined = run.metric_snapshot.metrics + metrics
        updated = dataclasses.replace(run, metric_snapshot=MetricSnapshot(metrics=combined))
        self._runs[run_id] = updated
        return updated

    def record_artifact(self, run_id: RunId, artifact: ExperimentArtifact) -> ExperimentRun:
        """Add an artifact to a run, returning the updated instance.

        Args:
            run_id:   The run to update.
            artifact: The artifact to add.

        Returns:
            The updated ``ExperimentRun``.

        Raises:
            RunNotFoundError: If not registered.
        """
        run = self.get_run(run_id)
        updated = dataclasses.replace(run, artifacts=(*run.artifacts, artifact))
        self._runs[run_id] = updated
        return updated

    def runs_for_experiment(self, experiment_id: ExperimentId) -> tuple[ExperimentRun, ...]:
        """Return all runs belonging to the given experiment.

        Args:
            experiment_id: The experiment to query.

        Returns:
            Tuple of matching runs (may be empty).
        """
        run_ids = self._runs_by_experiment.get(experiment_id, [])
        return tuple(self._runs[rid] for rid in run_ids if rid in self._runs)

    def runs_by_status(self, status: RunStatus) -> tuple[ExperimentRun, ...]:
        """Return all runs with the given status.

        Args:
            status: The run status to filter by.

        Returns:
            Tuple of matching runs.
        """
        return tuple(r for r in self._runs.values() if r.status == status)

    def run_count(self) -> int:
        """Return the total number of registered runs.

        Returns:
            Count of all runs across all experiments.
        """
        return len(self._runs)

    # ── Run group operations ──────────────────────────────────────────────────

    def register_run_group(self, group: ExperimentRunGroup) -> None:
        """Register a new run group.

        Args:
            group: The run group to register.

        Raises:
            InvalidExperimentError: If already registered.
        """
        if group.group_id in self._run_groups:
            raise InvalidExperimentError(f"Run group already registered: {group.group_id!s}")
        self._run_groups[group.group_id] = group

    def get_run_group(self, group_id: RunGroupId) -> ExperimentRunGroup:
        """Return the run group for the given id.

        Args:
            group_id: The run group to retrieve.

        Returns:
            The matching ``ExperimentRunGroup``.

        Raises:
            RunNotFoundError: If not registered.
        """
        group = self._run_groups.get(group_id)
        if group is None:
            raise RunNotFoundError(str(group_id))
        return group

    def groups_for_experiment(self, experiment_id: ExperimentId) -> tuple[ExperimentRunGroup, ...]:
        """Return all run groups belonging to the given experiment.

        Args:
            experiment_id: The experiment to query.

        Returns:
            Tuple of matching run groups.
        """
        return tuple(g for g in self._run_groups.values() if g.experiment_id == experiment_id)

    def __len__(self) -> int:
        return len(self._experiments)

    def __repr__(self) -> str:
        return (
            f"InMemoryExperimentRegistry("
            f"experiments={len(self._experiments)}, "
            f"runs={len(self._runs)})"
        )
