"""Schema versioning and migration abstractions.

Schema versioning solves two problems that arise as the platform evolves:

1. **Stored data outlives the code that wrote it.** Tick data written by
   schema v1 may need to be read by code running schema v2. The migration
   system defines how to transform bytes from one version to another.

2. **Multiple services may run different schema versions simultaneously.**
   A rolling deployment means some pods run v2 and some run v1. The
   compatibility strategy declares what mix is safe.

Design decisions:
    - Migrations operate on bytes (``bytes → bytes``), not domain objects.
      This allows offline migrations on archived Parquet files and avoids
      coupling migration logic to the current domain model version.
    - The ``SchemaRegistryProtocol`` finds migration paths automatically,
      composing individual ``MigrationProtocol`` steps into a chain.
    - ``CompatibilityStrategy`` (from ``models.py``) is used to annotate
      each migration so the registry can enforce safety constraints during
      rolling deployments.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from athena.storage.models import CompatibilityStrategy, SchemaVersion


@runtime_checkable
class MigrationProtocol(Protocol):
    """A single schema migration step: transform bytes from one version to another.

    Migrations are directional: ``up()`` upgrades from ``from_version`` to
    ``to_version``; ``down()`` reverses the transformation. Not all migrations
    are reversible — ``is_reversible`` declares whether ``down()`` is
    implemented.

    Implementations must be:
        - **Stateless**: the same input bytes always produce the same output bytes.
        - **Idempotent**: applying ``up()`` to already-upgraded bytes is handled
          gracefully (either a no-op or raises ``SchemaVersionError``).
        - **Atomic at the byte level**: a partial failure must leave the original
          bytes unchanged.
    """

    @property
    def from_version(self) -> SchemaVersion:
        """The schema version this migration upgrades from.

        Returns:
            The source ``SchemaVersion``.
        """
        ...

    @property
    def to_version(self) -> SchemaVersion:
        """The schema version this migration upgrades to.

        Returns:
            The target ``SchemaVersion``.
        """
        ...

    @property
    def schema_name(self) -> str:
        """The name of the schema this migration applies to.

        Returns:
            Schema name string (e.g. ``"Tick"``, ``"OHLCV"``).
        """
        ...

    @property
    def compatibility(self) -> CompatibilityStrategy:
        """The compatibility guarantee this migration provides.

        Returns:
            A ``CompatibilityStrategy`` value indicating whether readers
            using ``from_version`` can still read data written by ``to_version``
            and vice versa.
        """
        ...

    async def up(self, data: bytes) -> bytes:
        """Upgrade serialised bytes from ``from_version`` to ``to_version``.

        Args:
            data: Bytes serialised at ``from_version``.

        Returns:
            Bytes compatible with ``to_version``.

        Raises:
            SchemaVersionError: If ``data`` is not at ``from_version``.
            SerializationError: If the transformation fails.
        """
        ...

    async def down(self, data: bytes) -> bytes:
        """Downgrade serialised bytes from ``to_version`` to ``from_version``.

        Args:
            data: Bytes serialised at ``to_version``.

        Returns:
            Bytes compatible with ``from_version``.

        Raises:
            NotImplementedError: If ``is_reversible`` is ``False``.
            SchemaVersionError: If ``data`` is not at ``to_version``.
        """
        ...

    def is_reversible(self) -> bool:
        """Return ``True`` if ``down()`` is implemented for this migration.

        A migration is irreversible when the transformation loses information
        (e.g. dropping a column, narrowing a numeric type). Irreversible
        migrations require a backup strategy before deployment.

        Returns:
            ``True`` when ``down()`` can safely undo the migration.
        """
        ...


@runtime_checkable
class VersionRegistryProtocol(Protocol):
    """Tracks the current and historical schema versions for each entity type.

    The version registry is the source of truth for "what schema version is
    this backend currently at?" and "what versions have been deployed?".

    Implementations may persist the version history in a dedicated metadata
    table or file (e.g. ``schema_versions`` in TimescaleDB, a JSON sidecar
    for Parquet stores).
    """

    def current_version(self, schema_name: str) -> SchemaVersion:
        """Return the current (highest deployed) schema version.

        Args:
            schema_name: The name of the schema to query.

        Returns:
            The current ``SchemaVersion``.

        Raises:
            KeyError: If the schema has not been registered.
        """
        ...

    def register(self, schema_name: str, version: SchemaVersion) -> None:
        """Record that a schema version has been deployed.

        If ``version`` is older than the currently registered version,
        it is silently ignored (history is append-only and monotonically
        increasing).

        Args:
            schema_name: The schema identifier.
            version:     The deployed schema version.
        """
        ...

    def history(self, schema_name: str) -> tuple[SchemaVersion, ...]:
        """Return all registered versions in ascending order.

        Args:
            schema_name: The schema to query.

        Returns:
            An ordered tuple of all known ``SchemaVersion`` values.
            Returns an empty tuple if the schema has never been registered.
        """
        ...

    def is_registered(self, schema_name: str) -> bool:
        """Return ``True`` if the schema has been registered.

        Args:
            schema_name: The schema to check.

        Returns:
            ``True`` if ``register()`` has been called at least once with
            this schema name.
        """
        ...


@runtime_checkable
class SchemaRegistryProtocol(Protocol):
    """Manages migration paths and orchestrates multi-step schema upgrades.

    The registry accepts individual ``MigrationProtocol`` steps and computes
    migration chains automatically. For example, if migrations exist for
    v1→v2 and v2→v3, the registry can migrate data from v1 to v3 in two
    sequential steps without the caller knowing about v2.
    """

    def register_migration(self, migration: MigrationProtocol) -> None:
        """Register a single migration step.

        Args:
            migration: The migration to register. Identified by its
                ``schema_name``, ``from_version``, and ``to_version``.

        Raises:
            ValueError: If a migration for the same
                (schema_name, from_version, to_version) triplet is already
                registered.
        """
        ...

    def get_migration_path(
        self,
        schema_name: str,
        from_version: SchemaVersion,
        to_version: SchemaVersion,
    ) -> tuple[MigrationProtocol, ...]:
        """Find the shortest chain of migrations from ``from_version`` to ``to_version``.

        Uses a graph search over registered migrations to find the shortest
        path. For well-maintained schemas, this is typically a single step.

        Args:
            schema_name:  The schema to migrate.
            from_version: The starting version.
            to_version:   The target version.

        Returns:
            An ordered tuple of ``MigrationProtocol`` instances to apply
            sequentially to upgrade the data.

        Raises:
            SchemaVersionError: If no migration path exists between the
                requested versions.
        """
        ...

    async def migrate(
        self,
        schema_name: str,
        data: bytes,
        from_version: SchemaVersion,
        to_version: SchemaVersion,
    ) -> bytes:
        """Migrate ``data`` from ``from_version`` to ``to_version``.

        Applies the migration chain returned by ``get_migration_path()``
        sequentially. If any step fails, the error propagates and the
        original bytes are considered unchanged.

        Args:
            schema_name:  The schema identifier.
            data:         The bytes to migrate.
            from_version: The version the bytes are currently at.
            to_version:   The desired target version.

        Returns:
            The migrated bytes at ``to_version``.

        Raises:
            SchemaVersionError: If no migration path exists.
            SerializationError: If a migration step fails.
        """
        ...

    def has_migration(
        self,
        schema_name: str,
        from_version: SchemaVersion,
        to_version: SchemaVersion,
    ) -> bool:
        """Return ``True`` if a migration path exists between the versions.

        Args:
            schema_name:  The schema to query.
            from_version: The starting version.
            to_version:   The target version.

        Returns:
            ``True`` if ``get_migration_path()`` would succeed for these versions.
        """
        ...
