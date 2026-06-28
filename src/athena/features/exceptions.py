"""Feature domain exception hierarchy.

All feature exceptions inherit from ``FeatureError``, which inherits from
``AthenaError``. This preserves the platform-wide catch clause while allowing
fine-grained discrimination by subtype.

Hierarchy::

    AthenaError
    └── FeatureError
        ├── FeatureNotFoundError        — registry lookup found nothing
        ├── DuplicateFeatureError       — feature already registered
        ├── InvalidFeatureDefinitionError — definition fails domain rules
        ├── CyclicDependencyError       — dependency graph contains a cycle
        ├── VersionConflictError        — incompatible version constraints
        ├── InvalidInputRequirementError — input spec fails constraints
        └── FeatureSetError             — feature set is malformed
"""

from __future__ import annotations

from athena.platform.exceptions import AthenaError


class FeatureError(AthenaError):
    """Root exception for all feature domain errors.

    Args:
        message: Human-readable description.
        error_code: Optional machine-readable code (prefix: ``FTR``).
        **context: Diagnostic key-value pairs.
    """


class FeatureNotFoundError(FeatureError):
    """Raised when a registry lookup finds no matching feature.

    Args:
        feature_id: The identifier string that was not found.
        **context: Additional diagnostic context.
    """

    def __init__(self, feature_id: str, **context: object) -> None:
        super().__init__(
            f"Feature not found: {feature_id!r}",
            error_code="FTR_001",
            feature_id=feature_id,
            **context,
        )
        self.feature_id = feature_id


class DuplicateFeatureError(FeatureError):
    """Raised when a feature is registered but its identifier already exists.

    Args:
        feature_id: The identifier that already exists in the registry.
        **context: Additional diagnostic context.
    """

    def __init__(self, feature_id: str, **context: object) -> None:
        super().__init__(
            f"Feature already registered: {feature_id!r}",
            error_code="FTR_002",
            feature_id=feature_id,
            **context,
        )
        self.feature_id = feature_id


class InvalidFeatureDefinitionError(FeatureError):
    """Raised when a ``FeatureDefinition`` violates domain rules.

    Args:
        message: Description of the violated rule.
        **context: Additional diagnostic context (field names, values).
    """

    def __init__(self, message: str, **context: object) -> None:
        super().__init__(message, error_code="FTR_003", **context)


class CyclicDependencyError(FeatureError):
    """Raised when the feature dependency graph contains a cycle.

    A cycle prevents topological ordering and therefore prevents any valid
    computation sequence from being determined.

    Args:
        cycle_path: Human-readable representation of the cycle
            (e.g. ``"a -> b -> c -> a"``).
        **context: Additional diagnostic context.
    """

    def __init__(self, cycle_path: str, **context: object) -> None:
        super().__init__(
            f"Cyclic dependency detected: {cycle_path}",
            error_code="FTR_004",
            cycle_path=cycle_path,
            **context,
        )
        self.cycle_path = cycle_path


class VersionConflictError(FeatureError):
    """Raised when a feature version does not satisfy a declared constraint.

    Args:
        feature_id: The feature whose version was checked.
        required_constraint: The version constraint that was not met.
        actual_version: The version that was available.
        **context: Additional diagnostic context.
    """

    def __init__(
        self,
        feature_id: str,
        required_constraint: str,
        actual_version: str,
        **context: object,
    ) -> None:
        super().__init__(
            f"Feature {feature_id!r} version {actual_version!r} does not satisfy "
            f"constraint {required_constraint!r}",
            error_code="FTR_005",
            feature_id=feature_id,
            required_constraint=required_constraint,
            actual_version=actual_version,
            **context,
        )
        self.feature_id = feature_id
        self.required_constraint = required_constraint
        self.actual_version = actual_version


class InvalidInputRequirementError(FeatureError):
    """Raised when an ``InputRequirement`` violates its structural constraints.

    Args:
        message: Description of the constraint violation.
        **context: Additional diagnostic context.
    """

    def __init__(self, message: str, **context: object) -> None:
        super().__init__(message, error_code="FTR_006", **context)


class FeatureSetError(FeatureError):
    """Raised when a ``FeatureSet`` is malformed.

    Args:
        message: Description of the problem.
        **context: Additional diagnostic context.
    """

    def __init__(self, message: str, **context: object) -> None:
        super().__init__(message, error_code="FTR_007", **context)
