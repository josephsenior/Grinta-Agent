ARG FORGE_BUILD_VERSION=dev
FROM node:24.3.0-bookworm-slim AS frontend-builder

WORKDIR /app

COPY tsconfig.json /tsconfig.json
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install && \
    npm install \
      @rollup/rollup-linux-x64-gnu \
      lightningcss-linux-x64-gnu \
      @tailwindcss/oxide-linux-x64-gnu \
      --save-optional

COPY frontend ./
RUN npm run build

FROM python:3.12.10-slim AS base
FROM base AS backend-builder

WORKDIR /app
ENV PYTHONPATH='/app'

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

RUN apt-get update -y \
    && apt-get install -y curl make git build-essential jq gettext \
    && python3 -m pip install poetry --break-system-packages

COPY pyproject.toml poetry.lock ./
RUN touch README.md
RUN export POETRY_CACHE_DIR && poetry install --no-root && rm -rf $POETRY_CACHE_DIR

FROM base AS forge-app

WORKDIR /app

# re-declare for this section
ARG FORGE_BUILD_VERSION

ENV RUN_AS_Forge=true
# A random number--we need this to be different from the user's UID on the host machine
ENV FORGE_USER_ID=42420
ENV SANDBOX_LOCAL_RUNTIME_URL=http://host.docker.internal
ENV USE_HOST_NETWORK=false
ENV WORKSPACE_BASE=/opt/workspace_base
ENV FORGE_BUILD_VERSION=$FORGE_BUILD_VERSION
ENV SANDBOX_USER_ID=0
ENV FILE_STORE=local
ENV FILE_STORE_PATH=/.Forge
ENV INIT_GIT_IN_EMPTY_WORKSPACE=1
RUN mkdir -p $FILE_STORE_PATH
RUN mkdir -p $WORKSPACE_BASE

# Install MCP server dependencies (Node.js for npx, uv for tools, DuckDuckGo MCP)
RUN apt-get update -y \
    && apt-get install -y curl ssh nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# Install MCP servers (separate layer for cache efficiency)
RUN pip install uv duckduckgo-mcp-server --break-system-packages \
    && uv tool install mcp-server-fetch

# Default is 1000, but OSX is often 501
RUN sed -i 's/^UID_MIN.*/UID_MIN 499/' /etc/login.defs
# Default is 60000, but we've seen up to 200000
RUN sed -i 's/^UID_MAX.*/UID_MAX 1000000/' /etc/login.defs

RUN groupadd --gid $FORGE_USER_ID Forge
RUN useradd -l -m -u $FORGE_USER_ID --gid $FORGE_USER_ID -s /bin/bash Forge && \
    usermod -aG Forge Forge
RUN chown -R Forge:Forge /app && chmod -R 770 /app
RUN chown -R Forge:Forge $WORKSPACE_BASE && chmod -R 770 $WORKSPACE_BASE
# USER Forge - Commented out: entrypoint.sh must run as root to create enduser and set permissions

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:/root/.local/bin:$PATH" \
    PYTHONPATH='/app' \
    UV_TOOL_BIN_DIR=/root/.local/bin

COPY --chown=Forge:Forge --chmod=770 --from=backend-builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY --chown=Forge:Forge --chmod=770 ./microagents ./microagents
COPY --chown=Forge:Forge --chmod=770 ./forge ./forge
COPY --chown=Forge:Forge --chmod=777 ./forge/runtime/plugins ./forge/runtime/plugins
COPY --chown=Forge:Forge pyproject.toml poetry.lock README.md MANIFEST.in LICENSE ./

# This is run as "Forge" user, and will create __pycache__ with Forge:Forge ownership
RUN python -m forge.core.download  # No-op to download assets
# Add this line to set group ownership of all files/directories not already in "app" group
# Forge:Forge -> Forge:Forge
RUN find /app \! -group Forge -exec chgrp Forge {} +

COPY --chown=Forge:Forge --chmod=770 --from=frontend-builder /app/build ./frontend/build
COPY --chown=Forge:Forge --chmod=770 ./containers/app/entrypoint.sh /app/entrypoint.sh

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

WORKDIR /app

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "forge.server.listen:app", "--host", "0.0.0.0", "--port", "3000"]
