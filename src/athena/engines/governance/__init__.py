"""Governance Engine — audit trail, compliance, and regulatory reporting.

Critical property: this engine NEVER blocks execution. It consumes domain
events asynchronously. If the audit log write is slow, orders still flow.
If the reporting pipeline fails, trading continues. The governance engine
is a shadow of the system — it records everything but gates nothing.

The exception: risk limits are enforced synchronously by the Trading Engine's
pre-trade gate. The Governance Engine validates them post-trade and alerts.

Responsibilities:
    - Immutable, hash-chained audit log (every domain event from every engine)
    - SEBI-required trade logs and margin utilisation reports
    - Trade surveillance: wash trade detection, unusual activity patterns
    - Risk limit ledger: track current utilisation of all configured limits
    - Regulatory report generation on schedule (EOD, monthly)

Audit log integrity:
    Each AuditEntry contains the SHA-256 hash of the previous entry.
    Any retroactive modification is detectable. The audit table is
    append-only at the database level (no UPDATE/DELETE permitted).
"""
