"""Experiment domain validation utilities.

Returns ``ValidationResult`` (structured failure list) rather than raising.
This enables batch validation of experiment catalogues and run logs before
committing to storage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from athena.experiments.metadata import ReproducibilitySnapshot
    from athena.experiments.parameters import ParameterDefinition, ParameterSnapshot
    from athena.experiments.registry import Experiment, ExperimentRun, ExperimentRunGroup


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of a validation pass.

    Attributes:
        is_valid: ``True`` when no failures were found.
        failures: Tuple of human-readable failure messages.
    """

    is_valid: bool
    failures: tuple[str, ...] = ()

    @classmethod
    def ok(cls) -> ValidationResult:
        """Return a valid result with no failures.

        Returns:
            ``ValidationResult(is_valid=True)``.
        """
        return cls(is_valid=True)

    @classmethod
    def failed(cls, *messages: str) -> ValidationResult:
        """Return an invalid result with the given failure messages.

        Args:
            *messages: One or more failure descriptions.

        Returns:
            ``ValidationResult(is_valid=False, failures=(...))``.
        """
        return cls(is_valid=False, failures=tuple(messages))

    def merge(self, other: ValidationResult) -> ValidationResult:
        """Combine two results. Invalid if either is invalid.

        Args:
            other: The other result to merge.

        Returns:
            Combined ``ValidationResult`` with all failure messages.
        """
        combined = self.failures + other.failures
        return ValidationResult(is_valid=len(combined) == 0, failures=combined)


# ── Domain validators ──────────────────────────────────────────────────────────


def validate_experiment(experiment: Experiment) -> ValidationResult:
    """Validate an ``Experiment`` against domain business rules.

    Args:
        experiment: The experiment to validate.

    Returns:
        A ``ValidationResult``.
    """
    failures: list[str] = []

    if not experiment.name.strip():
        failures.append("Experiment.name must not be empty")

    return ValidationResult.ok() if not failures else ValidationResult.failed(*failures)


def validate_run(run: ExperimentRun) -> ValidationResult:
    """Validate an ``ExperimentRun`` against domain business rules.

    Args:
        run: The run to validate.

    Returns:
        A ``ValidationResult``.
    """
    failures: list[str] = []

    if run.started_at is not None and run.started_at.tzinfo is None:
        failures.append("ExperimentRun.started_at must be timezone-aware")

    if run.completed_at is not None and run.completed_at.tzinfo is None:
        failures.append("ExperimentRun.completed_at must be timezone-aware")

    if (
        run.started_at is not None
        and run.completed_at is not None
        and run.started_at > run.completed_at
    ):
        failures.append(
            f"ExperimentRun.started_at ({run.started_at}) must be "
            f"<= completed_at ({run.completed_at})"
        )

    if run.status.is_terminal and run.completed_at is None:
        failures.append(
            f"ExperimentRun in terminal status {run.status.value!r} should have completed_at set"
        )

    return ValidationResult.ok() if not failures else ValidationResult.failed(*failures)


def validate_parameter_snapshot(
    snapshot: ParameterSnapshot,
    definitions: tuple[ParameterDefinition, ...],
) -> ValidationResult:
    """Validate a parameter snapshot against declared definitions.

    Checks that all required parameters are present and all values are within
    allowed sets.

    Args:
        snapshot:    The parameter values to validate.
        definitions: The declared parameter definitions.

    Returns:
        A ``ValidationResult``.
    """
    failures: list[str] = []
    snapshot_dict = snapshot.to_dict()

    for defn in definitions:
        if defn.name not in snapshot_dict:
            if defn.is_required:
                failures.append(f"Required parameter {defn.name!r} is missing from snapshot")
        else:
            value = snapshot_dict[defn.name]
            if defn.allowed_values and not defn.is_value_allowed(value):
                failures.append(
                    f"Parameter {defn.name!r} value {value!r} is not in "
                    f"allowed values: {defn.allowed_values}"
                )

    return ValidationResult.ok() if not failures else ValidationResult.failed(*failures)


def validate_reproducibility_snapshot(
    snapshot: ReproducibilitySnapshot,
) -> ValidationResult:
    """Validate a ``ReproducibilitySnapshot`` for completeness.

    Args:
        snapshot: The reproducibility snapshot to validate.

    Returns:
        A ``ValidationResult`` with warnings for missing reproducibility fields.
    """
    failures: list[str] = []

    if snapshot.git_commit_hash is None:
        failures.append("ReproducibilitySnapshot.git_commit_hash is not set")

    if snapshot.git_is_dirty:
        failures.append(
            "Run was executed with uncommitted git changes — "
            "exact code state cannot be recovered from git history"
        )

    if snapshot.random_seed is None:
        failures.append(
            "ReproducibilitySnapshot.random_seed is not set — "
            "non-deterministic runs cannot be exactly reproduced"
        )

    return ValidationResult.ok() if not failures else ValidationResult.failed(*failures)


def validate_run_group(group: ExperimentRunGroup) -> ValidationResult:
    """Validate an ``ExperimentRunGroup`` for internal consistency.

    Args:
        group: The run group to validate.

    Returns:
        A ``ValidationResult``.
    """
    failures: list[str] = []

    if not group.name.strip():
        failures.append("ExperimentRunGroup.name must not be empty")

    if not group.run_ids:
        failures.append("ExperimentRunGroup.run_ids must not be empty")

    seen: set[str] = set()
    for rid in group.run_ids:
        s = str(rid)
        if s in seen:
            failures.append(f"Duplicate run_id in group: {s!r}")
        seen.add(s)

    return ValidationResult.ok() if not failures else ValidationResult.failed(*failures)
