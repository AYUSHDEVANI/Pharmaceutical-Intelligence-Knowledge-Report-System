# ===========================================================
# OpenFDA MCP Server — Dockerfile
# ===========================================================
# Multi-stage build on python:3.12-slim.
# Runs as non-root user with healthcheck.
#
#   docker build -t pikrs-openfda .
#   docker run -p 8103:8103 pikrs-openfda
# ===========================================================

# ---- Stage 1: dependencies ----
FROM python:3.12-slim AS builder

WORKDIR /build

COPY clinicaltrials/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Stage 2: runtime ----
FROM python:3.12-slim

# Security: run as non-root user
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --create-home appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy shared library
COPY shared /app/shared

# Copy application code
COPY clinicaltrials/app/ /app/app/

# Env defaults (can be overridden at runtime)
ENV HOST=0.0.0.0 \
    PORT=8102 \
    LOG_LEVEL=INFO \
    PYTHONUNBUFFERED=1

# Switch to non-root user
USER appuser

EXPOSE 8103

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8103/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8103"]
