# ADR-0002: Use uv as the Python Package Manager

**Status:** Accepted  
**Date:** 2026-06-27  
**Deciders:** Platform Engineering

---

## Context

A production quantitative platform requires a dependency manager that:
- Produces reproducible builds across developer machines, CI, and production containers
- Resolves complex scientific Python dependency graphs correctly (numpy, scipy, pandas)
- Supports separate dependency groups (dev, test, lint, docs) without polluting the runtime image
- Integrates with the `src/` layout and `pyproject.toml` standards
- Is fast enough that CI cold-start time is not a bottleneck

Candidates: `uv`, `Poetry`, `pip` + `pip-tools`.

## Decision

Use **uv** as the package manager for all dependency management, virtual environment management, and script execution.

| Criterion | uv | Poetry | pip + pip-tools |
|-----------|-----|--------|-----------------|
| Speed | ~100x faster than pip | ~5x faster than pip | Baseline |
| Lock file standard | PEP-compliant `uv.lock` | Proprietary `poetry.lock` | `requirements.txt` |
| Dependency groups | PEP 735 `[dependency-groups]` | `[tool.poetry.group.*]` | Manual extras |
| Python version mgmt | Built-in | Separate tool needed | Separate tool needed |
| `src/` layout | Native | Native | Manual |
| Maturity | 1.x, rapidly stabilising | Very mature (5+ years) | 30+ years |

## Consequences

**Positive:**
- CI cold-install time drops from ~2 minutes (pip) to ~10 seconds
- Lock file is PEP-compliant: readable by any PEP 517 tool, not uv-proprietary
- `[dependency-groups]` cleanly separates runtime from dev/test/lint dependencies
- uv manages Python version alongside packages (no separate pyenv required)

**Negative / Risks:**
- uv is younger than Poetry; some edge cases in complex graphs may surface
- Requires uv installation (`curl -LsSf https://astral.sh/uv/install.sh | sh`) — not pre-installed everywhere

**Mitigation:**
- `uv.lock` is committed to the repository — builds are reproducible even if uv behaviour changes
- CI uses pinned uv version (`UV_VERSION: "0.5.11"` in workflow env) to prevent unplanned upgrades
