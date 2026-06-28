"""Unit tests for metadata and reproducibility snapshot."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from athena.experiments.exceptions import InvalidExperimentError
from athena.experiments.metadata import (
    DatasetVersion,
    ExperimentMetadata,
    FeatureSetVersion,
    ReproducibilitySnapshot,
)

NOW = datetime(2025, 1, 15, tzinfo=UTC)


class TestDatasetVersion:
    def test_valid(self) -> None:
        dv = DatasetVersion("NSE NIFTY50 OHLCV 1D", "2025-01-15", source="fyers")
        assert dv.name == "NSE NIFTY50 OHLCV 1D"
        assert dv.source == "fyers"

    def test_empty_name_raises(self) -> None:
        with pytest.raises(InvalidExperimentError, match="name"):
            DatasetVersion("", "v1.0")

    def test_empty_version_raises(self) -> None:
        with pytest.raises(InvalidExperimentError, match="version"):
            DatasetVersion("dataset", "")

    def test_str(self) -> None:
        dv = DatasetVersion("NIFTY", "2025-01-15", source="nse")
        s = str(dv)
        assert "NIFTY" in s
        assert "nse" in s


class TestFeatureSetVersion:
    def test_valid(self) -> None:
        fv = FeatureSetVersion("momentum", "1.0.0", computation_hash="abc123")
        assert fv.computation_hash == "abc123"

    def test_empty_name_raises(self) -> None:
        with pytest.raises(InvalidExperimentError, match="name"):
            FeatureSetVersion("", "1.0.0")

    def test_empty_version_raises(self) -> None:
        with pytest.raises(InvalidExperimentError, match="version"):
            FeatureSetVersion("features", "")

    def test_str(self) -> None:
        fv = FeatureSetVersion("momentum", "1.0.0")
        assert "momentum" in str(fv)


class TestReproducibilitySnapshot:
    def test_clean_snapshot(self) -> None:
        snap = ReproducibilitySnapshot(
            git_commit_hash="abc123",
            git_branch="main",
            git_is_dirty=False,
            random_seed=42,
            python_version="3.12.3",
        )
        assert snap.is_clean is True
        assert len(snap.snapshot_hash) == 64  # SHA-256

    def test_dirty_snapshot_not_clean(self) -> None:
        snap = ReproducibilitySnapshot(git_commit_hash="abc123", git_is_dirty=True)
        assert snap.is_clean is False

    def test_no_commit_not_clean(self) -> None:
        snap = ReproducibilitySnapshot()
        assert snap.is_clean is False

    def test_hash_deterministic(self) -> None:
        s1 = ReproducibilitySnapshot(git_commit_hash="abc123", random_seed=42)
        s2 = ReproducibilitySnapshot(git_commit_hash="abc123", random_seed=42)
        assert s1.snapshot_hash == s2.snapshot_hash

    def test_hash_changes_with_seed(self) -> None:
        s1 = ReproducibilitySnapshot(random_seed=42)
        s2 = ReproducibilitySnapshot(random_seed=99)
        assert s1.snapshot_hash != s2.snapshot_hash

    def test_with_dataset_versions(self) -> None:
        dv = DatasetVersion("NIFTY", "2025-01-15")
        snap = ReproducibilitySnapshot(dataset_versions=(dv,))
        assert len(snap.dataset_versions) == 1

    def test_with_feature_set_versions(self) -> None:
        fv = FeatureSetVersion("momentum", "1.0.0")
        snap = ReproducibilitySnapshot(feature_set_versions=(fv,))
        assert len(snap.feature_set_versions) == 1

    def test_hash_changes_with_dataset(self) -> None:
        dv1 = DatasetVersion("NIFTY", "v1")
        dv2 = DatasetVersion("NIFTY", "v2")
        s1 = ReproducibilitySnapshot(dataset_versions=(dv1,))
        s2 = ReproducibilitySnapshot(dataset_versions=(dv2,))
        assert s1.snapshot_hash != s2.snapshot_hash

    def test_custom_fields(self) -> None:
        snap = ReproducibilitySnapshot(custom_fields=(("key", "value"),))
        assert snap.custom_fields == (("key", "value"),)

    def test_str(self) -> None:
        snap = ReproducibilitySnapshot(git_commit_hash="abc1234def")
        s = str(snap)
        assert "abc1234" in s


class TestExperimentMetadata:
    def test_valid(self) -> None:
        m = ExperimentMetadata(
            author="Test Suite",
            description="Test experiment",
            tags=frozenset({"test"}),
        )
        assert m.author == "Test Suite"

    def test_empty_author_raises(self) -> None:
        with pytest.raises(InvalidExperimentError, match="author"):
            ExperimentMetadata(author="", description="Desc")

    def test_empty_description_raises(self) -> None:
        with pytest.raises(InvalidExperimentError, match="description"):
            ExperimentMetadata(author="Author", description="")

    def test_naive_created_at_raises(self) -> None:
        with pytest.raises(InvalidExperimentError, match="timezone-aware"):
            ExperimentMetadata(
                author="A",
                description="D",
                created_at=datetime(2025, 1, 15),
            )

    def test_has_tag_true(self) -> None:
        m = ExperimentMetadata(author="A", description="D", tags=frozenset({"momentum"}))
        assert m.has_tag("momentum") is True

    def test_has_tag_false(self) -> None:
        m = ExperimentMetadata(author="A", description="D")
        assert m.has_tag("nonexistent") is False

    def test_hypothesis_optional(self) -> None:
        m = ExperimentMetadata(
            author="A", description="D", hypothesis="RSI momentum is predictive on NSE equities"
        )
        assert m.hypothesis is not None

    def test_str(self) -> None:
        m = ExperimentMetadata(author="Author", description="D", tags=frozenset({"t1"}))
        s = str(m)
        assert "Author" in s
