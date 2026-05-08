# ── Stage 1: Build Vue 3 frontend ────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

COPY frontend/ ./
RUN npm run build
# Vite outputs to /app/backend/static (per vite.config.js outDir)


# ── Stage 2: Python runtime ───────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# System deps: gcc for psycopg2/sentence-transformers, libpq-dev for PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements-backend.txt ./
RUN pip install --no-cache-dir -r requirements-backend.txt

# Application source
COPY sql_agent/ ./sql_agent/
COPY config/    ./config/
COPY backend/   ./backend/

# Copy built Vue SPA from stage 1
COPY --from=frontend-builder /app/backend/static ./backend/static/

# Runtime environment
ENV SQL_AGENT_CONFIG_DIR=/app/config
ENV PYTHONPATH=/app

EXPOSE 8000

# Increase keep-alive timeout for long-running SSE streams (multi-agent can take 60-120s)
CMD ["uvicorn", "backend.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--timeout-keep-alive", "300"]
