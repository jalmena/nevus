# Development recipes. `just --list` shows them.

set shell := ["bash", "-euo", "pipefail", "-c"]

# Install everything a checkout needs.
setup:
    cd backend && uv sync
    cd frontend && pnpm install

# Run the backend (http://127.0.0.1:8080) and the frontend dev server (http://127.0.0.1:5173) together.
dev:
    (cd backend && NEVUS_DATA_DIR=../data uv run nevus serve) & (cd frontend && pnpm dev); wait

# Lint and type-check both sides.
lint:
    cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy
    cd frontend && pnpm typecheck && pnpm lint && pnpm format:check

# Format both sides.
format:
    cd backend && uv run ruff format . && uv run ruff check --fix .
    cd frontend && pnpm format

# Run every test.
test:
    cd backend && uv run pytest
    cd frontend && pnpm test

# Build the frontend and the container image (podman or docker).
image engine="podman" version="devel":
    {{engine}} build -f deploy/Dockerfile --build-arg VERSION={{version}} -t nevus:{{version}} .

# Start the built image on http://127.0.0.1:8080 with ./data as the data directory.
run engine="podman" version="devel":
    {{engine}} run --rm -p 8080:8080 -v "$PWD/data:/data:Z" -e PUID=$(id -u) -e PGID=$(id -g) nevus:{{version}}

# Database migrations.
migrate:
    cd backend && uv run alembic upgrade head

revision message:
    cd backend && uv run alembic revision --autogenerate -m "{{message}}"
