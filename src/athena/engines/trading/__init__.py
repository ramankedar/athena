"""Trading Engine — order management, risk enforcement, and position tracking.

This is the most critical engine in the platform. Any defect here has
direct financial consequence.

Responsibilities:
    - Order Management System (OMS): full order lifecycle tracking
    - Execution Management System (EMS): order routing, retry, idempotency
    - Pre-trade risk gate: synchronous validation before any order is submitted
    - Position ledger: real-time open positions, unrealised P&L, notional exposure
    - Post-trade reconciliation: internal ledger vs. broker position report
    - Circuit breaker management: halt trading when broker connectivity degrades

Critical invariants (must never be violated):
    1. No order is submitted unless all pre-trade risk checks have passed
    2. Every submitted order has a unique idempotency_key
    3. Position ledger is reconciled against broker state at every checkpoint
    4. The BrokerPort is the ONLY code path authorised to call the broker API
"""
