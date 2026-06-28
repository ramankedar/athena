"""Unit tests for storage value objects."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime

import pytest

from athena.storage.models import (
    CompatibilityStrategy,
    FilterExpression,
    FilterOperator,
    HealthCheckResult,
    HealthStatus,
    OptimisticLockSpec,
    Page,
    Pagination,
    QuerySpec,
    SchemaVersion,
    SerializationFormat,
    SortDirection,
    SortField,
    StorageBackend,
    StorageMetadata,
    StorageRecord,
    TimeRangeFilter,
)

NOW = datetime(2025, 1, 15, 9, 15, tzinfo=UTC)
LATER = datetime(2025, 1, 15, 15, 30, tzinfo=UTC)


class TestSchemaVersion:
    def test_construction(self) -> None:
        v = SchemaVersion(1, 2, 3)
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_str(self) -> None:
        assert str(SchemaVersion(1, 2, 3)) == "1.2.3"

    def test_negative_major_raises(self) -> None:
        with pytest.raises(ValueError, match="major"):
            SchemaVersion(-1, 0, 0)

    def test_negative_minor_raises(self) -> None:
        with pytest.raises(ValueError, match="minor"):
            SchemaVersion(1, -1, 0)

    def test_negative_patch_raises(self) -> None:
        with pytest.raises(ValueError, match="patch"):
            SchemaVersion(1, 0, -1)

    def test_is_frozen(self) -> None:
        v = SchemaVersion(1, 0, 0)
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            v.major = 2  # type: ignore[misc]

    def test_is_hashable(self) -> None:
        assert hash(SchemaVersion(1, 0, 0)) is not None

    def test_backward_compat_same_major(self) -> None:
        v1 = SchemaVersion(1, 0, 0)
        v1_1 = SchemaVersion(1, 1, 0)
        assert v1_1.is_backward_compatible_with(v1) is True

    def test_not_backward_compat_different_major(self) -> None:
        v1 = SchemaVersion(1, 0, 0)
        v2 = SchemaVersion(2, 0, 0)
        assert v2.is_backward_compatible_with(v1) is False

    def test_same_version_backward_compat(self) -> None:
        v = SchemaVersion(1, 0, 0)
        assert v.is_backward_compatible_with(v) is True

    def test_older_not_backward_compat_with_newer(self) -> None:
        v1_1 = SchemaVersion(1, 1, 0)
        v1_2 = SchemaVersion(1, 2, 0)
        assert v1_1.is_backward_compatible_with(v1_2) is False

    def test_from_string_valid(self) -> None:
        v = SchemaVersion.from_string("2.4.1")
        assert v.major == 2
        assert v.minor == 4
        assert v.patch == 1

    def test_from_string_zeros(self) -> None:
        assert SchemaVersion.from_string("0.0.0") == SchemaVersion(0, 0, 0)

    def test_from_string_invalid_format(self) -> None:
        with pytest.raises(ValueError, match=r"major\.minor\.patch"):
            SchemaVersion.from_string("1.2")

    def test_from_string_non_integer(self) -> None:
        with pytest.raises(ValueError, match="integers"):
            SchemaVersion.from_string("a.b.c")


class TestPagination:
    def test_defaults(self) -> None:
        p = Pagination()
        assert p.offset == 0
        assert p.limit == 100

    def test_custom_values(self) -> None:
        p = Pagination(offset=50, limit=25)
        assert p.offset == 50
        assert p.limit == 25

    def test_negative_offset_raises(self) -> None:
        with pytest.raises(ValueError, match="offset"):
            Pagination(offset=-1)

    def test_zero_limit_raises(self) -> None:
        with pytest.raises(ValueError, match="limit"):
            Pagination(limit=0)

    def test_limit_over_10000_raises(self) -> None:
        with pytest.raises(ValueError, match="limit"):
            Pagination(limit=10_001)

    def test_limit_10000_is_valid(self) -> None:
        p = Pagination(limit=10_000)
        assert p.limit == 10_000

    def test_next_offset(self) -> None:
        assert Pagination(offset=0, limit=100).next_offset == 100
        assert Pagination(offset=100, limit=50).next_offset == 150

    def test_is_frozen(self) -> None:
        p = Pagination()
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            p.offset = 10  # type: ignore[misc]


class TestSortField:
    def test_construction_with_defaults(self) -> None:
        f = SortField("timestamp_utc")
        assert f.field == "timestamp_utc"
        assert f.direction == SortDirection.ASC

    def test_custom_direction(self) -> None:
        f = SortField("ltp", SortDirection.DESC)
        assert f.direction == SortDirection.DESC

    def test_empty_field_raises(self) -> None:
        with pytest.raises(ValueError, match="field"):
            SortField("")

    def test_whitespace_only_field_raises(self) -> None:
        with pytest.raises(ValueError, match="field"):
            SortField("   ")

    def test_is_frozen(self) -> None:
        f = SortField("x")
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            f.field = "y"  # type: ignore[misc]


class TestFilterExpression:
    def test_construction(self) -> None:
        f = FilterExpression("symbol", FilterOperator.EQ, "NSE:NIFTY50-INDEX")
        assert f.field == "symbol"
        assert f.operator == FilterOperator.EQ
        assert f.value == "NSE:NIFTY50-INDEX"

    def test_value_can_be_any_object(self) -> None:
        f1 = FilterExpression("volume", FilterOperator.GTE, 1000)
        f2 = FilterExpression("tags", FilterOperator.IN, ["a", "b"])
        f3 = FilterExpression("name", FilterOperator.CONTAINS, None)
        assert f1.value == 1000
        assert f2.value == ["a", "b"]
        assert f3.value is None

    def test_empty_field_raises(self) -> None:
        with pytest.raises(ValueError, match="field"):
            FilterExpression("", FilterOperator.EQ, "x")

    def test_is_frozen(self) -> None:
        f = FilterExpression("f", FilterOperator.EQ, "v")
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            f.field = "other"  # type: ignore[misc]

    def test_all_operators(self) -> None:
        ops = list(FilterOperator)
        assert FilterOperator.EQ in ops
        assert FilterOperator.BETWEEN in ops
        assert len(ops) == 10


class TestTimeRangeFilter:
    def test_valid_construction(self) -> None:
        r = TimeRangeFilter(from_utc=NOW, to_utc=LATER)
        assert r.from_utc == NOW
        assert r.to_utc == LATER

    def test_naive_from_raises(self) -> None:
        with pytest.raises(ValueError, match="from_utc"):
            TimeRangeFilter(from_utc=datetime(2025, 1, 15), to_utc=LATER)

    def test_naive_to_raises(self) -> None:
        with pytest.raises(ValueError, match="to_utc"):
            TimeRangeFilter(from_utc=NOW, to_utc=datetime(2025, 1, 15, 15))

    def test_equal_from_and_to_raises(self) -> None:
        with pytest.raises(ValueError, match="from_utc"):
            TimeRangeFilter(from_utc=NOW, to_utc=NOW)

    def test_from_after_to_raises(self) -> None:
        with pytest.raises(ValueError, match="from_utc"):
            TimeRangeFilter(from_utc=LATER, to_utc=NOW)

    def test_is_frozen(self) -> None:
        r = TimeRangeFilter(NOW, LATER)
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            r.from_utc = LATER  # type: ignore[misc]


class TestQuerySpec:
    def test_empty_spec(self) -> None:
        spec = QuerySpec()
        assert spec.filters == ()
        assert spec.sort_fields == ()
        assert spec.time_range is None

    def test_with_filters_and_sort(self) -> None:
        spec = QuerySpec(
            filters=(FilterExpression("symbol", FilterOperator.EQ, "X"),),
            sort_fields=(SortField("ts"),),
        )
        assert len(spec.filters) == 1
        assert len(spec.sort_fields) == 1

    def test_is_frozen(self) -> None:
        spec = QuerySpec()
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            spec.filters = ()  # type: ignore[misc]


class TestOptimisticLockSpec:
    def test_construction(self) -> None:
        lock = OptimisticLockSpec(expected_version=3)
        assert lock.expected_version == 3

    def test_zero_version_valid(self) -> None:
        lock = OptimisticLockSpec(expected_version=0)
        assert lock.expected_version == 0

    def test_negative_version_raises(self) -> None:
        with pytest.raises(ValueError, match="expected_version"):
            OptimisticLockSpec(expected_version=-1)

    def test_is_frozen(self) -> None:
        lock = OptimisticLockSpec(3)
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            lock.expected_version = 4  # type: ignore[misc]


class TestStorageMetadata:
    def _make(self) -> StorageMetadata:
        return StorageMetadata(
            created_at=NOW,
            updated_at=NOW,
            version=1,
            schema_version=SchemaVersion(1, 0, 0),
        )

    def test_construction(self) -> None:
        m = self._make()
        assert m.version == 1
        assert m.created_by is None

    def test_naive_created_at_raises(self) -> None:
        with pytest.raises(ValueError, match="created_at"):
            StorageMetadata(
                created_at=datetime(2025, 1, 15),
                updated_at=NOW,
                version=1,
                schema_version=SchemaVersion(1, 0, 0),
            )

    def test_naive_updated_at_raises(self) -> None:
        with pytest.raises(ValueError, match="updated_at"):
            StorageMetadata(
                created_at=NOW,
                updated_at=datetime(2025, 1, 15),
                version=1,
                schema_version=SchemaVersion(1, 0, 0),
            )

    def test_zero_version_raises(self) -> None:
        with pytest.raises(ValueError, match="version"):
            StorageMetadata(
                created_at=NOW,
                updated_at=NOW,
                version=0,
                schema_version=SchemaVersion(1, 0, 0),
            )

    def test_is_frozen(self) -> None:
        m = self._make()
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            m.version = 2  # type: ignore[misc]


class TestStorageRecord:
    def test_construction(self) -> None:
        meta = StorageMetadata(
            created_at=NOW,
            updated_at=NOW,
            version=1,
            schema_version=SchemaVersion(1, 0, 0),
        )
        record: StorageRecord[str] = StorageRecord(key="k", value="hello", metadata=meta)
        assert record.key == "k"
        assert record.value == "hello"
        assert record.metadata is meta

    def test_is_frozen(self) -> None:
        meta = StorageMetadata(
            created_at=NOW,
            updated_at=NOW,
            version=1,
            schema_version=SchemaVersion(1, 0, 0),
        )
        record: StorageRecord[int] = StorageRecord(key="k", value=42, metadata=meta)
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            record.value = 99  # type: ignore[misc]


class TestPage:
    def test_construction(self) -> None:
        page: Page[str] = Page(
            items=("a", "b", "c"),
            total=3,
            offset=0,
            limit=10,
            has_next=False,
            has_previous=False,
        )
        assert page.items == ("a", "b", "c")
        assert page.total == 3

    def test_empty_page(self) -> None:
        page: Page[str] = Page(
            items=(),
            total=0,
            offset=0,
            limit=10,
            has_next=False,
            has_previous=False,
        )
        assert len(page.items) == 0

    def test_negative_total_raises(self) -> None:
        with pytest.raises(ValueError, match="total"):
            Page(items=(), total=-1, offset=0, limit=10, has_next=False, has_previous=False)

    def test_negative_offset_raises(self) -> None:
        with pytest.raises(ValueError, match="offset"):
            Page(items=(), total=0, offset=-1, limit=10, has_next=False, has_previous=False)

    def test_zero_limit_raises(self) -> None:
        with pytest.raises(ValueError, match="limit"):
            Page(items=(), total=0, offset=0, limit=0, has_next=False, has_previous=False)

    def test_is_frozen(self) -> None:
        page: Page[str] = Page((), 0, 0, 10, False, False)
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            page.total = 5  # type: ignore[misc]


class TestHealthCheckResult:
    def test_healthy_result(self) -> None:
        r = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            backend=StorageBackend.TIMESCALEDB,
            latency_ms=1.5,
            message="OK",
            checked_at=NOW,
        )
        assert r.is_healthy is True
        assert r.is_operational is True

    def test_degraded_result(self) -> None:
        r = HealthCheckResult(
            status=HealthStatus.DEGRADED,
            backend=StorageBackend.TIMESCALEDB,
            latency_ms=5000.0,
            message="High latency",
            checked_at=NOW,
        )
        assert r.is_healthy is True
        assert r.is_operational is False

    def test_unhealthy_result(self) -> None:
        r = HealthCheckResult(
            status=HealthStatus.UNHEALTHY,
            backend=StorageBackend.TIMESCALEDB,
            latency_ms=None,
            message="Connection refused",
            checked_at=NOW,
        )
        assert r.is_healthy is False
        assert r.is_operational is False

    def test_naive_checked_at_raises(self) -> None:
        with pytest.raises(ValueError, match="checked_at"):
            HealthCheckResult(
                status=HealthStatus.HEALTHY,
                backend=StorageBackend.TIMESCALEDB,
                latency_ms=1.0,
                message="OK",
                checked_at=datetime(2025, 1, 15),
            )

    def test_negative_latency_raises(self) -> None:
        with pytest.raises(ValueError, match="latency_ms"):
            HealthCheckResult(
                status=HealthStatus.HEALTHY,
                backend=StorageBackend.TIMESCALEDB,
                latency_ms=-1.0,
                message="OK",
                checked_at=NOW,
            )

    def test_none_latency_is_valid(self) -> None:
        r = HealthCheckResult(
            status=HealthStatus.UNHEALTHY,
            backend="custom",
            latency_ms=None,
            message="unreachable",
            checked_at=NOW,
        )
        assert r.latency_ms is None

    def test_string_backend(self) -> None:
        r = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            backend="custom-db",
            latency_ms=2.0,
            message="OK",
            checked_at=NOW,
        )
        assert r.backend == "custom-db"


class TestEnumerations:
    def test_sort_direction_values(self) -> None:
        assert SortDirection.ASC == "asc"
        assert SortDirection.DESC == "desc"

    def test_filter_operator_values(self) -> None:
        assert FilterOperator.EQ == "eq"
        assert FilterOperator.BETWEEN == "between"

    def test_serialization_format_values(self) -> None:
        assert SerializationFormat.JSON == "json"
        assert SerializationFormat.PARQUET == "parquet"

    def test_storage_backend_values(self) -> None:
        assert StorageBackend.TIMESCALEDB == "timescaledb"
        assert StorageBackend.IN_MEMORY == "in_memory"

    def test_health_status_values(self) -> None:
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.UNHEALTHY == "unhealthy"

    def test_compatibility_strategy_values(self) -> None:
        assert CompatibilityStrategy.BACKWARD == "backward"
        assert CompatibilityStrategy.FULL == "full"
        assert CompatibilityStrategy.NONE == "none"
