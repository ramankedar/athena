"""Storage health check interfaces.

``StorageHealthProtocol`` defines how any storage adapter exposes its
operational status. Health checks serve two audiences:

- **Startup readiness**: checked before the platform accepts market data
  or orders, ensuring no engine starts if its storage backend is down.

- **Runtime monitoring**: queried periodically by Prometheus scrapers and
  the Governance Engine's monitoring loop to detect degradation early.

Three-tier status model (from ``HealthStatus`` in ``models.py``):
    HEALTHY   — backend is reachable and within latency/capacity thresholds.
    DEGRADED  — backend is reachable but impaired (high latency, replica lag,
                low disk). Operations succeed but may be slow. Raises an alert.
    UNHEALTHY — backend is unreachable or returning errors. Operations fail.
                Raises ``StorageHealthError`` and pages on-call.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from athena.storage.models import HealthCheckResult, StorageBackend


@runtime_checkable
class StorageHealthProtocol(Protocol):
    """Health check interface for a storage backend.

    Every concrete storage adapter implements this Protocol alongside the
    repository protocols. It is intentionally small — a single ``check()``
    method is sufficient to cover connectivity, latency, and capacity.

    Note:
        Implementations should set ``DEGRADED`` rather than ``UNHEALTHY``
        for conditions that are impaired but operational (e.g. replica lag
        < 10s, disk utilisation 85-95%). Reserve ``UNHEALTHY`` for conditions
        where the backend cannot serve requests at all.
    """

    async def check(self) -> HealthCheckResult:
        """Perform a complete health check and return the result.

        The implementation should:

        1. Attempt a lightweight connectivity probe (e.g. ``SELECT 1`` for
           SQL backends, HEAD request for S3, ``PING`` for Redis).
        2. Measure round-trip latency.
        3. Optionally check disk usage, replication lag, and connection pool
           exhaustion.
        4. Classify the result as ``HEALTHY``, ``DEGRADED``, or ``UNHEALTHY``.

        Returns:
            A ``HealthCheckResult`` with the status, latency, and a message.
            Never raises — exceptional conditions are reflected in the result's
            ``status`` and ``message`` fields.
        """
        ...

    @property
    def backend(self) -> StorageBackend | str:
        """The backend type this health check monitors.

        Returns:
            A ``StorageBackend`` enum value, or a free-form string for custom
            backends not yet in the enum.
        """
        ...


@runtime_checkable
class StorageHealthRegistryProtocol(Protocol):
    """Registry that aggregates health checks from multiple storage backends.

    The platform may use multiple backends simultaneously — TimescaleDB for
    recent data, S3 for archived Parquet files, Redis for caching. The registry
    allows a single ``check_all()`` call to assess the full storage layer.
    """

    def register(self, health_check: StorageHealthProtocol) -> None:
        """Register a storage backend health check.

        Args:
            health_check: A ``StorageHealthProtocol`` implementation to include
                in aggregated checks.
        """
        ...

    async def check_all(self) -> tuple[HealthCheckResult, ...]:
        """Run all registered health checks concurrently.

        Implementations should run checks in parallel (e.g. via
        ``asyncio.gather``) to minimise total check time. A slow or
        unresponsive backend should not block results from healthy ones.

        Returns:
            A tuple of ``HealthCheckResult`` objects, one per registered backend,
            in registration order.
        """
        ...

    async def check_one(self, backend: StorageBackend | str) -> HealthCheckResult:
        """Run the health check for a specific backend.

        Args:
            backend: The backend to check.

        Returns:
            The ``HealthCheckResult`` for the specified backend.

        Raises:
            KeyError: If no health check is registered for the given backend.
        """
        ...

    @property
    def registered_backends(self) -> tuple[StorageBackend | str, ...]:
        """Return all backend identifiers currently registered.

        Returns:
            A tuple of backend identifiers in registration order.
        """
        ...
