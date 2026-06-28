"""Data quality representation for market data.

``DataQuality`` records what is known about the reliability of a piece of
market data. Quality is expressed as two complementary views:

1. A ``frozenset[QualityFlag]`` capturing specific known issues (or
   confirming completeness). Multiple flags can apply simultaneously —
   a bar can be both ``GAP_FILLED`` (synthetic) and ``SUSPICIOUS_PRICE``
   (the synthetic price looks implausible after the fact).

2. A ``float`` confidence score (0.0-1.0) for programmatic filtering.
   ``1.0`` means the data is fully reliable; ``0.0`` means it should not
   be used. The score allows callers to set thresholds without caring about
   the specific flag combination.

Design rationale — why not a single enum quality level?
    A ``SUSPECT`` enum collapses "volume spike" and "gap-filled" into one
    bucket. A research query might want to include gap-filled bars but exclude
    suspicious prices. ``frozenset[QualityFlag]`` supports precise filtering.

Factory classmethods (``good()``, ``gap_filled()``, ``synthetic()``) provide
the common cases without boilerplate.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class QualityFlag(StrEnum):
    """A specific observation about a piece of market data's quality.

    Attributes:
        COMPLETE:          Data is fully formed with no known issues.
        GAP_FILLED:        One or more values were filled synthetically
            (e.g. forward-filled OHLCV for a period with no trades).
        SYNTHETIC:         The entire bar or tick was generated without
            underlying market activity.
        SUSPICIOUS_VOLUME: Traded volume deviates significantly from expected
            (e.g. zero volume during normal hours, or an extreme spike).
        SUSPICIOUS_PRICE:  Price deviates significantly from expected range
            (e.g. obvious data error from vendor).
        STALE_TIMESTAMP:   The timestamp does not align with the expected
            bar frequency (e.g. a 1-minute bar whose open_time is 09:17
            when bars should open on the minute).
        DUPLICATE:         Another record exists for the same time period.
            The record with this flag is the one that should be discarded.
        CROSSED_MARKET:    For quotes: bid >= ask (invalid market state).
        ZERO_VOLUME:       Volume is exactly zero (valid for some instruments
            during low-activity periods, but suspicious for liquid markets).
        ADJUSTED:          Prices have been adjusted for corporate actions.
    """

    COMPLETE = "complete"
    GAP_FILLED = "gap_filled"
    SYNTHETIC = "synthetic"
    SUSPICIOUS_VOLUME = "suspicious_volume"
    SUSPICIOUS_PRICE = "suspicious_price"
    STALE_TIMESTAMP = "stale_timestamp"
    DUPLICATE = "duplicate"
    CROSSED_MARKET = "crossed_market"
    ZERO_VOLUME = "zero_volume"
    ADJUSTED = "adjusted"


_PROBLEMATIC_FLAGS: frozenset[QualityFlag] = frozenset(
    {
        QualityFlag.SUSPICIOUS_VOLUME,
        QualityFlag.SUSPICIOUS_PRICE,
        QualityFlag.STALE_TIMESTAMP,
        QualityFlag.DUPLICATE,
        QualityFlag.CROSSED_MARKET,
    }
)


@dataclass(frozen=True)
class DataQuality:
    """Quality record for a single piece of market data.

    Attributes:
        flags:      Frozenset of quality observations. The combination of
            ``COMPLETE`` with no other flags is the ideal state.
        confidence: Scalar reliability score from 0.0 (unusable) to 1.0
            (fully reliable). For callers that need simple threshold filtering
            without inspecting individual flags.

    Raises:
        ValueError: If ``confidence`` is not in [0.0, 1.0].

    Example::

        # Good data
        q = DataQuality.good()
        assert q.is_reliable
        assert not q.has_issues

        # Gap-filled data, still usable with caveats
        q = DataQuality.gap_filled()
        assert q.flags == frozenset({QualityFlag.GAP_FILLED})
    """

    flags: frozenset[QualityFlag]
    confidence: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"DataQuality.confidence must be in [0.0, 1.0], got {self.confidence}")

    # ── Factory classmethods ──────────────────────────────────────────────────

    @classmethod
    def good(cls) -> DataQuality:
        """Return a ``DataQuality`` indicating complete, reliable data.

        Returns:
            A ``DataQuality`` with ``{COMPLETE}`` flags and confidence 1.0.
        """
        return cls(flags=frozenset({QualityFlag.COMPLETE}), confidence=1.0)

    @classmethod
    def gap_filled(cls) -> DataQuality:
        """Return a ``DataQuality`` indicating a synthetically filled gap.

        Returns:
            A ``DataQuality`` with ``{GAP_FILLED}`` flags and confidence 0.5.
        """
        return cls(flags=frozenset({QualityFlag.GAP_FILLED}), confidence=0.5)

    @classmethod
    def synthetic(cls) -> DataQuality:
        """Return a ``DataQuality`` indicating fully synthetic data.

        Returns:
            A ``DataQuality`` with ``{SYNTHETIC}`` flags and confidence 0.3.
        """
        return cls(flags=frozenset({QualityFlag.SYNTHETIC}), confidence=0.3)

    @classmethod
    def adjusted(cls) -> DataQuality:
        """Return a ``DataQuality`` indicating data adjusted for corporate actions.

        Returns:
            A ``DataQuality`` with ``{COMPLETE, ADJUSTED}`` flags and confidence 1.0.
        """
        return cls(
            flags=frozenset({QualityFlag.COMPLETE, QualityFlag.ADJUSTED}),
            confidence=1.0,
        )

    @classmethod
    def with_flags(cls, *flags: QualityFlag, confidence: float = 0.8) -> DataQuality:
        """Construct a ``DataQuality`` with arbitrary flags.

        Args:
            *flags:     Quality flags to include.
            confidence: Reliability score. Defaults to 0.8.

        Returns:
            A new ``DataQuality`` with the specified flags and confidence.
        """
        return cls(flags=frozenset(flags), confidence=confidence)

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def is_complete(self) -> bool:
        """Return ``True`` when ``COMPLETE`` is the only flag.

        Returns:
            ``True`` when flags equals ``{QualityFlag.COMPLETE}`` or contains
            ``COMPLETE`` alongside ``ADJUSTED`` (adjusted complete data).
        """
        return QualityFlag.COMPLETE in self.flags and not (self.flags & _PROBLEMATIC_FLAGS)

    @property
    def is_reliable(self) -> bool:
        """Return ``True`` when data is suitable for production use.

        Returns:
            ``True`` when confidence >= 0.8 and no problematic flags are set.
        """
        return self.confidence >= 0.8 and not (self.flags & _PROBLEMATIC_FLAGS)

    @property
    def has_issues(self) -> bool:
        """Return ``True`` when any problematic quality flag is present.

        Returns:
            ``True`` when at least one of ``SUSPICIOUS_VOLUME``,
            ``SUSPICIOUS_PRICE``, ``STALE_TIMESTAMP``, ``DUPLICATE``,
            or ``CROSSED_MARKET`` is in ``self.flags``.
        """
        return bool(self.flags & _PROBLEMATIC_FLAGS)

    @property
    def is_synthetic(self) -> bool:
        """Return ``True`` when the data is entirely synthetic.

        Returns:
            ``True`` when ``SYNTHETIC`` is in ``self.flags``.
        """
        return QualityFlag.SYNTHETIC in self.flags

    @property
    def is_adjusted(self) -> bool:
        """Return ``True`` when the data has been adjusted for corporate actions.

        Returns:
            ``True`` when ``ADJUSTED`` is in ``self.flags``.
        """
        return QualityFlag.ADJUSTED in self.flags

    def merge(self, other: DataQuality) -> DataQuality:
        """Combine two ``DataQuality`` records into a single conservative result.

        Takes the union of flags and the minimum confidence score.

        Args:
            other: The other quality record to merge.

        Returns:
            A new ``DataQuality`` with combined flags and minimum confidence.
        """
        return DataQuality(
            flags=self.flags | other.flags,
            confidence=min(self.confidence, other.confidence),
        )

    def __str__(self) -> str:
        flag_str = ", ".join(sorted(f.value for f in self.flags))
        return f"DataQuality(confidence={self.confidence:.2f}, flags=[{flag_str}])"
