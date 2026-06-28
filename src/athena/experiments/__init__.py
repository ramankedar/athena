"""Athena Experiment Domain — Sprint 8.

Represents reproducible quantitative research experiments independently of
execution engines, ML models, and data ingestion. This package contains only
domain models, typed value objects, and Protocol interfaces.

Public API::

    from athena.experiments import (
        # Models (ids, enums, transitions)
        ExperimentId, RunId, RunGroupId,
        ExperimentStatus, RunStatus, RunGroupPurpose,
        is_valid_experiment_transition, is_valid_run_transition,

        # Parameters
        ParameterValueType, ParameterValue, ParameterDefinition, ParameterSnapshot,

        # Metrics
        MetricDirection, ExperimentMetric, MetricSnapshot,

        # Artifacts
        ArtifactType, ArtifactLocation, ExperimentArtifact,

        # Metadata & reproducibility
        DatasetVersion, FeatureSetVersion, ReproducibilitySnapshot,
        ExperimentMetadata,

        # Lineage
        ExperimentLineageNode, ExperimentLineageGraph,

        # Registry
        Experiment, ExperimentRun, ExperimentRunGroup,
        InMemoryExperimentRegistry,

        # Interfaces
        ExperimentRegistryProtocol,

        # Validation
        ValidationResult,
        validate_experiment, validate_run,
        validate_parameter_snapshot, validate_reproducibility_snapshot,
        validate_run_group,

        # Exceptions
        ExperimentError, ExperimentNotFoundError, DuplicateExperimentError,
        RunNotFoundError, InvalidExperimentError,
        InvalidRunStatusTransitionError, ExperimentLineageCycleError,
        InvalidParameterError,
    )
"""

from athena.experiments.artifacts import ArtifactLocation, ArtifactType, ExperimentArtifact
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
from athena.experiments.interfaces import ExperimentRegistryProtocol
from athena.experiments.lineage import ExperimentLineageGraph, ExperimentLineageNode
from athena.experiments.metadata import (
    DatasetVersion,
    ExperimentMetadata,
    FeatureSetVersion,
    ReproducibilitySnapshot,
)
from athena.experiments.metrics import ExperimentMetric, MetricDirection, MetricSnapshot
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
from athena.experiments.parameters import (
    ParameterDefinition,
    ParameterSnapshot,
    ParameterValue,
    ParameterValueType,
)
from athena.experiments.registry import (
    Experiment,
    ExperimentRun,
    ExperimentRunGroup,
    InMemoryExperimentRegistry,
)
from athena.experiments.validation import (
    ValidationResult,
    validate_experiment,
    validate_parameter_snapshot,
    validate_reproducibility_snapshot,
    validate_run,
    validate_run_group,
)

__all__ = [
    "VALID_EXPERIMENT_TRANSITIONS",
    "VALID_RUN_TRANSITIONS",
    "ArtifactLocation",
    "ArtifactType",
    "DatasetVersion",
    "DuplicateExperimentError",
    "Experiment",
    "ExperimentArtifact",
    "ExperimentError",
    "ExperimentId",
    "ExperimentLineageCycleError",
    "ExperimentLineageGraph",
    "ExperimentLineageNode",
    "ExperimentMetadata",
    "ExperimentMetric",
    "ExperimentNotFoundError",
    "ExperimentRegistryProtocol",
    "ExperimentRun",
    "ExperimentRunGroup",
    "ExperimentStatus",
    "FeatureSetVersion",
    "InMemoryExperimentRegistry",
    "InvalidExperimentError",
    "InvalidParameterError",
    "InvalidRunStatusTransitionError",
    "MetricDirection",
    "MetricSnapshot",
    "ParameterDefinition",
    "ParameterSnapshot",
    "ParameterValue",
    "ParameterValueType",
    "ReproducibilitySnapshot",
    "RunGroupId",
    "RunGroupPurpose",
    "RunId",
    "RunNotFoundError",
    "RunStatus",
    "ValidationResult",
    "is_valid_experiment_transition",
    "is_valid_run_transition",
    "validate_experiment",
    "validate_parameter_snapshot",
    "validate_reproducibility_snapshot",
    "validate_run",
    "validate_run_group",
]
