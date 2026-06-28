"""Experiment metadata and reproducibility snapshot value objects.

``ReproducibilitySnapshot`` captures everything needed to re-run an experiment
and obtain the same result:

- Source code version (git commit, branch, dirty flag)
- Randomness control (global random seed)
- Runtime environment (Python version, installed packages hash)
- Data provenance (dataset versions used)
- Feature provenance (feature set versions used)
- Platform version

``DatasetVersion`` and ``FeatureSetVersion`` use string identifiers rather than
actual types from peer layers (``athena.market_data``, ``athena.features``).
This preserves peer-layer isolation while capturing the necessary provenance.

``ExperimentMetadata`` is the human-facing record: author, description, tags,
and when the experiment was created.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import TYPE_CHECKING

from athena.experiments.exceptions import InvalidExperimentError

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class DatasetVersion:
    """A versioned reference to a dataset used in an experiment.

    Uses string identifiers to avoid importing from the ``athena.market_data``
    peer layer. The ``source`` field records which vendor provided the data
    (important for reproducibility — the same dataset name may resolve to
    different data from different vendors).

    Attributes:
        name:         Human-readable dataset identifier
            (e.g. ``"NSE:NIFTY50-INDEX OHLCV 1D"``).
        version:      Version tag for the dataset
            (e.g. a date ``"2025-01-15"``, a hash, or ``"v1.2.0"``).
        source:       Data vendor (e.g. ``"fyers"``, ``"nse_direct"``).
            ``None`` when source is unknown or irrelevant.
        record_count: Number of records in the dataset. ``None`` when unknown.

    Raises:
        InvalidExperimentError: If ``name`` or ``version`` is empty.
    """

    name: str
    version: str
    source: str | None = None
    record_count: int | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidExperimentError("DatasetVersion.name must not be empty")
        if not self.version.strip():
            raise InvalidExperimentError("DatasetVersion.version must not be empty")

    def __str__(self) -> str:
        src = f"/{self.source}" if self.source else ""
        return f"DatasetVersion({self.name!r} @ {self.version}{src})"


@dataclass(frozen=True)
class FeatureSetVersion:
    """A versioned reference to a feature set used in an experiment.

    Uses string identifiers to avoid importing from the ``athena.features``
    peer layer. ``computation_hash`` is the SHA-256 from the feature set's
    ``FeatureDefinition.computation_hash`` fields, allowing exact structural
    identity verification.

    Attributes:
        name:             Feature set name (e.g. ``"momentum_features"``).
        version:          Semantic version string (e.g. ``"1.0.0"``).
        computation_hash: Optional structural hash for exact deduplication.
            Maps to ``FeatureDefinition.computation_hash`` from
            ``athena.features``.

    Raises:
        InvalidExperimentError: If ``name`` or ``version`` is empty.
    """

    name: str
    version: str
    computation_hash: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidExperimentError("FeatureSetVersion.name must not be empty")
        if not self.version.strip():
            raise InvalidExperimentError("FeatureSetVersion.version must not be empty")

    def __str__(self) -> str:
        return f"FeatureSetVersion({self.name!r} v{self.version})"


@dataclass(frozen=True)
class ReproducibilitySnapshot:
    """Everything needed to exactly reproduce an experiment run.

    The ``snapshot_hash`` (SHA-256 of key fields) allows quick comparison:
    two runs with the same hash used identical code, seeds, data, and features.

    Attributes:
        git_commit_hash:     Full or short SHA-1 of the git commit.
            ``None`` when not in a git repository or not captured.
        git_branch:          Branch name at the time of the run.
        git_is_dirty:        ``True`` when there were uncommitted changes.
            A dirty state means the run is NOT fully reproducible from git alone.
        random_seed:         Global random seed set before the run. ``None``
            when randomness was not controlled.
        python_version:      Python interpreter version string (e.g. ``"3.12.3"``).
        environment_hash:    SHA-256 of the installed package list
            (e.g. hash of ``pip freeze`` output). ``None`` when not captured.
        dataset_versions:    All datasets consumed by the run.
        feature_set_versions: All feature sets consumed by the run.
        athena_version:      Platform version string. ``None`` when not captured.
        custom_fields:       Extra key-value provenance data as sorted string pairs.
        snapshot_hash:       SHA-256 of the above fields (auto-computed).

    Raises:
        InvalidExperimentError: If ``python_version`` is empty.
    """

    git_commit_hash: str | None = None
    git_branch: str | None = None
    git_is_dirty: bool = False
    random_seed: int | None = None
    python_version: str = ""
    environment_hash: str | None = None
    dataset_versions: tuple[DatasetVersion, ...] = ()
    feature_set_versions: tuple[FeatureSetVersion, ...] = ()
    athena_version: str | None = None
    custom_fields: tuple[tuple[str, str], ...] = ()
    snapshot_hash: str = field(default="", init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "snapshot_hash", self._compute_hash())

    def _compute_hash(self) -> str:
        parts: list[str] = [
            self.git_commit_hash or "",
            str(self.git_is_dirty),
            str(self.random_seed or ""),
            self.python_version,
            self.environment_hash or "",
            self.athena_version or "",
        ]
        parts.extend(f"{dv.name}@{dv.version}" for dv in self.dataset_versions)
        parts.extend(
            f"{fv.name}@{fv.version}#{fv.computation_hash or ''}"
            for fv in self.feature_set_versions
        )
        for k, v in sorted(self.custom_fields):
            parts.append(f"{k}={v}")
        content = "|".join(parts).encode("utf-8")
        return hashlib.sha256(content).hexdigest()

    @property
    def is_clean(self) -> bool:
        """Return ``True`` when the git state was clean at the time of the run.

        A clean run (committed code, no dirty state) is fully reproducible from
        ``git_commit_hash`` alone.

        Returns:
            ``True`` when ``git_commit_hash`` is set and ``git_is_dirty`` is ``False``.
        """
        return self.git_commit_hash is not None and not self.git_is_dirty

    def __str__(self) -> str:
        commit = self.git_commit_hash[:8] if self.git_commit_hash else "unknown"
        dirty = " (dirty)" if self.git_is_dirty else ""
        return f"ReproducibilitySnapshot(commit={commit}{dirty}, seed={self.random_seed})"


@dataclass(frozen=True)
class ExperimentMetadata:
    """Human-facing provenance record for an experiment.

    Attributes:
        author:      Person or team that created the experiment.
        description: Detailed explanation of the experiment's purpose.
        hypothesis:  Optional scientific hypothesis being tested.
        tags:        Frozenset of discovery tags.
        created_at:  UTC timestamp when the experiment was defined.
            Must be timezone-aware when provided.
        notes:       Optional free-form research notes.

    Raises:
        InvalidExperimentError: If ``author`` or ``description`` is empty,
            or ``created_at`` is timezone-naive.
    """

    author: str
    description: str
    hypothesis: str | None = None
    tags: frozenset[str] = field(default_factory=frozenset)
    created_at: datetime | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.author.strip():
            raise InvalidExperimentError("ExperimentMetadata.author must not be empty")
        if not self.description.strip():
            raise InvalidExperimentError("ExperimentMetadata.description must not be empty")
        if self.created_at is not None and self.created_at.tzinfo is None:
            raise InvalidExperimentError(
                "ExperimentMetadata.created_at must be timezone-aware when provided"
            )

    def has_tag(self, tag: str) -> bool:
        """Return ``True`` if the tag is present.

        Args:
            tag: Tag string to check.

        Returns:
            ``True`` when the tag is in ``self.tags``.
        """
        return tag in self.tags

    def __str__(self) -> str:
        return f"ExperimentMetadata(author={self.author!r}, tags={sorted(self.tags)})"
