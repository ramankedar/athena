"""Storage-domain exception hierarchy.

All storage exceptions inherit from ``StorageError``, which itself inherits
from ``AthenaError``. This allows callers to catch all storage failures with
a single clause while discriminating on subtype for specific handling.

Hierarchy::

    AthenaError
    └── StorageError
        ├── RecordNotFoundError      — get() found nothing for the key
        ├── DuplicateKeyError        — add() collides with an existing record
        ├── StorageConnectionError   — cannot reach the storage backend
        ├── TransactionError         — transaction commit/rollback failed
        ├── SerializationError       — encode or decode failed
        ├── VersionConflictError     — optimistic-lock version mismatch
        ├── StorageHealthError       — health check detected a problem
        ├── QueryError               — invalid or unsupported query specification
        └── SchemaVersionError       — schema version mismatch or missing migration
"""

from __future__ import annotations

from athena.platform.exceptions import AthenaError


class StorageError(AthenaError):
    """Root exception for all storage-domain errors.

    Args:
        message: Human-readable description of the failure.
        error_code: Optional machine-readable code (prefix: ``STR``).
        **context: Diagnostic key-value pairs (backend, table, key, etc.).
    """


class RecordNotFoundError(StorageError):
    """Raised when a ``get()`` call cannot locate a record for the given key.

    Distinct from returning ``None`` — this exception signals that the key
    is structurally valid but no matching record exists in storage.

    Args:
        key: The storage key that was not found.
        entity_type: Name of the entity type being queried (e.g. ``"Tick"``).
        **context: Additional diagnostic context.
    """

    def __init__(
        self,
        key: str,
        entity_type: str = "record",
        **context: object,
    ) -> None:
        super().__init__(
            f"{entity_type} not found for key: {key!r}",
            error_code="STR_001",
            key=key,
            entity_type=entity_type,
            **context,
        )
        self.key = key
        self.entity_type = entity_type


class DuplicateKeyError(StorageError):
    """Raised when an ``add()`` call collides with an existing record.

    Implementations that enforce uniqueness constraints raise this instead of
    silently overwriting the existing record.

    Args:
        key: The storage key that already exists.
        entity_type: Name of the entity type (e.g. ``"Instrument"``).
        **context: Additional diagnostic context.
    """

    def __init__(
        self,
        key: str,
        entity_type: str = "record",
        **context: object,
    ) -> None:
        super().__init__(
            f"A {entity_type} with key {key!r} already exists",
            error_code="STR_002",
            key=key,
            entity_type=entity_type,
            **context,
        )
        self.key = key
        self.entity_type = entity_type


class StorageConnectionError(StorageError):
    """Raised when the storage backend is unreachable or the connection fails.

    This is a transient error in most cases — callers should apply retry
    logic with exponential back-off before escalating to a circuit breaker.

    Args:
        backend: Name of the storage backend (e.g. ``"timescaledb"``).
        **context: Additional diagnostic context (host, port, retry count).
    """

    def __init__(self, backend: str, **context: object) -> None:
        super().__init__(
            f"Cannot connect to storage backend: {backend!r}",
            error_code="STR_003",
            backend=backend,
            **context,
        )
        self.backend = backend


class TransactionError(StorageError):
    """Raised when a transaction cannot be committed or rolled back successfully.

    A ``TransactionError`` during commit means the data may or may not have
    been persisted. Callers must treat the Unit of Work as poisoned and
    discard it — do not attempt further operations on the same UoW.

    Args:
        operation: The transaction operation that failed (e.g. ``"commit"``).
        **context: Additional diagnostic context.
    """

    def __init__(self, operation: str, **context: object) -> None:
        super().__init__(
            f"Transaction {operation!r} failed",
            error_code="STR_004",
            operation=operation,
            **context,
        )
        self.operation = operation


class SerializationError(StorageError):
    """Raised when serialisation or deserialisation of a domain object fails.

    Args:
        direction: Either ``"serialize"`` or ``"deserialize"``.
        entity_type: The type being processed (e.g. ``"Tick"``).
        **context: Additional diagnostic context (format, schema version).
    """

    def __init__(
        self,
        direction: str,
        entity_type: str,
        **context: object,
    ) -> None:
        super().__init__(
            f"Failed to {direction} {entity_type}",
            error_code="STR_005",
            direction=direction,
            entity_type=entity_type,
            **context,
        )
        self.direction = direction
        self.entity_type = entity_type


class VersionConflictError(StorageError):
    """Raised when an optimistic-lock write fails due to a version mismatch.

    The caller supplied an ``OptimisticLockSpec`` expecting a specific version
    number, but the record in storage has a different (typically higher) version,
    indicating a concurrent write occurred since the record was last read.

    Callers should re-read the record and retry the write with the new version.

    Args:
        key: The key of the conflicting record.
        expected_version: The version the caller expected.
        actual_version: The version found in storage.
        **context: Additional diagnostic context.
    """

    def __init__(
        self,
        key: str,
        expected_version: int,
        actual_version: int,
        **context: object,
    ) -> None:
        super().__init__(
            f"Version conflict for key {key!r}: "
            f"expected version {expected_version}, found {actual_version}",
            error_code="STR_006",
            key=key,
            expected_version=expected_version,
            actual_version=actual_version,
            **context,
        )
        self.key = key
        self.expected_version = expected_version
        self.actual_version = actual_version


class StorageHealthError(StorageError):
    """Raised when a storage health check detects a critical problem.

    This is raised only for ``UNHEALTHY`` status — ``DEGRADED`` is reported
    through ``HealthCheckResult`` without raising.

    Args:
        backend: Name of the storage backend.
        reason: Human-readable explanation of the health failure.
        **context: Additional diagnostic context.
    """

    def __init__(self, backend: str, reason: str, **context: object) -> None:
        super().__init__(
            f"Storage backend {backend!r} is unhealthy: {reason}",
            error_code="STR_007",
            backend=backend,
            reason=reason,
            **context,
        )
        self.backend = backend
        self.reason = reason


class QueryError(StorageError):
    """Raised when a ``QuerySpec`` is invalid or uses unsupported features.

    Different backends support different filter operators and sort strategies.
    Implementations raise this when a requested feature is not supported.

    Args:
        reason: Description of why the query is invalid.
        **context: Additional diagnostic context (operator, field, backend).
    """

    def __init__(self, reason: str, **context: object) -> None:
        super().__init__(
            f"Invalid query: {reason}",
            error_code="STR_008",
            reason=reason,
            **context,
        )
        self.reason = reason


class SchemaVersionError(StorageError):
    """Raised when a schema version mismatch prevents reading or writing data.

    This occurs when:
    - A stored record's schema version is newer than what the application knows.
    - A required migration path between two schema versions does not exist.

    Args:
        schema_name: The name of the schema (e.g. ``"Tick"``).
        **context: Additional diagnostic context (expected, actual version).
    """

    def __init__(self, schema_name: str, **context: object) -> None:
        super().__init__(
            f"Schema version error for {schema_name!r}",
            error_code="STR_009",
            schema_name=schema_name,
            **context,
        )
        self.schema_name = schema_name
