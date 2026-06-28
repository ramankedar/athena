"""Unit tests for experiment artifact value objects."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from athena.experiments.artifacts import ArtifactLocation, ArtifactType, ExperimentArtifact
from athena.experiments.exceptions import InvalidExperimentError
from athena.experiments.models import RunId

NOW = datetime(2025, 1, 15, tzinfo=UTC)


class TestArtifactType:
    def test_values(self) -> None:
        assert ArtifactType.BACKTEST_RESULTS == "backtest_results"
        assert ArtifactType.PLOT == "plot"
        assert ArtifactType.CUSTOM == "custom"
        assert ArtifactType.LOG_FILE == "log_file"


class TestArtifactLocation:
    def test_valid_s3(self) -> None:
        loc = ArtifactLocation(uri="s3://bucket/path.csv", storage_backend="s3")
        assert loc.uri.startswith("s3://")

    def test_empty_uri_raises(self) -> None:
        with pytest.raises(InvalidExperimentError, match="uri"):
            ArtifactLocation(uri="", storage_backend="s3")

    def test_empty_backend_raises(self) -> None:
        with pytest.raises(InvalidExperimentError, match="storage_backend"):
            ArtifactLocation(uri="s3://bucket/path", storage_backend="")

    def test_negative_size_raises(self) -> None:
        with pytest.raises(InvalidExperimentError, match="size_bytes"):
            ArtifactLocation(uri="s3://x", storage_backend="s3", size_bytes=-1)

    def test_with_hash(self) -> None:
        loc = ArtifactLocation(
            uri="s3://x/file.parquet",
            storage_backend="s3",
            content_hash="abc123",
            size_bytes=1024,
        )
        assert loc.content_hash == "abc123"
        assert loc.size_bytes == 1024

    def test_str(self) -> None:
        loc = ArtifactLocation(uri="s3://bucket/path", storage_backend="s3")
        s = str(loc)
        assert "s3" in s


class TestExperimentArtifact:
    def _loc(self) -> ArtifactLocation:
        return ArtifactLocation(uri="s3://bucket/result.parquet", storage_backend="s3")

    def test_valid_construction(self) -> None:
        run_id = RunId.generate()
        art = ExperimentArtifact(
            artifact_id="art-001",
            run_id=run_id,
            name="backtest_results",
            artifact_type=ArtifactType.BACKTEST_RESULTS,
            location=self._loc(),
        )
        assert art.name == "backtest_results"

    def test_empty_artifact_id_raises(self) -> None:
        with pytest.raises(InvalidExperimentError, match="artifact_id"):
            ExperimentArtifact(
                artifact_id="",
                run_id=RunId.generate(),
                name="result",
                artifact_type=ArtifactType.BACKTEST_RESULTS,
                location=self._loc(),
            )

    def test_empty_name_raises(self) -> None:
        with pytest.raises(InvalidExperimentError, match="name"):
            ExperimentArtifact(
                artifact_id="art-001",
                run_id=RunId.generate(),
                name="",
                artifact_type=ArtifactType.PLOT,
                location=self._loc(),
            )

    def test_naive_created_at_raises(self) -> None:
        with pytest.raises(InvalidExperimentError, match="timezone-aware"):
            ExperimentArtifact(
                artifact_id="art-001",
                run_id=RunId.generate(),
                name="result",
                artifact_type=ArtifactType.BACKTEST_RESULTS,
                location=self._loc(),
                created_at=datetime(2025, 1, 15),
            )

    def test_create_factory(self) -> None:
        run_id = RunId.generate()
        art = ExperimentArtifact.create(
            run_id=run_id,
            name="trade_log",
            artifact_type=ArtifactType.TRADE_LOG,
            location=self._loc(),
            created_at=NOW,
        )
        assert len(art.artifact_id) == 36  # UUID format
        assert art.created_at == NOW

    def test_str(self) -> None:
        art = ExperimentArtifact.create(
            run_id=RunId.generate(),
            name="result",
            artifact_type=ArtifactType.PLOT,
            location=self._loc(),
        )
        s = str(art)
        assert "result" in s
        assert "plot" in s
