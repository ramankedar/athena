"""Athena Feature Domain — Sprint 7.

Represents engineered features independently of how they are calculated.
This package contains only domain models, typed value objects, and Protocol
interfaces — no feature calculation logic, no ML models, no indicators.

Feature domain responsibilities:
    FeatureDefinition    — complete immutable specification of a feature
    FeatureSet           — named collection of feature identifiers
    FeatureVersion       — semantic versioning for reproducibility
    DependencyGraph      — DAG of feature dependencies with cycle detection
    FeatureMetadata      — provenance, authorship, tags, reproducibility
    InputRequirement     — what raw data a feature consumes
    FeatureOutputSchema  — what values a feature produces
    InMemoryFeatureRegistry — in-memory registry (no persistence)

Public API::

    from athena.features import (
        # Models
        FeatureId, FeatureVersion, FeatureNamespace, FeatureOutputType,
        InputDataType, InputTimeframe,

        # Schemas
        InputRequirement, FeatureOutputField, FeatureOutputSchema,

        # Metadata
        FeatureMetadata, ReproducibilityInfo, PaperReference,

        # Dependencies
        FeatureDependency, DependencyGraph, ImmutableDependencyGraph,

        # Registry
        FeatureDefinition, FeatureSet, InMemoryFeatureRegistry,

        # Interfaces
        FeatureRegistryProtocol, FeatureProviderProtocol,

        # Validation
        ValidationResult,
        validate_feature_definition, validate_dependency_graph,
        validate_feature_set,

        # Exceptions
        FeatureError, FeatureNotFoundError, DuplicateFeatureError,
        InvalidFeatureDefinitionError, CyclicDependencyError,
        VersionConflictError, InvalidInputRequirementError, FeatureSetError,
    )
"""

from athena.features.dependencies import (
    DependencyGraph,
    FeatureDependency,
    ImmutableDependencyGraph,
)
from athena.features.exceptions import (
    CyclicDependencyError,
    DuplicateFeatureError,
    FeatureError,
    FeatureNotFoundError,
    FeatureSetError,
    InvalidFeatureDefinitionError,
    InvalidInputRequirementError,
    VersionConflictError,
)
from athena.features.interfaces import FeatureProviderProtocol, FeatureRegistryProtocol
from athena.features.metadata import FeatureMetadata, PaperReference, ReproducibilityInfo
from athena.features.models import (
    FeatureId,
    FeatureNamespace,
    FeatureOutputType,
    FeatureVersion,
    InputDataType,
    InputTimeframe,
)
from athena.features.registry import (
    FeatureDefinition,
    FeatureSet,
    InMemoryFeatureRegistry,
)
from athena.features.schemas import (
    FeatureOutputField,
    FeatureOutputSchema,
    InputRequirement,
)
from athena.features.validation import (
    ValidationResult,
    validate_dependency_graph,
    validate_feature_definition,
    validate_feature_set,
)

__all__ = [
    "CyclicDependencyError",
    "DependencyGraph",
    "DuplicateFeatureError",
    "FeatureDefinition",
    "FeatureDependency",
    "FeatureError",
    "FeatureId",
    "FeatureMetadata",
    "FeatureNamespace",
    "FeatureNotFoundError",
    "FeatureOutputField",
    "FeatureOutputSchema",
    "FeatureOutputType",
    "FeatureProviderProtocol",
    "FeatureRegistryProtocol",
    "FeatureSet",
    "FeatureSetError",
    "FeatureVersion",
    "ImmutableDependencyGraph",
    "InMemoryFeatureRegistry",
    "InputDataType",
    "InputRequirement",
    "InputTimeframe",
    "InvalidFeatureDefinitionError",
    "InvalidInputRequirementError",
    "PaperReference",
    "ReproducibilityInfo",
    "ValidationResult",
    "VersionConflictError",
    "validate_dependency_graph",
    "validate_feature_definition",
    "validate_feature_set",
]
