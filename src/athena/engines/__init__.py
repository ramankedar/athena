"""Five-engine architecture for the Athena platform.

Engines:
    data         — market data ingestion, normalisation, and storage
    research     — backtesting, signal development, and analytics
    intelligence — ML pipeline (planned, not implemented in v1)
    trading      — order management, risk, and position tracking
    governance   — audit trail, compliance, and regulatory reporting

Each engine is internally structured as:
    core/           — domain models and application services specific to this engine
    application/    — use cases that orchestrate core logic
    infrastructure/ — concrete adapters (DB, APIs, message bus)

Engine peers must never import from each other's internals.
Cross-engine communication uses domain events from athena.core.events.
"""
