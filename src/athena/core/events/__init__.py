"""Domain events.

Domain events are immutable facts that something happened. They are the
primary mechanism for cross-engine communication. Every engine may publish
events; any other engine may subscribe to them through the event bus.

No engine calls another engine's services directly.
"""
