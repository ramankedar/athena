"""Core shared kernel — zero external dependencies.

This package contains:
    domain/   — immutable value objects and aggregates (Instrument, Tick, OHLCV)
    ports/    — typed Protocol interfaces for infrastructure adapters
    events/   — domain event base types

The dependency rule: nothing in athena.core may import from any other
athena.* subpackage. This is enforced by import-linter in CI.
"""
