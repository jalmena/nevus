# neVus — Product requirements

- Status: baseline v1, 2026-09-23, derived from the Product Owner's answers in [`docs/PRODUCT_QUESTIONS.md`](docs/PRODUCT_QUESTIONS.md) and the decisions in [`docs/adr/`](docs/adr/README.md).
- Audience: the engineering side (architecture, implementation, testing, design) and the Product Owner (PO) as the arbiter of scope.
- Change policy: requirements change through pull requests; a change that alters intended use or the automatic-analysis boundary needs a new or superseding ADR.

## 1. Product principle

> When a dermatologist asks in six months whether this mole has changed, the answer is a dated series of measured photographs, not "I think it was a little smaller".

neVus improves the quality of the information available when a professional eventually sees the patient. It does not replace the professional.

## 2. Intended use and non-goals

**Intended use statement** (appears in the README, the about screen and every report):

> neVus is a personal documentation and measurement aid. It stores dated photographs of skin marks, measures them against a physical reference, and shows how those measurements changed over time. It does not diagnose, screen for, or assess the risk of any disease. Every automated result is an observation for the person and their clinician to interpret.

Non-goals, permanent:

- No malignancy classifier, risk score, ABCDE score, melanoma probability or any other diagnostic output, not even behind an experimental setting ([ADR-0003](docs/adr/0003-automatic-analysis-boundary.md)).
- No algorithm-triggered medical advice, alerts or "see a doctor" prompts.
- No cloud dependency: no external accounts, storage, analytics or inference services. Optional integrations (email, webhooks, calendar feed, Web Push) are configured by the operator and off by default.
- No 3D body model.
- No public exposure of the server by default; remote access is the operator's VPN.

## 3. Users, persons and roles

- **User**: a login. Roles: `admin` (creates users, manages settings, sees everything needed to operate) and `member`.
- **Person**: the profile whose skin marks are tracked. A user may manage several persons (a household); a person may later receive their own login.
- **Profile access**: per person, a user is `owner`, `manager` (create and edit observations) or `viewer` (read only). Two adults can manage a child's profile.
- Registration is closed. The first visitor claims the instance and becomes admin; admins create the other accounts. No open sign-up.
- Every user has persistent preferences stored with the account: interface language (English or Spanish), theme (light, dark, system), uncertainty display, experimental-analysis setting per profile they own.

## 4. Glossary

| Term | Meaning |
| --- | --- |
| Body map | Front and back schematic silhouettes (SVG) divided into named zones; detail views (face, scalp, hands, feet) added progressively |
| Zone | A named anatomical region of the body map, ported from MoleMapper's 61-zone taxonomy and mapped to a standard surface-anatomy vocabulary for export |
| Body location | A zone plus a normalised point inside it (and the body-map version it refers to) |
| Lesion | A tracked mark: type `mole` or `other`, with a label, a body location, a discovery date, notes, tags, a status (active, removed, resolved) and a monitoring interval |
| Observation | One dated visit to a lesion: one or more images with roles, optional measurements, notes, quality flags, symptoms noted by the person |
| Image | A stored photograph: immutable scrubbed original plus regenerable renditions; carries a role (overview, close-up, with reference) and a modality (camera, dermatoscope) |
| Scale reference | The physical object that gives millimetres per pixel: the printed neVus card, a Euro coin, or a manual two-point line of known length |
| Measurement | A number with unit, method (manual, assisted, automatic), uncertainty and a link to the analysis that produced it |
| Analysis | A versioned, append-only record of what an algorithm computed on which input, with its parameters and model hash |
| Reminder | A per-lesion or per-person schedule that produces due items and notifications |
| Appointment | A dermatology visit date that drives the "Prepare my visit" flow |
| Session | A full-body capture: zone-by-zone photographs taken in one sitting, comparable with earlier sessions |
| Report | A generated PDF for a clinician: single lesion or profile summary, in English or Spanish |

## 5. Functional requirements

Each requirement has an identifier, a target release and, where useful, acceptance notes. Releases: 0.1.0 (core tracking), 0.2.0 (comparison and reports), 0.3.0 (assisted analysis, experimental), 0.4.0 (full-body sessions, experimental), 1.0.0 (hardening).

### 5.1 Accounts, persons and access

| ID | Requirement | Release |
| --- | --- | --- |
| FR-ACC-01 | First-run claim flow creates the admin; alternatively `NEVUS_ADMIN_USER`/`NEVUS_ADMIN_PASSWORD` read once at start-up, as documented for Tabernacle | 0.1.0 |
| FR-ACC-02 | Local accounts with argon2id password hashing and server-side sessions; login rate limiting; re-authentication ("sudo mode") before purging a profile or exporting all data | 0.1.0 |
| FR-ACC-03 | Admin creates, disables and resets users; no open registration | 0.1.0 |
| FR-ACC-04 | Persons with display name, optional birth year and optional skin-tone self-description (Fitzpatrick or Monk scale) used only for evaluation of image algorithms, never shown as a health attribute | 0.1.0 |
| FR-ACC-05 | Per-person access roles owner/manager/viewer; every query is scoped to the persons the user may see | 0.1.0 |
| FR-ACC-06 | Trusted-header SSO mode (`NEVUS_AUTH_MODE=proxy`) for reverse proxies with forward authentication; local login disabled in that mode; emergency local login through the CLI | 0.2.0 |
| FR-ACC-07 | Optional TOTP second factor with recovery codes | 1.0.0 |

### 5.2 Body map and lesions

| ID | Requirement | Release |
| --- | --- | --- |
| FR-MAP-01 | Front and back schematic silhouettes with named zones; tap a zone to see its lesions; pinch-zoom and drag on touch devices; keyboard operable | 0.1.0 |
| FR-MAP-02 | A lesion marker is a zone plus a normalised point; markers show status and "due" state; overlapping markers cluster and expand on tap | 0.1.0 |
| FR-MAP-03 | Body-map versions are stored so coordinates keep meaning when artwork changes | 0.1.0 |
| FR-MAP-04 | Detail views (face, scalp, hands, feet) with their own zones | 0.2.0 → 0.3.0 |
| FR-LES-01 | Create, edit, archive lesions: type (mole, other), label, location, discovery date, notes, tags, status, monitoring interval | 0.1.0 |
| FR-LES-02 | Auto-suggested memorable labels (ported idea) that the person can overwrite | 0.1.0 |
| FR-LES-03 | Lesion page: header with location and status, timeline of observations, latest measurement with ±, next due date, notes | 0.1.0 |

### 5.3 Observations and photography

| ID | Requirement | Release |
| --- | --- | --- |
| FR-OBS-01 | Add an observation to a lesion with one or more images, each with a role (overview, close-up, with reference) and a modality (camera, dermatoscope) | 0.1.0 |
| FR-OBS-02 | Capture through the native camera (file input with `capture`) on every device; live guided capture with framing and marker overlays when the page runs in a secure context and the platform supports it | 0.1.0 |
| FR-OBS-03 | On ingest: verify the file, strip all metadata except capture time and orientation (never GPS, serial numbers or maker notes), keep pixels untouched, store the original immutably by content hash, generate renditions (full, preview, thumbnail) without metadata | 0.1.0 |
| FR-OBS-04 | Capture time comes from EXIF when present, otherwise from the upload time; the person can correct the date; time zone recorded | 0.1.0 |
| FR-OBS-05 | Re-capture aid: when adding an observation, show the previous close-up as a translucent overlay or side panel to match framing | 0.1.0 |
| FR-OBS-06 | Offline capture queue: observations created without connectivity are kept in the browser and uploaded when back online, with clear status | 0.1.0 |
| FR-OBS-07 | Quality checks after capture (blur, exposure and glare, resolution, marker found, framing) produce warnings; the person may still save; the observation carries a visible "saved with quality warnings" flag; only unreadable files are refused | 0.1.0 |
| FR-OBS-08 | Notes and symptom checklist per observation (itching, bleeding, pain, "looks different to me") stored as the person's own words and flags, never interpreted | 0.1.0 |

### 5.4 Scale and measurement

| ID | Requirement | Release |
| --- | --- | --- |
| FR-MEA-01 | Printed neVus reference card (fiducial markers, millimetre scale, grey and white patches) detected automatically; gives millimetres per pixel, camera tilt and a colour reference; specification in [`docs/design/REFERENCE_CARD_SPEC.md`](docs/design/REFERENCE_CARD_SPEC.md) | 0.1.0 |
| FR-MEA-02 | Euro coins as secondary reference: tap the coin, the app fits a circle, the person picks the denomination and may adjust | 0.1.0 |
| FR-MEA-03 | Manual two-point line of known length as fallback | 0.1.0 |
| FR-MEA-04 | Semi-automatic lesion measurement: tap the lesion, the app proposes a circle or outline, the person adjusts or accepts; nothing is saved without confirmation; longest diameter, perpendicular diameter and area recorded in millimetres | 0.1.0 |
| FR-MEA-05 | Every measurement carries an uncertainty derived from the scale error, the tilt and the border uncertainty; shown as ± by default; a settings switch hides ± in the app; reports always show it | 0.1.0 |
| FR-MEA-06 | Differences between observations are shown with their combined uncertainty and labelled "no detectable change" when inside it; never rounded into a trend | 0.1.0 |
| FR-MEA-07 | Tilt gate: if the reference plane is tilted beyond the configured limit, the measurement is flagged and the person is invited to retake | 0.1.0 |

### 5.5 Timeline, comparison and charts

| ID | Requirement | Release |
| --- | --- | --- |
| FR-CMP-01 | Per-lesion timeline with thumbnails, dates, measurements, quality flags and notes | 0.1.0 |
| FR-CMP-02 | Side-by-side view of any two observations with synchronised zoom and scale bars | 0.2.0 |
| FR-CMP-03 | Overlay and slider views after alignment of the two close-ups; alignment abstains when confidence is low and says so | 0.2.0 |
| FR-CMP-04 | Difference heat map as a visual aid, labelled as such | 0.2.0 |
| FR-CMP-05 | Charts of diameter and area over time with uncertainty bands; export of the series as CSV | 0.2.0 |

### 5.6 Reminders and appointments

| ID | Requirement | Release |
| --- | --- | --- |
| FR-REM-01 | Monitoring interval per lesion (default 3 months) and per person for full-body sessions (default 12 months); due list on the home screen | 0.1.0 |
| FR-REM-02 | In-app due items and email notifications (operator-configured SMTP); snooze for 1 week or 1 month; mark as done by adding an observation | 0.1.0 |
| FR-REM-03 | Outgoing webhooks with presets (Home Assistant, n8n, ntfy, Gotify) and a per-person ICS calendar feed protected by a secret URL | 0.2.0 |
| FR-REM-04 | "Prepare my visit": enter an appointment date; neVus lists lesions due or never photographed, guides capture, and produces the report | 0.2.0 |
| FR-REM-05 | Web Push behind a feature flag, off by default, with a notice that it relays through browser vendors | 1.x |

### 5.7 Reports

| ID | Requirement | Release |
| --- | --- | --- |
| FR-REP-01 | PDF report for a single lesion: identity, location on the body map, observation history with dated images and scale bars, measurement table with ±, chart, the person's notes, methods used, intended-use statement | 0.2.0 |
| FR-REP-02 | PDF profile summary: body map with markers, lesion list with latest measurements and due state, highlights of measured changes | 0.2.0 |
| FR-REP-03 | Templates in English and Spanish, language selectable per report; A4 default, US Letter option | 0.2.0 |
| FR-REP-04 | Reports separate measured values, automated observations (labelled experimental where applicable), the person's observations, and leave interpretation to the clinician | 0.2.0 |
| FR-REP-05 | Free selection of lesions for a report | 0.3.0 |

### 5.8 Automatic analysis (experimental, opt-in)

| ID | Requirement | Release |
| --- | --- | --- |
| FR-ANA-01 | Per-profile setting `experimental_analysis`, off by default; when off, no automatic analyzer beyond the quality checks and the reference detection runs | 0.1.0 |
| FR-ANA-02 | Every automatic result is stored as a versioned analysis record and shown with an "experimental" label; it enters the record only when the person confirms it and can be rejected | 0.3.0 |
| FR-ANA-03 | Assisted segmentation without a manual seed, automatic measurement proposals, framing assessment | 0.3.0 |
| FR-ANA-04 | Re-analysis command to run a newer analyzer version over past observations without overwriting earlier results | 0.3.0 |
| FR-ANA-05 | Minimal labelling tool for the operator's personal evaluation set (outline correction, good/bad quality label); data never leaves the server | 0.3.0 |

### 5.9 Full-body sessions (experimental, opt-in)

| ID | Requirement | Release |
| --- | --- | --- |
| FR-SES-01 | Guided zone-by-zone capture protocol with standard poses; every zone can be skipped | 0.4.0 |
| FR-SES-02 | Mark lesions on zone photos and link them to registry entries | 0.4.0 |
| FR-SES-03 | Automatic lesion detection on zone photos and matching against the registry produce candidates (matched, new, uncertain) that the person confirms or rejects | 0.4.0 |
| FR-SES-04 | Session-to-session comparison view | 0.4.0 |
| FR-SES-05 | Privacy-blur tool for stored zone photos | 1.0.0 |

### 5.10 Data management

| ID | Requirement | Release |
| --- | --- | --- |
| FR-DAT-01 | Trash for lesions, observations and images with automatic purge after 30 days, including blob files; restore from trash | 0.1.0 |
| FR-DAT-02 | Complete export per person or instance: images, metadata as JSON, measurements as CSV, packaged and encrypted with a passphrase (`age` format) | 0.1.0 |
| FR-DAT-03 | Backup command producing an encrypted, consistent snapshot (database plus blobs); nightly schedule inside the container writing under the data directory; retention 30 daily and 12 monthly; restore command; both tested in CI | 0.1.0 |
| FR-DAT-04 | Profile purge: hard delete of a person and all their data after re-authentication; audit log keeps identifiers only | 0.1.0 |
| FR-DAT-05 | Storage quota per person (soft) and low-disk guard | 0.1.0 |

### 5.11 Settings and internationalisation

| ID | Requirement | Release |
| --- | --- | --- |
| FR-SET-01 | Interface available in English and Spanish; language persisted per user; instance default configurable | 0.1.0 |
| FR-SET-02 | Theme light, dark or system, persisted per user | 0.1.0 |
| FR-SET-03 | Uncertainty display switch (in-app only) | 0.1.0 |
| FR-SET-04 | Experimental-analysis switch per profile the user owns | 0.1.0 |
| FR-SET-05 | Notification channels configuration (SMTP, webhooks) restricted to admins | 0.1.0 / 0.2.0 |

### 5.12 Deployment and packaging

| ID | Requirement | Release |
| --- | --- | --- |
| FR-DEP-01 | Single container image, non-root, PUID/PGID, `/healthz`, `GET /` answers 200 without a session (application shell) so the CasaOS health check passes | RC |
| FR-DEP-02 | Docker Compose file with `x-casaos` metadata; entry in the personal app store ("jalmena store", category Others) | RC |
| FR-DEP-03 | SQLite by default in the data directory; optional external PostgreSQL through `NEVUS_DATABASE_URL`, feature-equivalent and tested in CI | 0.1.0 |
| FR-DEP-04 | Deployment guide covering the reverse proxy with an internal certificate authority, VPN-only access, HTTPS requirements for live camera and PWA, backups and restore | RC |
| FR-DEP-05 | Images for linux/amd64; linux/arm64 on release builds when the dependencies allow | RC / later |

## 6. Non-functional requirements

| ID | Requirement |
| --- | --- |
| NFR-PRI-01 | All data stays on the operator's server. No telemetry, no external calls at runtime unless the operator configures a channel. |
| NFR-PRI-02 | Logs never contain personal data (names, notes, image content); identifiers only. |
| NFR-PRI-03 | Images are served only through authenticated, authorised endpoints; never from a public static directory. |
| NFR-SEC-01 | Threat model and controls documented in [`SECURITY.md`](SECURITY.md); dependency and container scanning in CI; no secrets in the repository. |
| NFR-SEC-02 | Host allowlist against DNS rebinding; CSRF protection; secure cookies when served over HTTPS. |
| NFR-PER-01 | On a low-power x86 home server: page loads under 2 s on the LAN; image upload acknowledged immediately with background processing; quality checks within 5 s per image; assisted measurements within 15 s; the interface stays responsive while workers run. |
| NFR-PER-02 | Container image under 550 MB; memory under 1 GB at rest, under 3 GB with one active worker. |
| NFR-ACC-01 | WCAG 2.2 AA: keyboard operability, focus order, contrast, labels, reduced-motion support; automated checks in CI and manual audit before 1.0.0. |
| NFR-OFF-01 | Installable PWA; the application shell, the body map and the capture flow work offline; queued observations sync later. |
| NFR-REL-01 | Backup and restore round trip tested in CI on every change; database migrations tested against fixtures of every released schema. |
| NFR-MNT-01 | English-only code and documentation; Conventional Commits; GitFlow; SemVer; ADRs for structural decisions. |
| NFR-LIC-01 | AGPL-3.0-only; third-party components and their notices tracked in `THIRD_PARTY_NOTICES.md`; models and datasets used for training are licence-clean and documented in `MODEL_CARD.md`. |
| NFR-LAN-01 | User-facing text is descriptive: sizes, dates, differences, uncertainties. A CI lint rejects disease names, risk vocabulary and diagnostic thresholds in UI copy and report templates. |

## 7. Language rules for user-facing copy

- Say what was measured or observed, never what it means: "5.1 ± 0.4 mm", "no detectable change since 12 March", "image is blurry", "possible new mark, please confirm".
- Words that do not appear in the interface or reports: melanoma, cancer, malignant, benign, risk, suspicious, dangerous, urgent, diagnosis, probability of, ABCDE. The lint list lives with the frontend and report templates and is updated through pull requests.
- The sarcastic register belongs to the README and marketing copy; in-app copy is calm, short and neutral. The tagline "Because 'I think it was smaller' is not data." may appear on the login page and reports' footer.

## 8. Release scope summary

| Release | Includes |
| --- | --- |
| 0.1.0 | Accounts, persons, roles; EN/ES UI; body map front/back; lesions; observations with images, EXIF scrubbing, offline queue, quality warnings; scale references (card, coin, manual); semi-automatic measurement with ±; timeline; reminders (in-app, email); trash/purge; export; backup/restore; SQLite default and PostgreSQL option; CasaOS packaging; PWA |
| 0.2.0 | Side-by-side, overlay, slider, difference; charts; PDF reports EN/ES; "Prepare my visit"; webhooks and ICS; forward-auth SSO mode; first detail views |
| 0.3.0 | Experimental opt-in: assisted segmentation and automatic measurement proposals, framing assessment, re-analysis command, labelling tool; `MODEL_CARD.md`; free lesion selection in reports |
| 0.4.0 | Experimental opt-in: full-body sessions with guided capture, detection, matching and candidate review |
| 1.0.0 | TOTP; scheduled backup verification; accessibility and threat-model reviews; privacy blur; performance pass |
| 1.x | New-lesion detection across sessions, descriptive morphology and colour descriptors, Web Push (flagged), accelerated inference variant, more languages |

## 9. Assumptions to confirm with the PO

1. The uncertainty display switch affects the application only; PDF reports always show ± and the "no detectable change" label (engineering interpretation of answer 28).
2. In PostgreSQL mode the operator runs the database; neVus's backup command dumps it with the PostgreSQL client tools shipped in the image, and the restore command expects the same.
