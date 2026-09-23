# neVus — Architecture

Baseline 2026-09-23. This document describes the intended structure of neVus and the reasons behind it. Decisions with alternatives are recorded in [`docs/adr/`](docs/adr/README.md); requirements in [`PRODUCT_REQUIREMENTS.md`](PRODUCT_REQUIREMENTS.md). It will be kept in step with the code.

## 1. Overview

neVus is a single container that serves a progressive web application and an HTTP API, stores structured data in SQLite (or an operator-provided PostgreSQL), stores images as immutable content-addressed files on one data volume, and runs image analysis in a supervised pool of worker processes inside the same container. A command-line interface in the same image handles backup, restore, verification and maintenance.

```text
 phone / desktop browser                           home server
 ┌──────────────────────┐   HTTPS (reverse proxy)  ┌──────────────────────────────────────────────┐
 │ neVus PWA (React)    │ ───────────────────────▶ │ container: nevus                             │
 │ - body map, capture  │                          │ ┌──────────────┐  ┌────────────────────────┐ │
 │ - offline outbox     │ ◀─────────────────────── │ │ FastAPI      │  │ job supervisor         │ │
 │ - service worker     │        JSON, images       │ │ API + static │─▶│ process pool (CV, PDF) │ │
 └──────────────────────┘                          │ └──────┬───────┘  └──────────┬─────────────┘ │
                                                   │        │ SQLAlchemy           │ files        │
                                                   │ ┌──────▼──────────┐  ┌───────▼────────────┐ │
                                                   │ │ SQLite (default)│  │ /data/blobs (CAS)  │ │
                                                   │ │ or PostgreSQL   │  │ originals+renditions│ │
                                                   │ └─────────────────┘  └────────────────────┘ │
                                                   │  /data: db, blobs, backups, exports, models  │
                                                   └──────────────────────────────────────────────┘
```

Design principles: operational simplicity over architectural complexity; privacy by default; every number traceable to the code and inputs that produced it; nothing irreversible happens without the person's confirmation.

## 2. Technology choices

| Layer | Choice | Record |
| --- | --- | --- |
| Backend | Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.0 (sync ORM), Alembic, `opencv-python-headless`, NumPy, ONNX Runtime (CPU), Pillow with HEIF support, WeasyPrint | [ADR-0004](docs/adr/0004-python-fastapi-backend.md) |
| Database | SQLite (WAL) by default; PostgreSQL through `NEVUS_DATABASE_URL`; one portable data layer | [ADR-0005](docs/adr/0005-sqlite-default-postgresql-option.md) |
| Image storage | Content-addressed blobs on the data volume; scrubbed immutable originals; regenerable renditions; deferred garbage collection | [ADR-0006](docs/adr/0006-content-addressed-image-store.md) |
| Analysis | Pluggable analyzers writing append-only, versioned analysis records | [ADR-0007](docs/adr/0007-versioned-analysis-records.md) |
| Frontend | React 19, TypeScript, Vite, React Aria Components, TanStack Query, Dexie (IndexedDB), react-i18next, CSS Modules with design tokens, `vite-plugin-pwa` | [ADR-0008](docs/adr/0008-react-pwa-frontend.md) |
| Release engineering | GitFlow, Conventional Commits, commitizen, GitHub Actions, ghcr.io, personal CasaOS store | [ADR-0009](docs/adr/0009-release-engineering.md) |

## 3. Repository layout

```text
backend/            Python project (uv): src/nevus/{api,auth,domain,db,storage,jobs,cv,notify,reports,i18n,cli}, alembic/, tests/
frontend/           pnpm project: src/{app,features/*,design-system/{tokens,components},lib/{api,offline,camera,i18n}}, public/, e2e/
ml/                 Separate uv project for training, export and evaluation; never imported by the backend at runtime
deploy/             Dockerfile, docker-entrypoint.sh, compose.yaml (with x-casaos), reverse-proxy examples
docs/               Audits, research, ADRs, design system, data model, deployment and development guides
.github/workflows/  ci.yml, release.yml, publish.yml, security.yml
```

## 4. Backend

### 4.1 Modules

- `api`: FastAPI routers per feature (auth, users, persons, bodymap, lesions, observations, images, measurements, reminders, appointments, reports, sessions, analyses, settings, health). OpenAPI is the contract; the frontend client is generated from it.
- `auth`: password hashing (argon2id), server-side sessions, sudo mode, host allowlist, CSRF checks (`Sec-Fetch-Site`/`Origin` on unsafe methods), rate limiting, proxy-header mode, TOTP (later).
- `domain`: entities and services with the business rules (access scoping, measurement mathematics, uncertainty propagation, due-date computation, trash and purge).
- `db`: SQLAlchemy models, session management, migrations, the only module allowed to contain dialect-specific SQL.
- `storage`: content-addressed blob store, metadata scrubbing, renditions, garbage collection, quotas, backup manifests.
- `jobs`: job table, supervisor loop, process pool with per-kind timeouts, retry with leases.
- `cv`: analyzers (quality, scale references, segmentation, measurement, alignment, detection, matching) and the evaluation harness.
- `notify`: email, webhooks, ICS feed, Web Push (flagged).
- `reports`: Jinja2 templates (EN/ES) rendered to PDF with WeasyPrint; server-rendered SVG charts.
- `i18n`: message catalogues for server-generated text (emails, reports, validation messages).
- `cli`: `nevus` command (`backup`, `restore`, `verify`, `reanalyze`, `user`, `migrate`, `export`, `purge`).

### 4.2 Process model

One `uvicorn` process runs the API and an asyncio job supervisor. Heavy work (OpenCV, ONNX, PDF) runs in a `pebble` process pool (spawn context) with `os.nice(10)` and thread caps so two of the four cores stay free for the web. Jobs live in a `jobs` table (id, kind, payload, status, priority, run_after, attempts, lease_until, error) and are leased with a short transaction; expired leases are re-queued after a restart. `NEVUS_ROLE=all|web|worker` allows running the supervisor in a second container from the same image on the same volume if that ever becomes necessary; the job store interface is the only seam to replace.

### 4.3 Data model

Identifiers are UUIDv7 everywhere (sortable; the PWA can mint them offline and the server accepts idempotent creates). Timestamps are UTC; observations also store the capture time zone and the local capture date. Soft deletion (`deleted_at`) with a 30-day trash applies to persons, lesions, observations and images; purge is a separate, re-authenticated path.

| Entity | Key fields |
| --- | --- |
| `User` | username, email, password_hash, role (admin, member), language, theme, show_uncertainty, totp_secret (encrypted, later), disabled_at |
| `AuthSession` | id_hash, user_id, created_at, last_seen_at, expires_at, user_agent, ip |
| `Person` | display_name, birth_year, skin_tone (optional, evaluation only), owner_user_id, experimental_analysis, deleted_at |
| `PersonAccess` | user_id, person_id, role (owner, manager, viewer) |
| `BodyMap` | name, version, svg_hash, zones (JSON: code, name, side, view, polygon) |
| `BodyLocation` | person_id, body_map_id, zone_code, x, y (normalised to the view box), laterality, note |
| `Lesion` | person_id, body_location_id, type (mole, other), label, first_noticed_on, status, tags, notes, interval_days, deleted_at |
| `Observation` | lesion_id, captured_at, captured_tz, captured_local_date, notes, symptoms (JSON), quality_flags (JSON), created_by, deleted_at |
| `Image` | person_id, observation_id, session_capture_id, role, modality, sha256, bytes, mime, width, height, source_format, exif_subset (JSON), deleted_at |
| `Rendition` | image_id, kind (full, preview, thumb, mask, overlay), params_hash, sha256, width, height, bytes |
| `ScaleReference` | observation_id, kind (card, coin, manual), reference_mm, detected (JSON: corners, ids, tilt), mm_per_px, mm_per_px_sd, analysis_id |
| `Measurement` | observation_id, lesion_id, kind (longest_diameter, perpendicular_diameter, area), value, unit, method (manual, assisted, automatic), uncertainty_sd, scale_reference_id, analysis_id, confirmed_by, confirmed_at |
| `Analysis` | target_type, target_id, analyzer_name, analyzer_version, model_hash, params (JSON), params_hash, input_hash, outputs (JSON), confidence, status, decision (pending, confirmed, rejected), decided_by, decided_at, created_at |
| `Job` | kind, payload (JSON), status, priority, run_after, attempts, lease_until, error |
| `Reminder` | person_id, lesion_id (optional), interval_days, next_due_at, preferred_local_time, timezone, channels (JSON), snoozed_until |
| `NotificationDelivery` | reminder_id, due_date, channel, status, error |
| `Appointment` | person_id, date, notes, report_id |
| `PhotoSession` | person_id, started_at, body_map_id, protocol (JSON), status |
| `SessionCapture` | session_id, zone_code, image_id, pose_hint |
| `SessionCandidate` | capture_id, bbox, matched_lesion_id, decision (new, matched, ignored), analysis_id, decided_by, decided_at |
| `Report` | person_id, scope, lesion_ids (JSON), language, paper, options (JSON), blob_sha256, analyzer_versions (JSON), job_id |
| `AuditLog` | at, actor_user_id, action, target_type, target_id, ip, details (identifiers only) |
| `Setting` | key, value (JSON), encrypted |

### 4.4 Database strategy

SQLAlchemy 2.0 with portable column types (`Uuid`, `JSON`, `DateTime(timezone=True)`, `LargeBinary`) and no dialect-specific SQL outside `db/dialects.py`. Alembic migrations run in batch mode for SQLite; every migration runs against both engines in CI, plus an upgrade of fixture databases from each released schema. SQLite runs with WAL, `synchronous=NORMAL`, `busy_timeout=5000`, foreign keys on; PostgreSQL uses `psycopg` with a small pool. Hot JSON keys that need indexes (for example the latest diameter) are exposed as ordinary columns rather than JSON path indexes, so both engines behave the same. In SQLite mode the backup command snapshots the database with the online backup API and archives the blob tree; in PostgreSQL mode it archives the blob tree and a manifest, and the database dump is the operator's responsibility, documented with an example.

### 4.5 Image storage

```text
/data/
  nevus.sqlite3 (+ -wal, -shm)        when SQLite is used
  blobs/originals/ab/cd/<sha256>      immutable, metadata-scrubbed originals
  blobs/derived/ab/cd/<sha256>        regenerable renditions, masks, overlays
  models/                             optional overlay of verified model files
  exports/                            encrypted export bundles awaiting download
  backups/                            nightly encrypted snapshots (30 daily, 12 monthly)
  tmp/                                same filesystem, atomic renames
```

Ingest: validate the file, decode, drop every metadata segment except orientation and capture time (GPS, maker notes, serial numbers and unique identifiers never reach the disk), re-encode only if the source format is not JPEG or PNG, hash the result, write atomically, create renditions without metadata. Files are never modified after they are written; deletion is a database state until purge, and a garbage collector removes blobs unreferenced for longer than the backup interval. Directories are keyed by hash, not by person, so the file tree leaks nothing about who is who; access control lives entirely in the API.

### 4.6 Image analysis

An analyzer implements `name`, `version`, `model_hash`, a parameter schema and `run(context) -> result`. Results are stored as analysis records keyed by target, analyzer, version, model hash, parameter hash and input hash, so re-running the same analysis is a no-op and a new version creates new rows next to the old ones. Measurements point at the analysis that produced them; the interface shows the current analysis per target and can toggle "as recorded" versus "latest algorithm" on charts. Classical analyzers ship first (blur and exposure metrics, framing, fiducial card detection with tilt, coin fitting, manual scale, tap-seeded segmentation, Feret diameters and area with propagated uncertainty, feature-based alignment that abstains on low inlier counts). Learned models arrive as ONNX files bundled in the image under a manifest with hash, licence, data summary and metrics; models above the size budget go into a separate image variant; nothing is downloaded at runtime. Automatic analyzers beyond quality and reference detection run only for persons whose `experimental_analysis` setting is on, and their results wait for the person's decision.

### 4.7 Uncertainty model

For a lesion of diameter *d* measured with scale error σ_scale (relative) and border uncertainty σ_border (absolute, per edge): σ_d ≈ √((d·σ_scale)² + (2·σ_border)²). Scale error comes from the reference detection (marker corner residuals and tilt; coin circle fit residuals; manual line placement); border uncertainty from the segmentation method (assisted outline versus manual circle) and image resolution. A difference between two observations carries the combined uncertainty and is labelled "no detectable change" when it lies within it. Camera tilt θ foreshortens by cos θ; measurements beyond the tilt limit are flagged.

### 4.8 Notifications

A one-minute scheduler tick computes due reminders and enqueues delivery jobs keyed by reminder and due date for idempotency. Channels: in-app due list, email (SMTP configured by the admin), outgoing webhooks with JSON templates for Home Assistant, n8n, ntfy and Gotify, per-person ICS feeds under secret URLs, and Web Push behind a feature flag. Messages contain labels and dates, never images.

### 4.9 Reports

Jinja2 templates in English and Spanish, styled with the same design tokens as the application, rendered by WeasyPrint to PDF/A-3 with the JSON export of the included data attached. Report generation runs as a job with a time limit; images are downscaled for print; every report carries the intended-use statement, the methods used (reference type, analyzer versions) and separates measured values, automated observations, the person's notes and space for the clinician.

## 5. Frontend

- React 19 with TypeScript, built by Vite, served by the backend with a single-page fallback; hashed assets immutable, `index.html` and the service worker never cached.
- React Aria Components for accessible primitives (dialogs, sliders, tabs, menus, calendars); CSS Modules per component; design tokens as CSS custom properties in one file shared with the report templates ([`docs/design/DESIGN_BRIEF.md`](docs/design/DESIGN_BRIEF.md)).
- TanStack Query for server state; Dexie for the offline outbox of pending observations, drained on `online`, focus and visibility events; UUIDv7 minted client-side for idempotent uploads.
- `react-i18next` with JSON catalogues for English and Spanish; the language comes from the user's account and is mirrored locally for the login page; dates and numbers formatted with `Intl` per locale; millimetres everywhere.
- Camera: `<input type="file" accept="image/*" capture="environment">` always; `getUserMedia` guided capture with framing and marker overlays when `isSecureContext` and the platform allows it (disabled in iOS standalone mode because of known limitations).
- Body map: SVG silhouettes with zone paths, pointer and keyboard interaction, pinch-zoom via a gesture library, markers as SVG groups; the zone geometry is generated from the ported polygon data.
- Comparison: canvas-based side-by-side, overlay and slider views fed by the server's alignment result; charts with an SVG charting library.
- Service worker (`vite-plugin-pwa`, inject-manifest): precache the shell, network-first for API reads, cache-first for content-addressed renditions, purge on logout.

## 6. Security architecture (summary)

Details and the threat model are in [`SECURITY.md`](SECURITY.md). In short: argon2id passwords; random session identifiers hashed at rest; `HttpOnly`, `SameSite=Lax` cookies, `Secure` behind HTTPS; sudo mode for destructive actions; host allowlist against DNS rebinding; CSRF via fetch metadata and origin checks; per-request authorisation scoped to persons; images served only through authorised endpoints with `private, immutable` caching; secrets from a key file; webhook secrets encrypted at rest; dependency, secret and container scanning in CI; non-root container with dropped capabilities.

## 7. Deployment

Debian-slim base with `uv`-installed dependencies, `setpriv` to drop to PUID/PGID, `/healthz` for orchestration, `GET /` answering 200 without a session, one volume at `/data`, resource limits in the compose file, image size budget asserted in CI. The compose file carries `x-casaos` metadata for the personal store; the deployment guide covers the reverse proxy with an internal certificate authority (needed for live camera, PWA installation and Web Push), VPN-only remote access, backups, restore and upgrades. Images are built for linux/amd64 on every release and for linux/arm64 when the dependency wheels allow.

## 8. Observability

Structured JSON logs without personal data (identifiers only), request identifiers, job outcomes with durations, a `/healthz` endpoint reporting database, storage and worker state, and an optional Prometheus endpoint behind a setting.

## 9. Testing

- Backend unit tests: measurement mathematics with property-based tests (a synthetic disc of known size measures the same at any pixel scale), metadata scrubbing fixtures, blob store atomicity and garbage-collection grace, authorisation matrix per endpoint and role, job leasing under concurrency, scheduler idempotency.
- API tests against temporary databases on both engines; an OpenAPI snapshot drives the generated client so the frontend is type-checked against the server.
- Migration tests: `alembic check` on every change; upgrade of fixture databases from every released schema on both engines.
- Backup and restore: seed → encrypted backup → wipe → restore → verify counts and every blob hash, in CI and inside the container image.
- Image analysis evaluation: fixture images stratified by skin tone (synthetic, licence-clean public images, the operator's card photos at known distances); tolerance gates for card detection rate, millimetre-per-pixel error, disc diameter error, segmentation overlap, blur classification; regressions fail the build.
- Frontend: component tests with Testing Library, offline outbox state machine, map coordinate mathematics; Storybook with accessibility checks for every design-system component.
- End to end: Playwright on phone viewports for both browser engines: claim → person → place lesion → upload fixture → quality result → measurement → save → timeline; offline capture → queued → online → synced; axe checks fail on serious or critical issues.
- Descriptive-language lint over UI catalogues and report templates.

## 10. Release engineering

`feature/*` branches are integrated into `develop` through pull requests and a maintainer's local fast-forward after CI passes (no platform-generated commits); `release/*` branches bump the version and changelog with commitizen and merge into `main` with a merge commit; the tag creates a GitHub Release, the publish workflow builds and pushes multi-architecture images with SBOM and provenance, scans them, and opens a pull request in the personal store bumping the image tag, version, date and release notes; `main` is merged back into `develop`. Hotfixes branch from `main` and follow the same path. `latest` moves only on stable tags. See [ADR-0009](docs/adr/0009-release-engineering.md).
