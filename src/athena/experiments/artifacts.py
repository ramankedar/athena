"""Experiment artifact value objects.

An ``ExperimentArtifact`` is a file or dataset produced by an experiment run.
Examples: a backtest results CSV, a performance attribution plot, a trade log,
a configuration file, a serialised signal series.

``ArtifactLocation`` captures WHERE an artifact is stored (URI, backend, size,
content hash). The ``content_hash`` enables integrity verification — confirm the
artifact has not been modified since it was recorded.

``ArtifactType`` provides a controlled vocabulary so that artifact consumers
can filter by type without parsing free-form names.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import uuid4

from athena.experiments.exceptions import InvalidExperimentError

if TYPE_CHECKING:
    from datetime import datetime

    from athena.experiments.models import RunId


class ArtifactType(StrEnum):
    """Classification of an experiment artifact.

    Attributes:
        BACKTEST_RESULTS:    Detailed trade-level backtest output.
        PERFORMANCE_REPORT:  Aggregated performance metrics and tear sheet.
        TRADE_LOG:           Chronological log of all trades.
        SIGNAL_SERIES:       Time series of computed signals.
        PLOT:                Chart or visualisation (PNG, HTML, SVG).
        CONFIGURATION:       Experiment configuration file (JSON, YAML, TOML).
        LOG_FILE:            Execution log file.
        PARAMETER_IMPORTANCE: Feature or parameter importance ranking.
        CUSTOM:              Any artifact not covered by the above types.
    """

    BACKTEST_RESULTS = "backtest_results"
    PERFORMANCE_REPORT = "performance_report"
    TRADE_LOG = "trade_log"
    SIGNAL_SERIES = "signal_series"
    PLOT = "plot"
    CONFIGURATION = "configuration"
    LOG_FILE = "log_file"
    PARAMETER_IMPORTANCE = "parameter_importance"
    CUSTOM = "custom"


@dataclass(frozen=True)
class ArtifactLocation:
    """Physical location of an experiment artifact.

    Attributes:
        uri:              Full resource identifier
            (e.g. ``"s3://bucket/exp/run123/results.parquet"`` or
            ``"file:///local/path/results.csv"``).
        storage_backend:  Short identifier for the storage system
            (e.g. ``"s3"``, ``"gcs"``, ``"local"``, ``"azureblob"``).
        content_hash:     SHA-256 hash of the artifact's content for
            integrity verification. ``None`` when not computed.
        size_bytes:       File size in bytes. ``None`` when not known.

    Raises:
        InvalidExperimentError: If ``uri`` or ``storage_backend`` is empty.
    """

    uri: str
    storage_backend: str
    content_hash: str | None = None
    size_bytes: int | None = None

    def __post_init__(self) -> None:
        if not self.uri.strip():
            raise InvalidExperimentError("ArtifactLocation.uri must not be empty")
        if not self.storage_backend.strip():
            raise InvalidExperimentError("ArtifactLocation.storage_backend must not be empty")
        if self.size_bytes is not None and self.size_bytes < 0:
            raise InvalidExperimentError(
                f"ArtifactLocation.size_bytes must be >= 0, got {self.size_bytes}"
            )

    def __str__(self) -> str:
        return f"ArtifactLocation({self.storage_backend}:{self.uri})"


@dataclass(frozen=True)
class ExperimentArtifact:
    """An immutable record of a file or dataset produced by a run.

    Attributes:
        artifact_id:   Unique artifact identifier (UUID string).
        run_id:        The run that produced this artifact.
        name:          Human-readable name (e.g. ``"backtest_results_2025_01"``).
        artifact_type: Classification of the artifact.
        location:      Where the artifact is stored.
        description:   Optional explanation of the artifact's contents.
        created_at:    UTC timestamp when the artifact was recorded.
            ``None`` for legacy artifacts with no creation timestamp.
        tags:          Optional tags for discovery and filtering.

    Raises:
        InvalidExperimentError: If ``artifact_id`` or ``name`` is empty.
    """

    artifact_id: str
    run_id: RunId
    name: str
    artifact_type: ArtifactType
    location: ArtifactLocation
    description: str | None = None
    created_at: datetime | None = None
    tags: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.artifact_id.strip():
            raise InvalidExperimentError("ExperimentArtifact.artifact_id must not be empty")
        if not self.name.strip():
            raise InvalidExperimentError("ExperimentArtifact.name must not be empty")
        if self.created_at is not None and self.created_at.tzinfo is None:
            raise InvalidExperimentError(
                "ExperimentArtifact.created_at must be timezone-aware when provided"
            )

    @classmethod
    def create(
        cls,
        run_id: RunId,
        name: str,
        artifact_type: ArtifactType,
        location: ArtifactLocation,
        description: str | None = None,
        created_at: datetime | None = None,
        tags: frozenset[str] | None = None,
    ) -> ExperimentArtifact:
        """Create a new artifact with an auto-generated UUID identifier.

        Args:
            run_id:        The run that produced this artifact.
            name:          Human-readable artifact name.
            artifact_type: Type classification.
            location:      Storage location.
            description:   Optional description.
            created_at:    Optional UTC creation timestamp.
            tags:          Optional tags.

        Returns:
            A new ``ExperimentArtifact`` with a generated UUID.
        """
        return cls(
            artifact_id=str(uuid4()),
            run_id=run_id,
            name=name,
            artifact_type=artifact_type,
            location=location,
            description=description,
            created_at=created_at,
            tags=tags or frozenset(),
        )

    def __str__(self) -> str:
        return (
            f"ExperimentArtifact({self.name!r} [{self.artifact_type.value}] "
            f"@ {self.location.storage_backend})"
        )
