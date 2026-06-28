"""Unit tests for feature dependency graph."""

from __future__ import annotations

import pytest

from athena.features.dependencies import (
    DependencyGraph,
    FeatureDependency,
    ImmutableDependencyGraph,
)
from athena.features.exceptions import CyclicDependencyError
from athena.features.models import FeatureId, FeatureNamespace, FeatureVersion


def _fid(name: str) -> FeatureId:
    return FeatureId(FeatureNamespace.TECHNICAL, name)


def _dep(name: str, constraint: str | None = None, required: bool = True) -> FeatureDependency:
    return FeatureDependency(
        feature_id=_fid(name),
        version_constraint=constraint,
        is_required=required,
    )


class TestFeatureDependency:
    def test_required_default(self) -> None:
        dep = FeatureDependency(feature_id=_fid("rsi"))
        assert dep.is_required is True

    def test_optional(self) -> None:
        dep = FeatureDependency(feature_id=_fid("macd"), is_required=False)
        assert dep.is_required is False

    def test_satisfies_no_constraint(self) -> None:
        dep = FeatureDependency(feature_id=_fid("rsi"))
        assert dep.satisfies_constraint(FeatureVersion(1, 0, 0)) is True
        assert dep.satisfies_constraint(FeatureVersion(99, 0, 0)) is True

    def test_satisfies_version_constraint(self) -> None:
        dep = FeatureDependency(
            feature_id=_fid("rsi"),
            version_constraint=">=1.0.0",
        )
        assert dep.satisfies_constraint(FeatureVersion(1, 0, 0)) is True
        assert dep.satisfies_constraint(FeatureVersion(0, 9, 0)) is False

    def test_str(self) -> None:
        dep = FeatureDependency(
            feature_id=_fid("rsi"),
            version_constraint=">=1.0.0",
        )
        s = str(dep)
        assert "rsi" in s
        assert ">=1.0.0" in s


class TestDependencyGraph:
    def test_empty_graph(self) -> None:
        g = DependencyGraph()
        assert g.node_count == 0
        assert g.edge_count == 0

    def test_add_node(self) -> None:
        g = DependencyGraph()
        g.add_node(_fid("rsi"))
        assert g.node_count == 1
        assert g.has_node(_fid("rsi"))

    def test_add_node_idempotent(self) -> None:
        g = DependencyGraph()
        g.add_node(_fid("rsi"))
        g.add_node(_fid("rsi"))
        assert g.node_count == 1

    def test_add_dependency(self) -> None:
        g = DependencyGraph()
        g.add_dependency(_fid("macd"), _dep("ema_12"))
        assert g.node_count == 2
        assert g.edge_count == 1

    def test_topological_sort_simple(self) -> None:
        g = DependencyGraph()
        g.add_dependency(_fid("b"), _dep("a"))  # b requires a
        order = g.topological_sort()
        a_idx = list(order).index(_fid("a"))
        b_idx = list(order).index(_fid("b"))
        assert a_idx < b_idx  # a before b

    def test_topological_sort_chain(self) -> None:
        g = DependencyGraph()
        g.add_dependency(_fid("c"), _dep("b"))  # c requires b
        g.add_dependency(_fid("b"), _dep("a"))  # b requires a
        order = g.topological_sort()
        a_idx = list(order).index(_fid("a"))
        b_idx = list(order).index(_fid("b"))
        c_idx = list(order).index(_fid("c"))
        assert a_idx < b_idx < c_idx

    def test_cycle_detection_direct(self) -> None:
        g = DependencyGraph()
        g.add_dependency(_fid("b"), _dep("a"))  # b requires a
        with pytest.raises(CyclicDependencyError, match="->"):
            g.add_dependency(_fid("a"), _dep("b"))  # a requires b → cycle

    def test_cycle_detection_indirect(self) -> None:
        g = DependencyGraph()
        g.add_dependency(_fid("b"), _dep("a"))  # b requires a
        g.add_dependency(_fid("c"), _dep("b"))  # c requires b
        with pytest.raises(CyclicDependencyError):
            g.add_dependency(_fid("a"), _dep("c"))  # a requires c → cycle a→c→b→a

    def test_cycle_rolls_back_edge(self) -> None:
        import contextlib

        g = DependencyGraph()
        g.add_dependency(_fid("b"), _dep("a"))
        with contextlib.suppress(CyclicDependencyError):
            g.add_dependency(_fid("a"), _dep("b"))  # cycle
        # The graph should still be valid (edge not added)
        assert g.edge_count == 1

    def test_dependencies_of(self) -> None:
        g = DependencyGraph()
        g.add_dependency(_fid("macd"), _dep("ema_12"))
        g.add_dependency(_fid("macd"), _dep("ema_26"))
        deps = g.dependencies_of(_fid("macd"))
        assert len(deps) == 2

    def test_to_immutable(self) -> None:
        g = DependencyGraph()
        g.add_dependency(_fid("b"), _dep("a"))
        immutable = g.to_immutable()
        assert isinstance(immutable, ImmutableDependencyGraph)
        assert immutable.edge_count == 1

    def test_repr(self) -> None:
        g = DependencyGraph()
        g.add_node(_fid("x"))
        r = repr(g)
        assert "nodes=1" in r


class TestImmutableDependencyGraph:
    def test_empty(self) -> None:
        g = ImmutableDependencyGraph.empty()
        assert g.edge_count == 0
        assert g.node_count == 0

    def test_with_edges(self) -> None:
        a = _fid("a")
        b = _fid("b")
        dep = _dep("a")
        g = ImmutableDependencyGraph(
            edges=frozenset({(b, a)}),
            dependencies=(dep,),
        )
        assert g.edge_count == 1
        assert g.node_count == 2

    def test_str(self) -> None:
        g = ImmutableDependencyGraph.empty()
        s = str(g)
        assert "0" in s
