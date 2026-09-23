# ADR-0005: SQLite by default, PostgreSQL as a configurable option

- Status: Accepted
- Date: 2026-09-23
- Deciders: Product Owner (option requested), engineering (default and implementation)

## Context

A household produces a few writes per minute; the heavy bytes are image files, not rows. The simplest reliable deployment is one container with one data directory, where backup means one online database copy plus the blob tree. The maintainer's CasaOS host runs a shared PostgreSQL application, and the Product Owner asked for the ability to use an external PostgreSQL. Coupling health data to another application's database container (upgrade cadence, credentials, non-atomic backup with the blob store) is undesirable as a default but acceptable as an explicit operator choice.

## Decision

SQLite (WAL mode, `synchronous=NORMAL`, `busy_timeout`, foreign keys on) in the data directory is the default. An external PostgreSQL is supported through `NEVUS_DATABASE_URL` with full feature parity. One portable data layer (SQLAlchemy 2.0 portable types, Alembic batch migrations) serves both; dialect-specific SQL is confined to a single module. Continuous integration runs the test suite and every migration against both engines. Backups use SQLite's online backup API or `pg_dump` from the client tools shipped in the image, and the restore command handles both.

## Consequences

- Operators get a zero-configuration default and a documented path to PostgreSQL; the documentation states that in PostgreSQL mode the database server is the operator's responsibility and that backup consistency between database and blobs relies on the blob store's immutability and garbage-collection grace period.
- Indexed values must be ordinary columns (not JSON path expressions) so both engines behave the same.
- Every schema change costs a two-engine CI run; this is the price of the option.
- If a worker ever runs on another host, PostgreSQL becomes the required mode (SQLite over network filesystems is unsafe).
