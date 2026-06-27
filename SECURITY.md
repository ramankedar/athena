# Security Policy

## Supported Versions

Only the latest release on `main` receives security patches.

| Version | Supported |
|---------|-----------|
| latest (main) | Yes |
| < latest | No |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Send a detailed report to: **security@athena-platform.internal** *(replace with your actual security contact before making this repository public)*

Include in your report:
- A description of the vulnerability and its potential impact
- Steps to reproduce the issue
- The component or engine affected (Data / Research / Trading / Governance / Core)
- Any suggested mitigations if known

You will receive an acknowledgement within **48 hours** and a substantive response within **7 days**.

## Security Considerations Specific to This Platform

Athena interacts with live financial markets. The following areas are particularly sensitive:

- **Broker API credentials** — Fyers API keys grant the ability to submit real orders. Treat these as equivalent to banking credentials.
- **Order injection** — Any path that could cause an unvalidated order to reach the broker API is a critical vulnerability.
- **Audit trail integrity** — The hash-chained audit log is a regulatory requirement. Tampering with it is both a security issue and a legal matter.
- **Pre-trade risk bypass** — Any mechanism that could skip risk checks before order submission is a critical vulnerability.

## Security Controls in Place

- All secrets are `SecretStr` in configuration — they cannot appear in logs or error messages
- `detect-secrets` blocks accidental credential commits via pre-commit hook
- `pip-audit` runs on every PR to catch CVEs in the dependency tree
- CodeQL scans the codebase weekly with extended security queries
- Dependabot raises PRs for security updates automatically
- The audit log table is append-only at the database level (no UPDATE/DELETE allowed)
- The Docker runtime user is non-root (`uid=1001`)
