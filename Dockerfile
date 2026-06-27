# ── Athena Platform — Dockerfile ──────────────────────────────────────────────
#
# Multi-stage build:
#   Stage 1 (builder): installs uv and resolves the full dependency tree
#   Stage 2 (runtime): copies only the compiled venv — no build tools in prod
#
# Build:    docker build -t athena:local .
# Run:      docker run --env-file .env athena:local

# ── Stage 1: Builder ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Pin uv version for reproducible builds. Update deliberately.
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /usr/local/bin/

WORKDIR /build

# Layer cache: copy manifests first so dependency install is cached unless
# pyproject.toml or uv.lock change.
COPY pyproject.toml uv.lock* ./

# Install only production dependencies into an isolated venv.
# --no-dev       : exclude all dependency-groups (test, lint, docs, dev)
# --no-editable  : install the package properly (not as a symlink)
# --frozen       : fail if uv.lock is out of sync with pyproject.toml
RUN uv sync --frozen --no-dev --no-editable

# Copy source after deps so source changes don't invalidate the dep layer.
COPY src/ src/

# ── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Security: run as a dedicated non-root user.
RUN groupadd --gid 1001 athena \
    && useradd --uid 1001 --gid athena --no-create-home --shell /sbin/nologin athena

WORKDIR /app

# Copy the fully resolved virtual environment from the builder stage.
COPY --from=builder /build/.venv /app/.venv

# Runtime environment variables.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1

# Drop privileges.
USER athena

# Health check verifies the package is importable (not a network probe).
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import athena; print(athena.__version__)" || exit 1

ENTRYPOINT ["python", "-m", "athena.interfaces.cli"]
CMD ["--help"]
