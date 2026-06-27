"""Base domain event type.

All domain events inherit from DomainEvent. The three fields on the base
class form a universal audit header — every event in the system carries
a unique identity, a precise UTC timestamp, and an optional correlation ID
that links related events within a single request or workflow.

Concrete event types are defined in each engine's core layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(frozen=True)
class DomainEvent:
    """Immutable record of something that happened in the platform.

    Fields:
        event_id:       Globally unique identifier for this specific event instance.
        occurred_at:    UTC timestamp when the event was created. Microsecond precision.
        correlation_id: Optional ID linking events that belong to the same
                        logical workflow (e.g., all events for a single order cycle).
                        Propagated from the originating signal or command.
    """

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    correlation_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.occurred_at.tzinfo is None:
            raise ValueError("DomainEvent.occurred_at must be timezone-aware (UTC expected)")
