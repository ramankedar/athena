"""Unit tests for generic storage interface Protocols.

Tests verify that:
1. Protocol isinstance checks work (runtime_checkable).
2. Mock implementations satisfy the protocols structurally.
3. Objects missing required methods do NOT satisfy the protocols.
"""

from __future__ import annotations

from datetime import datetime

from athena.storage.interfaces import (
    ReadRepositoryProtocol,
    RepositoryProtocol,
    TimeSeriesRepositoryProtocol,
    WriteRepositoryProtocol,
)
from athena.storage.models import (
    OptimisticLockSpec,
    Page,
    QuerySpec,
    StorageKey,
)

# ── Minimal mock implementations ──────────────────────────────────────────────


class _MockReadRepo:
    """Minimal implementation satisfying ReadRepositoryProtocol."""

    async def get(self, key: StorageKey) -> object:
        raise NotImplementedError

    async def get_or_none(self, key: StorageKey) -> object | None:
        return None

    async def exists(self, key: StorageKey) -> bool:
        return False

    async def count(self, spec: QuerySpec | None = None) -> int:
        return 0

    async def list_all(self, spec: QuerySpec | None = None) -> Page[object]:
        return Page(items=(), total=0, offset=0, limit=10, has_next=False, has_previous=False)

    async def get_with_metadata(self, key: StorageKey) -> object:
        raise NotImplementedError


class _MockWriteRepo:
    """Minimal implementation satisfying WriteRepositoryProtocol."""

    async def add(self, entity: object) -> StorageKey:
        return "new-key"

    async def add_many(self, entities: object) -> tuple[StorageKey, ...]:
        return ()

    async def update(
        self,
        key: StorageKey,
        entity: object,
        lock: OptimisticLockSpec | None = None,
    ) -> None:
        pass

    async def remove(self, key: StorageKey) -> bool:
        return False

    async def remove_many(self, keys: object) -> int:
        return 0


class _MockRepository(_MockReadRepo, _MockWriteRepo):
    """Implementation satisfying RepositoryProtocol."""


class _MockTimeSeries(_MockRepository):
    """Implementation satisfying TimeSeriesRepositoryProtocol."""

    async def find_in_range(
        self,
        from_utc: datetime,
        to_utc: datetime,
        spec: QuerySpec | None = None,
    ) -> Page[object]:
        return Page((), 0, 0, 10, False, False)

    async def find_latest(self, spec: QuerySpec | None = None) -> object | None:
        return None

    async def delete_before(self, cutoff_utc: datetime) -> int:
        return 0


class _EmptyClass:
    """Has no storage methods — should satisfy NO protocol."""


# ── Tests ──────────────────────────────────────────────────────────────────────


class TestReadRepositoryProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockReadRepo(), ReadRepositoryProtocol)

    def test_mock_write_does_not_satisfy_read(self) -> None:
        assert not isinstance(_MockWriteRepo(), ReadRepositoryProtocol)

    def test_empty_class_does_not_satisfy(self) -> None:
        assert not isinstance(_EmptyClass(), ReadRepositoryProtocol)

    def test_full_repo_satisfies_read(self) -> None:
        assert isinstance(_MockRepository(), ReadRepositoryProtocol)


class TestWriteRepositoryProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockWriteRepo(), WriteRepositoryProtocol)

    def test_read_only_does_not_satisfy_write(self) -> None:
        assert not isinstance(_MockReadRepo(), WriteRepositoryProtocol)

    def test_full_repo_satisfies_write(self) -> None:
        assert isinstance(_MockRepository(), WriteRepositoryProtocol)


class TestRepositoryProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockRepository(), RepositoryProtocol)

    def test_read_only_does_not_satisfy(self) -> None:
        assert not isinstance(_MockReadRepo(), RepositoryProtocol)

    def test_write_only_does_not_satisfy(self) -> None:
        assert not isinstance(_MockWriteRepo(), RepositoryProtocol)


class TestTimeSeriesRepositoryProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockTimeSeries(), TimeSeriesRepositoryProtocol)

    def test_plain_repo_does_not_satisfy(self) -> None:
        assert not isinstance(_MockRepository(), TimeSeriesRepositoryProtocol)
