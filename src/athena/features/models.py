"""Core primitive value types for the Feature Domain.

Defines the fundamental typed identifiers and enumerations that form the
vocabulary of the feature domain. All types here are independent of any
peer layer (``athena.market_data``, ``athena.assets``, etc.).

Types defined here:
    ``FeatureId``         — structured identifier: namespace + name.
    ``FeatureVersion``    — semantic version with ordering and constraint support.
    ``FeatureNamespace``  — organisational taxonomy for features.
    ``FeatureOutputType`` — what kind of value a feature produces.
    ``InputDataType``     — what raw data type a feature requires.
    ``InputTimeframe``    — what bar resolution a feature requires.

Why independent ``InputDataType`` and ``InputTimeframe``?
    ``athena.features`` and ``athena.market_data`` are peer layers; neither
    may import from the other. ``InputTimeframe`` uses the same string codes
    as ``market_data.Timeframe`` (``"1T"``, ``"1D"``, etc.) so that the
    engine layer can translate between the two without burdening either domain
    with knowledge of the other.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar

from athena.features.exceptions import (
    InvalidFeatureDefinitionError,
)


class FeatureNamespace(StrEnum):
    """Organisational category for a feature.

    Attributes:
        TECHNICAL:            Price and volume based signals (RSI, MACD, ATR).
        VOLATILITY:           Realised and implied volatility signals (HV, IV rank).
        OPTIONS:              Options market signals (P/C ratio, skew, term structure).
        MARKET_MICROSTRUCTURE: Order book and tick-level signals (spread, depth, OFI).
        MACRO:                Macroeconomic and cross-asset signals (FII flows, VIX).
        FUNDAMENTAL:          Company fundamentals (P/E, EPS growth, debt ratios).
        CUSTOM:               User-defined and research-only features.
    """

    TECHNICAL = "technical"
    VOLATILITY = "volatility"
    OPTIONS = "options"
    MARKET_MICROSTRUCTURE = "market_microstructure"
    MACRO = "macro"
    FUNDAMENTAL = "fundamental"
    CUSTOM = "custom"


class FeatureOutputType(StrEnum):
    """What kind of value a feature produces per instrument per timestamp.

    Attributes:
        SCALAR:      A single floating-point value (RSI, ATR, IV rank).
        VECTOR:      Multiple named floats (MACD produces line, signal, histogram).
        BOOLEAN:     A True/False signal (golden cross, earnings in window).
        CATEGORICAL: A discrete label from a finite set (market regime: bull/bear).
        RANKING:     An ordinal rank within a universe (momentum decile 1-10).
        SERIES:      A time series embedded in a single feature value (rare).
    """

    SCALAR = "scalar"
    VECTOR = "vector"
    BOOLEAN = "boolean"
    CATEGORICAL = "categorical"
    RANKING = "ranking"
    SERIES = "series"


class InputDataType(StrEnum):
    """Type of raw market data a feature requires as input.

    Values are intentionally compatible with ``athena.market_data`` data type
    names so that engine-layer translation is straightforward.

    Attributes:
        OHLCV:        Aggregated OHLCV bars.
        TICK:         Raw tick data.
        QUOTE:        Bid/ask quote snapshots.
        TRADE:        Executed trade prints.
        ORDER_BOOK:   Level 2 order book depth.
        OPTION_CHAIN: Options chain (strikes, expirations, IV, greeks).
        INDEX:        Index level or NAV data.
        FUNDAMENTAL:  Quarterly/annual company fundamentals.
    """

    OHLCV = "ohlcv"
    TICK = "tick"
    QUOTE = "quote"
    TRADE = "trade"
    ORDER_BOOK = "order_book"
    OPTION_CHAIN = "option_chain"
    INDEX = "index"
    FUNDAMENTAL = "fundamental"


class InputTimeframe(StrEnum):
    """Bar resolution for an input data requirement.

    String codes match ``athena.market_data.Timeframe`` for compatibility.

    Attributes:
        TICK:       Raw tick-level data, no aggregation.
        SECOND_1:   1-second bars.
        MINUTE_1:   1-minute bars.
        MINUTE_5:   5-minute bars.
        MINUTE_15:  15-minute bars.
        MINUTE_30:  30-minute bars.
        HOUR_1:     1-hour bars.
        HOUR_4:     4-hour bars.
        DAY_1:      Daily bars.
        WEEK_1:     Weekly bars.
        MONTH_1:    Monthly bars.
    """

    TICK = "tick"
    SECOND_1 = "1S"
    MINUTE_1 = "1T"
    MINUTE_5 = "5T"
    MINUTE_15 = "15T"
    MINUTE_30 = "30T"
    HOUR_1 = "1H"
    HOUR_4 = "4H"
    DAY_1 = "1D"
    WEEK_1 = "1W"
    MONTH_1 = "1M"


@dataclass(frozen=True, order=True)
class FeatureVersion:
    """Semantic version for a feature definition.

    Follows SemVer conventions:
    - Incrementing ``major`` signals breaking changes (different computation).
    - Incrementing ``minor`` signals backward-compatible additions.
    - Incrementing ``patch`` signals backward-compatible fixes.

    Attributes:
        major: Breaking-change counter.
        minor: Backward-compatible addition counter.
        patch: Backward-compatible fix counter.

    Example::

        v1 = FeatureVersion(1, 0, 0)
        v2 = FeatureVersion(1, 2, 0)
        assert v2 > v1
        assert str(v2) == "1.2.0"
    """

    major: int
    minor: int
    patch: int

    def __post_init__(self) -> None:
        for name, val in (("major", self.major), ("minor", self.minor), ("patch", self.patch)):
            if val < 0:
                raise InvalidFeatureDefinitionError(
                    f"FeatureVersion.{name} must be >= 0, got {val}"
                )

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def satisfies(self, constraint: str) -> bool:
        """Return ``True`` when this version satisfies a constraint string.

        Supported operators: ``>=``, ``>``, ``<=``, ``<``, ``==``, ``!=``.

        Args:
            constraint: A constraint string like ``">=1.0.0"`` or ``"==2.1.3"``.

        Returns:
            ``True`` when the constraint is satisfied.

        Raises:
            ValueError: If the constraint string is malformed.
        """
        for op in (">=", "<=", "!=", ">", "<", "=="):
            if constraint.startswith(op):
                version_str = constraint[len(op) :]
                other = FeatureVersion.from_string(version_str)
                match op:
                    case ">=":
                        return self >= other
                    case "<=":
                        return self <= other
                    case "!=":
                        return self != other
                    case ">":
                        return self > other
                    case "<":
                        return self < other
                    case "==":
                        return self == other
        raise ValueError(f"Unsupported version constraint format: {constraint!r}")

    @classmethod
    def from_string(cls, version: str) -> FeatureVersion:
        """Parse a ``major.minor.patch`` string into a ``FeatureVersion``.

        Args:
            version: A version string (e.g. ``"1.2.3"``).

        Returns:
            A new ``FeatureVersion``.

        Raises:
            InvalidFeatureDefinitionError: If the string is malformed.
        """
        parts = version.split(".")
        if len(parts) != 3:
            raise InvalidFeatureDefinitionError(
                f"FeatureVersion must be 'major.minor.patch', got {version!r}"
            )
        try:
            return cls(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, TypeError) as exc:
            raise InvalidFeatureDefinitionError(
                f"FeatureVersion components must be integers: {version!r}"
            ) from exc


@dataclass(frozen=True)
class FeatureId:
    """Structured identifier for a feature: namespace + name.

    The string representation is ``"{namespace}:{name}"``, which is unique
    across all namespaces and human-readable.

    Attributes:
        namespace: The organisational category this feature belongs to.
        name:      The feature's local name within its namespace.
            Must be non-empty and contain only lowercase letters, digits,
            and underscores (``[a-z0-9_]+``).

    Example::

        rsi = FeatureId(FeatureNamespace.TECHNICAL, "rsi_14")
        str(rsi)  # "technical:rsi_14"
        FeatureId.parse("technical:rsi_14") == rsi  # True
    """

    SEPARATOR: ClassVar[str] = ":"

    namespace: FeatureNamespace
    name: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidFeatureDefinitionError("FeatureId.name must not be empty")
        allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_")
        invalid = set(self.name) - allowed
        if invalid:
            raise InvalidFeatureDefinitionError(
                f"FeatureId.name {self.name!r} contains invalid characters: "
                f"{sorted(invalid)} (only [a-z0-9_] are allowed)"
            )

    def __str__(self) -> str:
        return f"{self.namespace.value}{self.SEPARATOR}{self.name}"

    def __repr__(self) -> str:
        return f"FeatureId({self.namespace.value!r}, {self.name!r})"

    @classmethod
    def parse(cls, feature_id_str: str) -> FeatureId:
        """Parse a ``namespace:name`` string into a ``FeatureId``.

        Args:
            feature_id_str: A string in the form ``"namespace:name"``.

        Returns:
            A new ``FeatureId``.

        Raises:
            InvalidFeatureDefinitionError: If the string is malformed or the
                namespace is not a recognised ``FeatureNamespace`` value.
        """
        if cls.SEPARATOR not in feature_id_str:
            raise InvalidFeatureDefinitionError(
                f"FeatureId string must be 'namespace:name', got {feature_id_str!r}"
            )
        ns_str, _, name = feature_id_str.partition(cls.SEPARATOR)
        try:
            namespace = FeatureNamespace(ns_str)
        except ValueError as exc:
            raise InvalidFeatureDefinitionError(f"Unknown feature namespace: {ns_str!r}") from exc
        return cls(namespace=namespace, name=name)
