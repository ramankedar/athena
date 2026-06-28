"""Feature provenance and metadata value objects.

``FeatureMetadata`` carries the human-facing and research-governance
information about a feature: who authored it, what it does, which papers
inspired it, and whether it is deterministic.

``ReproducibilityInfo`` captures the information needed to exactly reproduce
a feature's output values in a future research run. A feature is fully
reproducible if it is deterministic (no random state) and its computation
hash matches.

Design note:
    Metadata is intentionally separate from the structural definition
    (``FeatureDefinition``). The ``description`` can change without affecting
    the ``computation_hash`` — the hash is derived from structural fields only.
    This means editing a description does not break existing research artefacts
    that reference the feature by hash.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from athena.features.exceptions import InvalidFeatureDefinitionError

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class ReproducibilityInfo:
    """Information required to reproduce a feature's output.

    Attributes:
        is_deterministic: ``True`` when the feature always produces the same
            output given the same inputs. A feature that uses a random number
            generator without a fixed seed is NOT deterministic.
        random_seed:      The fixed random seed used, when applicable.
            ``None`` for deterministic features or those with no random state.
        notes:            Optional human-readable notes about reproducibility
            caveats (e.g. "Results depend on the data provider's holiday
            calendar").

    Example::

        repro = ReproducibilityInfo(
            is_deterministic=True,
            notes="Fully deterministic given identical OHLCV input.",
        )
    """

    is_deterministic: bool
    random_seed: int | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if self.random_seed is not None and self.is_deterministic and self.random_seed < 0:
            raise InvalidFeatureDefinitionError(
                "ReproducibilityInfo.random_seed must be >= 0 when provided"
            )


@dataclass(frozen=True)
class PaperReference:
    """A reference to an academic paper or research source.

    Attributes:
        title:   Title of the paper or article.
        authors: Tuple of author names.
        year:    Publication year.
        url:     Optional URL to the paper (DOI link, arXiv, etc.).
    """

    title: str
    authors: tuple[str, ...]
    year: int
    url: str | None = None

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise InvalidFeatureDefinitionError("PaperReference.title must not be empty")
        if self.year < 1900 or self.year > 2200:
            raise InvalidFeatureDefinitionError(f"PaperReference.year {self.year} is implausible")

    def __str__(self) -> str:
        author_str = " & ".join(self.authors) if self.authors else "Unknown"
        return f"{author_str} ({self.year}). {self.title}"


@dataclass(frozen=True)
class FeatureMetadata:
    """Human-facing provenance record for a feature definition.

    Attributes:
        description:      Human-readable explanation of what the feature
            measures and how it should be interpreted.
        author:           Name or team that created the feature.
        created_at:       UTC timestamp when the feature was first defined.
            ``None`` for legacy features with unknown creation dates.
        tags:             Frozenset of free-form string tags for discovery
            (e.g. ``{"momentum", "short_term", "indian_markets"}``).
        reproducibility:  Reproducibility information.
        paper_references: Academic papers that inspired or document this feature.
        notes:            Optional long-form research notes. May include
            backtest observations, known limitations, or usage guidance.

    Example::

        metadata = FeatureMetadata(
            description="14-period Relative Strength Index on daily close prices.",
            author="Platform Engineering",
            tags=frozenset({"momentum", "oscillator"}),
            reproducibility=ReproducibilityInfo(is_deterministic=True),
        )
    """

    description: str
    author: str
    created_at: datetime | None = None
    tags: frozenset[str] = field(default_factory=frozenset)
    reproducibility: ReproducibilityInfo = field(
        default_factory=lambda: ReproducibilityInfo(is_deterministic=True)
    )
    paper_references: tuple[PaperReference, ...] = ()
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.description.strip():
            raise InvalidFeatureDefinitionError("FeatureMetadata.description must not be empty")
        if not self.author.strip():
            raise InvalidFeatureDefinitionError("FeatureMetadata.author must not be empty")
        if self.created_at is not None and self.created_at.tzinfo is None:
            raise InvalidFeatureDefinitionError(
                "FeatureMetadata.created_at must be timezone-aware when provided"
            )

    def has_tag(self, tag: str) -> bool:
        """Return ``True`` if the given tag is present in the metadata.

        Args:
            tag: The tag string to check.

        Returns:
            ``True`` when ``tag`` is in ``self.tags``.
        """
        return tag in self.tags

    def __str__(self) -> str:
        return f"FeatureMetadata(author={self.author!r}, tags={sorted(self.tags)})"
