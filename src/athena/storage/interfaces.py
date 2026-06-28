"""Generic storage interface Protocols.

These Protocols define the structural contract for any storage adapter
without coupling to a specific backend technology. Three tiers:

1. ``ReadRepositoryProtocol[T]``   — read-only access (``get``, ``list``, ``count``).
2. ``WriteRepositoryProtocol[T]``  — write-only access (``add``, ``update``, ``remove``).
3. ``RepositoryProtocol[T]``       — full read/write access (composes both).

An additional ``TimeSeriesRepositoryProtocol[T]`` extends the full repository
with time-range queries, suited for tick and OHLCV data.

Runtime-checkable note:
    ``isinstance(obj, ReadRepositoryProtocol)`` checks that ``obj`` has all
    required attributes at runtime, but does NOT check type parameters —
    ``isinstance(obj, ReadRepositoryProtocol[Tick])`` is not valid Python.
    Static analysis (mypy) enforces the type parameter; ``isinstance`` only
    checks structural compatibility.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TypeVar, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from athena.storage.models import (
        OptimisticLockSpec,
        Page,
        QuerySpec,
        StorageKey,
        StorageRecord,
    )

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)


@runtime_checkable
class ReadRepositoryProtocol(Protocol[T_co]):
    """Read-only access to a collection of domain entities.

    Implementations must not alter storage state. All methods are async
    to prevent blocking I/O in async contexts — even in-memory
    implementations should declare them ``async``.

    Type parameter:
        T_co: The entity type this repository reads. Covariant because
            ``ReadRepositoryProtocol[OHLCVBar]`` is a subtype of
            ``ReadRepositoryProtocol[object]``.
    """

    async def get(self, key: StorageKey) -> T_co:
        """Retrieve the entity for the given key.

        Args:
            key: The storage key to look up.

        Returns:
            The entity associated with ``key``.

        Raises:
            RecordNotFoundError: If no entity exists for ``key``.
            StorageConnectionError: If the backend is unreachable.
        """
        ...

    async def get_or_none(self, key: StorageKey) -> T_co | None:
        """Retrieve the entity for the given key, or ``None`` if not found.

        Unlike ``get()``, this method does not raise ``RecordNotFoundError``
        for a missing key — missing is a valid and expected outcome.

        Args:
            key: The storage key to look up.

        Returns:
            The entity, or ``None`` if no record exists for ``key``.

        Raises:
            StorageConnectionError: If the backend is unreachable.
        """
        ...

    async def exists(self, key: StorageKey) -> bool:
        """Return ``True`` if a record exists for the given key.

        Args:
            key: The storage key to check.

        Returns:
            ``True`` when a record exists; ``False`` otherwise.
        """
        ...

    async def count(self, spec: QuerySpec | None = None) -> int:
        """Return the total number of entities matching the given spec.

        Args:
            spec: Optional query filters. When ``None``, counts all records.

        Returns:
            Total matching record count. Always >= 0.
        """
        ...

    async def list_all(self, spec: QuerySpec | None = None) -> Page[T_co]:
        """Return a paginated list of entities matching the given spec.

        Args:
            spec: Optional query specification including filters, sort order,
                and pagination. When ``None``, returns the first page of all
                records in implementation-defined order.

        Returns:
            A ``Page`` containing the matching entities and pagination metadata.

        Raises:
            QueryError: If the spec contains unsupported filters or operators.
        """
        ...

    async def get_with_metadata(self, key: StorageKey) -> StorageRecord[T_co]:
        """Retrieve the entity and its storage metadata.

        Used when the caller needs provenance or version information for
        optimistic locking.

        Args:
            key: The storage key to look up.

        Returns:
            A ``StorageRecord`` containing the entity and its metadata.

        Raises:
            RecordNotFoundError: If no entity exists for ``key``.
        """
        ...


@runtime_checkable
class WriteRepositoryProtocol(Protocol[T]):
    """Write access to a collection of domain entities.

    All mutation operations are async. Implementations that enforce
    constraints (uniqueness, foreign key references) raise the appropriate
    storage exception rather than silently ignoring violations.

    Type parameter:
        T: The entity type this repository writes. Invariant because the
            repository both accepts ``T`` (writes) and returns keys for ``T``.
    """

    async def add(self, entity: T) -> StorageKey:
        """Persist a new entity and return its assigned storage key.

        Args:
            entity: The domain entity to persist.

        Returns:
            The ``StorageKey`` assigned to the new record.

        Raises:
            DuplicateKeyError: If a record with the same key already exists.
            SerializationError: If the entity cannot be serialised.
        """
        ...

    async def add_many(self, entities: Sequence[T]) -> tuple[StorageKey, ...]:
        """Persist multiple entities in a single operation.

        Bulk writes should be significantly faster than iterating ``add()``
        because they amortise connection and transaction overhead.

        Args:
            entities: Sequence of entities to persist. Order is preserved in
                the returned keys.

        Returns:
            A tuple of ``StorageKey`` values, one per entity, in the same order.

        Raises:
            DuplicateKeyError: If any entity collides with an existing key.
        """
        ...

    async def update(
        self,
        key: StorageKey,
        entity: T,
        lock: OptimisticLockSpec | None = None,
    ) -> None:
        """Replace an existing entity in storage.

        Args:
            key:    The key of the record to replace.
            entity: The new entity value.
            lock:   When provided, the implementation raises
                ``VersionConflictError`` if the record's current version
                does not match ``lock.expected_version``.

        Raises:
            RecordNotFoundError: If no record exists for ``key``.
            VersionConflictError: If ``lock`` is provided and the version
                does not match.
        """
        ...

    async def remove(self, key: StorageKey) -> bool:
        """Delete the record for the given key.

        Args:
            key: The key of the record to delete.

        Returns:
            ``True`` if a record was deleted; ``False`` if the key was not found.
        """
        ...

    async def remove_many(self, keys: Sequence[StorageKey]) -> int:
        """Delete multiple records in a single operation.

        Args:
            keys: Keys of the records to delete.

        Returns:
            The number of records actually deleted (may be less than
            ``len(keys)`` if some keys did not exist).
        """
        ...


@runtime_checkable
class RepositoryProtocol(
    ReadRepositoryProtocol[T],
    WriteRepositoryProtocol[T],
    Protocol[T],
):
    """Full read/write repository combining all CRUD operations.

    Most concrete storage adapters implement this Protocol. Split into
    ``ReadRepositoryProtocol`` and ``WriteRepositoryProtocol`` for callers
    that only need one direction (e.g. read-only research processes, or
    append-only audit log writers).
    """


@runtime_checkable
class TimeSeriesRepositoryProtocol(RepositoryProtocol[T], Protocol[T]):
    """Repository for entities with a primary timestamp dimension.

    Extends ``RepositoryProtocol`` with time-range queries optimised for
    time-series backends (TimescaleDB hypertables, Parquet partitioned by
    date, DuckDB temporal scans).

    Type parameter:
        T: An entity type that has a timestamp field (e.g. ``Tick``, ``OHLCV``).
    """

    async def find_in_range(
        self,
        from_utc: datetime,
        to_utc: datetime,
        spec: QuerySpec | None = None,
    ) -> Page[T]:
        """Return entities whose timestamp falls within ``[from_utc, to_utc)``.

        Args:
            from_utc: Inclusive lower bound (timezone-aware).
            to_utc:   Exclusive upper bound (timezone-aware).
            spec:     Optional additional filters and pagination.

        Returns:
            A paginated page of matching entities in ascending timestamp order.

        Raises:
            QueryError: If ``from_utc >= to_utc`` or datetimes are naive.
        """
        ...

    async def find_latest(self, spec: QuerySpec | None = None) -> T | None:
        """Return the most recent entity by timestamp.

        Args:
            spec: Optional filters. When ``None``, returns the absolute
                most recent entity across all symbols/instruments.

        Returns:
            The entity with the highest timestamp, or ``None`` if empty.
        """
        ...

    async def delete_before(self, cutoff_utc: datetime) -> int:
        """Delete all entities with a timestamp before the cutoff.

        Used for time-to-live purging of old tick data or rolling-window
        retention policies.

        Args:
            cutoff_utc: Exclusive upper bound for deletion (timezone-aware).

        Returns:
            The number of records deleted.

        Raises:
            QueryError: If ``cutoff_utc`` is naive.
        """
        ...
