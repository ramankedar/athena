"""Unit tests for instrument registry Protocol definitions."""

from __future__ import annotations

from athena.assets.interfaces import InstrumentLookupProtocol, InstrumentRegistryProtocol
from athena.assets.registry import InMemoryInstrumentRegistry


class TestInstrumentLookupProtocol:
    def test_registry_satisfies_lookup_protocol(self) -> None:
        assert isinstance(InMemoryInstrumentRegistry(), InstrumentLookupProtocol)

    def test_empty_class_does_not_satisfy(self) -> None:
        class Empty:
            pass

        assert not isinstance(Empty(), InstrumentLookupProtocol)


class TestInstrumentRegistryProtocol:
    def test_in_memory_registry_satisfies_protocol(self) -> None:
        assert isinstance(InMemoryInstrumentRegistry(), InstrumentRegistryProtocol)

    def test_registry_also_satisfies_lookup(self) -> None:
        registry = InMemoryInstrumentRegistry()
        assert isinstance(registry, InstrumentLookupProtocol)
        assert isinstance(registry, InstrumentRegistryProtocol)

    def test_empty_class_does_not_satisfy(self) -> None:
        class Empty:
            pass

        assert not isinstance(Empty(), InstrumentRegistryProtocol)
