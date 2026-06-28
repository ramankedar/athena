"""Service Protocol interfaces for the Experiment Domain.

These Protocols define the structural contracts for experiment registries and
run management services. No implementations are provided here; concrete adapters
(in-memory, database-backed) satisfy these protocols via structural subtyping.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from datetime import datetime

    from athena.experiments.metrics import ExperimentMetric
    from athena.experiments.models import (
        ExperimentId,
        ExperimentStatus,
        RunId,
        RunStatus,
    )
    from athena.experiments.registry import (
        Experiment,
        ExperimentRun,
    )


@runtime_checkable
class ExperimentRegistryProtocol(Protocol):
    """Full read/write registry for experiment domain objects.

    The standard implementation is ``InMemoryExperimentRegistry`` in
    ``athena.experiments.registry``.
    """

    def register(self, experiment: Experiment) -> None:
        """Register a new experiment.

        Args:
            experiment: The experiment to register.

        Raises:
            DuplicateExperimentError: If already registered.
        """
        ...

    def get_experiment(self, experiment_id: ExperimentId) -> Experiment:
        """Return the experiment for the given id.

        Args:
            experiment_id: The experiment to retrieve.

        Returns:
            The matching ``Experiment``.

        Raises:
            ExperimentNotFoundError: If not found.
        """
        ...

    def get_experiment_or_none(self, experiment_id: ExperimentId) -> Experiment | None:
        """Return the experiment, or ``None`` if not found.

        Args:
            experiment_id: The experiment to retrieve.

        Returns:
            The matching ``Experiment``, or ``None``.
        """
        ...

    def update_experiment_status(
        self, experiment_id: ExperimentId, new_status: ExperimentStatus
    ) -> Experiment:
        """Transition an experiment's status.

        Args:
            experiment_id: The experiment to update.
            new_status:    The target status.

        Returns:
            The updated ``Experiment``.
        """
        ...

    def find_by_status(self, status: ExperimentStatus) -> tuple[Experiment, ...]:
        """Return all experiments with the given status.

        Args:
            status: The status to filter by.

        Returns:
            Tuple of matching experiments.
        """
        ...

    def all_experiments(self) -> tuple[Experiment, ...]:
        """Return all registered experiments.

        Returns:
            Tuple of all experiments.
        """
        ...

    def experiment_count(self) -> int:
        """Return the number of registered experiments.

        Returns:
            Total count.
        """
        ...

    def register_run(self, run: ExperimentRun) -> None:
        """Register a new experiment run.

        Args:
            run: The run to register.
        """
        ...

    def get_run(self, run_id: RunId) -> ExperimentRun:
        """Return the run for the given id.

        Args:
            run_id: The run to retrieve.

        Returns:
            The matching ``ExperimentRun``.

        Raises:
            RunNotFoundError: If not found.
        """
        ...

    def advance_run_status(
        self,
        run_id: RunId,
        new_status: RunStatus,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        error_message: str | None = None,
    ) -> ExperimentRun:
        """Transition a run's status.

        Args:
            run_id:        The run to update.
            new_status:    The target status.
            started_at:    Set when transitioning to RUNNING.
            completed_at:  Set when transitioning to a terminal status.
            error_message: Set when transitioning to FAILED.

        Returns:
            The updated ``ExperimentRun``.
        """
        ...

    def record_metrics(self, run_id: RunId, metrics: tuple[ExperimentMetric, ...]) -> ExperimentRun:
        """Add metrics to a run.

        Args:
            run_id:  The run to update.
            metrics: Metrics to add.

        Returns:
            The updated ``ExperimentRun``.
        """
        ...

    def runs_for_experiment(self, experiment_id: ExperimentId) -> tuple[ExperimentRun, ...]:
        """Return all runs for the given experiment.

        Args:
            experiment_id: The experiment to query.

        Returns:
            Tuple of matching runs.
        """
        ...

    def run_count(self) -> int:
        """Return the total number of registered runs.

        Returns:
            Count of all runs.
        """
        ...
