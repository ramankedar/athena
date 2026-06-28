"""Feature domain validation utilities.

Returns ``ValidationResult`` (structured result with failure messages) rather
than raising immediately. This allows callers to batch-validate a catalogue
of feature definitions loaded from a YAML/database source and report all
errors before halting.

Note on ``ValidationResult`` duplication:
    ``ValidationResult`` is also defined in several other peer-layer domains.
    Since peer layers may not import from each other, each defines its own.
    The structure is identical; the type is domain-specific.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from athena.features.dependencies import DependencyGraph, ImmutableDependencyGraph
    from athena.features.registry import FeatureDefinition, FeatureSet


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of a feature domain validation pass.

    Attributes:
        is_valid: ``True`` when no failures were found.
        failures: Tuple of human-readable failure messages.
    """

    is_valid: bool
    failures: tuple[str, ...] = ()

    @classmethod
    def ok(cls) -> ValidationResult:
        """Return a result indicating no failures.

        Returns:
            A valid ``ValidationResult`` with no failures.
        """
        return cls(is_valid=True)

    @classmethod
    def failed(cls, *messages: str) -> ValidationResult:
        """Return a result indicating one or more failures.

        Args:
            *messages: Failure descriptions.

        Returns:
            An invalid ``ValidationResult``.
        """
        return cls(is_valid=False, failures=tuple(messages))

    def merge(self, other: ValidationResult) -> ValidationResult:
        """Combine two results. Invalid if either input is invalid.

        Args:
            other: The other result to merge.

        Returns:
            Combined ``ValidationResult`` with all failure messages.
        """
        combined = self.failures + other.failures
        return ValidationResult(is_valid=len(combined) == 0, failures=combined)


# ── Domain validators ──────────────────────────────────────────────────────────


def validate_feature_definition(definition: FeatureDefinition) -> ValidationResult:
    """Validate a ``FeatureDefinition`` against domain business rules.

    Checks beyond those enforced in ``FeatureDefinition.__post_init__``,
    including cross-field consistency rules.

    Args:
        definition: The feature definition to validate.

    Returns:
        A ``ValidationResult``.
    """
    failures: list[str] = []

    if not definition.display_name.strip():
        failures.append("display_name must not be empty")

    if not definition.input_requirements:
        failures.append("input_requirements must contain at least one entry")

    # Validate parameters are sorted for canonical form
    param_keys = [k for k, _ in definition.parameters]
    if param_keys != sorted(param_keys):
        failures.append(
            f"parameters should be sorted by key for canonical representation (got {param_keys})"
        )

    # Validate computation_hash is non-empty
    if not definition.computation_hash:
        failures.append("computation_hash must not be empty")

    return ValidationResult.ok() if not failures else ValidationResult.failed(*failures)


def validate_dependency_graph(
    graph: DependencyGraph | ImmutableDependencyGraph,
) -> ValidationResult:
    """Validate a dependency graph for basic structural correctness.

    Note:
        Acyclicity is enforced at construction time in ``DependencyGraph``.
        This validator catches structural issues on externally-constructed graphs.

    Args:
        graph: The graph to validate (mutable or immutable).

    Returns:
        A ``ValidationResult``.
    """
    failures: list[str] = []

    # For ImmutableDependencyGraph, check edge tuples are well-formed
    if hasattr(graph, "edges"):
        failures.extend(
            f"Malformed edge in dependency graph: {edge!r}"
            for edge in graph.edges  # type: ignore[union-attr]
            if not isinstance(edge, tuple) or len(edge) != 2
        )

    return ValidationResult.ok() if not failures else ValidationResult.failed(*failures)


def validate_feature_set(feature_set: FeatureSet) -> ValidationResult:
    """Validate a ``FeatureSet`` for internal consistency.

    Args:
        feature_set: The feature set to validate.

    Returns:
        A ``ValidationResult``.
    """
    failures: list[str] = []

    if not feature_set.name.strip():
        failures.append("FeatureSet.name must not be empty")

    if not feature_set.description.strip():
        failures.append("FeatureSet.description must not be empty")

    if not feature_set.feature_ids:
        failures.append("FeatureSet.feature_ids must not be empty")

    # Check for duplicates
    seen: set[str] = set()
    for fid in feature_set.feature_ids:
        s = str(fid)
        if s in seen:
            failures.append(f"Duplicate feature_id in set: {s!r}")
        seen.add(s)

    return ValidationResult.ok() if not failures else ValidationResult.failed(*failures)
