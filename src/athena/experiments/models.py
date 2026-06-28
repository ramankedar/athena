"""Core primitive types for the Experiment Domain.

Defines typed identifiers, status enumerations, and the run group purpose
vocabulary that form the shared language of the experiment domain.

Identifiers:
    ``ExperimentId`` — UUID-backed identifier for an experiment.
    ``RunId``        — UUID-backed identifier for a single experiment run.
    ``RunGroupId``   — UUID-backed identifier for a group of related runs.

Status state machines:
    ``ExperimentStatus``:  DRAFT → ACTIVE → ARCHIVED (or CANCELLED from either)
    ``RunStatus``:         PENDING → RUNNING → COMPLETED/FAILED/CANCELLED
    ``RunGroupPurpose``:   Classification of why a group of runs was created.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar
from uuid import UUID, uuid4

from athena.experiments.exceptions import InvalidExperimentError


class ExperimentStatus(StrEnum):
    """Lifecycle status of an experiment (the specification).

    Attributes:
        DRAFT:    Experiment is being designed. No runs can be created.
        ACTIVE:   Experiment is open for new runs.
        ARCHIVED: Experiment is read-only. Historical reference only.
        CANCELLED: Experiment was abandoned before completion.
    """

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        """Return ``True`` when no further status changes are possible.

        Returns:
            ``True`` for ``ARCHIVED`` and ``CANCELLED``.
        """
        return self in (ExperimentStatus.ARCHIVED, ExperimentStatus.CANCELLED)

    @property
    def accepts_runs(self) -> bool:
        """Return ``True`` when new runs can be created under this experiment.

        Returns:
            ``True`` only for ``ACTIVE``.
        """
        return self == ExperimentStatus.ACTIVE


class RunStatus(StrEnum):
    """Lifecycle status of a single experiment run.

    Attributes:
        PENDING:   Run has been created but not started.
        RUNNING:   Run is currently executing.
        COMPLETED: Run finished successfully.
        FAILED:    Run terminated with an error.
        CANCELLED: Run was stopped before completion.
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        """Return ``True`` when the run has ended and no further changes are expected.

        Returns:
            ``True`` for COMPLETED, FAILED, and CANCELLED.
        """
        return self in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED)

    @property
    def is_active(self) -> bool:
        """Return ``True`` when the run is currently executing.

        Returns:
            ``True`` only for RUNNING.
        """
        return self == RunStatus.RUNNING


class RunGroupPurpose(StrEnum):
    """Why a group of related experiment runs was created.

    Attributes:
        HYPERPARAMETER_SWEEP: Runs with systematically varied parameters.
        WALK_FORWARD:         Runs over consecutive time windows.
        CROSS_VALIDATION:     Runs over held-out data folds.
        MONTE_CARLO:          Runs with randomised inputs (different seeds).
        SENSITIVITY_ANALYSIS: Runs isolating the impact of single parameters.
        MANUAL_COMPARISON:    Ad-hoc group for side-by-side comparison.
    """

    HYPERPARAMETER_SWEEP = "hyperparameter_sweep"
    WALK_FORWARD = "walk_forward"
    CROSS_VALIDATION = "cross_validation"
    MONTE_CARLO = "monte_carlo"
    SENSITIVITY_ANALYSIS = "sensitivity_analysis"
    MANUAL_COMPARISON = "manual_comparison"


# ── Typed identifier value objects ─────────────────────────────────────────────


@dataclass(frozen=True)
class ExperimentId:
    """UUID-backed identifier for an experiment.

    Attributes:
        value: The underlying UUID.

    Example::

        eid = ExperimentId.generate()
        from_str = ExperimentId.from_string("550e8400-e29b-41d4-a716-446655440000")
    """

    value: UUID
    _PREFIX: ClassVar[str] = "exp"

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"ExperimentId({self.value!s})"

    @classmethod
    def generate(cls) -> ExperimentId:
        """Generate a new random UUID v4 experiment identifier.

        Returns:
            A new ``ExperimentId``.
        """
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> ExperimentId:
        """Parse a UUID string into an ``ExperimentId``.

        Args:
            value: A valid UUID string.

        Returns:
            An ``ExperimentId`` wrapping the parsed UUID.

        Raises:
            InvalidExperimentError: If the string is not a valid UUID.
        """
        try:
            return cls(UUID(value))
        except ValueError as exc:
            raise InvalidExperimentError(
                f"ExperimentId must be a valid UUID, got {value!r}"
            ) from exc


@dataclass(frozen=True)
class RunId:
    """UUID-backed identifier for a single experiment run.

    Attributes:
        value: The underlying UUID.
    """

    value: UUID

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"RunId({self.value!s})"

    @classmethod
    def generate(cls) -> RunId:
        """Generate a new random UUID v4 run identifier.

        Returns:
            A new ``RunId``.
        """
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> RunId:
        """Parse a UUID string into a ``RunId``.

        Args:
            value: A valid UUID string.

        Returns:
            A ``RunId`` wrapping the parsed UUID.

        Raises:
            InvalidExperimentError: If the string is not a valid UUID.
        """
        try:
            return cls(UUID(value))
        except ValueError as exc:
            raise InvalidExperimentError(f"RunId must be a valid UUID, got {value!r}") from exc


@dataclass(frozen=True)
class RunGroupId:
    """UUID-backed identifier for an experiment run group.

    Attributes:
        value: The underlying UUID.
    """

    value: UUID

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"RunGroupId({self.value!s})"

    @classmethod
    def generate(cls) -> RunGroupId:
        """Generate a new random UUID v4 run group identifier.

        Returns:
            A new ``RunGroupId``.
        """
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> RunGroupId:
        """Parse a UUID string into a ``RunGroupId``.

        Args:
            value: A valid UUID string.

        Returns:
            A ``RunGroupId`` wrapping the parsed UUID.

        Raises:
            InvalidExperimentError: If the string is not a valid UUID.
        """
        try:
            return cls(UUID(value))
        except ValueError as exc:
            raise InvalidExperimentError(f"RunGroupId must be a valid UUID, got {value!r}") from exc


# ── Valid status transition tables ────────────────────────────────────────────

VALID_EXPERIMENT_TRANSITIONS: frozenset[tuple[ExperimentStatus, ExperimentStatus]] = frozenset(
    {
        (ExperimentStatus.DRAFT, ExperimentStatus.ACTIVE),
        (ExperimentStatus.DRAFT, ExperimentStatus.CANCELLED),
        (ExperimentStatus.ACTIVE, ExperimentStatus.ARCHIVED),
        (ExperimentStatus.ACTIVE, ExperimentStatus.CANCELLED),
    }
)

VALID_RUN_TRANSITIONS: frozenset[tuple[RunStatus, RunStatus]] = frozenset(
    {
        (RunStatus.PENDING, RunStatus.RUNNING),
        (RunStatus.PENDING, RunStatus.CANCELLED),
        (RunStatus.RUNNING, RunStatus.COMPLETED),
        (RunStatus.RUNNING, RunStatus.FAILED),
        (RunStatus.RUNNING, RunStatus.CANCELLED),
    }
)


def is_valid_experiment_transition(
    from_status: ExperimentStatus, to_status: ExperimentStatus
) -> bool:
    """Return ``True`` if the experiment status transition is permitted.

    Identical statuses (no-op) are always valid.

    Args:
        from_status: Current status.
        to_status:   Target status.

    Returns:
        ``True`` when the transition is allowed.
    """
    if from_status == to_status:
        return True
    return (from_status, to_status) in VALID_EXPERIMENT_TRANSITIONS


def is_valid_run_transition(from_status: RunStatus, to_status: RunStatus) -> bool:
    """Return ``True`` if the run status transition is permitted.

    Args:
        from_status: Current status.
        to_status:   Target status.

    Returns:
        ``True`` when the transition is allowed.
    """
    if from_status == to_status:
        return True
    return (from_status, to_status) in VALID_RUN_TRANSITIONS
