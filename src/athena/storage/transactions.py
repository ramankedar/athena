"""Unit of Work and transaction abstractions.

The Unit of Work (UoW) pattern coordinates multiple repository operations
in a single atomic transaction without coupling repositories to each other
or to a specific connection management strategy.

Usage pattern::

    async with uow:
        await uow.instruments.upsert_instrument(instrument)
        await uow.ticks.add_tick(tick)
        await uow.commit()
    # On exception: uow.__aexit__ calls rollback automatically

Why Unit of Work over direct transactions?
    If repositories each manage their own connections, writing a tick AND
    updating the instrument master in the same atomic block requires passing
    the connection across two independent layers. UoW solves this by making
    the connection implicit — all repositories within a UoW share the same
    underlying session/connection, and committing/rolling back the UoW
    affects all of them atomically.

Transaction isolation levels:
    Different backends support different isolation levels. The
    ``TransactionIsolationLevel`` enum expresses the desired level; adapters
    map it to their native equivalent (e.g. PostgreSQL ``SET TRANSACTION
    ISOLATION LEVEL ...``).
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from types import TracebackType

    from athena.storage.repositories import (
        InstrumentRepositoryProtocol,
        OHLCVRepositoryProtocol,
        TickRepositoryProtocol,
    )


class TransactionIsolationLevel(StrEnum):
    """Standard ANSI SQL transaction isolation levels.

    Attributes:
        READ_UNCOMMITTED: Reads may see uncommitted changes from other
            transactions. Lowest isolation; fastest performance.
        READ_COMMITTED:   Reads only see committed data. Prevents dirty reads.
            Default for most PostgreSQL operations.
        REPEATABLE_READ:  All reads within the transaction see a consistent
            snapshot. Prevents non-repeatable reads.
        SERIALIZABLE:     Full isolation. Transactions appear to execute
            sequentially. Highest correctness guarantee; highest overhead.
    """

    READ_UNCOMMITTED = "read_uncommitted"
    READ_COMMITTED = "read_committed"
    REPEATABLE_READ = "repeatable_read"
    SERIALIZABLE = "serializable"


@runtime_checkable
class TransactionProtocol(Protocol):
    """Low-level transaction lifecycle for a single storage connection.

    Most application code should use ``UnitOfWorkProtocol`` instead of
    this lower-level protocol. ``TransactionProtocol`` is exposed for
    infrastructure adapters that need precise control over commit/rollback
    timing (e.g. bulk-loading jobs, schema migrations).
    """

    async def begin(
        self,
        isolation_level: TransactionIsolationLevel = TransactionIsolationLevel.READ_COMMITTED,
    ) -> None:
        """Open a new transaction on the underlying connection.

        Args:
            isolation_level: The isolation level to request. Defaults to
                ``READ_COMMITTED``, which is appropriate for most data
                ingestion and query operations.

        Raises:
            TransactionError: If a transaction is already open on this
                connection or the backend does not support the requested level.
        """
        ...

    async def commit(self) -> None:
        """Persist all writes made since ``begin()`` and close the transaction.

        Raises:
            TransactionError: If the commit fails. The transaction state after
                a commit failure is undefined — discard the connection.
        """
        ...

    async def rollback(self) -> None:
        """Undo all writes made since ``begin()`` and close the transaction.

        Safe to call from a ``finally`` block even if no transaction is open —
        implementations must be idempotent when called in a non-transactional
        state.
        """
        ...

    @property
    def is_active(self) -> bool:
        """Return ``True`` when a transaction is currently open.

        Returns:
            ``True`` between ``begin()`` and ``commit()``/``rollback()``.
        """
        ...


@runtime_checkable
class UnitOfWorkProtocol(Protocol):
    """Coordinated multi-repository atomic write context.

    All repositories accessed through a ``UnitOfWorkProtocol`` share the
    same underlying connection or session. Committing the UoW persists all
    writes atomically; any exception before commit triggers an automatic
    rollback in ``__aexit__``.

    Usage::

        async with uow:
            key = await uow.ticks.add_tick(tick)
            await uow.ohlcv.add_bar(bar)
            await uow.commit()
        # Automatic rollback if commit() is not reached

    Properties exposed here correspond to the Data Engine's storage needs.
    Additional repositories (order ledger, audit log) will be added to this
    protocol when their respective engine sprints are implemented.
    """

    @property
    def instruments(self) -> InstrumentRepositoryProtocol:
        """The instrument master repository within this Unit of Work.

        Returns:
            An ``InstrumentRepositoryProtocol`` sharing this UoW's session.
        """
        ...

    @property
    def ticks(self) -> TickRepositoryProtocol:
        """The tick repository within this Unit of Work.

        Returns:
            A ``TickRepositoryProtocol`` sharing this UoW's session.
        """
        ...

    @property
    def ohlcv(self) -> OHLCVRepositoryProtocol:
        """The OHLCV bar repository within this Unit of Work.

        Returns:
            An ``OHLCVRepositoryProtocol`` sharing this UoW's session.
        """
        ...

    async def commit(self) -> None:
        """Persist all repository writes and close the UoW.

        Raises:
            TransactionError: If the commit fails. The UoW is poisoned after
                a commit failure — do not attempt further operations.
        """
        ...

    async def rollback(self) -> None:
        """Undo all repository writes and close the UoW.

        Safe to call even if ``commit()`` was already successful (no-op).
        Always called by ``__aexit__`` when an exception propagates.
        """
        ...

    async def __aenter__(self) -> UnitOfWorkProtocol:
        """Open the Unit of Work (begin the underlying transaction).

        Returns:
            ``self``, allowing use as ``async with uow as uow:``.
        """
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        """Close the Unit of Work. Rolls back if commit() was not called.

        Args:
            exc_type: Exception type, or ``None`` if no exception occurred.
            exc_val:  Exception instance, or ``None``.
            exc_tb:   Traceback, or ``None``.

        Returns:
            ``False`` — exceptions are always propagated to the caller.
        """
        ...


@runtime_checkable
class TransactionManagerProtocol(Protocol):
    """Factory that produces ``UnitOfWorkProtocol`` instances.

    Application services receive a ``TransactionManagerProtocol`` rather
    than a concrete UoW, which allows the implementation (PostgreSQL, DuckDB,
    in-memory) to be swapped via dependency injection.

    Usage::

        async def ingest_data(
            manager: TransactionManagerProtocol,
            ticks: list[Tick],
        ) -> None:
            async with manager.unit_of_work() as uow:
                await uow.ticks.add_ticks(ticks)
                await uow.commit()
    """

    def unit_of_work(
        self,
        isolation_level: TransactionIsolationLevel = TransactionIsolationLevel.READ_COMMITTED,
    ) -> UnitOfWorkProtocol:
        """Create a new, independent Unit of Work.

        Args:
            isolation_level: The transaction isolation level to request.
                Defaults to ``READ_COMMITTED``.

        Returns:
            A new ``UnitOfWorkProtocol`` instance. The underlying transaction
            is not started until ``__aenter__`` is called.
        """
        ...
