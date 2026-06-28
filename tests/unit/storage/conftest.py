"""Shared fixtures for storage unit tests.

The storage domain is pure interfaces and value objects — no concrete backend.
Fixtures here provide:
  - Pre-built immutable model instances (SchemaVersion, Pagination, etc.)
  - Timezone-aware datetimes for timestamp fields
  - A lightweight ``TimeRangeFilter`` factory
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from athena.storage.models import (
    FilterExpression,
    FilterOperator,
    HealthCheckResult,
    HealthStatus,
    Pagination,
    QuerySpec,
    SchemaVersion,
    SortDirection,
    SortField,
    StorageBackend,
    StorageMetadata,
    TimeRangeFilter,
)

# ── Reference timestamps ──────────────────────────────────────────────────────

NOW = datetime(2025, 1, 15, 9, 15, 0, tzinfo=UTC)
LATER = datetime(2025, 1, 15, 15, 30, 0, tzinfo=UTC)
NAIVE = datetime(2025, 1, 15, 9, 15, 0)  # no tzinfo — should always fail


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def v1() -> SchemaVersion:
    """Schema version 1.0.0."""
    return SchemaVersion(1, 0, 0)


@pytest.fixture
def v1_1() -> SchemaVersion:
    """Schema version 1.1.0 — minor bump (backward compatible)."""
    return SchemaVersion(1, 1, 0)


@pytest.fixture
def v2() -> SchemaVersion:
    """Schema version 2.0.0 — major bump (breaking)."""
    return SchemaVersion(2, 0, 0)


@pytest.fixture
def default_pagination() -> Pagination:
    """Default pagination (offset=0, limit=100)."""
    return Pagination()


@pytest.fixture
def metadata(v1: SchemaVersion) -> StorageMetadata:
    """A complete StorageMetadata for use in storage record tests."""
    return StorageMetadata(
        created_at=NOW,
        updated_at=NOW,
        version=1,
        schema_version=v1,
        created_by="data_engine",
        backend=StorageBackend.TIMESCALEDB,
    )


@pytest.fixture
def time_range() -> TimeRangeFilter:
    """A valid half-open time range filter."""
    return TimeRangeFilter(from_utc=NOW, to_utc=LATER)


@pytest.fixture
def query_spec(time_range: TimeRangeFilter) -> QuerySpec:
    """A QuerySpec with a symbol filter, ascending sort, and time range."""
    return QuerySpec(
        filters=(FilterExpression("symbol", FilterOperator.EQ, "NSE:NIFTY50-INDEX"),),
        sort_fields=(SortField("timestamp_utc", SortDirection.ASC),),
        pagination=Pagination(offset=0, limit=50),
        time_range=time_range,
    )


@pytest.fixture
def healthy_result() -> HealthCheckResult:
    """A HEALTHY HealthCheckResult."""
    return HealthCheckResult(
        status=HealthStatus.HEALTHY,
        backend=StorageBackend.TIMESCALEDB,
        latency_ms=1.2,
        message="Connected and responsive",
        checked_at=NOW,
    )
