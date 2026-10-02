# Threat model

Reviewed for 1.0.0 on 2026-10-02 against the code of that release. `SECURITY.md` lists the controls; this document says what they defend, what they do not, and what the review changed. It is repeated whenever a release adds an entry point (a push channel, a new integration, another way to sign in) or a new way to run code over uploaded content (a learned model).

## What is protected, in order

1. The photographs of skin and the images derived from them, with their dates: they are intimate, identifying and permanent.
2. The integrity of the record: nothing is altered or removed without the person's intent and an audit trail, because the record exists to be trusted later.
3. Credentials, sessions, second-factor secrets and recovery codes, and the webhook and email secrets.
4. Backups and exports, which hold everything above in one file.

## Who might attack, and with what

| Actor | Capabilities assumed |
| --- | --- |
| Someone on the home network or the VPN without an account | Reaches the server over HTTPS; can guess passwords and probe the API |
| A hostile website open in a member's browser | Can make the browser send requests to the server's address (cross-site requests, DNS rebinding) |
| A household member with an account | Signed in; may try to see persons not shared with them or act beyond their role |
| An attacker with a copy of the disk, a backup or an export | Offline access to every file |
| A compromised integration endpoint | A webhook receiver or a mail server under someone else's control |
| Out of scope | Root on the server; the operator's passphrases; an unlocked device with an open session; the browser itself |

## Entry points

1. **The web application**: sign-in (password, second factor, recovery codes), the JSON API, uploads, image and report downloads, the service worker's cache.
2. **The reverse proxy**: TLS termination and, in proxy mode, the identity headers.
3. **Background work**: image decoding and analysis (Pillow, OpenCV), report rendering (WeasyPrint), backups and their verification (age, tar), outgoing webhooks (HTTP), email (SMTP) and, behind a flag, push messages to the browsers' push services (see the addendum).
4. **The data directory**: the database, the blob store, the server secret, backups and exports at rest.
5. **The command line**: `restore`, `emergency-login`, the start-up administrator reset from the environment.
6. **The supply chain**: dependencies, the container image, the continuous-integration runner.

## Misuse cases, controls and what remains

| Threat | Where | Control | Residual risk |
| --- | --- | --- | --- |
| Guessing a password | sign-in | argon2id; a sliding-window limit per address and account; the optional second factor | A weak password is the person's choice. The limiter is in memory, so a restart forgets it and several processes would not share it; one process serves the site |
| Guessing a one-time or recovery code | second factor | six digits valid for one step either side and never twice; recovery codes of about 50 bits stored hashed, one use; the same limiter, which also ends the pending sign-in; every refusal audited | None worth noting |
| Stealing a session | cookie | random token stored hashed; `HttpOnly`, `SameSite=Lax`, `Secure` over HTTPS; idle and absolute lifetimes; other sessions end on a new password or a new second factor | A device left unlocked |
| Cross-site request forgery | API | unsafe methods need same-site fetch metadata or a matching origin; `SameSite=Lax` | None known |
| Cross-site scripting | pages | strict content security policy; React escaping; no raw HTML insertion anywhere; server-made SVG (the QR code) shown through an image, not inlined | A vulnerability in a dependency |
| DNS rebinding from a hostile site | server | host allowlist; private addresses and configured names only | None known |
| Seeing another person's record | API | every endpoint checks the person's access rows (owner, manager, viewer) and the admin role where needed; tested by an endpoint-by-role matrix | None known |
| Guessing an image address | images | content-hash names are unguessable and still need a session and the person's access | None known |
| A crafted upload | ingest, analyses | decoded to validate, bounded in bytes and pixels, re-encoded when not web-safe, metadata stripped; analyses run in worker processes with timeouts | Decoder bugs (Pillow, libheif, OpenCV) are patched through dependency updates; uploads are decoded in the web process, which the pixel limit bounds |
| Spoofed identity headers | proxy mode | headers trusted only on connections whose peer is a configured proxy address; the server does not rewrite peer addresses; outside proxy mode the headers are ignored | A compromised proxy, which is the identity provider's own boundary |
| Lockout | sign-in | recovery codes; an administrator turns a member's factor off; the start-up reset for the administrator; a one-use emergency link when the proxy is down | None worth noting |
| Server-side request forgery through webhooks | webhooks | `http` and `https` only; administrators only; a fixed, signed body | Receivers on the home network are the point, so private addresses are not blocked |
| Fetching from the report renderer | reports | a fetcher that serves only the report's own assets; no network | None known |
| Reading secrets from the database | at rest | second-factor, webhook and email secrets encrypted with a key derived from the server secret file | The file lives next to the database and goes into the backup, which is itself encrypted |
| A stolen backup or export | at rest | `age` encryption with the operator's passphrase; `nevus verify --backup` proves the archive is whole | A weak passphrase |
| A stolen disk | at rest | the application does not encrypt files; the operator encrypts the volume (`docs/DEPLOYMENT.md`) | Accepted: full-disk encryption is the operator's layer |
| Covering tracks | audit | an append-only log with identifiers only; refused sign-ins are recorded even though the request fails | Logs on the same disk as the data |
| Exhausting the server | everything | upload size and pixel limits, a free-space guard, job timeouts, one low-priority worker, a 60-second report wait in the interface | No per-user CPU quota; accepted on a private network |
| Losing the record silently | backups | a nightly encrypted backup, pruned by retention; every week the latest one is read back and the live store checked; administrators warned on failure | A copy off the machine is still the operator's job |
| Exposing intimate photographs | sessions | every region can be skipped and two say they may show intimate areas; any part of a stored photo can be blurred, which removes the original at once; no telemetry, no third parties | Backups made before a blur hold the original until they rotate |
| A poisoned dependency or image | supply chain | locked dependencies; secret scanning, dependency audit and image scanning in CI; software bill of materials and provenance on published images; updates with a stability delay | The self-hosted runner is the operator's machine |

## What this review changed

- Refused sign-in attempts were not in the audit log: the refusal rolled the request back. They are committed before the request is refused.
- A second factor with recovery codes, an administrator's reset and the start-up reset exist; `SECURITY.md` and `docs/DEPLOYMENT.md` describe them.
- The latest backup is read back every week, with a warning when it would not restore.
- The QR code of the second factor is served as a standalone SVG shown through an image, never inlined as HTML.
- The secrets scan has a configuration that names the documented test vectors, so a real finding is not lost among false ones.

## Accepted residual risks

- The sign-in limiter is per process and in memory.
- Uploads are decoded in the web process, bounded by the pixel limit.
- Webhooks may target any address on the home network.
- Nothing is encrypted at rest except backups and exports.

## Addendum for 1.1.0: Web Push

Reviewed on 2026-10-02 with the code that adds push notifications behind `NEVUS_WEB_PUSH`.

New entry points: the subscription endpoints of the API (a signed-in user registers or removes a device), the outgoing HTTPS requests to the browsers' push services, and the service worker's `push` handler, which shows what the browser has already decrypted.

| Misuse case | Who | Controls | What remains |
| --- | --- | --- | --- |
| The push service, or anyone on the path to it, reads a message | the relay, network observers | each message is encrypted on the server for one device with the key material the browser created (RFC 8291, `aes128gcm`); the plaintext is names and dates, never photographs or notes | The relay learns that a message was sent, to which device and when |
| A forged message reaches a device | a third party who learns an endpoint | the push services accept only messages signed with the server's key pair (VAPID), which is stored encrypted with the server's key; endpoints are kept with the account that registered them | Nothing: a message without the signature is dropped by the relay |
| A subscription is planted to make the server call an address of the attacker's choosing | a signed-in user | endpoints must be HTTPS; the server sends nothing but the encrypted message and the signature; a device is forgotten after five failures or when the relay reports it gone | A user may still point the server at a public HTTPS address of their own, which receives messages meant for them and nothing else |
| The flag is on and the operator did not want the relay | the operator | off by default; the settings page says where the message travels; calendar feeds and webhooks remain the channels that stay on the network | The relay is inherent to the mechanism |

The review changed nothing else: the subscription endpoints follow the same authentication, CSRF and audit rules as the rest of the API, and the digest that is pushed is the one the email channel already sends.

## Next review

When any of these arrives: OpenID Connect or another sign-in method, an integration that accepts data from outside, a learned model that runs over uploaded photographs, or a second worker process.
