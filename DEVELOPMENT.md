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

A fresh instance has no accounts: the first person to open it claims it and becomes the administrator (`POST /api/auth/claim`). Alternatively set `NEVUS_ADMIN_USER` and `NEVUS_ADMIN_PASSWORD` before the first start; they are read at start-up only, and setting them again resets that account's password, which is the documented way back in after a forgotten one. Pending database migrations are applied at start-up (`NEVUS_AUTO_MIGRATE=false` disables that).

## Tests

- Backend: `pytest` against a temporary data directory. Continuous integration runs the same suite twice, on SQLite and on PostgreSQL, plus `alembic upgrade head` and `alembic check` on both engines.
- Frontend: vitest with Testing Library in jsdom.
- Image: the CI builds the image, asserts the size budget, starts it, checks `/healthz` and that `/` answers 200 without a session, verifies the process runs as uid 1000 and that `PUID`/`PGID` are honoured on a root-owned bind mount.

## Looking at the design

Tests say whether a screen works; they do not say whether it looks right. After a change to the interface, run the screenshot gallery and look at it:

```sh
pnpm run build && pnpm run shots      # in frontend/
```

It starts the real backend on a scratch data directory, walks every screen on a phone and on a desktop (Playwright, `e2e/gallery.spec.ts`), saves each in light and dark under `frontend/.screenshots/<device>/`, and makes contact sheets (`contact-<device>-<scheme>.png`) with `tools/screenshots/contact_sheet.py`. Check spacing, wrapping, contrast and wording in both schemes, and fix what looks wrong before the change is done. The journey test (`pnpm run e2e`) saves screenshots of its own pages too when `NEVUS_E2E_SHOTS=<dir>` is set. `uv run tools/screenshots/take.py` is a different thing: the three store screenshots, from a seeded instance with plausible photos, for `docs/design/screenshots/`.

A review pass reads the gallery with a designer's eye: one primary action per screen, destructive actions apart, occasional tools folded, the content's own order, two panes where there is room.

## Conventions

- English everywhere; see [`CONTRIBUTING.md`](CONTRIBUTING.md).
- GitFlow: `feature/*` from `develop`, pull request back, linear history; releases on `release/*` into `main` (see [ADR-0009](docs/adr/0009-release-engineering.md)).
- Conventional Commits with a DCO sign-off (`git commit -s`); `pre-commit install --hook-type commit-msg --hook-type pre-commit` enables the local checks.
- Colours only through tokens (`frontend/src/design-system/tokens/tokens.css`); stylelint rejects raw colours elsewhere.
- Dependency updates arrive through Renovate pull requests against `develop` (the Renovate GitHub app must be enabled on the repository).

## Migrations

`just revision "add lesions"` autogenerates a migration from the models; review it (SQLite needs batch mode, which the environment enables automatically), then `just migrate`. Every migration must apply cleanly on both engines; the CI enforces it.

## Body map

The silhouette and the zone geometry are generated, not drawn by hand. `uv run tools/bodymap/build.py --preview docs/design/bodymap` rebuilds `zones.json` in both the backend and the frontend (the two copies must stay identical; CI checks it) and refreshes the labelled previews in `docs/design/bodymap/`. The zone identifiers, names and hit polygons come from MoleMapper (see `THIRD_PARTY_NOTICES.md`); the silhouette is neVus artwork built in `tools/bodymap/build.py`. Design notes: `docs/design/BODY_MAP.md`.

## Adding a language

The languages neVus speaks are listed once, in `backend/src/nevus/languages.py`, in the chooser's order; the API types, the stored preferences and the documents read that list, and `frontend/src/lib/i18n/index.ts` keeps the same list with each language's own name. To add one:

1. Add its code to `Language` in `languages.py` and to `supportedLanguages`, `languageNames` and the catalogue imports in `index.ts`; add it to `rtlLanguages` if it is written right to left. The PDF documents set Epilogue and fall back to the fonts the image installs (Noto Core and Droid Sans Fallback cover every script neVus speaks); a new script needs no bundled font.
2. Frontend: copy `src/lib/i18n/locales/en.json` to `<code>.json` and translate every string, keeping the `{{placeholders}}`; give every plural key the forms the language's `Intl.PluralRules` has (`_one` and `_other` for most, `_few` and `_many` as well for Russian and Polish, all six for Arabic, `_other` alone for Chinese, Japanese, Korean and Indonesian). `tests/i18n.test.ts` checks keys, placeholders and plural forms against English.
3. Backend: write `reports/locales/<code>.json` (wording, month names, date patterns and decimal mark; start from `en.json`), add the language to `TEXT` in `notify/email.py`, `notify/calendar.py`, `notify/webhooks.py` and `cv/card_sheet.py`, to `GREETING` in `api/push.py` and to `README_TEXT` in `cv/card_mesh.py`; then run `uv run --project backend python tools/i18n/zone_names.py` to copy the zone names of every catalogue into `reports/zone_names.json`. `tests/test_languages.py` checks that every catalogue has every language with the same keys and placeholders.
4. Lint: `tests/test_language.py` checks every catalogue for disease names in every script; give the language its own list of risk and prompting words in `FORBIDDEN` when you can, and put in `ALLOWED` the exact sentences that say what neVus does not do.
5. Regenerate the API types (`nevus openapi`, then `pnpm run openapi`) and mention the language in the README.

## Releasing

One release is one pull request into `main` plus what the release workflow does with it.

1. `git checkout -b release/X.Y.Z develop`
2. `uvx --from commitizen cz bump --yes` (add `--prerelease alpha --increment MINOR` for a pre-release). This rewrites the version in `backend/pyproject.toml`, `frontend/package.json` and `deploy/compose.yaml` (both the card version and the image tag), writes `CHANGELOG.md` and commits. Amend the commit with `git commit --amend -s --no-edit` so it carries the sign-off, then `cd backend && uv lock` and commit the refreshed lockfile. Delete the local tag commitizen created (`git tag -d vX.Y.Z`): the workflow tags the merge commit on `main`.
3. Push the branch, open the pull request against `main`, wait for green checks, then merge locally with `git merge --no-ff` and push `main`.
4. The release workflow publishes `ghcr.io/jalmena/nevus:X.Y.Z` (amd64 and arm64), smoke-tests and scans it, tags the commit, creates the GitHub Release from the changelog and, when a `STORE_TOKEN` secret exists, opens the store pull request; otherwise bump `Apps/Nevus` in the store by hand.
5. Merge `main` back into `develop` and delete the release branch.

Hotfixes branch from `main` (`hotfix/*`), bump the patch version the same way and follow steps 3 to 5.

## Continuous integration runners

The CI workflow runs on GitHub-hosted runners (`ubuntu-latest`): the repository is public, so they cost nothing, and up to twenty run in parallel. The jobs come in two stages: the cheap checks first (commit messages, secrets and dependency audits, the frontend's lint, types, tests and build), and only when they pass the three expensive jobs side by side (backend tests on SQLite and PostgreSQL, the container image, the end-to-end journey). A failure in the first stage stops there. A whole run takes about ten minutes.

Until 1.1.0 the workflow ran on a self-hosted runner labelled `nevus`, an LXC with two cores on the maintainer's home lab provisioned from the personal runners repository; one run took about an hour there, and the jobs had to form a chain so a failure did not cost the rest. The runner is kept registered and can take the workflow again by changing `runs-on` in `.github/workflows/ci.yml` to `[self-hosted, nevus]`; its own tolerances (health-check retries, a two-minute wait for the smoke test, the pango libraries installed when missing) are still in the workflow. The release workflow has always run on GitHub-hosted runners, because it builds arm64 images with QEMU.
