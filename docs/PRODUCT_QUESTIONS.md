# Product questions for the Product Owner

Date: 2026-09-23. These questions close the discovery phase. Each carries the default the engineering side will apply unless the Product Owner (PO) answers otherwise, so the whole list can be answered as "defaults OK except …". Priority: **P0** needed before `PRODUCT_REQUIREMENTS.md`; **P1** needed before the phase that implements the feature; **P2** can be postponed.

Decided items are marked **DECIDED** and recorded in the ADRs where relevant.

## 1. Product purpose (P0)

1. **Who is tracked in v1?** Only the PO, or a household where one login manages several people (partner, children)? *Why:* decides whether `User` (login) and `Person` (the profile being tracked) are separate entities from day one. *Default:* separate `User` and `Person`; one user may manage several persons.
   **Answer:** _pending_
2. **Unit of value first:** per-lesion timeline (MoleMapper-style) first, full-body sessions later? *Default:* yes; lesion timeline first, full-body sessions as the Phase 6 differentiator.
   **Answer:** _pending_
3. **Scope of "lesion":** pigmented lesions/moles only, or any skin mark worth following (scars, patches, rashes)? *Why:* affects taxonomy, measurement methods and language. *Default:* moles plus a generic "other mark" type without special handling.
   **Answer:** _pending_

## 2. UX (P0)

4. **Capture path:** native camera through the file picker (works over plain HTTP, best image quality, no live guidance) vs in-browser live camera with a framing overlay (needs HTTPS). *Default:* native camera by default with a post-capture quality check; live camera as an enhancement when a secure context is available.
   **Answer:** _pending_
5. **Home screen:** body map first plus a compact "due for re-photo" strip? *Default:* yes.
   **Answer:** _pending_
6. **Onboarding depth:** minimal (technical user) or a first-run guided walkthrough? *Default:* minimal, with contextual empty states that teach.
   **Answer:** _pending_
7. **UI language:** English only, with strings externalised from day one so Spanish can be added? *Default:* yes.
   **Answer:** _pending_

## 3. Visual identity (P1)

8. **Palette direction:** (a) warm neutrals with one calm accent (teal/moss), observational rather than clinical; (b) cool clinical white/blue; (c) dark-first. *Default:* (a) with full dark-mode support.
   **Answer:** _pending_
9. **Body illustration style:** flat schematic neutral silhouette (gender-neutral, skin-tone-neutral outline) vs realistic anatomy. *Default:* flat schematic.
   **Answer:** _pending_
10. **Tone split:** the sarcastic tone lives in the README and marketing copy; in-app microcopy stays calm and neutral. *Default:* yes.
    **Answer:** _pending_

## 4. Data and privacy (P0)

11. **Authentication:** local accounts (argon2id, server sessions) in 0.1.0; optional trusted-header SSO through the PO's reverse proxy and identity provider (forward-auth pattern) in 0.2.0; TOTP in 1.0. *Default:* yes, in that order.
    **Answer:** _pending_
12. **Encryption at rest:** rely on disk/volume encryption plus encrypted backups, or add app-level encryption of images and database (more complexity, key management)? *Default:* no app-level encryption; encrypted backups (`age`) yes.
    **Answer:** _pending_
13. **Deletion semantics:** immediate hard delete vs trash with a 30-day purge (images included). *Default:* trash plus purge; export offered before deletion.
    **Answer:** _pending_
14. **EXIF policy:** strip everything except capture time and orientation; never keep GPS; optionally keep the camera model for quality analytics. *Default:* as stated.
    **Answer:** _pending_
15. **Digital sharing:** PDF export only (no share links) in v1? *Default:* PDF only; no public exposure ever by default.
    **Answer:** _pending_

## 5. Photography (P0/P1)

16. **Phones in use:** Android, iOS, or both? *Why:* iOS Safari limits PWA, camera and push differently. *Default:* assume both.
    **Answer:** _pending_
17. **Originals:** always keep full-resolution originals (roughly 3–8 MB each)? *Default:* yes, immutable.
    **Answer:** _pending_
18. **Quality gate behaviour:** block saving on poor quality, or warn and allow with a visible flag? *Default:* warn and allow; block only unreadable files.
    **Answer:** _pending_
19. **Images per observation:** allow several with roles (overview, close-up, with reference)? *Default:* yes, one or more.
    **Answer:** _pending_
20. **Dermatoscope attachments:** does the PO own or plan a smartphone dermatoscope? *Default:* record a "modality" tag from day one, no special processing.
    **Answer:** _pending_
21. **Intimate regions in zone/full-body photos:** zones are always user-selectable (any can be skipped); add a privacy-blur tool for stored zone photos in a later phase? *Default:* skippable zones from day one; blur tool in Phase 7.
    **Answer:** _pending_

## 6. Body mapping (P0)

22. **Granularity:** named zones (MoleMapper style) plus a free point inside the zone, on front/back SVG silhouettes. *Default:* yes (hybrid).
    **Answer:** _pending_
23. **Extra views:** face/scalp, hands, feet, left/right side views. *Default:* front/back in v1; detail views added progressively.
    **Answer:** _pending_
24. **Body types:** one neutral silhouette or selectable variants (adult/child, body shapes)? *Default:* one neutral silhouette; child scaling later if needed.
    **Answer:** _pending_
25. **3D body:** out of scope? *Default:* out of scope (complexity vs value for personal use).
    **Answer:** _pending_

## 7. Measurements (P1)

26. **Reference objects actually available:** Euro coins, a printed neVus reference card (marker plus mm scale, designed by the project), a ruler, a bank card (85.60 × 53.98 mm). *Default:* printed reference card as primary (robust detection, known geometry), Euro coins as secondary, a manual two-point scale as fallback.
    **Answer:** _pending_
27. **Measurement mode:** semi-automatic (detected outline/diameter, always user-adjustable) vs manual only. *Default:* semi-automatic with a mandatory manual override.
    **Answer:** _pending_
28. **Uncertainty display:** show a ± range (e.g. 4.4 ± 0.3 mm) and never present sub-uncertainty differences as change. *Default:* yes.
    **Answer:** _pending_

## 8. Reminders (P1)

29. **Channels:** in-app due list; email (SMTP); outgoing webhook with presets for Home Assistant, n8n, ntfy and Gotify; ICS calendar feed; Web Push (needs HTTPS and relays through browser vendors' push services). *Default:* in-app plus email in 0.1.0; webhook plus ICS in 0.2.0; Web Push behind a flag later.
    **Answer:** _pending_
30. **Defaults:** global default interval (3 months) with per-lesion override; snooze semantics; full-body session cadence (12 months). *Default:* 3 months / 12 months.
    **Answer:** _pending_
31. **Appointment-driven mode:** a "Prepare my visit" flow (enter the appointment date → checklist of lesions due → guided capture → report) as the primary engagement loop, periodic reminders secondary. *Why:* MoleMapper saw near-zero habit formation and a 2020 randomised trial found monthly reminders gave no benefit. *Default:* yes.
    **Answer:** _pending_

## 9. Medical reports (P1)

32. **Report language:** ship report templates in English and Spanish (UI stays English)? *Why:* the brief allows other languages when there is a product requirement; the dermatologist may read Spanish. *Default:* both templates when reports arrive (0.2.0); language selectable per report.
    **Answer:** _pending_
33. **Report scopes:** single lesion; selected lesions; whole-profile summary (body map, list, highlights). *Default:* single lesion plus profile summary in v1.
    **Answer:** _pending_
34. **Paper:** A4, with US Letter as an option. *Default:* as stated.
    **Answer:** _pending_

## 10. Computer vision / ML (P1/P2)

35. **Model distribution:** bundle small models in the image (+100–300 MB) vs an optional, checksum-verified model pack fetched once from GitHub Releases. *Default:* classical CV always bundled; learned models as an optional pack.
    **Answer:** _pending_
36. **Priority order:** quality gate → segmentation/measurement → same-lesion alignment/change → session matching → new-lesion candidates. *Default:* confirmed.
    **Answer:** _pending_
37. **Hard no-go:** no malignancy classifier or risk score, not even "experimental", in the shipped UI. **DECIDED:** no-go (see [ADR-0003](adr/0003-automatic-analysis-boundary.md)).
38. **Automatic-analysis boundary (regulatory).** **DECIDED:** automatic analyses (segmentation, change flags, new-lesion candidates) are opt-in per profile, off by default, labelled experimental and always user-confirmed, with an explicit intended-use statement and a CI lint that keeps disease names, risk words and thresholds out of UI copy and reports ([ADR-0003](adr/0003-automatic-analysis-boundary.md)).
39. **Personal evaluation set:** is the PO willing to label a small set of their own photos to calibrate and evaluate (never leaving their server)? *Default:* yes.
    **Answer:** _pending_
40. **CPU-only inference** on the home server (seconds per image, in the background) acceptable for v1; iGPU acceleration only if it pays off later. *Default:* yes.
    **Answer:** _pending_

## 11. Multi-user (P0)

41. **Roles:** admin vs member plus per-person access (two adults both managing a child's profile)? *Default:* admin/member plus explicit per-person sharing.
    **Answer:** _pending_
42. **Registration:** closed; the admin creates accounts; a first-run claim flow. *Default:* yes.
    **Answer:** _pending_

## 12. CasaOS deployment (P0)

43. **Access path:** an HTTPS hostname behind the PO's reverse proxy with the internal certificate authority, plus VPN for remote access. **Do the PO's phones already trust that internal CA** (does an existing internal HTTPS service show a valid padlock on the phone)? *Why:* decides whether live camera, PWA installation and offline mode are available on day one.
    **Answer:** _pending_
44. **Database:** SQLite in a single container (backup is one directory; no coupling to any shared database container). Object only if there is a reason of the PO's own to prefer PostgreSQL. *Default:* SQLite.
    **Answer:** _pending_
45. **Backups:** destination path under the app's data directory picked up by the PO's existing backup job, encrypted with a passphrase (`age`); retention. *Default:* nightly, encrypted, 30 daily / 12 monthly.
    **Answer:** _pending_
46. **Architectures:** amd64 required; arm64 nice-to-have if CV wheels allow. *Default:* amd64 first, arm64 when cheap.
    **Answer:** _pending_

## 13. App store integration (P0 for the store, P1 for the neVus entry)

47. **Store identity:** display name and one-line description for the personal store, and an icon direction. The internal `store_id` stays unchanged regardless (the specification requires stability).
    **Answer:** _pending_
48. **Rename now or later?** Step 1 (content migration) now; Step 2 (repository rename) later, only after verifying redirects on a throwaway repository. *Default:* Step 1 now, Step 2 later.
    **Answer:** _pending_
49. **Category for neVus:** there is no Health category in the fixed v2 list (`Media, Productivity, Home, Networking, AI, Finance, Social, Developer, Others`). *Default:* `Others`; alternative `Home`.
    **Answer:** _pending_

## 14. Open source / licensing (P0)

50. **Licence.** **DECIDED:** AGPL-3.0-only. MoleMapper's BSD-3 notices are preserved in `THIRD_PARTY_NOTICES.md`.
51. **Relationship to MoleMapper:** "inspired by MoleMapper (OHSU)", BSD notice preserved, no OHSU/MoleMapper branding, no implied endorsement. *Default:* yes.
    **Answer:** _pending_
52. **Repository visibility.** **DECIDED:** public from day one.
53. **Contributions:** DCO sign-off, no CLA; Conventional Commits enforced by CI. *Default:* yes.
    **Answer:** _pending_

## 15. Branding (P1)

54. **Name.** **DECIDED:** wordmark `neVus` ("nevus vs. us"); identifiers lowercase `nevus`. Findings in [NAME_CHECK.md](research/NAME_CHECK.md).
55. **Mark direction,** anchored by the capital V: (a) the V as two observation lines converging on a dot (the mole under watch); (b) a dot with concentric time rings where one ring opens into a V; (c) a pure typographic wordmark with the V as the only accent colour. *Default:* (a), with (c) as the compact/favicon fallback.
    **Answer:** _pending_
56. **Type character:** a neutral system-like humanist sans vs a more distinctive self-hosted typeface. *Default:* distinctive but quiet humanist sans, self-hosted (no third-party font services at runtime).
    **Answer:** _pending_
57. **Tagline tone:** "Evidence, not memory." / "Your moles, on the record." / "Because 'I think it was smaller' is not data." *Default:* "Evidence, not memory." for the product; the longer sarcastic lines for the README.
    **Answer:** _pending_
