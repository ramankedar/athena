"""Input requirement and output schema value objects.

Every ``FeatureDefinition`` declares:
1. What raw data it **consumes** — via ``InputRequirement`` objects.
2. What values it **produces** — via ``FeatureOutputSchema``.

These declarations are the contract between the feature domain and the
computation engine. An engine reads them to determine:
- Which data to prefetch before computing a feature.
- How to allocate storage for feature values.
- Whether a feature's output is compatible with a model's expected inputs.

No calculation logic lives here — only the specification of data shapes.
"""

from __future__ import annotations

from dataclasses import dataclass

from athena.features.exceptions import (
    InvalidFeatureDefinitionError,
    InvalidInputRequirementError,
)
from athena.features.models import FeatureOutputType, InputDataType, InputTimeframe


@dataclass(frozen=True)
class InputRequirement:
    """Declaration of a single raw data input needed by a feature.

    A feature may have multiple ``InputRequirement`` objects — for example,
    a volatility-adjusted momentum feature might require daily OHLCV bars
    AND daily option chain snapshots.

    Attributes:
        data_type:       The type of raw market data required.
        timeframe:       The bar resolution. ``None`` for tick-level data types
            (TICK, QUOTE, TRADE, ORDER_BOOK) where no aggregation applies.
        lookback_periods: Number of historical bars required (e.g. 14 for RSI-14).
            Must be >= 1. ``None`` means the feature needs the entire history.
        min_periods:     Minimum number of bars required to produce any output.
            Must be >= 1 and <= ``lookback_periods`` when both are set.
            ``None`` defaults to ``lookback_periods``.
        description:     Optional human-readable description of why this input
            is required.

    Raises:
        InvalidInputRequirementError: If ``min_periods > lookback_periods``,
            or either is < 1.

    Example::

        # RSI-14 on daily OHLCV: needs at least 2 bars to compute, prefers 14
        rsi_input = InputRequirement(
            data_type=InputDataType.OHLCV,
            timeframe=InputTimeframe.DAY_1,
            lookback_periods=14,
            min_periods=2,
        )
    """

    data_type: InputDataType
    timeframe: InputTimeframe | None = None
    lookback_periods: int | None = None
    min_periods: int | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        if self.lookback_periods is not None and self.lookback_periods < 1:
            raise InvalidInputRequirementError(
                f"InputRequirement.lookback_periods must be >= 1 (got {self.lookback_periods})"
            )
        if self.min_periods is not None and self.min_periods < 1:
            raise InvalidInputRequirementError(
                f"InputRequirement.min_periods must be >= 1 (got {self.min_periods})"
            )
        if (
            self.min_periods is not None
            and self.lookback_periods is not None
            and self.min_periods > self.lookback_periods
        ):
            raise InvalidInputRequirementError(
                f"InputRequirement.min_periods ({self.min_periods}) must be "
                f"<= lookback_periods ({self.lookback_periods})"
            )

    @property
    def effective_min_periods(self) -> int | None:
        """Return ``min_periods`` if set, else ``lookback_periods``, else ``None``.

        Returns:
            The effective minimum period count for this requirement.
        """
        if self.min_periods is not None:
            return self.min_periods
        return self.lookback_periods

    def __str__(self) -> str:
        tf = f"@{self.timeframe.value}" if self.timeframe else ""
        lb = f" x{self.lookback_periods}" if self.lookback_periods else ""
        return f"InputRequirement({self.data_type.value}{tf}{lb})"


@dataclass(frozen=True)
class FeatureOutputField:
    """Specification for a single value in a feature's output.

    A scalar feature has one ``FeatureOutputField``. A vector feature (like
    MACD) has multiple, each with a distinct name.

    Attributes:
        name:        Field name (e.g. ``"macd_line"``, ``"signal_line"``).
            For scalar features this is typically the feature's own name.
        output_type: The data type of this field.
        description: Optional human-readable description.
        units:       Optional physical units (e.g. ``"percent"``, ``"INR"``,
            ``"ratio"``).

    Raises:
        InvalidFeatureDefinitionError: If ``name`` is empty.
    """

    name: str
    output_type: FeatureOutputType
    description: str | None = None
    units: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidFeatureDefinitionError("FeatureOutputField.name must not be empty")

    def __str__(self) -> str:
        return f"OutputField({self.name!r}: {self.output_type.value})"


@dataclass(frozen=True)
class FeatureOutputSchema:
    """Complete specification of all values a feature produces.

    A feature's output schema is an ordered tuple of ``FeatureOutputField``
    objects. Field names must be unique within the schema.

    Attributes:
        fields: Ordered tuple of output field specifications.

    Raises:
        InvalidFeatureDefinitionError: If ``fields`` is empty or contains
            duplicate field names.

    Example::

        macd_schema = FeatureOutputSchema(
            fields=(
                FeatureOutputField("macd_line", FeatureOutputType.SCALAR),
                FeatureOutputField("signal_line", FeatureOutputType.SCALAR),
                FeatureOutputField("histogram", FeatureOutputType.SCALAR),
            )
        )
    """

    fields: tuple[FeatureOutputField, ...]

    def __post_init__(self) -> None:
        if not self.fields:
            raise InvalidFeatureDefinitionError(
                "FeatureOutputSchema.fields must contain at least one field"
            )
        names = [f.name for f in self.fields]
        if len(names) != len(set(names)):
            dupes = [n for n in names if names.count(n) > 1]
            raise InvalidFeatureDefinitionError(
                f"FeatureOutputSchema contains duplicate field names: {sorted(set(dupes))}"
            )

    @property
    def field_names(self) -> tuple[str, ...]:
        """Return the names of all output fields.

        Returns:
            Tuple of field name strings in definition order.
        """
        return tuple(f.name for f in self.fields)

    @property
    def is_scalar(self) -> bool:
        """Return ``True`` when the schema has exactly one scalar field.

        Returns:
            ``True`` for single-value scalar outputs.
        """
        return len(self.fields) == 1 and self.fields[0].output_type == FeatureOutputType.SCALAR

    def get_field(self, name: str) -> FeatureOutputField | None:
        """Return the field with the given name, or ``None``.

        Args:
            name: Field name to look up.

        Returns:
            The matching ``FeatureOutputField``, or ``None``.
        """
        for f in self.fields:
            if f.name == name:
                return f
        return None

    def __len__(self) -> int:
        return len(self.fields)

    def __str__(self) -> str:
        names = ", ".join(f.name for f in self.fields)
        return f"FeatureOutputSchema({names})"
