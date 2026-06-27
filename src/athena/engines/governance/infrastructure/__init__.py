"""Governance Engine — infrastructure layer.

Adapters:
    TimescaleAuditLog       — append-only audit log in TimescaleDB
    ReportGenerator         — renders SEBI-format CSV/PDF trade reports
    AlertDispatcher         — sends compliance alerts (email, Slack, PagerDuty)
"""
