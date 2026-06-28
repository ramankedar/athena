"""Experiment parameter schema and snapshot value objects.

Two separate concerns:

``ParameterDefinition``
    What a parameter IS — name, type, constraints, default. Belongs to the
    experiment specification and is shared across all runs.

``ParameterSnapshot``
    What values were ACTUALLY USED in a specific run. Immutable once recorded.
    The ``snapshot_hash`` (SHA-256 of sorted name=value pairs) enables quick
    deduplication: two runs with identical parameter values share a hash.

All parameter values are stored as strings for serialisability. Typed
accessor methods (``as_int``, ``as_float``, ``as_bool``) handle conversion.
Using ``object`` rather than ``Any`` avoids disabling mypy while accepting
any Python value in ``from_mapping``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib

from athena.experiments.exceptions import InvalidParameterError


class ParameterValueType(StrEnum):
    """The data type of a parameter value.

    Attributes:
        STRING:  Free-form text (e.g. exchange code, strategy name).
        INTEGER: Whole number (e.g. lookback period, lot size).
        FLOAT:   Real number (e.g. commission rate, stop-loss pct).
        BOOLEAN: True/False flag (e.g. use_leverage, enable_shorting).
        DATE:    ISO-8601 date string (e.g. backtest start date).
        SYMBOL:  Instrument symbol string (e.g. ``"NSE:NIFTY50-INDEX"``).
    """

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    SYMBOL = "symbol"


@dataclass(frozen=True)
class ParameterValue:
    """A single named parameter value stored as a string.

    Attributes:
        name:       Parameter name (must be non-empty).
        raw_value:  String representation of the value.
        value_type: Declared type, used for conversion and validation.

    Example::

        p = ParameterValue("period", "14", ParameterValueType.INTEGER)
        assert p.as_int() == 14
    """

    name: str
    raw_value: str
    value_type: ParameterValueType

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidParameterError("name", "parameter name must not be empty")

    def as_int(self) -> int:
        """Parse the value as an integer.

        Returns:
            Integer representation of ``raw_value``.

        Raises:
            InvalidParameterError: If the value cannot be parsed as int.
        """
        try:
            return int(self.raw_value)
        except (ValueError, TypeError) as exc:
            raise InvalidParameterError(
                self.name,
                f"cannot convert {self.raw_value!r} to integer",
            ) from exc

    def as_float(self) -> float:
        """Parse the value as a float.

        Returns:
            Float representation of ``raw_value``.

        Raises:
            InvalidParameterError: If the value cannot be parsed as float.
        """
        try:
            return float(self.raw_value)
        except (ValueError, TypeError) as exc:
            raise InvalidParameterError(
                self.name,
                f"cannot convert {self.raw_value!r} to float",
            ) from exc

    def as_bool(self) -> bool:
        """Parse the value as a boolean.

        Accepts ``"true"``/``"false"`` (case-insensitive) and ``"1"``/``"0"``.

        Returns:
            Boolean representation of ``raw_value``.

        Raises:
            InvalidParameterError: If the value is not a recognised boolean string.
        """
        normalised = self.raw_value.strip().lower()
        if normalised in ("true", "1", "yes"):
            return True
        if normalised in ("false", "0", "no"):
            return False
        raise InvalidParameterError(
            self.name,
            f"cannot convert {self.raw_value!r} to bool "
            "(expected 'true'/'false'/'1'/'0'/'yes'/'no')",
        )

    def __str__(self) -> str:
        return f"{self.name}={self.raw_value!r}"


@dataclass(frozen=True)
class ParameterDefinition:
    """Schema declaration for a single experiment parameter.

    Attributes:
        name:           Parameter identifier.
        value_type:     Expected data type.
        description:    Human-readable explanation.
        default_value:  String representation of the default. ``None`` when
            no default applies and the parameter is always required.
        min_value:      Minimum allowed value as string. ``None`` = no lower bound.
        max_value:      Maximum allowed value as string. ``None`` = no upper bound.
        allowed_values: Finite set of acceptable values. Empty = no restriction.
        is_required:    When ``True``, runs must supply this parameter explicitly.

    Raises:
        InvalidParameterError: If ``name`` is empty.
    """

    name: str
    value_type: ParameterValueType
    description: str | None = None
    default_value: str | None = None
    min_value: str | None = None
    max_value: str | None = None
    allowed_values: tuple[str, ...] = ()
    is_required: bool = True

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidParameterError("name", "parameter name must not be empty")

    def is_value_allowed(self, value: str) -> bool:
        """Return ``True`` when ``value`` is within the allowed set.

        If ``allowed_values`` is empty, all values are allowed.

        Args:
            value: The string value to check.

        Returns:
            ``True`` when allowed.
        """
        if not self.allowed_values:
            return True
        return value in self.allowed_values

    def __str__(self) -> str:
        req = "required" if self.is_required else f"optional={self.default_value!r}"
        return f"ParameterDefinition({self.name!r}: {self.value_type.value}, {req})"


@dataclass(frozen=True)
class ParameterSnapshot:
    """Immutable snapshot of all parameter values used in a single run.

    Values are stored as a sorted tuple of ``ParameterValue`` objects (sorted
    by name for canonical ordering). The ``snapshot_hash`` is a SHA-256 of
    the sorted ``name=value`` strings, enabling deduplication.

    Attributes:
        values:        Sorted tuple of ``ParameterValue`` objects.
        snapshot_hash: SHA-256 of the canonical parameter string.

    Example::

        snap = ParameterSnapshot.from_mapping({"period": "14", "smoothing": "EMA"})
        assert snap.get("period").as_int() == 14
    """

    values: tuple[ParameterValue, ...]
    snapshot_hash: str

    def __post_init__(self) -> None:
        # Verify sorting
        names = [v.name for v in self.values]
        if names != sorted(names):
            raise InvalidParameterError(
                "values",
                "ParameterSnapshot.values must be sorted by name",
            )

    @classmethod
    def from_mapping(
        cls,
        params: dict[str, str],
        type_hints: dict[str, ParameterValueType] | None = None,
    ) -> ParameterSnapshot:
        """Construct a ``ParameterSnapshot`` from a name->string-value mapping.

        Parameters are sorted by name to ensure canonical ordering.

        Args:
            params:     Dictionary of parameter names to string values.
            type_hints: Optional mapping of name to ``ParameterValueType``.
                When not provided, all values are typed as ``STRING``.

        Returns:
            A new ``ParameterSnapshot``.
        """
        type_hints = type_hints or {}
        sorted_values = tuple(
            ParameterValue(
                name=name,
                raw_value=value,
                value_type=type_hints.get(name, ParameterValueType.STRING),
            )
            for name, value in sorted(params.items())
        )
        hash_input = "|".join(f"{v.name}={v.raw_value}" for v in sorted_values)
        snapshot_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
        return cls(values=sorted_values, snapshot_hash=snapshot_hash)

    def get(self, name: str) -> ParameterValue | None:
        """Return the ``ParameterValue`` for the given name, or ``None``.

        Args:
            name: Parameter name to look up.

        Returns:
            The matching ``ParameterValue``, or ``None``.
        """
        for v in self.values:
            if v.name == name:
                return v
        return None

    def to_dict(self) -> dict[str, str]:
        """Return a plain dict of name -> raw_value pairs.

        Returns:
            Dictionary suitable for display or serialisation.
        """
        return {v.name: v.raw_value for v in self.values}

    def __len__(self) -> int:
        return len(self.values)

    def __str__(self) -> str:
        pairs = ", ".join(f"{v.name}={v.raw_value!r}" for v in self.values)
        return f"ParameterSnapshot({pairs})"
