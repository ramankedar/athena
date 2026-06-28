"""Experiment domain exception hierarchy.

All experiment exceptions inherit from ``ExperimentError``, which inherits
from ``AthenaError``.

Hierarchy::

    AthenaError
    └── ExperimentError
        ├── ExperimentNotFoundError       — registry lookup found nothing
        ├── DuplicateExperimentError      — experiment already registered
        ├── RunNotFoundError              — run lookup found nothing
        ├── InvalidExperimentError        — experiment violates domain rules
        ├── InvalidRunStatusTransitionError — illegal status transition
        ├── ExperimentLineageCycleError   — lineage graph contains a cycle
        └── InvalidParameterError         — parameter fails constraints
"""

from __future__ import annotations

from athena.platform.exceptions import AthenaError


class ExperimentError(AthenaError):
    """Root exception for all experiment domain errors.

    Args:
        message: Human-readable description.
        error_code: Optional machine-readable code (prefix: ``EXP``).
        **context: Diagnostic key-value pairs.
    """


class ExperimentNotFoundError(ExperimentError):
    """Raised when an experiment registry lookup finds no matching experiment.

    Args:
        experiment_id: The identifier that was not found.
        **context: Additional diagnostic context.
    """

    def __init__(self, experiment_id: str, **context: object) -> None:
        super().__init__(
            f"Experiment not found: {experiment_id!r}",
            error_code="EXP_001",
            experiment_id=experiment_id,
            **context,
        )
        self.experiment_id = experiment_id


class DuplicateExperimentError(ExperimentError):
    """Raised when an experiment is registered but its identifier already exists.

    Args:
        experiment_id: The identifier that already exists.
        **context: Additional diagnostic context.
    """

    def __init__(self, experiment_id: str, **context: object) -> None:
        super().__init__(
            f"Experiment already registered: {experiment_id!r}",
            error_code="EXP_002",
            experiment_id=experiment_id,
            **context,
        )
        self.experiment_id = experiment_id


class RunNotFoundError(ExperimentError):
    """Raised when an experiment run lookup finds nothing.

    Args:
        run_id: The run identifier that was not found.
        **context: Additional diagnostic context.
    """

    def __init__(self, run_id: str, **context: object) -> None:
        super().__init__(
            f"Experiment run not found: {run_id!r}",
            error_code="EXP_003",
            run_id=run_id,
            **context,
        )
        self.run_id = run_id


class InvalidExperimentError(ExperimentError):
    """Raised when an experiment or run violates domain business rules.

    Args:
        message: Description of the violated rule.
        **context: Additional diagnostic context.
    """

    def __init__(self, message: str, **context: object) -> None:
        super().__init__(message, error_code="EXP_004", **context)


class InvalidRunStatusTransitionError(ExperimentError):
    """Raised when an experiment run status transition is not permitted.

    Args:
        from_status: The current run status.
        to_status: The target run status that was rejected.
        run_id: The run whose status was being changed.
        **context: Additional diagnostic context.
    """

    def __init__(
        self,
        from_status: str,
        to_status: str,
        run_id: str = "",
        **context: object,
    ) -> None:
        super().__init__(
            f"Invalid run status transition: {from_status!r} -> {to_status!r}",
            error_code="EXP_005",
            from_status=from_status,
            to_status=to_status,
            run_id=run_id,
            **context,
        )
        self.from_status = from_status
        self.to_status = to_status
        self.run_id = run_id


class ExperimentLineageCycleError(ExperimentError):
    """Raised when the experiment lineage graph would form a cycle.

    Args:
        cycle_path: Human-readable representation of the cycle.
        **context: Additional diagnostic context.
    """

    def __init__(self, cycle_path: str, **context: object) -> None:
        super().__init__(
            f"Experiment lineage cycle detected: {cycle_path}",
            error_code="EXP_006",
            cycle_path=cycle_path,
            **context,
        )
        self.cycle_path = cycle_path


class InvalidParameterError(ExperimentError):
    """Raised when a parameter value violates its declared constraints.

    Args:
        parameter_name: Name of the parameter that failed.
        reason: Description of the constraint that was violated.
        **context: Additional diagnostic context.
    """

    def __init__(self, parameter_name: str, reason: str, **context: object) -> None:
        super().__init__(
            f"Invalid parameter {parameter_name!r}: {reason}",
            error_code="EXP_007",
            parameter_name=parameter_name,
            reason=reason,
            **context,
        )
        self.parameter_name = parameter_name
        self.reason = reason
