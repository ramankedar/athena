"""Unit tests for the DomainEvent base class."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from athena.core.events.base import DomainEvent


class TestDomainEventIdentity:
    def test_each_event_has_unique_id(self) -> None:
        ids = {DomainEvent().event_id for _ in range(100)}
        assert len(ids) == 100

    def test_event_id_is_uuid(self) -> None:
        assert isinstance(DomainEvent().event_id, UUID)

    def test_custom_correlation_id(self) -> None:
        cid = UUID("12345678-1234-5678-1234-567812345678")
        event = DomainEvent(correlation_id=cid)
        assert event.correlation_id == cid

    def test_correlation_id_defaults_to_none(self) -> None:
        assert DomainEvent().correlation_id is None


class TestDomainEventTimestamp:
    def test_occurred_at_is_utc_aware(self) -> None:
        event = DomainEvent()
        assert event.occurred_at.tzinfo is not None

    def test_occurred_at_is_recent(self) -> None:
        before = datetime.now(UTC)
        event = DomainEvent()
        after = datetime.now(UTC)
        assert before <= event.occurred_at <= after

    def test_naive_timestamp_raises(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            DomainEvent(occurred_at=datetime(2025, 1, 15, 9, 15, 0))  # noqa: DTZ001,RUF100


class TestDomainEventImmutability:
    def test_is_frozen(self) -> None:
        event = DomainEvent()
        with pytest.raises((AttributeError, TypeError)):
            event.event_id = UUID("00000000-0000-0000-0000-000000000000")  # type: ignore[misc]

    def test_is_hashable(self) -> None:
        event = DomainEvent()
        assert hash(event) is not None

    def test_two_events_are_never_equal(self) -> None:
        # Each DomainEvent has a unique event_id, so two instances are never equal.
        e1 = DomainEvent()
        e2 = DomainEvent()
        assert e1 != e2
