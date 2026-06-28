"""Unit tests for storage health check interfaces."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from athena.storage.health import StorageHealthProtocol, StorageHealthRegistryProtocol
from athena.storage.models import HealthCheckResult, HealthStatus, StorageBackend

NOW = datetime(2025, 1, 15, 9, 15, tzinfo=UTC)


class _MockHealthCheck:
    def __init__(
        self,
        backend: StorageBackend | str,
        status: HealthStatus = HealthStatus.HEALTHY,
    ) -> None:
        self._backend = backend
        self._status = status

    async def check(self) -> HealthCheckResult:
        return HealthCheckResult(
            status=self._status,
            backend=self._backend,
            latency_ms=1.0 if self._status != HealthStatus.UNHEALTHY else None,
            message=self._status.value,
            checked_at=NOW,
        )

    @property
    def backend(self) -> StorageBackend | str:
        return self._backend


class _MockRegistry:
    def __init__(self) -> None:
        self._checks: dict[StorageBackend | str, _MockHealthCheck] = {}

    def register(self, health_check: _MockHealthCheck) -> None:
        self._checks[health_check.backend] = health_check

    async def check_all(self) -> tuple[HealthCheckResult, ...]:
        return tuple([await check.check() for check in self._checks.values()])

    async def check_one(self, backend: StorageBackend | str) -> HealthCheckResult:
        if backend not in self._checks:
            raise KeyError(f"No health check for {backend}")
        return await self._checks[backend].check()

    @property
    def registered_backends(self) -> tuple[StorageBackend | str, ...]:
        return tuple(self._checks.keys())


class _EmptyClass:
    pass


class TestStorageHealthProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockHealthCheck(StorageBackend.TIMESCALEDB), StorageHealthProtocol)

    def test_empty_class_does_not_satisfy(self) -> None:
        assert not isinstance(_EmptyClass(), StorageHealthProtocol)

    async def test_check_returns_result(self) -> None:
        check = _MockHealthCheck(StorageBackend.TIMESCALEDB)
        result = await check.check()
        assert isinstance(result, HealthCheckResult)
        assert result.is_healthy

    async def test_unhealthy_check(self) -> None:
        check = _MockHealthCheck(StorageBackend.TIMESCALEDB, HealthStatus.UNHEALTHY)
        result = await check.check()
        assert not result.is_healthy

    def test_backend_property(self) -> None:
        check = _MockHealthCheck(StorageBackend.DUCKDB)
        assert check.backend == StorageBackend.DUCKDB

    def test_string_backend(self) -> None:
        check = _MockHealthCheck("custom-backend")
        assert check.backend == "custom-backend"


class TestStorageHealthRegistryProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockRegistry(), StorageHealthRegistryProtocol)

    def test_register_and_check_all(self) -> None:
        registry = _MockRegistry()
        registry.register(_MockHealthCheck(StorageBackend.TIMESCALEDB))
        registry.register(_MockHealthCheck(StorageBackend.DUCKDB))
        assert len(registry.registered_backends) == 2

    async def test_check_all_returns_all_results(self) -> None:
        registry = _MockRegistry()
        registry.register(_MockHealthCheck(StorageBackend.TIMESCALEDB))
        registry.register(_MockHealthCheck(StorageBackend.DUCKDB))
        results = await registry.check_all()
        assert len(results) == 2

    async def test_check_one_returns_specific_result(self) -> None:
        registry = _MockRegistry()
        registry.register(_MockHealthCheck(StorageBackend.TIMESCALEDB, HealthStatus.DEGRADED))
        result = await registry.check_one(StorageBackend.TIMESCALEDB)
        assert result.status == HealthStatus.DEGRADED

    async def test_check_one_unknown_backend_raises(self) -> None:
        registry = _MockRegistry()
        with pytest.raises(KeyError):
            await registry.check_one(StorageBackend.S3)

    def test_registered_backends_empty_initially(self) -> None:
        registry = _MockRegistry()
        assert registry.registered_backends == ()
