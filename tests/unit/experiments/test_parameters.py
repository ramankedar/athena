"""Unit tests for parameter value objects."""

from __future__ import annotations

import pytest

from athena.experiments.exceptions import InvalidParameterError
from athena.experiments.parameters import (
    ParameterDefinition,
    ParameterSnapshot,
    ParameterValue,
    ParameterValueType,
)


class TestParameterValueType:
    def test_values(self) -> None:
        assert ParameterValueType.STRING == "string"
        assert ParameterValueType.INTEGER == "integer"
        assert ParameterValueType.FLOAT == "float"
        assert ParameterValueType.BOOLEAN == "boolean"
        assert ParameterValueType.DATE == "date"
        assert ParameterValueType.SYMBOL == "symbol"


class TestParameterValue:
    def test_valid_string(self) -> None:
        p = ParameterValue("smoothing", "EMA", ParameterValueType.STRING)
        assert p.name == "smoothing"
        assert p.raw_value == "EMA"

    def test_empty_name_raises(self) -> None:
        with pytest.raises(InvalidParameterError, match="name"):
            ParameterValue("", "14", ParameterValueType.INTEGER)

    def test_as_int(self) -> None:
        p = ParameterValue("period", "14", ParameterValueType.INTEGER)
        assert p.as_int() == 14

    def test_as_int_invalid(self) -> None:
        p = ParameterValue("period", "abc", ParameterValueType.STRING)
        with pytest.raises(InvalidParameterError, match="integer"):
            p.as_int()

    def test_as_float(self) -> None:
        p = ParameterValue("rate", "0.05", ParameterValueType.FLOAT)
        assert p.as_float() == pytest.approx(0.05)

    def test_as_float_invalid(self) -> None:
        p = ParameterValue("rate", "not_float", ParameterValueType.STRING)
        with pytest.raises(InvalidParameterError, match="float"):
            p.as_float()

    def test_as_bool_true_variants(self) -> None:
        for val in ("true", "True", "TRUE", "1", "yes", "YES"):
            p = ParameterValue("flag", val, ParameterValueType.BOOLEAN)
            assert p.as_bool() is True

    def test_as_bool_false_variants(self) -> None:
        for val in ("false", "False", "FALSE", "0", "no", "NO"):
            p = ParameterValue("flag", val, ParameterValueType.BOOLEAN)
            assert p.as_bool() is False

    def test_as_bool_invalid(self) -> None:
        p = ParameterValue("flag", "maybe", ParameterValueType.BOOLEAN)
        with pytest.raises(InvalidParameterError, match="bool"):
            p.as_bool()

    def test_str(self) -> None:
        p = ParameterValue("period", "14", ParameterValueType.INTEGER)
        assert "period" in str(p)
        assert "14" in str(p)


class TestParameterDefinition:
    def test_valid_construction(self) -> None:
        d = ParameterDefinition("period", ParameterValueType.INTEGER)
        assert d.name == "period"
        assert d.is_required is True

    def test_empty_name_raises(self) -> None:
        with pytest.raises(InvalidParameterError, match="name"):
            ParameterDefinition("", ParameterValueType.STRING)

    def test_is_value_allowed_no_restriction(self) -> None:
        d = ParameterDefinition("p", ParameterValueType.STRING)
        assert d.is_value_allowed("anything") is True

    def test_is_value_allowed_restricted(self) -> None:
        d = ParameterDefinition(
            "smoothing", ParameterValueType.STRING, allowed_values=("SMA", "EMA")
        )
        assert d.is_value_allowed("SMA") is True
        assert d.is_value_allowed("WMA") is False

    def test_optional_parameter(self) -> None:
        d = ParameterDefinition(
            "opt", ParameterValueType.INTEGER, is_required=False, default_value="10"
        )
        assert d.is_required is False
        assert d.default_value == "10"

    def test_str(self) -> None:
        d = ParameterDefinition("period", ParameterValueType.INTEGER)
        s = str(d)
        assert "period" in s


class TestParameterSnapshot:
    def test_from_mapping_empty(self) -> None:
        snap = ParameterSnapshot.from_mapping({})
        assert len(snap) == 0

    def test_from_mapping_sorted(self) -> None:
        snap = ParameterSnapshot.from_mapping({"z": "last", "a": "first"})
        assert snap.values[0].name == "a"
        assert snap.values[1].name == "z"

    def test_snapshot_hash_deterministic(self) -> None:
        s1 = ParameterSnapshot.from_mapping({"period": "14"})
        s2 = ParameterSnapshot.from_mapping({"period": "14"})
        assert s1.snapshot_hash == s2.snapshot_hash

    def test_snapshot_hash_changes_with_values(self) -> None:
        s1 = ParameterSnapshot.from_mapping({"period": "14"})
        s2 = ParameterSnapshot.from_mapping({"period": "20"})
        assert s1.snapshot_hash != s2.snapshot_hash

    def test_get_existing(self) -> None:
        snap = ParameterSnapshot.from_mapping({"period": "14"})
        val = snap.get("period")
        assert val is not None
        assert val.as_int() == 14

    def test_get_missing(self) -> None:
        snap = ParameterSnapshot.from_mapping({"period": "14"})
        assert snap.get("nonexistent") is None

    def test_to_dict(self) -> None:
        snap = ParameterSnapshot.from_mapping({"a": "1", "b": "2"})
        d = snap.to_dict()
        assert d == {"a": "1", "b": "2"}

    def test_with_type_hints(self) -> None:
        snap = ParameterSnapshot.from_mapping(
            {"period": "14"},
            type_hints={"period": ParameterValueType.INTEGER},
        )
        assert snap.get("period").value_type == ParameterValueType.INTEGER  # type: ignore[union-attr]

    def test_str(self) -> None:
        snap = ParameterSnapshot.from_mapping({"period": "14"})
        assert "period" in str(snap)

    def test_unsorted_raises(self) -> None:
        with pytest.raises(InvalidParameterError, match="sorted"):
            ParameterSnapshot(
                values=(
                    ParameterValue("z", "last", ParameterValueType.STRING),
                    ParameterValue("a", "first", ParameterValueType.STRING),
                ),
                snapshot_hash="dummy",
            )
