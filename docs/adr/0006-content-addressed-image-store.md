# ADR-0006: Content-addressed image store with scrubbed immutable originals

- Status: Accepted
- Date: 2026-09-23
- Deciders: engineering, privacy policy set by the Product Owner

## Context

Photographs are the core evidence. They must survive every future algorithm, be re-measurable at full resolution, be free of location and device identifiers, be backed up consistently with the database, and be deletable with certainty. Phones embed GPS coordinates, serial numbers and maker notes in every file. The Product Owner decided that originals are kept at full resolution, that metadata is stripped except capture time and orientation, and that deletion goes through a 30-day trash.

## Decision

Images are stored as files named by the SHA-256 of their scrubbed bytes under `blobs/originals/ab/cd/<sha256>`, written atomically and never modified. Scrubbing removes every metadata segment except orientation and capture time; pixels are untouched; re-encoding happens only for formats the browser cannot display (HEIC becomes JPEG at high quality with the source format recorded). Renditions (full, preview, thumbnail, masks, overlays) are regenerable and live under `blobs/derived/`. Directories are keyed by hash, not by person. Deletion is a database state until the trash period ends; a garbage collector then removes blobs unreferenced for longer than the backup interval. Backups snapshot the database first and archive the blob tree second; because blobs are immutable and garbage collection lags, the archive is always a superset of what the snapshot references. Metadata lives in the database; the file tree carries no names, dates or locations.

## Consequences

- Deduplication is free; integrity verification is a hash walk; restores are copies.
- Access control cannot rely on the filesystem and lives entirely in the API, which serves images through authorised endpoints with immutable private caching.
- Storage grows with originals (a few megabytes each); a soft quota per person and a low-disk guard protect the server.
- Nothing about a person can be inferred from the storage layout, which simplifies encrypted backups and off-site copies.
