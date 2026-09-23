# neVus — Roadmap

Baseline 2026-09-23. Phases are ordered so that every release is useful on its own and each one feeds the next with better data. Sizes are relative effort: S (days), M (one to two weeks), L (several weeks), XL (a quarter or more of part-time work). Details of scope live in [`PRODUCT_REQUIREMENTS.md`](PRODUCT_REQUIREMENTS.md); structure in [`ARCHITECTURE.md`](ARCHITECTURE.md).

| Phase | Release | Slice that makes it demoable | Exit criteria | Size |
| --- | --- | --- | --- | --- |
| 0 — Discovery | — | Audits, landscape, name check, product questions, requirements, architecture, roadmap, design brief, reference-card specification | Documents merged; PO answers recorded | S |
| 1 — Foundation | internal | Repository scaffold, GitFlow, CI; FastAPI with `/healthz`; local accounts and claim flow; users, persons, access roles; SQLite and PostgreSQL through one data layer with migrations; content-addressed image store with metadata scrubbing and renditions; React shell with tokens, core components, EN/ES strings and PWA manifest. Demo: log in on a phone, upload a photo, see a scrubbed thumbnail | CI green on both database engines; container boots as non-root with PUID/PGID | M |
| 2 — Deployment | first release candidate | Container image with size budget, compose with `x-casaos`, publish workflow to ghcr.io, entry in "jalmena store", deployment guide (reverse proxy with internal CA, VPN, HTTPS), backup and restore commands with a nightly snapshot. Demo: install from the store, open over HTTPS on a phone, install the PWA | Backup → wipe → restore round trip passes in CI and on the home server | S/M |
| 3 — Core tracking | **0.1.0** | Body map front/back with markers; lesions; observations with roles and modality; live guided capture in secure contexts; offline queue; quality warnings; reference card, Euro coins and manual scale; semi-automatic measurement with ±; timeline; in-app and email reminders; trash, export, settings (language, theme, uncertainty switch, experimental switch). Useful without any learned model | Measurement of the printed test disc within tolerance on fixture photos; accessibility checks pass; first real observations recorded by the PO | L |
| 4 — Comparison and reports | 0.2.0 | Side-by-side, overlay, slider and difference views with abstaining alignment; charts with uncertainty bands; PDF reports EN/ES (lesion, profile summary); "Prepare my visit"; webhooks and ICS; forward-auth SSO mode; first detail views | A report accepted by the PO's dermatologist as useful; alignment abstains on unrelated pairs in tests | M |
| 5 — Assisted analysis | 0.3.0 | Analyzer framework in earnest behind the experimental switch: assisted segmentation, automatic measurement proposals, framing assessment, re-analysis command, labelling tool for the personal evaluation set, `MODEL_CARD.md`; free lesion selection in reports | Evaluation gates on licence-clean sets and the personal set pass per skin tone; every model has a card | L (XL with own training) |
| 6 — Full-body sessions | 0.4.0 | Zone-by-zone guided protocol with skippable zones; lesion detection on zone photos; matching against the registry; candidate review; session comparison | Matching precision and recall measured on the UPMC longitudinal set and the personal set; candidates always reviewable | XL |
| 7 — Hardening | **1.0.0** | TOTP; scheduled backup verification; accessibility audit; threat-model review; privacy-blur tool; performance pass on the home server; documentation complete | Audit findings closed; restore drill documented; no open high or critical findings | M |
| 8 — Beyond | 1.x | New-lesion detection across sessions, descriptive morphology and colour descriptors, Web Push behind a flag, accelerated inference image variant if latency demands, more languages | Each item behind its own evaluation gate | open |

## Dependencies between phases

- Phase 3 depends on the reference card design (Phase 0 specification, printable generator in Phase 3) and on the image store and scrubbing from Phase 1.
- Phase 4's alignment and Phase 5's segmentation depend on the analyzer framework and versioned analysis records introduced in Phase 3 in their minimal form.
- Phase 6 depends on the detection and matching evaluation sets being assembled during Phase 5.
- The store entry (Phase 2) depends on the personal store's multi-app migration, tracked in the store repository.

## Risks carried into the plan

| Risk | Mitigation |
| --- | --- |
| Inference latency on a low-power CPU | Small quantised models on 512 px crops; one low-priority worker; measured budgets in CI; an accelerated image variant as escape hatch |
| Camera and HTTPS on phones | Native capture always works; guided capture only in secure contexts; installation guide for the internal certificate authority |
| Measurement accuracy claims | Uncertainty everywhere; planar reference card preferred over coins; tilt gate; "no detectable change" label |
| Skin-tone bias in detection and segmentation | Stratified evaluation with per-group gates; user-correctable results; limitations stated in the model card |
| Scope creep in machine learning | Classical baselines first; every model needs a card and an evaluation gate; automatic features stay behind the experimental switch |
| Regulatory perception | Intended-use statement everywhere; descriptive-language lint; no risk outputs, ever |
| Data loss | Content-addressed immutable originals, WAL, nightly encrypted snapshots, restore round trip in CI, integrity verification command |

## Versioning and releases

Semantic Versioning with the 0.x caveat that minor versions may break compatibility until 1.0.0; every release note says what changed for operators. Tags `vX.Y.Z` create a GitHub Release, container images on ghcr.io and an update pull request in the personal store.
