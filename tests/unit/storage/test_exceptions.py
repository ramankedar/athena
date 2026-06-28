"""Unit tests for the storage exception hierarchy."""

from __future__ import annotations

import pytest

from athena.platform.exceptions import AthenaError
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


class TestStorageError:
    def test_is_athena_error(self) -> None:
        assert issubclass(StorageError, AthenaError)

    def test_construction_with_context(self) -> None:
        exc = StorageError("something failed", backend="timescaledb", table="ticks")
        assert "something failed" in str(exc)
        assert exc.context["backend"] == "timescaledb"
        assert exc.context["table"] == "ticks"

    def test_optional_error_code(self) -> None:
        exc = StorageError("msg", error_code="STR_000")
        assert exc.error_code == "STR_000"


class TestRecordNotFoundError:
    def test_is_storage_error(self) -> None:
        assert issubclass(RecordNotFoundError, StorageError)

    def test_message_contains_key(self) -> None:
        exc = RecordNotFoundError("NSE:NIFTY50")
        assert "NSE:NIFTY50" in str(exc)

    def test_default_entity_type(self) -> None:
        exc = RecordNotFoundError("key-123")
        assert exc.entity_type == "record"
        assert exc.context["entity_type"] == "record"

    def test_custom_entity_type(self) -> None:
        exc = RecordNotFoundError("key-123", entity_type="Tick")
        assert exc.entity_type == "Tick"
        assert "Tick" in str(exc)

    def test_key_stored(self) -> None:
        exc = RecordNotFoundError("my-key")
        assert exc.key == "my-key"

    def test_error_code(self) -> None:
        exc = RecordNotFoundError("key")
        assert exc.error_code == "STR_001"

    def test_caught_as_athena_error(self) -> None:
        with pytest.raises(AthenaError):
            raise RecordNotFoundError("key")


class TestDuplicateKeyError:
    def test_is_storage_error(self) -> None:
        assert issubclass(DuplicateKeyError, StorageError)

    def test_message_contains_key(self) -> None:
        exc = DuplicateKeyError("dup-key")
        assert "dup-key" in str(exc)

    def test_custom_entity_type(self) -> None:
        exc = DuplicateKeyError("k", entity_type="Instrument")
        assert exc.entity_type == "Instrument"

    def test_error_code(self) -> None:
        assert DuplicateKeyError("k").error_code == "STR_002"


class TestStorageConnectionError:
    def test_is_storage_error(self) -> None:
        assert issubclass(StorageConnectionError, StorageError)

    def test_message_contains_backend(self) -> None:
        exc = StorageConnectionError("timescaledb")
        assert "timescaledb" in str(exc)

    def test_backend_stored(self) -> None:
        exc = StorageConnectionError("duckdb")
        assert exc.backend == "duckdb"

    def test_error_code(self) -> None:
        assert StorageConnectionError("x").error_code == "STR_003"

    def test_additional_context(self) -> None:
        exc = StorageConnectionError("pg", host="db.prod", port=5432)
        assert exc.context["host"] == "db.prod"


class TestTransactionError:
    def test_is_storage_error(self) -> None:
        assert issubclass(TransactionError, StorageError)

    def test_message_contains_operation(self) -> None:
        exc = TransactionError("commit")
        assert "commit" in str(exc)

    def test_operation_stored(self) -> None:
        exc = TransactionError("rollback")
        assert exc.operation == "rollback"

    def test_error_code(self) -> None:
        assert TransactionError("commit").error_code == "STR_004"


class TestSerializationError:
    def test_is_storage_error(self) -> None:
        assert issubclass(SerializationError, StorageError)

    def test_message_contains_direction_and_type(self) -> None:
        exc = SerializationError("serialize", "Tick")
        assert "serialize" in str(exc)
        assert "Tick" in str(exc)

    def test_attributes_stored(self) -> None:
        exc = SerializationError("deserialize", "OHLCV", format="parquet")
        assert exc.direction == "deserialize"
        assert exc.entity_type == "OHLCV"
        assert exc.context["format"] == "parquet"

    def test_error_code(self) -> None:
        assert SerializationError("serialize", "T").error_code == "STR_005"


class TestVersionConflictError:
    def test_is_storage_error(self) -> None:
        assert issubclass(VersionConflictError, StorageError)

    def test_message_contains_key_and_versions(self) -> None:
        exc = VersionConflictError("my-key", expected_version=3, actual_version=5)
        assert "my-key" in str(exc)
        assert "3" in str(exc)
        assert "5" in str(exc)

    def test_attributes_stored(self) -> None:
        exc = VersionConflictError("k", 2, 4)
        assert exc.key == "k"
        assert exc.expected_version == 2
        assert exc.actual_version == 4

    def test_error_code(self) -> None:
        assert VersionConflictError("k", 1, 2).error_code == "STR_006"


class TestStorageHealthError:
    def test_is_storage_error(self) -> None:
        assert issubclass(StorageHealthError, StorageError)

    def test_message_contains_backend_and_reason(self) -> None:
        exc = StorageHealthError("timescaledb", "connection refused")
        assert "timescaledb" in str(exc)
        assert "connection refused" in str(exc)

    def test_attributes_stored(self) -> None:
        exc = StorageHealthError("pg", "timeout")
        assert exc.backend == "pg"
        assert exc.reason == "timeout"

    def test_error_code(self) -> None:
        assert StorageHealthError("x", "y").error_code == "STR_007"


class TestQueryError:
    def test_is_storage_error(self) -> None:
        assert issubclass(QueryError, StorageError)

    def test_message_contains_reason(self) -> None:
        exc = QueryError("unsupported operator LIKE")
        assert "unsupported operator LIKE" in str(exc)

    def test_reason_stored(self) -> None:
        exc = QueryError("invalid time range")
        assert exc.reason == "invalid time range"

    def test_error_code(self) -> None:
        assert QueryError("x").error_code == "STR_008"


class TestSchemaVersionError:
    def test_is_storage_error(self) -> None:
        assert issubclass(SchemaVersionError, StorageError)

    def test_message_contains_schema_name(self) -> None:
        exc = SchemaVersionError("Tick")
        assert "Tick" in str(exc)

    def test_schema_name_stored(self) -> None:
        exc = SchemaVersionError("OHLCV", expected="1.0.0", found="2.0.0")
        assert exc.schema_name == "OHLCV"
        assert exc.context["expected"] == "1.0.0"

    def test_error_code(self) -> None:
        assert SchemaVersionError("x").error_code == "STR_009"
