"""Unit tests for serialisation Protocol definitions."""

from __future__ import annotations

from athena.storage.models import SchemaVersion, SerializationFormat
from athena.storage.serialization import (
    CodecProtocol,
    DeserializerProtocol,
    SchemaProtocol,
    SerializerProtocol,
)

V1 = SchemaVersion(1, 0, 0)


# ── Minimal mock implementations ──────────────────────────────────────────────


class _MockSerializer:
    @property
    def format(self) -> SerializationFormat:
        return SerializationFormat.JSON

    def serialize(self, value: object) -> bytes:
        return b'{"key":"value"}'


class _MockDeserializer:
    @property
    def format(self) -> SerializationFormat:
        return SerializationFormat.JSON

    def deserialize(self, data: bytes) -> object:
        return {"key": "value"}


class _MockCodec:
    @property
    def format(self) -> SerializationFormat:
        return SerializationFormat.MSGPACK

    @property
    def schema_version(self) -> SchemaVersion:
        return V1

    def serialize(self, value: object) -> bytes:
        return b"\x82\xa3key\xa5value"

    def deserialize(self, data: bytes) -> object:
        return {"key": "value"}


class _MockSchema:
    @property
    def name(self) -> str:
        return "Tick"

    @property
    def version(self) -> SchemaVersion:
        return V1

    @property
    def format(self) -> SerializationFormat:
        return SerializationFormat.JSON

    def validate(self, data: bytes) -> bool:
        return len(data) > 0


class _EmptyClass:
    pass


# ── Tests ──────────────────────────────────────────────────────────────────────


class TestSerializerProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockSerializer(), SerializerProtocol)

    def test_empty_class_does_not_satisfy(self) -> None:
        assert not isinstance(_EmptyClass(), SerializerProtocol)

    def test_serialize_returns_bytes(self) -> None:
        s = _MockSerializer()
        result = s.serialize({"key": "value"})
        assert isinstance(result, bytes)

    def test_format_property(self) -> None:
        s = _MockSerializer()
        assert s.format == SerializationFormat.JSON


class TestDeserializerProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockDeserializer(), DeserializerProtocol)

    def test_deserialize_returns_object(self) -> None:
        d = _MockDeserializer()
        result = d.deserialize(b'{"key":"value"}')
        assert result == {"key": "value"}

    def test_format_property(self) -> None:
        d = _MockDeserializer()
        assert d.format == SerializationFormat.JSON


class TestCodecProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockCodec(), CodecProtocol)

    def test_serializer_alone_satisfies_codec(self) -> None:
        # _MockSerializer lacks schema_version and deserialize, so it should NOT
        # satisfy CodecProtocol
        assert not isinstance(_MockSerializer(), CodecProtocol)

    def test_roundtrip(self) -> None:
        codec = _MockCodec()
        original = {"key": "value"}
        encoded = codec.serialize(original)
        decoded = codec.deserialize(encoded)
        assert decoded == original

    def test_schema_version_property(self) -> None:
        assert _MockCodec().schema_version == V1

    def test_format_property(self) -> None:
        assert _MockCodec().format == SerializationFormat.MSGPACK


class TestSchemaProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        assert isinstance(_MockSchema(), SchemaProtocol)

    def test_empty_class_does_not_satisfy(self) -> None:
        assert not isinstance(_EmptyClass(), SchemaProtocol)

    def test_properties(self) -> None:
        schema = _MockSchema()
        assert schema.name == "Tick"
        assert schema.version == V1
        assert schema.format == SerializationFormat.JSON

    def test_validate_non_empty_bytes(self) -> None:
        schema = _MockSchema()
        assert schema.validate(b'{"symbol": "NSE:NIFTY50"}') is True

    def test_validate_empty_bytes(self) -> None:
        schema = _MockSchema()
        assert schema.validate(b"") is False
