# Security

neVus stores some of the most personal data a household has. This document states the threat model, the controls the software provides, what the operator must do, and how to report a vulnerability. It is updated with every release that changes the security posture.

## Reporting a vulnerability

Please do not open a public issue for security problems. Use GitHub's private vulnerability reporting on this repository ("Security" → "Report a vulnerability"). You will get an acknowledgement within seven days and a fix or a mitigation plan as soon as practical; credit is given in the release notes unless you prefer otherwise. Only the latest minor release line receives security fixes before 1.0.0.

## Assets

- Photographs of skin and the derived images, including their capture dates.
- Measurements, notes, symptom flags, body locations, reminders and appointment dates.
- Account credentials, sessions, second-factor secrets, webhook and email secrets.
- Backups and export bundles.
- The integrity of the record: nothing may be altered or removed without the person's intent and an audit trail.

## Trust boundaries and actors

- The server is on a private network; remote access is through the operator's VPN. The reverse proxy terminates TLS with a certificate the household's devices trust.
- Actors: household members with accounts (admin or member) and per-person roles; the operator (usually the admin); anyone on the local network or VPN without an account; a malicious website open in a member's browser (cross-site attacks); an attacker with a stolen backup or disk; a compromised optional integration endpoint (webhook receiver, email server).
- Out of scope: an attacker with root on the server or with the operator's encryption passphrases; physical access to an unlocked device with an open session.

## Controls in the software

Authentication and sessions

- Passwords hashed with argon2id (parameters tuned to roughly 150 ms on the target hardware); login rate limiting; closed registration with a first-run claim flow; optional TOTP with recovery codes (1.0.0).
- Server-side sessions with random identifiers stored hashed; cookies `HttpOnly`, `SameSite=Lax`, `Secure` when the request arrives over HTTPS; idle and absolute lifetimes; sign-out everywhere.
- Re-authentication ("sudo mode") before purging a person, exporting all data, changing security settings or disabling a user.
- Trusted-header mode for forward authentication is enabled only by explicit configuration, trusts headers only from configured proxy addresses, and disables local login while active; an emergency local login exists through the command line.

Authorisation

- Every request is scoped to the persons the user may access (owner, manager, viewer); administrative endpoints require the admin role; authorisation is tested with an endpoint-by-role matrix.
- Images and renditions are served only through authorised endpoints; no static directory exposes the blob store; content-addressed URLs are unguessable but still require a session.

Web protections

- Host allowlist: the application answers only for private addresses, `localhost`, `.local` names and the hostnames the operator configures, which defeats DNS rebinding from a hostile website.
- Cross-site request forgery: unsafe methods require same-site fetch metadata or a matching origin; the session cookie is `SameSite=Lax`.
- Strict content security policy, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Cross-Origin-Resource-Policy: same-origin`, frame embedding denied.
- Uploads are validated by decoding, limited in size and pixel count, and re-encoded when the format is not web-safe; metadata is stripped on ingest.

Data at rest and in motion

- Backups and exports are encrypted with a passphrase in the `age` format and can be decrypted with the standard `age` tool without neVus.
- Webhook and email secrets are encrypted with a key derived from a server secret stored in a file, never in the database or the compose file.
- The application never contacts external services unless the operator configures a channel; there is no telemetry.

Supply chain and build

- Locked dependencies; secret scanning, dependency auditing and container image scanning in continuous integration; software bill of materials and provenance attached to published images; automated dependency updates with a stability delay.
- Images run as a non-root user with PUID/PGID mapping; no capabilities beyond the defaults; read-only root filesystem where practical.

Logging and audit

- Logs contain identifiers, never names, notes or image content.
- An append-only audit log records who did what to which record, with identifiers only.

## Operator responsibilities

- Keep the server on a private network and reach it remotely through a VPN; do not expose neVus to the public internet.
- Terminate TLS at a reverse proxy with a certificate the household's devices trust; without HTTPS the browser will not allow live camera capture or installation as an application, and cookies are not marked secure.
- Set a strong admin password and enable the second factor when available; create one account per person.
- Encrypt the disk or volume that holds the data directory if the server could be stolen; the application does not encrypt files at rest.
- Keep the encryption passphrase for backups somewhere other than the server; test a restore at least once.
- Update neVus when releases are published; read the release notes for security-relevant changes.

## Threat model review

A structured review (assets, entry points, misuse cases, controls, residual risks) is scheduled for the hardening phase before 1.0.0 and repeated when a release adds an entry point (for example Web Push or a new integration).
