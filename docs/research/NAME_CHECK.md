# Name check: "Nevus" / neVus

Date: 2026-09-23. Purpose: check whether the working name "Nevus" collides with existing products, trademarks, repositories, packages or domains, and whether it carries unintended diagnostic implications. Checked with app-store lookup APIs, the GitHub API, package-registry APIs and RDAP/WHOIS. Official trademark databases could not be queried automatically, so this is not a clearance.

## Decision

The Product Owner chose the wordmark **neVus**, read as an abbreviation of "nevus vs. us", with all identifiers in lowercase `nevus` (`jalmena/nevus`, `ghcr.io/jalmena/nevus`, compose `name: nevus`, `io.github.jalmena.nevus`, PyPI `nevus`). The soft conflicts below stay documented; the mitigation is the intended-use statement and calm in-app language (see [ADR-0003](../adr/0003-automatic-analysis-boundary.md)). Revisit only if a conflict materialises.

## 1. Existing products using the name

| Product | What it is | Status | Conflict |
| --- | --- | --- | --- |
| Nevus AI (FatCube Limited, UK; <https://apps.apple.com/us/app/nevus-ai/id6502666699>, Android `com.nevus_app`) | Melanoma risk assessment plus mole tracking; iOS (released 2025-06-24) and Android (100+ installs, updated 2026-06-03); describes itself as a "registered Class I medical device with the MHRA (UK)", UK-only, subscription | live (verified via the iTunes API) | High: same name root, same function, diagnostic positioning |
| <https://github.com/nevusapp/nevusapp> (org created 2026-03-15) | German native iOS app "Nevus – iOS App für Nevus-Überwachung": body-region catalogue, photo comparison, reminders, no cloud; README says "production ready – version 1.0" | not found in App Store searches (US/GB/DE/ES) | High: identical name and concept, unpublished |
| nēvus (Rocksauce Studios) | Old "iPhone & Android Skin Companion" | both store listings return 404; page still served at <https://www.nevusapp.com/> (domain re-registered 2026-03-16) | Medium |
| "Родинки" / Nevus (Sedelnikoff N., Android `com.mk24lab.healthskin`) | Android mole app, 1K+ installs | live | Medium-low |
| Look-alikes in the niche: Naevo (iOS mole monitor, 2026-02), Nevio (mole tracker, 2026-08), `margherita-c/nevus_app` (Flutter) | | live | Medium (crowded niche) |
| Nevus Doctor (<https://ehealthresearch.no/en/projects/nevus-doctor>, NCT03246412) | Norwegian research decision-support tool for GPs | research | Low |
| Nevus Outreach (<https://www.nevus.org/>) | US nonprofit for congenital nevi; holds nevus.org since 1997 | active | Low for trademarks; dominates search results |
| Nevu (<https://github.com/Ipmake/NevuForPlex>, image `ipmake/nevu`, in the TrueNAS catalogue) | Self-hosted Plex UI | active | Medium: one letter off, same NAS/self-hosted channel |

## 2. Trademarks

- Official databases could not be checked automatically: USPTO sits behind a JavaScript challenge; EUIPO TMview reset the connection; eSearch plus is a single-page app; Justia, Trademarkia, uspto.report and UK IPO returned 403. Web searches found no "NEVUS" word mark, only unrelated NEVA/NVUS/NOVUS. This is inconclusive, not a clearance.
- Manual check before any public launch: TMview (<https://www.tmdn.org/tmview/>), EUIPO eSearch (<https://euipo.europa.eu/eSearch/>), USPTO (<https://tmsearch.uspto.gov/>), WIPO (<https://branddb.wipo.int/>); Nice classes 9, 10, 42 and 44; offices EM, ES and WO.
- Registrability (inference, not legal advice): "nevus / naevus / nevo / Nävus" is the generic medical word in EU languages, so NEVUS for mole-tracking software would probably be refused as descriptive (EUTMR Art. 7(1)(b)/(c); US Lanham Act §2(e)(1)). That means neither we nor anyone else can likely own NEVUS alone for this product. Composite marks such as "NEVUS AI" and passing-off claims remain possible.

## 3. GitHub

- `jalmena/nevus` is free (now taken by this project).
- `github.com/nevus` is a dormant personal account (created 2011, no public repositories), so a `nevus` organisation is not available; GitHub's name-squatting policy might release it on request, without guarantee.
- Also taken: `nevusapp` (org), `naevus` (user), `nevi` (user). Free: `nevus-app`, `nevushq`, `getnevus`, `nevus-dev`, `nevus-org`, `nevuslog`, `nevus-tracker`.
- Repository search for "nevus" is dominated by NevuForPlex, melanoma-vs-nevus machine-learning repositories and the two mole apps above.

## 4. Package and container names

| Registry | `nevus` |
| --- | --- |
| npm | Taken: <https://www.npmjs.com/package/nevus> 0.0.1, an unrelated "Nevus ordering service" SDK (2024). Use `@jalmena/nevus` if ever needed |
| PyPI | Appears free (JSON API 404) |
| crates.io, RubyGems, NuGet | Free (404) |
| Docker Hub | `nevus` is a user account (joined 2022, one repository), so taken |
| `ghcr.io/jalmena/nevus` | Free (own namespace) |

## 5. Domains

| Domain | Result | Method |
| --- | --- | --- |
| nevus.app | not found (probably available) | Google Registry RDAP |
| nevus.dev | not found | Google Registry RDAP |
| nevus.health | not found | rdap.nic.health |
| nevus.sh | not found | WHOIS |
| getnevus.com | not registered | Verisign RDAP |
| nevus.io | registered 2023-06-19 (Namecheap), expires 2027 | WHOIS |

Context: nevus.com registered (1998); nevus.org belongs to Nevus Outreach; nevus.net (2024) parked for sale; nevusapp.com registered 2026-03-16; nevuslog.com and nevustracker.com unregistered. "Not found" may still mean premium or reserved; confirm at a registrar.

## 6. Implications and discoverability

- The word sounds clinical: it is doctors' vocabulary and FatCube uses it for a regulated device. Under the EU MDR a product's intended purpose is read from its labelling and promotional material; a pure photo diary is generally not a medical device, but the name combined with change-detection or risk wording pushes toward MDR Rule 11. Keep an explicit "not a diagnostic tool" statement everywhere the name appears.
- Variants: "Nevus Log" / "Nevus Tracker" read as a logbook but are still descriptive; "Nevi" is noisy (Nevi AI, Nevis, Navi); "Naevus" looks almost like Naevo, an existing mole app.
- Findability is poor: web searches for "nevus" return Wikipedia, DermNet and Healthline; GitHub searches return ML classifiers. People will find the project with "nevus self-hosted" or "nevus CasaOS". Fine for a personal store, weak for public adoption.

## 7. Verdict

- No blocking registered mark found (unverified in the official databases).
- Every identifier needed is free: `jalmena/nevus`, `ghcr.io/jalmena/nevus`, `io.github.jalmena.nevus`, compose `name: nevus`.
- Real soft conflicts: Nevus AI (same function, regulated device, in the stores since 2025), the `nevusapp` project (identical concept), npm `nevus`, Nevu in the self-hosted channel, and a generic, hard-to-protect brand.
- Fallbacks screened quickly (no trademark search): Molenote (.app/.dev unregistered, npm free, GitHub user exists, .com taken), MoleMinder (GitHub handle, .app, .dev and npm free, .com taken), Freckly (.app/.dev unregistered, npm free, GitHub user exists, .com taken). Kept only for reference.
