"""Athena Storage Foundation — Sprint 3.

Defines how Athena interacts with persistence without committing to a specific
storage backend. This package contains only interfaces and domain models —
no concrete database connections, SQL, or backend-specific code.

Supported future backends (defined by type only here):
    TimescaleDB — time-series-optimised PostgreSQL (primary backend)
    DuckDB      — embedded analytical database (research and backtesting)
    S3          — object storage for archived Parquet files
    Parquet     — local columnar files for offline research
    In-Memory   — ephemeral store for testing and caching

Public API::

    from athena.storage import (
        # Models
        StorageKey, SchemaVersion, Pagination, Page, SortDirection,
        SortField, FilterOperator, FilterExpression, QuerySpec,
        TimeRangeFilter, OptimisticLockSpec, StorageMetadata, StorageRecord,
        HealthStatus, HealthCheckResult, SerializationFormat, StorageBackend,
        CompatibilityStrategy,

        # Generic interfaces
        ReadRepositoryProtocol, WriteRepositoryProtocol, RepositoryProtocol,
        TimeSeriesRepositoryProtocol,

        # Domain-specific repositories
        InstrumentRepositoryProtocol, TickRepositoryProtocol,
        OHLCVRepositoryProtocol,

        # Unit of Work
        TransactionIsolationLevel, TransactionProtocol,
        UnitOfWorkProtocol, TransactionManagerProtocol,

        # Health
        StorageHealthProtocol, StorageHealthRegistryProtocol,

        # Serialisation
        SerializerProtocol, DeserializerProtocol, CodecProtocol,
        SchemaProtocol,

        # Versioning
        MigrationProtocol, VersionRegistryProtocol, SchemaRegistryProtocol,

        # Exceptions
        StorageError, RecordNotFoundError, DuplicateKeyError,
        StorageConnectionError, TransactionError, SerializationError,
        VersionConflictError, StorageHealthError, QueryError,
        SchemaVersionError,
    )
"""

from athena.storage.exceptions import (
    DuplicateKeyError,
    QueryError,
    RecordNotFoundError,
    SchemaVersionError,
    SerializationError,
    StorageConnectionError,
    StorageError,
    StorageHealthError,
    TransactionError,
    VersionConflictError,
)
from athena.storage.health import StorageHealthProtocol, StorageHealthRegistryProtocol
from athena.storage.interfaces import (
    ReadRepositoryProtocol,
    RepositoryProtocol,
    TimeSeriesRepositoryProtocol,
    WriteRepositoryProtocol,
)
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
    StorageKey,
    StorageMetadata,
    StorageRecord,
    TimeRangeFilter,
)
from athena.storage.repositories import (
    InstrumentRepositoryProtocol,
    OHLCVRepositoryProtocol,
    TickRepositoryProtocol,
)
from athena.storage.serialization import (
    CodecProtocol,
    DeserializerProtocol,
    SchemaProtocol,
    SerializerProtocol,
)
from athena.storage.transactions import (
    TransactionIsolationLevel,
    TransactionManagerProtocol,
    TransactionProtocol,
    UnitOfWorkProtocol,
)
from athena.storage.versioning import (
    MigrationProtocol,
    SchemaRegistryProtocol,
    VersionRegistryProtocol,
)

__all__ = [
    "CodecProtocol",
    "CompatibilityStrategy",
    "DeserializerProtocol",
    "DuplicateKeyError",
    "FilterExpression",
    "FilterOperator",
    "HealthCheckResult",
    "HealthStatus",
    "InstrumentRepositoryProtocol",
    "MigrationProtocol",
    "OHLCVRepositoryProtocol",
    "OptimisticLockSpec",
    "Page",
    "Pagination",
    "QueryError",
    "QuerySpec",
    "ReadRepositoryProtocol",
    "RecordNotFoundError",
    "RepositoryProtocol",
    "SchemaProtocol",
    "SchemaRegistryProtocol",
    "SchemaVersion",
    "SchemaVersionError",
    "SerializationError",
    "SerializationFormat",
    "SerializerProtocol",
    "SortDirection",
    "SortField",
    "StorageBackend",
    "StorageConnectionError",
    "StorageError",
    "StorageHealthError",
    "StorageHealthProtocol",
    "StorageHealthRegistryProtocol",
    "StorageKey",
    "StorageMetadata",
    "StorageRecord",
    "TickRepositoryProtocol",
    "TimeRangeFilter",
    "TimeSeriesRepositoryProtocol",
    "TransactionError",
    "TransactionIsolationLevel",
    "TransactionManagerProtocol",
    "TransactionProtocol",
    "UnitOfWorkProtocol",
    "VersionConflictError",
    "VersionRegistryProtocol",
    "WriteRepositoryProtocol",
]
