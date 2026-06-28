"""Unit tests for experiment lineage graph."""

from __future__ import annotations

import contextlib

import pytest

from athena.experiments.exceptions import ExperimentLineageCycleError
from athena.experiments.lineage import ExperimentLineageGraph, ExperimentLineageNode
from athena.experiments.models import ExperimentId


def _eid() -> ExperimentId:
    return ExperimentId.generate()


class TestExperimentLineageNode:
    def test_root_node(self) -> None:
        node = ExperimentLineageNode(
            experiment_id=_eid(),
            parent_ids=frozenset(),
        )
        assert node.is_root is True

    def test_non_root_node(self) -> None:
        parent = _eid()
        node = ExperimentLineageNode(
            experiment_id=_eid(),
            parent_ids=frozenset({parent}),
        )
        assert node.is_root is False

    def test_str(self) -> None:
        node = ExperimentLineageNode(experiment_id=_eid(), parent_ids=frozenset())
        assert "0 parents" in str(node)


class TestExperimentLineageGraph:
    def test_empty_graph(self) -> None:
        g = ExperimentLineageGraph()
        assert g.experiment_count == 0
        assert g.roots == frozenset()

    def test_add_root(self) -> None:
        g = ExperimentLineageGraph()
        eid = _eid()
        g.add_experiment(eid)
        assert g.has_experiment(eid)
        assert eid in g.roots

    def test_add_child(self) -> None:
        g = ExperimentLineageGraph()
        parent = _eid()
        child = _eid()
        g.add_experiment(parent)
        g.add_experiment(child, parent_ids=frozenset({parent}))
        assert parent in g.direct_parents(child)
        assert child in g.direct_children(parent)

    def test_ancestors(self) -> None:
        g = ExperimentLineageGraph()
        a = _eid()
        b = _eid()
        c = _eid()
        g.add_experiment(a)
        g.add_experiment(b, parent_ids=frozenset({a}))
        g.add_experiment(c, parent_ids=frozenset({b}))
        ancestors = g.ancestors(c)
        assert a in ancestors
        assert b in ancestors
        assert c not in ancestors

    def test_descendants(self) -> None:
        g = ExperimentLineageGraph()
        a = _eid()
        b = _eid()
        c = _eid()
        g.add_experiment(a)
        g.add_experiment(b, parent_ids=frozenset({a}))
        g.add_experiment(c, parent_ids=frozenset({b}))
        descendants = g.descendants(a)
        assert b in descendants
        assert c in descendants
        assert a not in descendants

    def test_roots(self) -> None:
        g = ExperimentLineageGraph()
        a = _eid()
        b = _eid()
        g.add_experiment(a)
        g.add_experiment(b, parent_ids=frozenset({a}))
        assert a in g.roots
        assert b not in g.roots

    def test_leaves(self) -> None:
        g = ExperimentLineageGraph()
        a = _eid()
        b = _eid()
        g.add_experiment(a)
        g.add_experiment(b, parent_ids=frozenset({a}))
        assert b in g.leaves
        assert a not in g.leaves

    def test_cycle_direct_raises(self) -> None:
        g = ExperimentLineageGraph()
        a = _eid()
        b = _eid()
        g.add_experiment(a)
        g.add_experiment(b, parent_ids=frozenset({a}))
        with pytest.raises(ExperimentLineageCycleError, match="->"):
            g.add_experiment(a, parent_ids=frozenset({b}))

    def test_cycle_rolls_back(self) -> None:
        g = ExperimentLineageGraph()
        a = _eid()
        b = _eid()
        g.add_experiment(a)
        g.add_experiment(b, parent_ids=frozenset({a}))
        count_before = g.experiment_count
        with contextlib.suppress(ExperimentLineageCycleError):
            g.add_experiment(a, parent_ids=frozenset({b}))
        # experiment count unchanged after rollback
        assert g.experiment_count == count_before

    def test_indirect_cycle_raises(self) -> None:
        g = ExperimentLineageGraph()
        a = _eid()
        b = _eid()
        c = _eid()
        g.add_experiment(a)
        g.add_experiment(b, parent_ids=frozenset({a}))
        g.add_experiment(c, parent_ids=frozenset({b}))
        with pytest.raises(ExperimentLineageCycleError):
            g.add_experiment(a, parent_ids=frozenset({c}))

    def test_to_node(self) -> None:
        g = ExperimentLineageGraph()
        a = _eid()
        b = _eid()
        g.add_experiment(a)
        g.add_experiment(b, parent_ids=frozenset({a}))
        node = g.to_node(b)
        assert node is not None
        assert node.is_root is False

    def test_to_node_not_found(self) -> None:
        g = ExperimentLineageGraph()
        assert g.to_node(_eid()) is None

    def test_multi_parent(self) -> None:
        g = ExperimentLineageGraph()
        p1 = _eid()
        p2 = _eid()
        child = _eid()
        g.add_experiment(p1)
        g.add_experiment(p2)
        g.add_experiment(child, parent_ids=frozenset({p1, p2}))
        parents = g.direct_parents(child)
        assert p1 in parents
        assert p2 in parents

    def test_repr(self) -> None:
        g = ExperimentLineageGraph()
        r = repr(g)
        assert "experiments=0" in r
