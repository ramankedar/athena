"""Immutable value objects for the storage domain.

All models are frozen dataclasses or enumerations. They carry no behaviour
beyond structural validation in ``__post_init__`` and simple derived properties.

Design notes:
    - ``Page[T]`` uses ``tuple[T_co, ...]`` for true immutability.
    - ``QuerySpec`` composes ``FilterExpression``, ``SortField``, ``Pagination``,
      and ``TimeRangeFilter`` — keeping query logic backend-agnostic.
    - ``StorageMetadata`` is the provenance record attached to every stored entity.
    - ``SchemaVersion`` uses semantic versioning; only major bumps break backward
      compatibility.
    - ``TimeRangeFilter`` is intentionally NOT imported from ``athena.time``.
      The storage domain and the time domain are peer layers. Using raw
      ``datetime`` objects here keeps the two domains decoupled.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from datetime import datetime

_T_co = TypeVar("_T_co", covariant=True)


# ── Type alias ─────────────────────────────────────────────────────────────────

StorageKey = str
"""Canonical string representation of a storage record key.

Every backend converts to and from its native key type (``int``, ``UUID``,
S3 path, etc.) at the adapter boundary. Within the storage domain, all keys
are strings to keep the interface layer backend-neutral.

Examples:
    ``"NSE:NIFTY50-INDEX"`` — instrument key
    ``"NSE:NIFTY50-INDEX::2025-01-15T09:15:00Z"`` — tick composite key
"""


# ── Enumerations ───────────────────────────────────────────────────────────────


class SortDirection(StrEnum):
    """Direction for an ordered query result.

    Attributes:
        ASC:  Results ordered from smallest to largest value.
        DESC: Results ordered from largest to smallest value.
    """

    ASC = "asc"
    DESC = "desc"


class FilterOperator(StrEnum):
    """Comparison operator in a ``FilterExpression``.

    Backend adapters translate these operators to their native equivalents
    (SQL ``WHERE``, Pandas boolean masks, Parquet predicate pushdown, etc.).

    Attributes:
        EQ:       Field exactly equals value.
        NEQ:      Field does not equal value.
        GT:       Field is strictly greater than value.
        GTE:      Field is greater than or equal to value.
        LT:       Field is strictly less than value.
        LTE:      Field is less than or equal to value.
        IN:       Field value is a member of the given collection.
        NOT_IN:   Field value is not a member of the given collection.
        CONTAINS: Field string value contains the given substring.
        BETWEEN:  Field value falls between two bounds (inclusive).
    """

    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    BETWEEN = "between"


class SerializationFormat(StrEnum):
    """Wire format for serialising domain objects to bytes.

    Attributes:
        JSON:     Human-readable JSON. Suitable for configuration and small records.
        MSGPACK:  Compact binary JSON-compatible format. Good default for events.
        PARQUET:  Columnar format optimised for analytics and bulk S3 storage.
        ARROW:    Apache Arrow IPC format. Low-copy interchange with DuckDB/Polars.
        PROTOBUF: Protocol Buffers. Schema-enforced binary format.
    """

    JSON = "json"
    MSGPACK = "msgpack"
    PARQUET = "parquet"
    ARROW = "arrow"
    PROTOBUF = "protobuf"


class StorageBackend(StrEnum):
    """Identifier for a supported storage backend.

    Attributes:
        TIMESCALEDB: PostgreSQL with TimescaleDB extension (default).
        DUCKDB:      Embedded analytical database (research and backtesting).
        S3:          AWS S3 compatible object storage (bulk archive).
        PARQUET:     Local Parquet files (offline research).
        IN_MEMORY:   Ephemeral in-process store (testing and caching).
    """

    TIMESCALEDB = "timescaledb"
    DUCKDB = "duckdb"
    S3 = "s3"
    PARQUET = "parquet"
    IN_MEMORY = "in_memory"


class HealthStatus(StrEnum):
    """Status level for a storage health check.

    Attributes:
        HEALTHY:   Backend is operating within normal parameters.
        DEGRADED:  Backend is reachable but impaired (high latency, low disk,
            replica lag). Operations may be slow but will succeed.
        UNHEALTHY: Backend is unreachable or returning errors. Operations
            will fail. Raises ``StorageHealthError``.
    """

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class CompatibilityStrategy(StrEnum):
    """Backward/forward compatibility guarantee for a schema migration.

    Attributes:
        BACKWARD: New schema readers can read data written by the old schema.
        FORWARD:  Old schema readers can read data written by the new schema.
        FULL:     Both backward and forward compatible.
        NONE:     No compatibility guarantee. Full re-encode required.
    """

    BACKWARD = "backward"
    FORWARD = "forward"
    FULL = "full"
    NONE = "none"


# ── Value objects ──────────────────────────────────────────────────────────────


@dataclass(frozen=True, order=True)
class SchemaVersion:
    """Semantic version for a storage schema.

    Only the ``major`` component indicates a breaking change. Incrementing
    ``minor`` adds new optional fields (backward compatible). Incrementing
    ``patch`` fixes defects without schema changes.

    Attributes:
        major: Breaking-change counter. Readers using a lower major version
            cannot read records written with a higher one.
        minor: Backward-compatible addition counter.
        patch: Backward-compatible fix counter.

    Example::

        v1 = SchemaVersion(1, 0, 0)
        v2 = SchemaVersion(1, 2, 0)
        assert v2.is_backward_compatible_with(v1)
    """

    major: int
    minor: int
    patch: int

    def __post_init__(self) -> None:
        for name, val in (("major", self.major), ("minor", self.minor), ("patch", self.patch)):
            if val < 0:
                raise ValueError(f"SchemaVersion.{name} must be >= 0, got {val}")

    def is_backward_compatible_with(self, other: SchemaVersion) -> bool:
        """Return ``True`` if this version can read data written by ``other``.

        Backward compatibility is guaranteed when the major version matches
        and this version is newer (higher minor/patch) than ``other``.

        Args:
            other: The older schema version to compare against.

        Returns:
            ``True`` when this version can read ``other``'s records.
        """
        return self.major == other.major and (self.minor, self.patch) >= (other.minor, other.patch)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    @classmethod
    def from_string(cls, version: str) -> SchemaVersion:
        """Parse a dotted version string into a ``SchemaVersion``.

        Args:
            version: A string in the form ``"major.minor.patch"``.

        Returns:
            A new ``SchemaVersion`` instance.

        Raises:
            ValueError: If the string is not in the expected format.
        """
        parts = version.split(".")
        if len(parts) != 3:
            raise ValueError(f"SchemaVersion string must be 'major.minor.patch', got {version!r}")
        try:
            return cls(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"SchemaVersion components must be integers: {version!r}") from exc


@dataclass(frozen=True)
class Pagination:
    """Cursor-free offset/limit pagination parameters.

    Attributes:
        offset: Number of records to skip (zero-indexed). Must be >= 0.
        limit:  Maximum records to return per page. Must be between 1 and 10 000.

    Example::

        page = Pagination(offset=0, limit=100)
        next_page = Pagination(offset=100, limit=100)
    """

    offset: int = 0
    limit: int = 100

    def __post_init__(self) -> None:
        if self.offset < 0:
            raise ValueError(f"Pagination.offset must be >= 0, got {self.offset}")
        if not (1 <= self.limit <= 10_000):
            raise ValueError(f"Pagination.limit must be between 1 and 10000, got {self.limit}")

    @property
    def next_offset(self) -> int:
        """The offset to use for the next page.

        Returns:
            ``offset + limit``.
        """
        return self.offset + self.limit


@dataclass(frozen=True)
class SortField:
    """A single field name and sort direction for an ordered query.

    Attributes:
        field:     Name of the field to sort by.
        direction: ``ASC`` (default) or ``DESC``.
    """

    field: str
    direction: SortDirection = SortDirection.ASC

    def __post_init__(self) -> None:
        if not self.field.strip():
            raise ValueError("SortField.field must not be empty")


@dataclass(frozen=True)
class FilterExpression:
    """A single predicate used to narrow a query result set.

    Attributes:
        field:    Name of the field to filter on.
        operator: Comparison operator.
        value:    The right-hand side of the comparison. Typed as ``object``
            (not ``Any``) to avoid disabling mypy while still accepting any
            Python value. Backend adapters are responsible for type-checking
            the value against the field's storage type.

    Example::

        FilterExpression("symbol", FilterOperator.EQ, "NSE:NIFTY50-INDEX")
        FilterExpression("ltp", FilterOperator.GTE, Decimal("24000"))
        FilterExpression("volume", FilterOperator.BETWEEN, (1000, 5000))
    """

    field: str
    operator: FilterOperator
    value: object

    def __post_init__(self) -> None:
        if not self.field.strip():
            raise ValueError("FilterExpression.field must not be empty")


@dataclass(frozen=True)
class TimeRangeFilter:
    """A half-open time range filter ``[from_utc, to_utc)`` for time-series queries.

    Both datetimes must be timezone-aware. This type is intentionally local
    to the storage domain and does not import ``athena.time.TimeRange``
    to keep the two peer layers decoupled.

    Attributes:
        from_utc: Inclusive lower bound (timezone-aware UTC).
        to_utc:   Exclusive upper bound (timezone-aware UTC).

    Raises:
        ValueError: If either datetime is naive, or ``from_utc >= to_utc``.
    """

    from_utc: datetime
    to_utc: datetime

    def __post_init__(self) -> None:
        if self.from_utc.tzinfo is None:
            raise ValueError("TimeRangeFilter.from_utc must be timezone-aware")
        if self.to_utc.tzinfo is None:
            raise ValueError("TimeRangeFilter.to_utc must be timezone-aware")
        if self.from_utc >= self.to_utc:
            raise ValueError(
                f"TimeRangeFilter.from_utc must be < to_utc: {self.from_utc!r} >= {self.to_utc!r}"
            )


@dataclass(frozen=True)
class QuerySpec:
    """A complete, backend-agnostic query specification.

    Composes filters, sort order, pagination, and an optional time range.
    Backend adapters translate this into their native query language
    (SQL, Parquet predicate pushdown, Polars expressions, etc.).

    Attributes:
        filters:    Zero or more filter predicates (ANDed together).
        sort_fields: Zero or more sort specifications (applied in order).
        pagination: Offset/limit pagination parameters.
        time_range: Optional time range for time-series queries. When set,
            implementations apply this as an additional constraint on the
            record's primary timestamp field.
    """

    filters: tuple[FilterExpression, ...] = ()
    sort_fields: tuple[SortField, ...] = ()
    pagination: Pagination = field(default_factory=Pagination)
    time_range: TimeRangeFilter | None = None


@dataclass(frozen=True)
class OptimisticLockSpec:
    """Specification for an optimistic-locking write operation.

    Passed to ``update()`` to prevent lost updates under concurrent writes.
    If the stored record's version does not match ``expected_version``,
    the implementation raises ``VersionConflictError``.

    Attributes:
        expected_version: The version number the caller read from storage
            before constructing the update. Must be >= 0.

    Example::

        # Re-read → update → write with lock
        record = await repo.get_with_metadata(key)
        updated = transform(record.value)
        lock = OptimisticLockSpec(expected_version=record.metadata.version)
        await repo.update(key, updated, lock=lock)
    """

    expected_version: int

    def __post_init__(self) -> None:
        if self.expected_version < 0:
            raise ValueError(
                f"OptimisticLockSpec.expected_version must be >= 0, got {self.expected_version}"
            )


@dataclass(frozen=True)
class StorageMetadata:
    """Provenance and concurrency metadata attached to every stored record.

    Attributes:
        created_at:     UTC timestamp when the record was first written.
        updated_at:     UTC timestamp of the most recent write.
        version:        Monotonically increasing write counter. Used for
            optimistic locking. Starts at 1 on first write.
        schema_version: Schema version of the serialised representation.
        created_by:     Optional identifier of the engine or service that
            created the record (e.g. ``"data_engine"``).
        backend:        The storage backend where the record is held.
    """

    created_at: datetime
    updated_at: datetime
    version: int
    schema_version: SchemaVersion
    created_by: str | None = None
    backend: StorageBackend | None = None

    def __post_init__(self) -> None:
        if self.created_at.tzinfo is None:
            raise ValueError("StorageMetadata.created_at must be timezone-aware")
        if self.updated_at.tzinfo is None:
            raise ValueError("StorageMetadata.updated_at must be timezone-aware")
        if self.version < 1:
            raise ValueError(f"StorageMetadata.version must be >= 1, got {self.version}")


@dataclass(frozen=True)
class StorageRecord(Generic[_T_co]):
    """A domain value paired with its storage metadata.

    Returned by ``get_with_metadata()`` and ``list_with_metadata()`` when
    the caller needs provenance information alongside the domain object.

    Attributes:
        key:      Storage key for this record.
        value:    The domain object.
        metadata: Provenance and concurrency metadata.
    """

    key: StorageKey
    value: _T_co
    metadata: StorageMetadata


@dataclass(frozen=True)
class Page(Generic[_T_co]):
    """A single page of results from a list query.

    All list operations return ``Page[T]`` to prevent unbounded result sets.
    The ``total`` field reflects the total matching record count (not just
    the current page size), enabling UI pagination and progress reporting.

    Attributes:
        items:        Tuple of entities on this page.
        total:        Total count of matching entities across all pages.
        offset:       Offset used to produce this page.
        limit:        Limit used to produce this page.
        has_next:     Whether more pages exist after this one.
        has_previous: Whether pages exist before this one.
    """

    items: tuple[_T_co, ...]
    total: int
    offset: int
    limit: int
    has_next: bool
    has_previous: bool

    def __post_init__(self) -> None:
        if self.total < 0:
            raise ValueError(f"Page.total must be >= 0, got {self.total}")
        if self.offset < 0:
            raise ValueError(f"Page.offset must be >= 0, got {self.offset}")
        if self.limit < 1:
            raise ValueError(f"Page.limit must be >= 1, got {self.limit}")


@dataclass(frozen=True)
class HealthCheckResult:
    """Outcome of a single storage health check invocation.

    Attributes:
        status:       HEALTHY, DEGRADED, or UNHEALTHY.
        backend:      Name of the storage backend that was checked.
        latency_ms:   Round-trip latency in milliseconds. ``None`` when the
            backend was unreachable.
        message:      Human-readable description of the health state.
        checked_at:   UTC timestamp when the health check was performed.
    """

    status: HealthStatus
    backend: StorageBackend | str
    latency_ms: float | None
    message: str
    checked_at: datetime

    def __post_init__(self) -> None:
        if self.checked_at.tzinfo is None:
            raise ValueError("HealthCheckResult.checked_at must be timezone-aware")
        if self.latency_ms is not None and self.latency_ms < 0:
            raise ValueError(f"HealthCheckResult.latency_ms must be >= 0, got {self.latency_ms}")

    @property
    def is_healthy(self) -> bool:
        """Return ``True`` when status is ``HEALTHY`` or ``DEGRADED``.

        Returns:
            ``False`` only for ``UNHEALTHY`` — the backend cannot serve requests.
        """
        return self.status != HealthStatus.UNHEALTHY

    @property
    def is_operational(self) -> bool:
        """Return ``True`` when status is exactly ``HEALTHY``.

        Returns:
            ``False`` for both ``DEGRADED`` and ``UNHEALTHY``.
        """
        return self.status == HealthStatus.HEALTHY
