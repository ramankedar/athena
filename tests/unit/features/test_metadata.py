"""Unit tests for feature metadata value objects."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime

import pytest

from athena.features.exceptions import InvalidFeatureDefinitionError
from athena.features.metadata import FeatureMetadata, PaperReference, ReproducibilityInfo

NOW = datetime(2025, 1, 15, 10, 0, tzinfo=UTC)


class TestReproducibilityInfo:
    def test_deterministic(self) -> None:
        r = ReproducibilityInfo(is_deterministic=True)
        assert r.is_deterministic is True
        assert r.random_seed is None

    def test_with_seed(self) -> None:
        r = ReproducibilityInfo(is_deterministic=True, random_seed=42)
        assert r.random_seed == 42

    def test_negative_seed_with_deterministic_raises(self) -> None:
        with pytest.raises(InvalidFeatureDefinitionError, match="random_seed"):
            ReproducibilityInfo(is_deterministic=True, random_seed=-1)

    def test_is_frozen(self) -> None:
        r = ReproducibilityInfo(is_deterministic=True)
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            r.is_deterministic = False  # type: ignore[misc]


class TestPaperReference:
    def test_valid_construction(self) -> None:
        ref = PaperReference(
            title="RSI: A new momentum oscillator",
            authors=("J. Welles Wilder",),
            year=1978,
        )
        assert ref.year == 1978

    def test_empty_title_raises(self) -> None:
        with pytest.raises(InvalidFeatureDefinitionError, match="title"):
            PaperReference(title="", authors=("Author",), year=2000)

    def test_implausible_year_raises(self) -> None:
        with pytest.raises(InvalidFeatureDefinitionError, match="implausible"):
            PaperReference(title="Test", authors=(), year=1850)

    def test_str(self) -> None:
        ref = PaperReference(
            title="RSI",
            authors=("Wilder",),
            year=1978,
            url="https://example.com",
        )
        s = str(ref)
        assert "Wilder" in s
        assert "1978" in s
        assert "RSI" in s

    def test_with_url(self) -> None:
        ref = PaperReference(
            title="Test Paper",
            authors=("A. Author",),
            year=2020,
            url="https://arxiv.org/abs/1234",
        )
        assert ref.url is not None

    def test_no_authors(self) -> None:
        ref = PaperReference(title="Test", authors=(), year=2020)
        assert "Unknown" in str(ref)


class TestFeatureMetadata:
    def test_valid_construction(self, basic_metadata: FeatureMetadata) -> None:
        assert basic_metadata.author == "Test Suite"
        assert "test" in basic_metadata.tags

    def test_empty_description_raises(self) -> None:
        with pytest.raises(InvalidFeatureDefinitionError, match="description"):
            FeatureMetadata(description="", author="Author")

    def test_empty_author_raises(self) -> None:
        with pytest.raises(InvalidFeatureDefinitionError, match="author"):
            FeatureMetadata(description="Desc", author="")

    def test_naive_created_at_raises(self) -> None:
        with pytest.raises(InvalidFeatureDefinitionError, match="timezone-aware"):
            FeatureMetadata(
                description="Desc",
                author="Author",
                created_at=datetime(2025, 1, 15),
            )

    def test_utc_created_at_valid(self) -> None:
        m = FeatureMetadata(
            description="Desc",
            author="Author",
            created_at=NOW,
        )
        assert m.created_at == NOW

    def test_has_tag_true(self) -> None:
        m = FeatureMetadata(
            description="Desc",
            author="Author",
            tags=frozenset({"momentum", "oscillator"}),
        )
        assert m.has_tag("momentum") is True

    def test_has_tag_false(self) -> None:
        m = FeatureMetadata(description="Desc", author="Author")
        assert m.has_tag("nonexistent") is False

    def test_paper_references(self) -> None:
        ref = PaperReference("Test", ("Author",), 2020)
        m = FeatureMetadata(
            description="Desc",
            author="Author",
            paper_references=(ref,),
        )
        assert len(m.paper_references) == 1

    def test_is_frozen(self) -> None:
        m = FeatureMetadata(description="Desc", author="Author")
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            m.author = "Other"  # type: ignore[misc]

    def test_str(self) -> None:
        m = FeatureMetadata(
            description="Desc",
            author="Author",
            tags=frozenset({"tag1"}),
        )
        s = str(m)
        assert "Author" in s
