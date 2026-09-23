# neVus

**Evidence, not memory.**

neVus is a self-hosted application for keeping a longitudinal photographic record of your moles and other skin marks: where each one sits on your body, what it looked like on each date, how large it measured against a physical reference, and how those numbers moved between dermatology visits.

Your dermatologist has hundreds of patients and approximately seven minutes. Your mole does not care. When the question "has this changed since last time?" comes up, neVus exists so that the answer is a dated series of measured photographs rather than "I think it was a little smaller".

> **Status: Phase 0, discovery.** There is nothing to install yet. This repository holds the audits, research and decisions that come before the first line of application code. The [roadmap](#roadmap) says what comes next.

## What neVus is

- A personal record on your own server. Photos and measurements never leave the machine you run it on. No cloud, no account with anyone, no telemetry.
- A body map to register marks, a timeline of observations per mark, side-by-side and overlay comparison, measurements with their uncertainty, reminders, and printable reports to take to an appointment.
- Built for a phone in front of a bathroom mirror and for a browser on a desk, packaged for CasaOS and for plain Docker Compose.

## What neVus is not

neVus is not a diagnostic tool and does not assess risk. It will never compute a melanoma probability, an ABCDE score or a "see a doctor" alert. Every automated result, whether a measurement, an alignment or a candidate mark in a later photo, is presented as an observation with its uncertainty, for you to confirm or discard and for a clinician to interpret. The intended use is documentation and measurement support for a conversation with a professional. The reasoning behind this boundary is recorded in [ADR-0003](docs/adr/0003-automatic-analysis-boundary.md).

## Why

Remembering what a mole looked like eight months ago is not exactly a controlled clinical measurement. Dermatologists rarely have the time or the equipment to photograph and measure every lesion of every patient at every visit, so the longitudinal evidence, when it exists at all, lives in the patient's memory. neVus moves it into dated, measured, comparable records that fit in a PDF.

## Relationship to MoleMapper

neVus is inspired by [MoleMapper](https://github.com/ohsu-molemapper/MoleMapper_Final), the iOS research app released by Oregon Health & Science University under a BSD licence. It is a clean reimplementation for a self-hosted web stack, not a fork: the zone taxonomy, the zone geometry, the coin table and the tap-to-fit measurement idea are ported with the OHSU notice preserved in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Everything else is new. neVus is not affiliated with or endorsed by OHSU, Sage Bionetworks or the MoleMapper study; "MoleMapper" is their trademark. The audit that led to this decision is in [docs/audits/MOLEMAPPER_AUDIT.md](docs/audits/MOLEMAPPER_AUDIT.md) and the decision itself in [ADR-0002](docs/adr/0002-reimplement-instead-of-fork.md).

## Roadmap

| Phase | Release | What becomes possible |
| --- | --- | --- |
| 0 — Discovery | — | Audits, research, product questions, requirements, architecture, design brief |
| 1 — Foundation | internal | Accounts and profiles, photo ingestion with metadata scrubbing, the design system, the application shell |
| 2 — Deployment | first release candidate | Container image, CasaOS app store entry, backup and restore |
| 3 — Core tracking | 0.1.0 | Body map, marks, photographed observations with a quality check, measurement in millimetres against a printed card or a coin, timelines, reminders, encrypted export |
| 4 — Comparison and reports | 0.2.0 | Side-by-side, overlay and difference views, measurement charts, PDF reports, "prepare my visit" |
| 5 — Computer vision | 0.3.0 | Assisted segmentation and measurement, framing checks, reproducible analysis records (opt-in, experimental) |
| 6 — Full-body sessions | 0.4.0 | Guided zone-by-zone capture, matching between sessions, candidate review (opt-in, experimental) |
| 7 — Hardening | 1.0.0 | Second factor, scheduled encrypted backups, accessibility and threat-model reviews |

## Documents

- Audits: [MoleMapper_Final](docs/audits/MOLEMAPPER_AUDIT.md) · [the personal CasaOS app store](docs/audits/APPSTORE_AUDIT.md)
- Research: [landscape of projects, datasets, algorithms and regulation](docs/research/LANDSCAPE.md) · [name check](docs/research/NAME_CHECK.md) · [CasaOS / ZimaOS store conventions](docs/research/CASAOS_STORE_CONVENTIONS.md)
- Product: [questions for the Product Owner](docs/PRODUCT_QUESTIONS.md)
- Decisions: [architecture decision records](docs/adr/README.md)
- Coming next: `PRODUCT_REQUIREMENTS.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `DEVELOPMENT.md`, `DEPLOYMENT.md`, `SECURITY.md`, `PRIVACY.md`, `MODEL_CARD.md`

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). Everything in this repository is written in English. Branches follow GitFlow, commits follow Conventional Commits with a DCO sign-off, and pull requests need green checks. Never attach photographs of real people to issues or pull requests; synthetic fixtures exist for that.

## Licence

neVus is licensed under the GNU Affero General Public License, version 3.0 only. See [LICENSE](LICENSE). Notices for third-party material are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
