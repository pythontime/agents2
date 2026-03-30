# =============================================================================
# Contoso HR Agent — Multi-stage Docker build
#
# Stage 1: Install dependencies with uv (fast, cached)
# Stage 2: Slim runtime image with only what's needed
#
# The app uses pyproject.toml project_root detection (walks up to find
# pyproject.toml), so we must keep pyproject.toml in the image alongside src/.
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Build — install dependencies into a virtual environment
# ---------------------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# Copy dependency files first for layer caching
# README.md is required by pyproject.toml (readme = "README.md") for hatchling to build the package
COPY pyproject.toml uv.lock README.md ./

# Install dependencies (no dev deps) into a venv
# --no-progress avoids Unicode bullet characters that crash Azure CLI log streaming on Windows
RUN uv venv /app/.venv && uv sync --frozen --no-dev --no-install-project --no-progress

# Copy the rest of the project
COPY src/ ./src/
COPY web/ ./web/
COPY sample_knowledge/ ./sample_knowledge/

# Install the project itself (editable-like, into the venv)
RUN uv sync --frozen --no-dev --no-progress

# ---------------------------------------------------------------------------
# Stage 2: Runtime — slim image with just Python + installed packages
# ---------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

# Security: run as non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser

WORKDIR /app

# Copy the virtual environment from the builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source, static files, and knowledge docs
COPY --from=builder /app/pyproject.toml ./
COPY --from=builder /app/README.md ./
COPY --from=builder /app/src/ ./src/
COPY --from=builder /app/web/ ./web/
COPY --from=builder /app/sample_knowledge/ ./sample_knowledge/

# Create data directories (runtime-only, ephemeral in ACA)
RUN mkdir -p data/incoming data/processed data/outgoing data/chroma \
             data/knowledge data/chat_sessions \
    && chown -R appuser:appuser /app

# Put the venv's bin on PATH so entrypoints work
ENV PATH="/app/.venv/bin:$PATH"
# Ensure Python doesn't buffer stdout/stderr (important for container logs)
ENV PYTHONUNBUFFERED=1

USER appuser

# Seed ChromaDB with knowledge docs on container startup, then run the engine.
# The seed step takes ~10-20s on first boot (embeds 146 chunks via Azure).
# Subsequent container restarts re-seed (ephemeral storage in ACA).
CMD ["sh", "-c", "hr-seed && hr-engine"]

# FastAPI engine listens on 8080
EXPOSE 8080
