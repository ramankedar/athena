"""Unit tests for experiment domain Protocol interfaces."""

from __future__ import annotations

from athena.experiments.interfaces import ExperimentRegistryProtocol
from athena.experiments.registry import InMemoryExperimentRegistry


class _EmptyClass:
    pass


class TestExperimentRegistryProtocol:
    def test_in_memory_satisfies(self) -> None:
        assert isinstance(InMemoryExperimentRegistry(), ExperimentRegistryProtocol)

    def test_empty_class_does_not_satisfy(self) -> None:
        assert not isinstance(_EmptyClass(), ExperimentRegistryProtocol)
