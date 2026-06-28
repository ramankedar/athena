"""Serialisation interfaces for the storage domain.

Serialisation is intentionally decoupled from storage: a ``CodecProtocol[T]``
knows how to transform ``T`` to bytes and back; the storage adapter knows
where to put those bytes. This separation means:

- A ``TickCodec`` can be reused across TimescaleDB (BLOB columns),
  S3 (object bodies), and Parquet (column-level encoding).
- Schema evolution is handled by the codec, not the storage adapter.
- Codecs can be unit-tested without a storage backend.

Three interfaces are provided:

``SerializerProtocol[T]``
    Write direction only: domain object → bytes.
    Used by append-only archives and audit trails.

``DeserializerProtocol[T]``
    Read direction only: bytes → domain object.
    Used by read-only research processes that replay stored data.

``CodecProtocol[T]``
    Full bidirectional codec: combines both directions.
    Used by the standard read/write repository adapters.

Additionally, ``SchemaProtocol`` defines the schema metadata that accompanies
serialised bytes — schema name, version, and format. Backends that support
schema validation (e.g. Confluent Schema Registry for Kafka, Avro for Parquet)
implement this Protocol.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TypeVar, runtime_checkable

if TYPE_CHECKING:
    from athena.storage.models import SchemaVersion, SerializationFormat

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)
T_contra = TypeVar("T_contra", contravariant=True)


@runtime_checkable
class SerializerProtocol(Protocol[T_contra]):
    """Write-direction codec: transforms a domain object to raw bytes.

    Implementations must be stateless and deterministic: serialising the
    same object twice must produce equivalent bytes (though not necessarily
    identical — e.g. JSON key ordering may vary).

    Type parameter:
        T_contra: The entity type this serialiser accepts. Contravariant
            because ``SerializerProtocol[object]`` (accepts any object) is
            a subtype of ``SerializerProtocol[Tick]`` (accepts only Tick).
    """

    def serialize(self, value: T_contra) -> bytes:
        """Encode ``value`` to its wire representation.

        Args:
            value: The domain object to encode.

        Returns:
            Raw bytes representing the encoded object.

        Raises:
            SerializationError: If the object cannot be encoded.
        """
        ...

    @property
    def format(self) -> SerializationFormat:
        """The wire format produced by this serialiser.

        Returns:
            A ``SerializationFormat`` enum value (JSON, MSGPACK, etc.).
        """
        ...


@runtime_checkable
class DeserializerProtocol(Protocol[T_co]):
    """Read-direction codec: reconstructs a domain object from raw bytes.

    Type parameter:
        T_co: The entity type this deserialiser produces. Covariant because
            a ``DeserializerProtocol[OHLCV]`` satisfies contexts expecting a
            ``DeserializerProtocol[object]``.
    """

    def deserialize(self, data: bytes) -> T_co:
        """Decode raw bytes to a domain object.

        Args:
            data: The raw bytes to decode.

        Returns:
            The reconstructed domain object.

        Raises:
            SerializationError: If ``data`` is malformed or uses an
                incompatible schema version.
        """
        ...

    @property
    def format(self) -> SerializationFormat:
        """The wire format this deserialiser accepts.

        Returns:
            A ``SerializationFormat`` enum value matching the bytes produced
            by the corresponding ``SerializerProtocol``.
        """
        ...


@runtime_checkable
class CodecProtocol(Protocol[T]):
    """Bidirectional serialisation codec: domain object ↔ bytes.

    Composes ``SerializerProtocol`` and ``DeserializerProtocol`` for the
    standard read/write storage adapter use case.

    Type parameter:
        T: The entity type. Invariant because the codec both accepts T
            (in ``serialize``) and produces T (in ``deserialize``).
    """

    def serialize(self, value: T) -> bytes:
        """Encode ``value`` to bytes.

        Args:
            value: The domain object to encode.

        Returns:
            Raw bytes.

        Raises:
            SerializationError: If encoding fails.
        """
        ...

    def deserialize(self, data: bytes) -> T:
        """Decode bytes to a domain object.

        Args:
            data: The raw bytes to decode.

        Returns:
            The reconstructed domain object.

        Raises:
            SerializationError: If decoding fails.
        """
        ...

    @property
    def format(self) -> SerializationFormat:
        """The wire format used by this codec.

        Returns:
            A ``SerializationFormat`` enum value.
        """
        ...

    @property
    def schema_version(self) -> SchemaVersion:
        """The schema version this codec currently writes.

        When a ``MigrationProtocol`` upgrades data, the deserialiser checks
        this version against the version embedded in the stored bytes to
        detect whether migration is needed.

        Returns:
            The current write-side ``SchemaVersion``.
        """
        ...


@runtime_checkable
class SchemaProtocol(Protocol):
    """Metadata contract for a serialisation schema.

    Backends that enforce schema compatibility (Kafka with Avro, Parquet
    with Iceberg metadata, TimescaleDB with ``schema_version`` columns) can
    register a ``SchemaProtocol`` implementation with a schema registry.
    """

    @property
    def name(self) -> str:
        """The canonical name of this schema (e.g. ``"Tick"``, ``"OHLCV"``).

        Returns:
            Schema name string.
        """
        ...

    @property
    def version(self) -> SchemaVersion:
        """The version of this schema definition.

        Returns:
            The schema's current ``SchemaVersion``.
        """
        ...

    @property
    def format(self) -> SerializationFormat:
        """The wire format described by this schema.

        Returns:
            The ``SerializationFormat`` this schema applies to.
        """
        ...

    def validate(self, data: bytes) -> bool:
        """Return ``True`` if ``data`` conforms to this schema.

        Args:
            data: The bytes to validate.

        Returns:
            ``True`` when the bytes are valid; ``False`` otherwise.
            Does not raise — validation errors are signalled by the
            return value to allow callers to handle them gracefully.
        """
        ...
