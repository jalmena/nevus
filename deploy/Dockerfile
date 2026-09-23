# syntax=docker/dockerfile:1.7
# neVus: one image, one container. The frontend is built with Node and served by the Python backend.

FROM node:24-alpine AS frontend
WORKDIR /src/frontend
RUN corepack enable
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.13-slim AS backend
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/src ./src
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./
RUN uv sync --frozen --no-dev

FROM python:3.13-slim
ARG VERSION=devel
LABEL org.opencontainers.image.title="neVus" \
      org.opencontainers.image.description="Self-hosted longitudinal tracking of moles and skin marks. Not a diagnostic tool." \
      org.opencontainers.image.source="https://github.com/jalmena/nevus" \
      org.opencontainers.image.licenses="AGPL-3.0-only" \
      org.opencontainers.image.version="${VERSION}"

# setpriv drops privileges in the entrypoint (util-linux); tzdata for local dates; curl for the healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends util-linux tzdata curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 nevus && useradd --uid 1000 --gid 1000 --create-home --shell /usr/sbin/nologin nevus \
    && mkdir -p /data /app/static && chown -R nevus:nevus /data /app

COPY --from=backend --chown=nevus:nevus /app /app
COPY --from=frontend --chown=nevus:nevus /src/frontend/dist /app/static
COPY --chmod=755 deploy/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

ENV PATH="/app/.venv/bin:$PATH" \
    NEVUS_DATA_DIR=/data \
    NEVUS_STATIC_DIR=/app/static \
    NEVUS_BIND=0.0.0.0 \
    NEVUS_PORT=8080 \
    PUID=1000 \
    PGID=1000 \
    TZ=UTC

WORKDIR /app
VOLUME ["/data"]
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8080/healthz >/dev/null || exit 1

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["nevus", "serve"]
