# Product questions for the Product Owner

Date: 2026-09-23. These questions closed the discovery phase. Every question carries the default the engineering side proposed and the Product Owner's (PO) answer, all recorded on 2026-09-23. Priority: **P0** needed before `PRODUCT_REQUIREMENTS.md`; **P1** needed before the phase that implements the feature. Items marked **DECIDED** earlier in the day are recorded in the ADRs where relevant.

Answers that depart from the proposed default are marked **(departs from default)**.

## 1. Product purpose (P0)

1. **Who is tracked in v1?** *Default:* separate `User` (login) and `Person` (profile being tracked); one user may manage several persons.
   **Answer:** Household model. `User` and `Person` are separate from day one; one login manages several persons (partner, children); a person may receive their own login later.
2. **Unit of value first.** *Default:* per-lesion timeline first, full-body sessions later.
   **Answer:** Per-lesion timeline first; full-body sessions are the Phase 6 differentiator.
3. **Scope of "lesion".** *Default:* moles plus a generic "other mark" type without special handling.
   **Answer:** Moles plus a generic "other mark" type, no special handling.

## 2. UX (P0)

4. **Capture path.** *Default:* native camera by default with a post-capture quality check; live guided capture when a secure context is available.
   **Answer:** Native camera by default; live guided capture (framing, marker) enabled automatically when the context is secure.
5. **Home screen.** *Default:* body map first plus a compact "due for re-photo" strip.
   **Answer:** Body map plus a compact strip with the lesions due and the next appointment.
6. **Onboarding depth.** *Default:* minimal, with contextual empty states that teach.
   **Answer:** Minimal, with empty states that teach.
7. **UI language.** *Default:* English only, strings externalised from day one.
   **Answer (departs from default):** English **and Spanish from 0.1.0**, with a persistent per-user language setting stored with the account (as in Tabernacle).

## 3. Visual identity (P1)

8. **Palette direction.** *Default:* warm neutrals with one calm accent, full dark mode.
   **Answer:** Warm neutrals with one calm accent (teal or moss), full dark-mode support; red is reserved for system errors and never used for lesions.
9. **Body illustration style.** *Default:* flat schematic neutral silhouette.
   **Answer:** Flat schematic silhouette, gender- and skin-tone-neutral.
10. **Tone split.** *Default:* sarcasm in README and marketing, calm in-app microcopy.
    **Answer:** Sarcasm outside (README, marketing), calm and neutral inside the application and the reports.

## 4. Data and privacy (P0)

11. **Authentication.** *Default:* local accounts in 0.1.0; forward-auth SSO option in 0.2.0; TOTP in 1.0.
    **Answer:** Yes, in that order.
12. **Encryption at rest.** *Default:* no app-level encryption; encrypted backups (`age`).
    **Answer:** No application-level encryption; disk or volume encryption is the operator's choice; every backup that leaves the server is encrypted with a passphrase (`age`).
13. **Deletion semantics.** *Default:* trash plus 30-day purge; export offered before deletion.
    **Answer:** Trash with automatic purge after 30 days, including image files; export offered before deletion; deleting a whole profile requires re-authentication.
14. **EXIF policy.** *Default:* strip everything except capture time and orientation; never GPS.
    **Answer:** Strip everything except capture time and orientation; never keep GPS; pixels untouched.
15. **Digital sharing.** *Default:* PDF only; no public exposure.
    **Answer:** PDF only; no share links.

## 5. Photography (P0/P1)

16. **Phones in use.** *Default:* assume both platforms.
    **Answer:** Android and iOS; end-to-end tests on both engines.
17. **Originals.** *Default:* keep full-resolution originals, immutable.
    **Answer:** Always keep the full-resolution original, immutable.
18. **Quality gate behaviour.** *Default:* warn and allow with a visible flag; block only unreadable files.
    **Answer:** Warn and allow; the observation is marked "saved with quality warnings" in the timeline and reports; only unreadable files are blocked.
19. **Images per observation.** *Default:* one or more, with roles.
    **Answer:** One or more images per observation, each with a role (overview, close-up, with scale reference).
20. **Dermatoscope attachments.** *Default:* record a capture "modality" tag from day one.
    **Answer:** No dermatoscope planned; record the modality tag from day one anyway.
21. **Intimate regions in zone/full-body photos.** *Default:* skippable zones from day one; blur tool in the hardening phase.
    **Answer:** Zones skippable from v1; privacy-blur tool for stored zone photos in the hardening phase (1.0).

## 6. Body mapping (P0)

22. **Granularity.** *Default:* named zones plus a free point inside the zone (hybrid).
    **Answer:** Hybrid: named zones plus a free point inside the zone, on front and back SVG silhouettes.
23. **Extra views.** *Default:* front/back in v1; detail views progressively.
    **Answer:** Front and back in v1; detail views (face, scalp, hands, feet) added progressively.
24. **Body types.** *Default:* one neutral silhouette.
    **Answer:** One neutral silhouette; child scaling later if needed.
25. **3D body.** *Default:* out of scope.
    **Answer:** Out of scope.

## 7. Measurements (P1)

26. **Reference objects.** *Default:* printed neVus card primary; Euro coins secondary; manual two-point scale fallback.
    **Answer:** Printed neVus reference card (marker, mm scale, grey patch) as primary; Euro coins as secondary; manual two-point line as fallback.
27. **Measurement mode.** *Default:* semi-automatic with mandatory manual override.
    **Answer:** Semi-automatic (tap, proposed outline or diameter) with manual correction always available; nothing is saved without confirmation.
28. **Uncertainty display.** *Default:* always show ±; never present sub-uncertainty differences as change.
    **Answer (departs from default):** Uncertainty display is **enabled by default and can be switched off in the settings page**. Confirmed by the PO later the same day: the switch affects in-app display only; PDF reports always show ± and the "no detectable change" classification.

## 8. Reminders (P1)

29. **Channels.** *Default:* in-app + email in 0.1.0; webhook + ICS in 0.2.0; Web Push behind a flag later.
    **Answer:** As proposed: in-app and email (SMTP) in 0.1.0; outgoing webhook (Home Assistant, n8n, ntfy, Gotify presets) and ICS calendar feed in 0.2.0; Web Push behind a feature flag later.
30. **Defaults.** *Default:* 3 months per lesion, 12 months per full-body session.
    **Answer:** 3 months per lesion (overridable per lesion), 12 months per full-body session; snooze options of 1 week and 1 month.
31. **Appointment-driven mode.** *Default:* "Prepare my visit" as the primary engagement loop.
    **Answer:** Yes: "Prepare my visit" (appointment date → lesions due → guided capture → report) is the primary flow, shipped with reports in 0.2.0; periodic reminders are secondary.

## 9. Medical reports (P1)

32. **Report language.** *Default:* English and Spanish templates when reports arrive.
    **Answer:** English and Spanish templates from the first report release; language selectable per report.
33. **Report scopes.** *Default:* single lesion plus profile summary in v1.
    **Answer:** Single lesion and profile summary first; free selection of lesions in a later iteration.
34. **Paper.** *Default:* A4, with US Letter as an option.
    **Answer:** A4 by default, US Letter as an option.

## 10. Computer vision / ML (P1/P2)

35. **Model distribution.** *Default:* classical CV always bundled; learned models as an optional pack.
    **Answer:** Classical CV always bundled; small models (up to about 40 MB) inside the image; larger models in a separate image variant; nothing is downloaded at runtime.
36. **Priority order.** *Default:* quality gate → segmentation/measurement → same-lesion alignment/change → session matching → new-lesion candidates.
    **Answer:** Confirmed.
37. **Hard no-go.** **DECIDED:** no malignancy classifier or risk score, ever ([ADR-0003](adr/0003-automatic-analysis-boundary.md)).
38. **Automatic-analysis boundary (regulatory).** **DECIDED:** automatic analyses are opt-in per profile, off by default, labelled experimental and always user-confirmed, with an explicit intended-use statement and a CI lint on user-facing language ([ADR-0003](adr/0003-automatic-analysis-boundary.md)).
39. **Personal evaluation set.** *Default:* yes.
    **Answer:** Yes: the PO will label a small personal set (tens of photos with the card at known distances, reviewed contours); neVus ships a minimal labelling tool; the data never leaves the server.
40. **CPU-only inference.** *Default:* yes; iGPU acceleration only if it pays off later.
    **Answer:** CPU-only in v1 (small quantised models, one low-priority worker); iGPU acceleration only if it pays off later.

## 11. Multi-user (P0)

41. **Roles.** *Default:* admin/member plus explicit per-person sharing.
    **Answer:** Admin and member roles plus per-person access (owner, manager, viewer), so two adults can manage a child's profile.
42. **Registration.** *Default:* closed; admin creates accounts; first-run claim flow.
    **Answer:** Closed registration; the admin creates accounts; the first person in claims the instance and becomes admin.

## 12. CasaOS deployment (P0)

43. **Access path and internal CA trust.** *Why:* decides whether live camera, PWA installation and offline mode work on day one.
    **Answer:** The PO's phones already trust the internal certificate authority used by the reverse proxy, so HTTPS is valid on mobile from day one; live camera, PWA installation and the offline capture queue are available in v1.
44. **Database.** *Default:* SQLite in a single container.
    **Answer (departs from default):** SQLite in a single container by default, **with a configurable external PostgreSQL option**. Both dialects are supported and exercised in CI. Confirmed later the same day: in PostgreSQL mode the database backup is the operator's responsibility; neVus backs up the image store and a manifest only.
45. **Backups.** *Default:* nightly, encrypted, 30 daily / 12 monthly.
    **Answer:** Nightly encrypted snapshot (`age`, passphrase) under the app's data directory, picked up by the operator's existing backup job; retention 30 daily and 12 monthly; command-line restore tested in CI.
46. **Architectures.** *Default:* amd64 first, arm64 when cheap.
    **Answer:** amd64 first (all builds); arm64 added on release and tag builds with a boot test, when the wheels allow.

## 13. App store integration

47. **Store identity.**
    **Answer:** Display name **"jalmena store"**; the internal `store_id` stays unchanged.
48. **Rename now or later?** *Default:* Step 1 now, Step 2 later.
    **Answer:** The PO renamed the repository to `jalmena/jalmena-appstore` on 2026-09-23. Verified the same day: the old `raw.githubusercontent.com` and jsDelivr URLs still answer 200 with identical `Content-Length` and no redirect, and `github.com` redirects. Step 1 (content migration) is pending and must also update the base URL and README to the new name.
49. **Category for neVus.** *Default:* `Others`.
    **Answer:** `Others`.

## 14. Open source / licensing (P0)

50. **Licence.** **DECIDED:** AGPL-3.0-only.
51. **Relationship to MoleMapper.** *Default:* "inspired by", BSD notice preserved, no marks, no endorsement.
    **Answer:** As written in the README and `THIRD_PARTY_NOTICES.md`.
52. **Repository visibility.** **DECIDED:** public from day one.
53. **Contributions.** *Default:* DCO sign-off, no CLA; Conventional Commits enforced by CI.
    **Answer:** DCO without CLA; Conventional Commits checked in CI.

## 15. Branding (P1)

54. **Name.** **DECIDED:** wordmark `neVus` ("nevus vs. us"); identifiers lowercase `nevus` ([NAME_CHECK.md](research/NAME_CHECK.md)).
55. **Mark direction.** *Default:* the V as two observation lines converging on a dot.
    **Answer:** explored over five rounds of sketches.
    **Settled (same day, after five rounds):** the divider mark, with a hinge hole of half the disc's diameter in the inverse colour; the mark stands in for the V of the wordmark. See `docs/design/brand/identity/`.
    **Approved by the PO (same day):** the mark and the wordmark are always shown on the dark background.
56. **Type character.** *Default:* quiet humanist sans, self-hosted.
    **Answer:** A quiet humanist sans-serif with its own character, libre licence, self-hosted, tabular figures for measurements.
    **Revised (same day):** for the wordmark, a typeface whose letterforms are as symmetric as possible (geometric); several wordmarks in candidate typefaces to be offered. The interface typeface follows the wordmark's choice where legibility allows.
    **Settled (same day):** wordmark in B612 Bold (wordmark only) with the mark as the V, optically centred; interface in Epilogue, body 500, secondary 400, emphasis 600, tabular figures.
57. **Tagline.** *Default:* "Evidence, not memory." for the product.
    **Answer (departs from default):** The product tagline is **"Because 'I think it was smaller' is not data."** The other candidate lines may be used in README copy.
