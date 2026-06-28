"""Service Protocol interfaces for the Feature Domain.

These Protocols define the structural contracts for feature registries and
computation providers. No implementations are provided here — concrete adapters
satisfy these protocols via structural subtyping.

Two categories:

1. ``FeatureRegistryProtocol`` — CRUD for ``FeatureDefinition`` objects.
   Satisfied by ``InMemoryFeatureRegistry`` (domain layer) and future
   database-backed implementations (infrastructure layer).

2. ``FeatureProviderProtocol`` — computes feature values on demand.
   The interface is intentionally minimal: the domain declares what features
   exist and what they need; the provider computes them. Computation is a
   future sprint concern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from athena.features.models import FeatureId, FeatureNamespace
    from athena.features.registry import FeatureDefinition, FeatureSet


@runtime_checkable
class FeatureRegistryProtocol(Protocol):
    """Full read/write registry for ``FeatureDefinition`` objects.

    The standard implementation is ``InMemoryFeatureRegistry`` in
    ``athena.features.registry``. Database-backed implementations satisfy
    this Protocol via structural subtyping.
    """

    def register(self, definition: FeatureDefinition) -> None:
        """Register a new feature definition.

        Args:
            definition: The feature to register.

        Raises:
            DuplicateFeatureError: If the feature id is already registered.
        """
        ...

    def get(self, feature_id: FeatureId) -> FeatureDefinition:
        """Return the definition for the given feature id.

        Args:
            feature_id: The feature to retrieve.

        Returns:
            The matching ``FeatureDefinition``.

        Raises:
            FeatureNotFoundError: If not registered.
        """
        ...

    def get_or_none(self, feature_id: FeatureId) -> FeatureDefinition | None:
        """Return the definition, or ``None`` if not registered.

        Args:
            feature_id: The feature to retrieve.

        Returns:
            The matching ``FeatureDefinition``, or ``None``.
        """
        ...

    def exists(self, feature_id: FeatureId) -> bool:
        """Return ``True`` if the feature is registered.

        Args:
            feature_id: The feature to check.

        Returns:
            ``True`` when registered.
        """
        ...

    def remove(self, feature_id: FeatureId) -> bool:
        """Remove a feature from the registry.

        Args:
            feature_id: The feature to remove.

        Returns:
            ``True`` if removed; ``False`` if not found.
        """
        ...

    def find_by_namespace(self, namespace: FeatureNamespace) -> tuple[FeatureDefinition, ...]:
        """Return all features in the given namespace.

        Args:
            namespace: The namespace to filter by.

        Returns:
            Tuple of matching definitions (may be empty).
        """
        ...

    def all_features(self) -> tuple[FeatureDefinition, ...]:
        """Return all registered feature definitions.

        Returns:
            Tuple of all registered definitions.
        """
        ...

    def count(self, namespace: FeatureNamespace | None = None) -> int:
        """Return the count of registered features.

        Args:
            namespace: When provided, count only features in this namespace.

        Returns:
            Total count.
        """
        ...

    def register_set(self, feature_set: FeatureSet) -> None:
        """Register a feature set.

        Args:
            feature_set: The set to register.
        """
        ...

    def get_set(self, name: str) -> FeatureSet:
        """Return the feature set with the given name.

        Args:
            name: The set name.

        Returns:
            The matching ``FeatureSet``.

        Raises:
            FeatureNotFoundError: If not found.
        """
        ...


@runtime_checkable
class FeatureProviderProtocol(Protocol):
    """Provider that computes feature values for specific instruments.

    This is a stub for the feature computation engine that will be implemented
    in a future sprint. The interface is minimal: a provider declares which
    features it supports and computes them on demand.

    Note:
        The return type of ``compute`` is ``object`` because the feature values
        domain (what computed feature values look like) has not been defined
        yet. Future sprints will introduce typed return values.
    """

    @property
    def supported_features(self) -> frozenset[FeatureId]:
        """Return the set of feature identifiers this provider can compute.

        Returns:
            Frozenset of supported ``FeatureId`` objects.
        """
        ...

    @property
    def provider_name(self) -> str:
        """Human-readable name of this provider.

        Returns:
            Provider name string (e.g. ``"pandas_provider"``).
        """
        ...

    def supports(self, feature_id: FeatureId) -> bool:
        """Return ``True`` if this provider can compute the given feature.

        Args:
            feature_id: The feature to check.

        Returns:
            ``True`` when the feature is in ``supported_features``.
        """
        ...
