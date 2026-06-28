"""Unit tests for DataQuality and QualityFlag."""

from __future__ import annotations

import pytest

from athena.market_data.quality import DataQuality, QualityFlag


class TestQualityFlag:
    def test_values(self) -> None:
        assert QualityFlag.COMPLETE == "complete"
        assert QualityFlag.GAP_FILLED == "gap_filled"
        assert QualityFlag.SYNTHETIC == "synthetic"
        assert QualityFlag.SUSPICIOUS_VOLUME == "suspicious_volume"
        assert QualityFlag.SUSPICIOUS_PRICE == "suspicious_price"
        assert QualityFlag.STALE_TIMESTAMP == "stale_timestamp"
        assert QualityFlag.DUPLICATE == "duplicate"
        assert QualityFlag.CROSSED_MARKET == "crossed_market"
        assert QualityFlag.ZERO_VOLUME == "zero_volume"
        assert QualityFlag.ADJUSTED == "adjusted"


class TestDataQuality:
    def test_invalid_confidence_below_zero(self) -> None:
        with pytest.raises(ValueError, match="confidence"):
            DataQuality(flags=frozenset(), confidence=-0.1)

    def test_invalid_confidence_above_one(self) -> None:
        with pytest.raises(ValueError, match="confidence"):
            DataQuality(flags=frozenset(), confidence=1.1)

    def test_boundary_confidence_zero(self) -> None:
        q = DataQuality(flags=frozenset(), confidence=0.0)
        assert q.confidence == 0.0

    def test_boundary_confidence_one(self) -> None:
        q = DataQuality(flags=frozenset(), confidence=1.0)
        assert q.confidence == 1.0

    def test_good_factory(self) -> None:
        q = DataQuality.good()
        assert q.confidence == 1.0
        assert QualityFlag.COMPLETE in q.flags
        assert q.is_complete is True
        assert q.is_reliable is True
        assert q.has_issues is False

    def test_gap_filled_factory(self) -> None:
        q = DataQuality.gap_filled()
        assert QualityFlag.GAP_FILLED in q.flags
        assert q.confidence == 0.5

    def test_synthetic_factory(self) -> None:
        q = DataQuality.synthetic()
        assert QualityFlag.SYNTHETIC in q.flags
        assert q.confidence == 0.3
        assert q.is_synthetic is True

    def test_adjusted_factory(self) -> None:
        q = DataQuality.adjusted()
        assert QualityFlag.ADJUSTED in q.flags
        assert q.is_adjusted is True
        assert q.confidence == 1.0

    def test_with_flags_factory(self) -> None:
        q = DataQuality.with_flags(QualityFlag.SUSPICIOUS_VOLUME, confidence=0.4)
        assert QualityFlag.SUSPICIOUS_VOLUME in q.flags
        assert q.confidence == 0.4

    def test_has_issues_suspicious_price(self) -> None:
        q = DataQuality.with_flags(QualityFlag.SUSPICIOUS_PRICE)
        assert q.has_issues is True

    def test_has_issues_duplicate(self) -> None:
        q = DataQuality.with_flags(QualityFlag.DUPLICATE)
        assert q.has_issues is True

    def test_has_issues_crossed_market(self) -> None:
        q = DataQuality.with_flags(QualityFlag.CROSSED_MARKET)
        assert q.has_issues is True

    def test_is_complete_with_adjusted_flag(self) -> None:
        q = DataQuality(
            flags=frozenset({QualityFlag.COMPLETE, QualityFlag.ADJUSTED}),
            confidence=1.0,
        )
        assert q.is_complete is True

    def test_is_complete_false_with_suspicious(self) -> None:
        q = DataQuality(
            flags=frozenset({QualityFlag.COMPLETE, QualityFlag.SUSPICIOUS_PRICE}),
            confidence=0.9,
        )
        assert q.is_complete is False

    def test_is_reliable_high_confidence_no_issues(self) -> None:
        q = DataQuality(flags=frozenset({QualityFlag.COMPLETE}), confidence=0.9)
        assert q.is_reliable is True

    def test_is_reliable_low_confidence(self) -> None:
        q = DataQuality(flags=frozenset({QualityFlag.COMPLETE}), confidence=0.7)
        assert q.is_reliable is False

    def test_merge_combines_flags(self) -> None:
        q1 = DataQuality(flags=frozenset({QualityFlag.GAP_FILLED}), confidence=0.5)
        q2 = DataQuality(flags=frozenset({QualityFlag.SUSPICIOUS_VOLUME}), confidence=0.7)
        merged = q1.merge(q2)
        assert QualityFlag.GAP_FILLED in merged.flags
        assert QualityFlag.SUSPICIOUS_VOLUME in merged.flags
        assert merged.confidence == 0.5  # min of 0.5 and 0.7

    def test_str_representation(self) -> None:
        q = DataQuality.good()
        s = str(q)
        assert "1.00" in s
        assert "complete" in s
