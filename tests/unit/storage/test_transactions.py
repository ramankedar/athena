"""Unit tests for transaction and Unit of Work Protocol definitions."""

from __future__ import annotations

from types import TracebackType

import pytest

from athena.storage.transactions import (
    TransactionIsolationLevel,
    TransactionManagerProtocol,
    TransactionProtocol,
    UnitOfWorkProtocol,
)

# ── Minimal mock implementations ──────────────────────────────────────────────


class _MockTransaction:
    _active: bool = False

    async def begin(
        self,
        isolation_level: TransactionIsolationLevel = TransactionIsolationLevel.READ_COMMITTED,
    ) -> None:
        self._active = True

    async def commit(self) -> None:
        self._active = False

    async def rollback(self) -> None:
        self._active = False

    @property
    def is_active(self) -> bool:
        return self._active


class _MockInstrumentRepo:
    async def get_instrument(self, symbol: object) -> object:
        raise NotImplementedError

    async def get_instrument_or_none(self, symbol: object) -> object | None:
        return None

    async def find_instruments(self, **kwargs: object) -> object:
        raise NotImplementedError

    async def upsert_instrument(self, instrument: object) -> str:
        return "key"

    async def upsert_many(self, instruments: object) -> int:
        return 0

    async def count_instruments(self, **kwargs: object) -> int:
        return 0


class _MockTickRepo:
    async def get_tick(self, symbol: object, ts: object) -> object:
        raise NotImplementedError

    async def get_latest_tick(self, symbol: object) -> object | None:
        return None

    async def find_ticks(self, *args: object, **kwargs: object) -> object:
        raise NotImplementedError

    async def add_tick(self, tick: object) -> str:
        return "key"

    async def add_ticks(self, ticks: object) -> int:
        return 0

    async def delete_ticks_before(self, symbol: object, cutoff: object) -> int:
        return 0

    async def count_ticks(self, *args: object, **kwargs: object) -> int:
        return 0


class _MockOHLCVRepo:
    async def get_bar(self, *args: object) -> object:
        raise NotImplementedError

    async def find_bars(self, *args: object, **kwargs: object) -> object:
        raise NotImplementedError

    async def get_latest_bar(self, *args: object) -> object | None:
        return None

    async def add_bar(self, bar: object) -> str:
        return "key"

    async def add_bars(self, bars: object) -> int:
        return 0

    async def count_bars(self, *args: object, **kwargs: object) -> int:
        return 0

    async def delete_bars_before(self, *args: object) -> int:
        return 0


class _MockUoW:
    committed: bool = False
    rolled_back: bool = False

    @property
    def instruments(self) -> _MockInstrumentRepo:
        return _MockInstrumentRepo()

    @property
    def ticks(self) -> _MockTickRepo:
        return _MockTickRepo()

    @property
    def ohlcv(self) -> _MockOHLCVRepo:
        return _MockOHLCVRepo()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def __aenter__(self) -> _MockUoW:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        if exc_type is not None:
            await self.rollback()
        return False


class _MockTransactionManager:
    def unit_of_work(
        self,
        isolation_level: TransactionIsolationLevel = TransactionIsolationLevel.READ_COMMITTED,
    ) -> _MockUoW:
        return _MockUoW()


class _EmptyClass:
    pass


# ── Tests ──────────────────────────────────────────────────────────────────────


class TestTransactionIsolationLevel:
    def test_values(self) -> None:
        assert TransactionIsolationLevel.READ_COMMITTED == "read_committed"
        assert TransactionIsolationLevel.SERIALIZABLE == "serializable"
        assert TransactionIsolationLevel.REPEATABLE_READ == "repeatable_read"
        assert TransactionIsolationLevel.READ_UNCOMMITTED == "read_uncommitted"

    def test_is_str(self) -> None:
        assert isinstance(TransactionIsolationLevel.READ_COMMITTED, str)

    def test_all_members_present(self) -> None:
        levels = {lvl.value for lvl in TransactionIsolationLevel}
        assert "read_committed" in levels
        assert "serializable" in levels
        assert len(levels) == 4


class TestTransactionProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockTransaction(), TransactionProtocol)

    def test_empty_class_does_not_satisfy(self) -> None:
        assert not isinstance(_EmptyClass(), TransactionProtocol)


class TestUnitOfWorkProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockUoW(), UnitOfWorkProtocol)

    def test_empty_class_does_not_satisfy(self) -> None:
        assert not isinstance(_EmptyClass(), UnitOfWorkProtocol)

    async def test_context_manager_commits(self) -> None:
        uow = _MockUoW()
        async with uow:
            await uow.commit()
        assert uow.committed is True

    async def test_context_manager_rolls_back_on_exception(self) -> None:
        uow = _MockUoW()
        with pytest.raises(ValueError, match="test"):
            async with uow:
                raise ValueError("test")
        assert uow.rolled_back is True


class TestTransactionManagerProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockTransactionManager(), TransactionManagerProtocol)

    def test_produces_uow(self) -> None:
        manager = _MockTransactionManager()
        uow = manager.unit_of_work()
        assert isinstance(uow, UnitOfWorkProtocol)

    def test_produces_uow_with_isolation_level(self) -> None:
        manager = _MockTransactionManager()
        uow = manager.unit_of_work(TransactionIsolationLevel.SERIALIZABLE)
        assert isinstance(uow, UnitOfWorkProtocol)
