"""Experiment lineage graph.

Tracks parent-child relationships between experiments, enabling:
- Impact analysis: which experiments depend on a given experiment?
- Provenance: what sequence of experiments produced this result?
- Reproducibility: the full experimental lineage needed to reproduce a run.

The lineage graph is a Directed Acyclic Graph (DAG) where edges represent
"depends on" relationships. Cycle detection uses DFS with three-colour marking
— the same algorithm as the feature dependency graph in ``athena.features``.

``ExperimentLineageNode`` is an immutable snapshot of a single experiment's
lineage position. The mutable ``ExperimentLineageGraph`` is managed by the
registry and provides ancestor/descendant traversal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from athena.experiments.exceptions import ExperimentLineageCycleError

if TYPE_CHECKING:
    from athena.experiments.models import ExperimentId


@dataclass(frozen=True)
class ExperimentLineageNode:
    """Immutable lineage position for a single experiment.

    Attributes:
        experiment_id: The experiment this node represents.
        parent_ids:    Direct parent experiments (experiments this one
            depends on or extends).

    Example::

        node = ExperimentLineageNode(
            experiment_id=ExperimentId.generate(),
            parent_ids=frozenset({parent_exp_id}),
        )
        assert not node.is_root  # has a parent
    """

    experiment_id: ExperimentId
    parent_ids: frozenset[ExperimentId]

    @property
    def is_root(self) -> bool:
        """Return ``True`` when the experiment has no parents.

        Returns:
            ``True`` when ``parent_ids`` is empty.
        """
        return len(self.parent_ids) == 0

    def __str__(self) -> str:
        n = len(self.parent_ids)
        return f"LineageNode({self.experiment_id!s}, {n} parents)"


class ExperimentLineageGraph:
    """Mutable DAG of experiment lineage relationships.

    Edges represent "experiment A depends on / is derived from experiment B".
    Edges are directed from child to parent: if A depends on B, there is an
    edge from A to B.

    Cycle detection:
        DFS with three-colour marking (WHITE=0, GREY=1, BLACK=2). If DFS
        reaches a GREY node, a back-edge — and therefore a cycle — exists.
        ``ExperimentLineageCycleError`` is raised and the edge is not added.

    Usage::

        graph = ExperimentLineageGraph()
        graph.add_experiment(child_id, parent_ids={parent_id})
        ancestors = graph.ancestors(child_id)
    """

    def __init__(self) -> None:
        # Maps experiment_id -> set of parent_ids (edges point to parents)
        self._parents: dict[ExperimentId, set[ExperimentId]] = {}
        # Reverse map for efficient descendant lookup
        self._children: dict[ExperimentId, set[ExperimentId]] = {}

    def add_experiment(
        self,
        experiment_id: ExperimentId,
        parent_ids: frozenset[ExperimentId] | None = None,
    ) -> None:
        """Register an experiment with its parent relationships.

        Validates that adding the parents would not create a cycle.

        Args:
            experiment_id: The experiment to register.
            parent_ids:    Direct parent experiments. ``None`` or empty = root.

        Raises:
            ExperimentLineageCycleError: If the parents would create a cycle.
        """
        parents = parent_ids or frozenset()

        if experiment_id not in self._parents:
            self._parents[experiment_id] = set()
        if experiment_id not in self._children:
            self._children[experiment_id] = set()

        for parent_id in parents:
            if parent_id not in self._parents:
                self._parents[parent_id] = set()
            if parent_id not in self._children:
                self._children[parent_id] = set()

            self._parents[experiment_id].add(parent_id)
            self._children[parent_id].add(experiment_id)

        try:
            self._check_acyclic()
        except ExperimentLineageCycleError:
            # Rollback
            for parent_id in parents:
                self._parents[experiment_id].discard(parent_id)
                self._children[parent_id].discard(experiment_id)
            raise

    def ancestors(self, experiment_id: ExperimentId) -> frozenset[ExperimentId]:
        """Return all ancestors (transitive parents) of the given experiment.

        Args:
            experiment_id: The experiment whose ancestors to retrieve.

        Returns:
            Frozenset of all experiment IDs that are ancestors, at any depth.
            Empty when the experiment is a root or not in the graph.
        """
        result: set[ExperimentId] = set()
        stack = list(self._parents.get(experiment_id, set()))
        while stack:
            parent = stack.pop()
            if parent not in result:
                result.add(parent)
                stack.extend(self._parents.get(parent, set()))
        return frozenset(result)

    def descendants(self, experiment_id: ExperimentId) -> frozenset[ExperimentId]:
        """Return all descendants (transitive children) of the given experiment.

        Args:
            experiment_id: The experiment whose descendants to retrieve.

        Returns:
            Frozenset of all experiment IDs that are descendants, at any depth.
        """
        result: set[ExperimentId] = set()
        stack = list(self._children.get(experiment_id, set()))
        while stack:
            child = stack.pop()
            if child not in result:
                result.add(child)
                stack.extend(self._children.get(child, set()))
        return frozenset(result)

    def direct_parents(self, experiment_id: ExperimentId) -> frozenset[ExperimentId]:
        """Return the direct (immediate) parents of the given experiment.

        Args:
            experiment_id: The experiment to query.

        Returns:
            Frozenset of direct parent IDs.
        """
        return frozenset(self._parents.get(experiment_id, set()))

    def direct_children(self, experiment_id: ExperimentId) -> frozenset[ExperimentId]:
        """Return the direct (immediate) children of the given experiment.

        Args:
            experiment_id: The experiment to query.

        Returns:
            Frozenset of direct child IDs.
        """
        return frozenset(self._children.get(experiment_id, set()))

    @property
    def roots(self) -> frozenset[ExperimentId]:
        """Return all experiments with no parents (origin experiments).

        Returns:
            Frozenset of root experiment IDs.
        """
        return frozenset(eid for eid, parents in self._parents.items() if not parents)

    @property
    def leaves(self) -> frozenset[ExperimentId]:
        """Return all experiments with no children (most recent experiments).

        Returns:
            Frozenset of leaf experiment IDs.
        """
        return frozenset(eid for eid, children in self._children.items() if not children)

    def has_experiment(self, experiment_id: ExperimentId) -> bool:
        """Return ``True`` if the experiment is in the lineage graph.

        Args:
            experiment_id: The experiment to check.

        Returns:
            ``True`` when registered.
        """
        return experiment_id in self._parents

    def to_node(self, experiment_id: ExperimentId) -> ExperimentLineageNode | None:
        """Return the lineage node for the given experiment, or ``None``.

        Args:
            experiment_id: The experiment to retrieve.

        Returns:
            An ``ExperimentLineageNode``, or ``None`` if not in the graph.
        """
        if experiment_id not in self._parents:
            return None
        return ExperimentLineageNode(
            experiment_id=experiment_id,
            parent_ids=frozenset(self._parents[experiment_id]),
        )

    @property
    def experiment_count(self) -> int:
        """Number of experiments in the lineage graph.

        Returns:
            Total count of registered experiments.
        """
        return len(self._parents)

    def _check_acyclic(self) -> None:
        """Raise ``ExperimentLineageCycleError`` if the graph contains a cycle."""
        colour: dict[ExperimentId, int] = {eid: 0 for eid in self._parents}
        path: list[ExperimentId] = []

        def dfs(node: ExperimentId) -> None:
            colour[node] = 1  # GREY
            path.append(node)
            for parent in self._parents.get(node, set()):
                if colour.get(parent, 0) == 1:
                    cycle_start = path.index(parent)
                    cycle_nodes = [*path[cycle_start:], parent]
                    cycle_str = " -> ".join(str(n) for n in cycle_nodes)
                    raise ExperimentLineageCycleError(cycle_str)
                if colour.get(parent, 0) == 0:
                    dfs(parent)
            path.pop()
            colour[node] = 2  # BLACK

        for node in list(self._parents.keys()):
            if colour.get(node, 0) == 0:
                dfs(node)

    def __repr__(self) -> str:
        return (
            f"ExperimentLineageGraph(experiments={self.experiment_count}, roots={len(self.roots)})"
        )
