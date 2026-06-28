"""Feature definition, feature set, and in-memory registry.

This module contains the central domain objects for the Feature Domain:

``FeatureDefinition``
    The complete, immutable specification of a feature: its identity,
    version, input requirements, output schema, dependencies, parameters,
    and metadata. Each definition carries a ``computation_hash`` — a
    SHA-256 digest of its structural content — enabling deduplication and
    exact reproducibility tracking.

``FeatureSet``
    A named, versioned collection of ``FeatureId`` references. Used by
    strategies and models to declare which features they consume. Lightweight
    by design — it stores identifiers, not full definitions.

``InMemoryFeatureRegistry``
    A pure in-memory implementation of ``FeatureRegistryProtocol`` (defined
    in ``athena.features.interfaces``). No I/O, no persistence. Pre-loaded
    or populated at startup.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import TYPE_CHECKING

from athena.features.exceptions import (
    DuplicateFeatureError,
    FeatureNotFoundError,
    FeatureSetError,
    InvalidFeatureDefinitionError,
)

if TYPE_CHECKING:
    from athena.features.dependencies import ImmutableDependencyGraph
    from athena.features.metadata import FeatureMetadata
    from athena.features.models import FeatureId, FeatureNamespace, FeatureVersion
    from athena.features.schemas import FeatureOutputSchema, InputRequirement


@dataclass(frozen=True)
class FeatureDefinition:
    """Complete, immutable specification of a feature.

    This is the primary domain entity of the Feature Domain. It describes
    everything the computation engine needs to know about a feature except
    the implementation: what data it requires, what it produces, what other
    features it depends on, and how to configure it.

    Attributes:
        id:                  Structured identifier (namespace + name).
        version:             Semantic version.
        display_name:        Human-readable name (e.g. ``"RSI (14-period)"``).
        input_requirements:  Tuple of raw data requirements.
        output_schema:       What values the feature produces.
        dependencies:        Dependency graph snapshot (may be empty).
        metadata:            Provenance, tags, and reproducibility.
        parameters:          Feature configuration as sorted (key, str_value) pairs.
            Example: ``(("period", "14"),)`` for RSI-14.
        is_experimental:     When ``True``, this feature has not been promoted
            to production use. Experimental features may change without notice.
        computation_hash:    SHA-256 of structural content. Auto-computed in
            ``__post_init__`` from id, version, parameters, dependencies,
            and output schema. Excludes metadata to allow description edits
            without invalidating research artefacts.

    Example::

        rsi = FeatureDefinition(
            id=FeatureId(FeatureNamespace.TECHNICAL, "rsi_14"),
            version=FeatureVersion(1, 0, 0),
            display_name="RSI (14-period)",
            input_requirements=(
                InputRequirement(InputDataType.OHLCV, InputTimeframe.DAY_1, 14, 2),
            ),
            output_schema=FeatureOutputSchema((
                FeatureOutputField("rsi", FeatureOutputType.SCALAR, units="percent"),
            )),
            dependencies=ImmutableDependencyGraph.empty(),
            metadata=FeatureMetadata(
                description="Relative Strength Index over 14 trading days.",
                author="Platform Engineering",
                tags=frozenset({"momentum", "oscillator"}),
            ),
            parameters=(("period", "14"),),
        )
    """

    id: FeatureId
    version: FeatureVersion
    display_name: str
    input_requirements: tuple[InputRequirement, ...]
    output_schema: FeatureOutputSchema
    dependencies: ImmutableDependencyGraph
    metadata: FeatureMetadata
    parameters: tuple[tuple[str, str], ...] = ()
    is_experimental: bool = False
    computation_hash: str = field(default="", init=False)

    def __post_init__(self) -> None:
        if not self.display_name.strip():
            raise InvalidFeatureDefinitionError("FeatureDefinition.display_name must not be empty")
        if not self.input_requirements:
            raise InvalidFeatureDefinitionError(
                "FeatureDefinition.input_requirements must contain at least one entry"
            )
        # Compute and store computation_hash
        object.__setattr__(self, "computation_hash", self._compute_hash())

    def _compute_hash(self) -> str:
        """Compute the SHA-256 hash of this feature's structural content.

        The hash covers:
        - Feature identifier (namespace:name)
        - Version string
        - Sorted parameters
        - Sorted dependency edges (as strings)
        - Output schema field names and types

        It does NOT cover:
        - description, author, tags, notes (metadata)
        - is_experimental flag

        Returns:
            A hex-encoded SHA-256 digest string.
        """
        parts: list[str] = [
            str(self.id),
            str(self.version),
        ]
        # Parameters sorted by key for determinism
        sorted_params = sorted(self.parameters, key=lambda kv: kv[0])
        parts.extend(f"{k}={v}" for k, v in sorted_params)
        # Dependencies sorted by string repr for determinism
        dep_strs = sorted(f"{a!s}->{b!s}" for a, b in self.dependencies.edges)
        parts.extend(dep_strs)
        # Output schema fields
        parts.extend(f"{f.name}:{f.output_type.value}" for f in self.output_schema.fields)

        content = "|".join(parts).encode("utf-8")
        return hashlib.sha256(content).hexdigest()

    def get_parameter(self, key: str) -> str | None:
        """Return the string value of a parameter by key, or ``None``.

        Args:
            key: The parameter key to look up.

        Returns:
            The string value, or ``None`` when the key is not present.
        """
        for k, v in self.parameters:
            if k == key:
                return v
        return None

    def __str__(self) -> str:
        return (
            f"FeatureDefinition({self.id!s} v{self.version!s}"
            + (" [experimental]" if self.is_experimental else "")
            + ")"
        )


@dataclass(frozen=True)
class FeatureSet:
    """A named, versioned collection of feature identifiers.

    ``FeatureSet`` stores references to features by ``FeatureId``, not full
    definitions. This keeps it lightweight for transport and caching while
    the registry resolves the full definitions on demand.

    Attributes:
        name:        Human-readable name for this set (e.g. ``"momentum_v2"``).
        version:     Semantic version for this set. Bump when adding/removing
            features.
        description: Human-readable description of what this set represents.
        feature_ids: Ordered tuple of feature identifiers. No duplicates.
        tags:        Optional frozenset of tags for discovery.

    Raises:
        FeatureSetError: If ``feature_ids`` is empty or contains duplicates.
        InvalidFeatureDefinitionError: If ``name`` or ``description`` is empty.

    Example::

        momentum = FeatureSet(
            name="momentum_features",
            version=FeatureVersion(1, 0, 0),
            description="Core momentum signals for the NSE universe.",
            feature_ids=(
                FeatureId(FeatureNamespace.TECHNICAL, "rsi_14"),
                FeatureId(FeatureNamespace.TECHNICAL, "macd_12_26_9"),
            ),
        )
    """

    name: str
    version: FeatureVersion
    description: str
    feature_ids: tuple[FeatureId, ...]
    tags: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidFeatureDefinitionError("FeatureSet.name must not be empty")
        if not self.description.strip():
            raise InvalidFeatureDefinitionError("FeatureSet.description must not be empty")
        if not self.feature_ids:
            raise FeatureSetError("FeatureSet.feature_ids must not be empty")
        seen: set[FeatureId] = set()
        for fid in self.feature_ids:
            if fid in seen:
                raise FeatureSetError(f"FeatureSet contains duplicate feature_id: {fid!s}")
            seen.add(fid)

    def contains(self, feature_id: FeatureId) -> bool:
        """Return ``True`` if the given feature is in this set.

        Args:
            feature_id: The feature to check.

        Returns:
            ``True`` when present.
        """
        return feature_id in self.feature_ids

    def __len__(self) -> int:
        return len(self.feature_ids)

    def __str__(self) -> str:
        return f"FeatureSet({self.name!r} v{self.version!s}, {len(self.feature_ids)} features)"


class InMemoryFeatureRegistry:
    """Pure in-memory feature registry with no persistence.

    Stores ``FeatureDefinition`` and ``FeatureSet`` objects in plain dicts.
    All operations are O(1) for direct lookups by id.

    Suitable for:
    - Unit tests (no infrastructure required)
    - Research notebooks and backtesting environments
    - Platform startup before a database-backed registry is available

    Example::

        registry = InMemoryFeatureRegistry()
        registry.register(rsi_definition)
        rsi = registry.get(FeatureId(FeatureNamespace.TECHNICAL, "rsi_14"))
    """

    def __init__(self) -> None:
        self._features: dict[FeatureId, FeatureDefinition] = {}
        self._feature_sets: dict[str, FeatureSet] = {}
        self._by_namespace: dict[FeatureNamespace, list[FeatureId]] = {}

    # ── Feature registration ──────────────────────────────────────────────────

    def register(self, definition: FeatureDefinition) -> None:
        """Register a feature definition.

        Args:
            definition: The feature to register.

        Raises:
            DuplicateFeatureError: If a feature with the same ``FeatureId``
                is already registered.
        """
        if definition.id in self._features:
            raise DuplicateFeatureError(str(definition.id))
        self._features[definition.id] = definition
        self._by_namespace.setdefault(definition.id.namespace, []).append(definition.id)

    def register_or_replace(self, definition: FeatureDefinition) -> None:
        """Register a feature, replacing any existing definition with the same id.

        Args:
            definition: The feature to register.
        """
        if definition.id in self._features:
            # Remove old namespace index entry
            ns_list = self._by_namespace.get(definition.id.namespace, [])
            if definition.id in ns_list:
                ns_list.remove(definition.id)
        self._features[definition.id] = definition
        self._by_namespace.setdefault(definition.id.namespace, []).append(definition.id)

    def remove(self, feature_id: FeatureId) -> bool:
        """Remove a feature from the registry.

        Args:
            feature_id: The feature to remove.

        Returns:
            ``True`` if the feature was found and removed; ``False`` otherwise.
        """
        if feature_id not in self._features:
            return False
        del self._features[feature_id]
        ns_list = self._by_namespace.get(feature_id.namespace, [])
        if feature_id in ns_list:
            ns_list.remove(feature_id)
        return True

    # ── Feature lookup ────────────────────────────────────────────────────────

    def get(self, feature_id: FeatureId) -> FeatureDefinition:
        """Return the feature definition for the given id.

        Args:
            feature_id: The feature to retrieve.

        Returns:
            The matching ``FeatureDefinition``.

        Raises:
            FeatureNotFoundError: If not registered.
        """
        definition = self._features.get(feature_id)
        if definition is None:
            raise FeatureNotFoundError(str(feature_id))
        return definition

    def get_or_none(self, feature_id: FeatureId) -> FeatureDefinition | None:
        """Return the feature definition, or ``None`` if not registered.

        Args:
            feature_id: The feature to retrieve.

        Returns:
            The matching ``FeatureDefinition``, or ``None``.
        """
        return self._features.get(feature_id)

    def exists(self, feature_id: FeatureId) -> bool:
        """Return ``True`` if the feature is registered.

        Args:
            feature_id: The feature to check.

        Returns:
            ``True`` when registered.
        """
        return feature_id in self._features

    def find_by_namespace(self, namespace: FeatureNamespace) -> tuple[FeatureDefinition, ...]:
        """Return all features in the given namespace.

        Args:
            namespace: The namespace to filter by.

        Returns:
            Tuple of matching definitions (may be empty).
        """
        return tuple(
            self._features[fid]
            for fid in self._by_namespace.get(namespace, [])
            if fid in self._features
        )

    def find_by_tag(self, tag: str) -> tuple[FeatureDefinition, ...]:
        """Return all features tagged with the given tag.

        Args:
            tag: The tag to filter by.

        Returns:
            Tuple of matching definitions (may be empty).
        """
        return tuple(d for d in self._features.values() if d.metadata.has_tag(tag))

    def find_by_hash(self, computation_hash: str) -> FeatureDefinition | None:
        """Return the feature matching the given computation hash, or ``None``.

        Args:
            computation_hash: The SHA-256 hash to look up.

        Returns:
            The matching ``FeatureDefinition``, or ``None``.
        """
        for definition in self._features.values():
            if definition.computation_hash == computation_hash:
                return definition
        return None

    def all_features(self) -> tuple[FeatureDefinition, ...]:
        """Return all registered feature definitions.

        Returns:
            Tuple of all registered definitions.
        """
        return tuple(self._features.values())

    def count(self, namespace: FeatureNamespace | None = None) -> int:
        """Return the count of registered features.

        Args:
            namespace: When provided, count only features in this namespace.

        Returns:
            Total count matching the filter.
        """
        if namespace is None:
            return len(self._features)
        return len(self._by_namespace.get(namespace, []))

    # ── Feature set management ─────────────────────────────────────────────────

    def register_set(self, feature_set: FeatureSet) -> None:
        """Register a feature set.

        Args:
            feature_set: The set to register.

        Raises:
            DuplicateFeatureError: If a set with the same name exists.
        """
        if feature_set.name in self._feature_sets:
            raise DuplicateFeatureError(f"FeatureSet:{feature_set.name}")
        self._feature_sets[feature_set.name] = feature_set

    def get_set(self, name: str) -> FeatureSet:
        """Return the feature set with the given name.

        Args:
            name: The set name.

        Returns:
            The matching ``FeatureSet``.

        Raises:
            FeatureNotFoundError: If not registered.
        """
        fs = self._feature_sets.get(name)
        if fs is None:
            raise FeatureNotFoundError(f"FeatureSet:{name}")
        return fs

    def resolve_set(self, name: str) -> tuple[FeatureDefinition, ...]:
        """Resolve a feature set to its full definitions.

        Args:
            name: The feature set name to resolve.

        Returns:
            Tuple of ``FeatureDefinition`` objects in the set's declared order.

        Raises:
            FeatureNotFoundError: If the set or any feature in it is not found.
        """
        fs = self.get_set(name)
        return tuple(self.get(fid) for fid in fs.feature_ids)

    def __len__(self) -> int:
        return len(self._features)

    def __repr__(self) -> str:
        return (
            f"InMemoryFeatureRegistry("
            f"features={len(self._features)}, "
            f"sets={len(self._feature_sets)})"
        )
