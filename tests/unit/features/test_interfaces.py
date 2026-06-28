"""Unit tests for feature domain Protocol interfaces."""

from __future__ import annotations

from athena.features.interfaces import FeatureProviderProtocol, FeatureRegistryProtocol
from athena.features.models import FeatureId, FeatureNamespace
from athena.features.registry import InMemoryFeatureRegistry


class _MockProvider:
    @property
    def supported_features(self) -> frozenset[FeatureId]:
        return frozenset({FeatureId(FeatureNamespace.TECHNICAL, "rsi_14")})

    @property
    def provider_name(self) -> str:
        return "mock_provider"

    def supports(self, feature_id: FeatureId) -> bool:
        return feature_id in self.supported_features


class _EmptyClass:
    pass


class TestFeatureRegistryProtocol:
    def test_in_memory_satisfies(self) -> None:
        assert isinstance(InMemoryFeatureRegistry(), FeatureRegistryProtocol)

    def test_empty_class_does_not_satisfy(self) -> None:
        assert not isinstance(_EmptyClass(), FeatureRegistryProtocol)


class TestFeatureProviderProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockProvider(), FeatureProviderProtocol)

    def test_empty_class_does_not_satisfy(self) -> None:
        assert not isinstance(_EmptyClass(), FeatureProviderProtocol)

    def test_supports_feature(self) -> None:
        provider = _MockProvider()
        assert provider.supports(FeatureId(FeatureNamespace.TECHNICAL, "rsi_14")) is True
        assert provider.supports(FeatureId(FeatureNamespace.TECHNICAL, "macd")) is False

    def test_vendor_name(self) -> None:
        assert _MockProvider().provider_name == "mock_provider"
