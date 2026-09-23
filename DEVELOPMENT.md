# Developing neVus

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (installs Python 3.13 for you), Node 24 (for example through [fnm](https://github.com/Schniz/fnm)) with pnpm enabled by `corepack enable`, and podman or docker for the image. [just](https://github.com/casey/just) is optional but the recipes below assume it.
- No system-wide installs are needed; everything lives in `backend/.venv` and `frontend/node_modules`.

## Layout

```text
backend/    FastAPI application (uv project, src layout), Alembic migrations, tests
frontend/   React + TypeScript progressive web application (pnpm, Vite), design tokens, translations
deploy/     Dockerfile, entrypoint, compose file with the CasaOS metadata
docs/       Audits, research, decision records, design brief and the brand identity
```

The architecture and its reasons are in [`ARCHITECTURE.md`](ARCHITECTURE.md) and [`docs/adr/`](docs/adr/README.md).

## Everyday commands

```sh
just setup        # install dependencies on both sides
just dev          # backend on :8080 and the Vite dev server on :5173 (proxying /api and /healthz)
just lint         # ruff, mypy, tsc, eslint, stylelint, prettier
just test         # pytest and vitest
just image        # build the container image with podman (pass engine="docker" to use docker)
just run          # start the image with ./data as the data directory
```

Without `just`: run the commands in `justfile` by hand; they are one line each.

## Configuration

Every setting is an environment variable prefixed with `NEVUS_` (see `backend/src/nevus/config.py`). A checkout needs none: data goes to `./data`, SQLite is used, and the server answers to private addresses, `localhost` and `.local` names. Set `NEVUS_ALLOWED_HOSTS` to answer to a public hostname behind a reverse proxy, and `NEVUS_DATABASE_URL` to use an external PostgreSQL.

## Tests

- Backend: `pytest` against a temporary data directory. Continuous integration runs the same suite twice, on SQLite and on PostgreSQL, plus `alembic upgrade head` and `alembic check` on both engines.
- Frontend: vitest with Testing Library in jsdom.
- Image: the CI builds the image, asserts the size budget, starts it, checks `/healthz` and that `/` answers 200 without a session, verifies the process runs as uid 1000 and that `PUID`/`PGID` are honoured on a root-owned bind mount.

## Conventions

- English everywhere; see [`CONTRIBUTING.md`](CONTRIBUTING.md).
- GitFlow: `feature/*` from `develop`, pull request back, linear history; releases on `release/*` into `main` (see [ADR-0009](docs/adr/0009-release-engineering.md)).
- Conventional Commits with a DCO sign-off (`git commit -s`); `pre-commit install --hook-type commit-msg --hook-type pre-commit` enables the local checks.
- Colours only through tokens (`frontend/src/design-system/tokens/tokens.css`); stylelint rejects raw colours elsewhere.
- Dependency updates arrive through Renovate pull requests against `develop` (the Renovate GitHub app must be enabled on the repository).

## Migrations

`just revision "add lesions"` autogenerates a migration from the models; review it (SQLite needs batch mode, which the environment enables automatically), then `just migrate`. Every migration must apply cleanly on both engines; the CI enforces it.
