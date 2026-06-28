"""Unit tests for schema versioning Protocol definitions."""

from __future__ import annotations

import pytest

from athena.storage.models import CompatibilityStrategy, SchemaVersion
from athena.storage.versioning import (
    MigrationProtocol,
    SchemaRegistryProtocol,
    VersionRegistryProtocol,
)

V1 = SchemaVersion(1, 0, 0)
V2 = SchemaVersion(2, 0, 0)
V1_1 = SchemaVersion(1, 1, 0)


# ── Minimal mock implementations ──────────────────────────────────────────────


class _MockMigration:
    def __init__(
        self,
        schema: str = "Tick",
        from_ver: SchemaVersion = V1,
        to_ver: SchemaVersion = V2,
        reversible: bool = True,
    ) -> None:
        self._schema = schema
        self._from = from_ver
        self._to = to_ver
        self._reversible = reversible

    @property
    def from_version(self) -> SchemaVersion:
        return self._from

    @property
    def to_version(self) -> SchemaVersion:
        return self._to

    @property
    def schema_name(self) -> str:
        return self._schema

    @property
    def compatibility(self) -> CompatibilityStrategy:
        return CompatibilityStrategy.BACKWARD

    async def up(self, data: bytes) -> bytes:
        return data + b"_v2"

    async def down(self, data: bytes) -> bytes:
        if not self._reversible:
            raise NotImplementedError
        return data.removesuffix(b"_v2")

    def is_reversible(self) -> bool:
        return self._reversible


class _MockVersionRegistry:
    def __init__(self) -> None:
        self._data: dict[str, list[SchemaVersion]] = {}

    def current_version(self, schema_name: str) -> SchemaVersion:
        if schema_name not in self._data:
            raise KeyError(schema_name)
        return max(self._data[schema_name])

    def register(self, schema_name: str, version: SchemaVersion) -> None:
        self._data.setdefault(schema_name, []).append(version)

    def history(self, schema_name: str) -> tuple[SchemaVersion, ...]:
        return tuple(sorted(self._data.get(schema_name, [])))

    def is_registered(self, schema_name: str) -> bool:
        return schema_name in self._data


class _MockSchemaRegistry:
    def __init__(self) -> None:
        self._migrations: list[_MockMigration] = []

    def register_migration(self, migration: _MockMigration) -> None:
        self._migrations.append(migration)

    def get_migration_path(
        self,
        schema_name: str,
        from_version: SchemaVersion,
        to_version: SchemaVersion,
    ) -> tuple[_MockMigration, ...]:
        path = [
            m
            for m in self._migrations
            if m.schema_name == schema_name
            and m.from_version == from_version
            and m.to_version == to_version
        ]
        if not path:
            from athena.storage.exceptions import SchemaVersionError

            raise SchemaVersionError(schema_name, from_version=str(from_version))
        return tuple(path)

    async def migrate(
        self,
        schema_name: str,
        data: bytes,
        from_version: SchemaVersion,
        to_version: SchemaVersion,
    ) -> bytes:
        path = self.get_migration_path(schema_name, from_version, to_version)
        for step in path:
            data = await step.up(data)
        return data

    def has_migration(
        self,
        schema_name: str,
        from_version: SchemaVersion,
        to_version: SchemaVersion,
    ) -> bool:
        return any(
            m.schema_name == schema_name
            and m.from_version == from_version
            and m.to_version == to_version
            for m in self._migrations
        )


class _EmptyClass:
    pass


# ── Tests ──────────────────────────────────────────────────────────────────────


class TestMigrationProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockMigration(), MigrationProtocol)

    def test_empty_class_does_not_satisfy(self) -> None:
        assert not isinstance(_EmptyClass(), MigrationProtocol)

    def test_version_properties(self) -> None:
        m = _MockMigration()
        assert m.from_version == V1
        assert m.to_version == V2
        assert m.schema_name == "Tick"

    def test_compatibility_property(self) -> None:
        m = _MockMigration()
        assert m.compatibility == CompatibilityStrategy.BACKWARD

    async def test_up_transforms_data(self) -> None:
        m = _MockMigration()
        result = await m.up(b"original")
        assert result == b"original_v2"

    async def test_down_reverses_transformation(self) -> None:
        m = _MockMigration(reversible=True)
        upgraded = await m.up(b"original")
        downgraded = await m.down(upgraded)
        assert downgraded == b"original"

    async def test_down_raises_when_irreversible(self) -> None:
        m = _MockMigration(reversible=False)
        with pytest.raises(NotImplementedError):
            await m.down(b"data_v2")

    def test_is_reversible(self) -> None:
        assert _MockMigration(reversible=True).is_reversible() is True
        assert _MockMigration(reversible=False).is_reversible() is False


class TestVersionRegistryProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockVersionRegistry(), VersionRegistryProtocol)

    def test_register_and_current(self) -> None:
        registry = _MockVersionRegistry()
        registry.register("Tick", V1)
        assert registry.current_version("Tick") == V1

    def test_current_returns_highest_version(self) -> None:
        registry = _MockVersionRegistry()
        registry.register("Tick", V1)
        registry.register("Tick", V2)
        registry.register("Tick", V1_1)
        assert registry.current_version("Tick") == V2

    def test_current_unregistered_raises(self) -> None:
        registry = _MockVersionRegistry()
        with pytest.raises(KeyError):
            registry.current_version("Unknown")

    def test_history_ordered(self) -> None:
        registry = _MockVersionRegistry()
        registry.register("Tick", V2)
        registry.register("Tick", V1)
        history = registry.history("Tick")
        assert history[0] == V1
        assert history[1] == V2

    def test_history_empty_for_unregistered(self) -> None:
        assert _MockVersionRegistry().history("Unknown") == ()

    def test_is_registered(self) -> None:
        registry = _MockVersionRegistry()
        assert registry.is_registered("Tick") is False
        registry.register("Tick", V1)
        assert registry.is_registered("Tick") is True


class TestSchemaRegistryProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockSchemaRegistry(), SchemaRegistryProtocol)

    def test_register_migration(self) -> None:
        registry = _MockSchemaRegistry()
        migration = _MockMigration()
        registry.register_migration(migration)
        assert registry.has_migration("Tick", V1, V2)

    def test_has_migration_false_when_absent(self) -> None:
        registry = _MockSchemaRegistry()
        assert registry.has_migration("Tick", V1, V2) is False

    def test_get_migration_path(self) -> None:
        registry = _MockSchemaRegistry()
        m = _MockMigration()
        registry.register_migration(m)
        path = registry.get_migration_path("Tick", V1, V2)
        assert len(path) == 1
        assert path[0] is m

    def test_get_migration_path_raises_when_absent(self) -> None:
        from athena.storage.exceptions import SchemaVersionError

        registry = _MockSchemaRegistry()
        with pytest.raises(SchemaVersionError):
            registry.get_migration_path("Tick", V1, V2)

    async def test_migrate_applies_steps(self) -> None:
        registry = _MockSchemaRegistry()
        registry.register_migration(_MockMigration())
        result = await registry.migrate("Tick", b"data", V1, V2)
        assert result == b"data_v2"
