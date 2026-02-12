# ============================================================================
# Forge — Multi-stage Docker build
# ============================================================================
# Usage:
#   docker compose up              # recommended (uses docker-compose.yml)
#   docker build -t forge .        # standalone build
#   docker run -p 3000:3000 forge  # standalone run
# ============================================================================

# --------------- Stage 1: Frontend build ---------------
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

COPY frontend/ ./
COPY tsconfig.json /app/
RUN pnpm run build

# --------------- Stage 2: Backend runtime ---------------
FROM python:3.12-slim AS runtime

# System deps for tmux (libtmux) and git
RUN apt-get update && apt-get install -y --no-install-recommends \
    tmux git curl && \
    rm -rf /var/lib/apt/lists/*

# Install Poetry
ENV POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="$POETRY_HOME/bin:$PATH"

WORKDIR /app

# Install Python dependencies (cache-friendly layer ordering)
COPY pyproject.toml poetry.toml poetry.lock* ./
RUN poetry install --no-root --no-directory --only main 2>/dev/null || \
    poetry install --no-root --no-directory

# Copy backend source
COPY backend/ ./backend/
COPY config.template.toml ./config.template.toml
COPY start_server.py ./

# Copy built frontend
COPY --from=frontend-builder /app/frontend/build ./frontend/build

# Default config: copy template if no config.toml mounted
RUN cp config.template.toml config.toml

# Runtime environment
ENV FORGE_HOST=0.0.0.0 \
    FORGE_PORT=3000 \
    WORKSPACE_BASE=/app/workspace

EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || exit 1

CMD ["python", "start_server.py"]
