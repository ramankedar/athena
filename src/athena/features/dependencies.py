"""Feature dependency graph value objects.

A ``FeatureDependency`` declares that one feature requires the output of
another feature as one of its inputs. When multiple features are composed,
their dependency relationships form a Directed Acyclic Graph (DAG).

``DependencyGraph`` maintains this DAG, validates acyclicity using
DFS-based topological ordering, and provides the execution sequence that
any computation engine must follow: all dependencies before their dependents.

Why a DAG and not a simple list?
    Flat dependency lists cannot express transitive relationships. If feature
    C depends on B, and B depends on A, a computation engine needs to know
    that A must be computed before B, and B before C — in that exact order.
    A DAG encodes these relationships precisely and enables the engine to
    compute features in the correct order with minimal redundant work.

Cycle detection:
    DFS with three-colour marking (WHITE=0, GREY=1, BLACK=2). If DFS
    reaches a GREY node (currently being visited), a back-edge exists and
    therefore a cycle. The ``CyclicDependencyError`` includes the cycle path
    for debugging.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from athena.features.exceptions import (
    CyclicDependencyError,
)

if TYPE_CHECKING:
    from athena.features.models import FeatureId, FeatureVersion


@dataclass(frozen=True)
class FeatureDependency:
    """A declared dependency from one feature on another.

    Attributes:
        feature_id:         The ``FeatureId`` of the required upstream feature.
        version_constraint: An optional semantic version constraint string
            (e.g. ``">=1.0.0"``, ``"==2.1.3"``). ``None`` means any version
            is acceptable.
        is_required:        ``True`` when computation cannot proceed without
            this dependency. ``False`` for optional enhancements.
        description:        Optional human-readable description of why this
            dependency exists.

    Example::

        # MACD requires EMA to be pre-computed
        dep = FeatureDependency(
            feature_id=FeatureId(FeatureNamespace.TECHNICAL, "ema_12"),
            version_constraint=">=1.0.0",
            is_required=True,
            description="MACD fast line uses 12-period EMA as input.",
        )
    """

    feature_id: FeatureId
    version_constraint: str | None = None
    is_required: bool = True
    description: str | None = None

    def satisfies_constraint(self, version: FeatureVersion) -> bool:
        """Return ``True`` when ``version`` satisfies this dependency's constraint.

        Args:
            version: The version of the available upstream feature.

        Returns:
            ``True`` when no constraint is set, or when ``version`` satisfies
            ``self.version_constraint``.
        """
        if self.version_constraint is None:
            return True
        return version.satisfies(self.version_constraint)

    def __str__(self) -> str:
        constraint = f" {self.version_constraint}" if self.version_constraint else ""
        req = "" if self.is_required else " (optional)"
        return f"Depends({self.feature_id!s}{constraint}{req})"


class DependencyGraph:
    """A mutable Directed Acyclic Graph of feature dependencies.

    Nodes are ``FeatureId`` objects. Directed edges represent "requires"
    relationships: an edge from A to B means "A requires B".

    The graph validates acyclicity on each ``add_dependency`` call,
    failing immediately if a cycle would be introduced.

    Usage::

        graph = DependencyGraph()
        graph.add_node(FeatureId(FeatureNamespace.TECHNICAL, "rsi_14"))
        graph.add_dependency(
            dependent=FeatureId(FeatureNamespace.TECHNICAL, "rsi_divergence"),
            dependency=FeatureDependency(
                feature_id=FeatureId(FeatureNamespace.TECHNICAL, "rsi_14")
            ),
        )
        order = graph.topological_sort()
    """

    def __init__(self) -> None:
        # Adjacency list: dependent_id -> set of dependency_ids
        self._edges: dict[FeatureId, set[FeatureId]] = {}
        # All declared dependencies keyed by (dependent_id, dependency_id)
        self._dependencies: dict[tuple[FeatureId, FeatureId], FeatureDependency] = {}

    def add_node(self, feature_id: FeatureId) -> None:
        """Add a node to the graph without any edges.

        Adding an existing node is a no-op.

        Args:
            feature_id: The feature to add as a node.
        """
        if feature_id not in self._edges:
            self._edges[feature_id] = set()

    def add_dependency(
        self,
        dependent: FeatureId,
        dependency: FeatureDependency,
    ) -> None:
        """Add a directed edge: ``dependent`` requires ``dependency.feature_id``.

        Both nodes are added automatically if not already present. After adding
        the edge, the graph is checked for cycles. If a cycle is detected, the
        edge is NOT added and ``CyclicDependencyError`` is raised.

        Args:
            dependent:  The feature that requires the upstream feature.
            dependency: The declared dependency (contains the upstream feature id).

        Raises:
            CyclicDependencyError: If adding this edge would create a cycle.
        """
        dep_id = dependency.feature_id
        self.add_node(dependent)
        self.add_node(dep_id)

        # Temporarily add the edge to check for cycles
        self._edges[dependent].add(dep_id)
        self._dependencies[(dependent, dep_id)] = dependency

        # Validate — rollback if cycle detected
        try:
            self._check_acyclic()
        except CyclicDependencyError:
            self._edges[dependent].discard(dep_id)
            self._dependencies.pop((dependent, dep_id), None)
            raise

    def dependencies_of(self, feature_id: FeatureId) -> frozenset[FeatureDependency]:
        """Return all declared dependencies of the given feature.

        Args:
            feature_id: The feature whose dependencies to retrieve.

        Returns:
            Frozenset of ``FeatureDependency`` objects. Empty when the feature
            has no dependencies or is not in the graph.
        """
        return frozenset(
            dep for (dependent, _), dep in self._dependencies.items() if dependent == feature_id
        )

    def topological_sort(self) -> tuple[FeatureId, ...]:
        """Return all nodes in topological order (dependencies before dependents).

        Returns:
            An ordered tuple of ``FeatureId`` objects. All dependencies of a
            feature appear before the feature itself.

        Raises:
            CyclicDependencyError: If the graph contains a cycle (should not
                happen if ``add_dependency`` is always used, but defensive).
        """
        visited: set[FeatureId] = set()
        result: list[FeatureId] = []

        def dfs(node: FeatureId) -> None:
            if node in visited:
                return
            visited.add(node)
            for neighbour in self._edges.get(node, set()):
                dfs(neighbour)
            result.append(node)

        for node in self._edges:
            dfs(node)

        return tuple(result)

    def has_node(self, feature_id: FeatureId) -> bool:
        """Return ``True`` if the feature is in the graph.

        Args:
            feature_id: The feature to check.

        Returns:
            ``True`` when present.
        """
        return feature_id in self._edges

    @property
    def node_count(self) -> int:
        """Number of nodes in the graph.

        Returns:
            Total count of feature nodes.
        """
        return len(self._edges)

    @property
    def edge_count(self) -> int:
        """Number of directed edges in the graph.

        Returns:
            Total count of dependency relationships.
        """
        return sum(len(deps) for deps in self._edges.values())

    def _check_acyclic(self) -> None:
        """Raise ``CyclicDependencyError`` if the graph has a cycle.

        Uses DFS with three-colour marking:
            0 (WHITE) = unvisited
            1 (GREY)  = in current DFS path
            2 (BLACK) = fully processed
        """
        colour: dict[FeatureId, int] = {node: 0 for node in self._edges}
        path: list[FeatureId] = []

        def dfs(node: FeatureId) -> None:
            colour[node] = 1  # GREY
            path.append(node)
            for neighbour in self._edges.get(node, set()):
                if colour.get(neighbour, 0) == 1:
                    # Back edge — cycle found
                    cycle_start = path.index(neighbour)
                    cycle_nodes = [*path[cycle_start:], neighbour]
                    cycle_str = " -> ".join(str(n) for n in cycle_nodes)
                    raise CyclicDependencyError(cycle_str)
                if colour.get(neighbour, 0) == 0:
                    dfs(neighbour)
            path.pop()
            colour[node] = 2  # BLACK

        for node in list(self._edges.keys()):
            if colour.get(node, 0) == 0:
                dfs(node)

    def to_immutable(self) -> ImmutableDependencyGraph:
        """Return an immutable snapshot of this graph.

        Returns:
            An ``ImmutableDependencyGraph`` capturing the current state.
        """
        return ImmutableDependencyGraph(
            edges=frozenset(
                (dependent, dep_id) for dependent, deps in self._edges.items() for dep_id in deps
            ),
            dependencies=tuple(self._dependencies.values()),
        )

    def __repr__(self) -> str:
        return f"DependencyGraph(nodes={self.node_count}, edges={self.edge_count})"


@dataclass(frozen=True)
class ImmutableDependencyGraph:
    """An immutable snapshot of a dependency graph.

    Stored within a ``FeatureDefinition`` to preserve the dependency
    structure at the time the feature was defined.

    Attributes:
        edges:        Frozenset of ``(dependent_id, dependency_id)`` pairs.
        dependencies: Tuple of all ``FeatureDependency`` objects.
    """

    edges: frozenset[tuple[FeatureId, FeatureId]]
    dependencies: tuple[FeatureDependency, ...]

    @property
    def node_count(self) -> int:
        """Number of distinct feature nodes.

        Returns:
            Count of unique feature ids across all edges.
        """
        nodes: set[FeatureId] = set()
        for dependent, dep_id in self.edges:
            nodes.add(dependent)
            nodes.add(dep_id)
        return len(nodes)

    @property
    def edge_count(self) -> int:
        """Number of directed edges.

        Returns:
            ``len(self.edges)``.
        """
        return len(self.edges)

    @classmethod
    def empty(cls) -> ImmutableDependencyGraph:
        """Return an empty (no dependencies) graph.

        Returns:
            An ``ImmutableDependencyGraph`` with no nodes or edges.
        """
        return cls(edges=frozenset(), dependencies=())

    def __str__(self) -> str:
        return f"ImmutableDependencyGraph(nodes={self.node_count}, edges={self.edge_count})"
