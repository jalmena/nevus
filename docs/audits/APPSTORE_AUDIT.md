# Audit: `jalmena/tabernacle-appstore` and its evolution into a multi-app personal store

Date: 2026-09-23. Scope: the maintainer's CasaOS/ZimaOS app store repository, which today distributes a single application (Tabernacle) and must become the personal store that also distributes neVus without breaking the existing Tabernacle installation. Method: inspection of the local clone and of the published `gh-pages` branch, plus the conventions documented in [CasaOS / ZimaOS third-party app store conventions](../research/CASAOS_STORE_CONVENTIONS.md).


> **Update, 2026-09-23.** The maintainer renamed the repository to `jalmena/jalmena-appstore` after this audit was written. Verified the same day: the old `raw.githubusercontent.com` feed URLs and the old jsDelivr base URL still answer HTTP 200 with the same `Content-Length` and no redirect, and `github.com` redirects with 301, so subscribed CasaOS and ZimaOS clients are unaffected. Step 2 below is therefore done; Step 1 must additionally update the `base-url` in both workflows and `scripts/build.sh`, and the README, to the new name, while documenting that the old URLs remain valid. The display name chosen by the maintainer is "jalmena store"; neVus goes under the `Others` category.

## 1. Current structure

Tracked files:

```text
.github/workflows/release.yml     tag v* → build → deploy dist/ to gh-pages
.github/workflows/validate.yml    PR/push → docker compose config + build
Apps/Tabernacle/docker-compose.yml
Apps/Tabernacle/icon.svg
Apps/Tabernacle/screenshot-1..3.png
Apps/Tabernacle/thumbnail.png
README.md
category-list.json                one category: Media
scripts/build.sh                  local build, same engine as the workflow
store-config.json                 store_id jalmena-tabernacle, name "Tabernacle"
supported-languages.json          ["en_US"]
```

`dist/` and `.cache/` are build output and are ignored.

## 2. CasaOS integration

- The app definition follows the v1 + v2 dual convention: compose `name: tabernacle`, `x-casaos.id: io.github.jalmena.tabernacle`, pinned semver image `ghcr.io/jalmena/tabernacle:0.6.0`, lowercase locale keys (`en_us`), absolute asset URLs on `raw.githubusercontent.com/...@main`, `version`/`update_at`/`release_notes` maintained by hand, service-level `x-casaos` descriptions for env/ports/volumes, a Docker healthcheck, `/DATA/AppData/tabernacle/data` as the data volume, host port 8440 chosen to avoid collisions with the official and BigBear stores.
- Store identity: `store-config.json` v2, `store_id: jalmena-tabernacle`, display name "Tabernacle", description and icon pointing at the Tabernacle assets.
- Published feed URLs already in use by subscribers (the compatibility contract):
  - CasaOS v1 zip: `https://raw.githubusercontent.com/jalmena/tabernacle-appstore/gh-pages/tabernacle-appstore.zip`
  - v2: `https://raw.githubusercontent.com/jalmena/tabernacle-appstore/gh-pages/index.json` (advertised) and `.../store.json` (present); `base_url` = `https://cdn.jsdelivr.net/gh/jalmena/tabernacle-appstore@gh-pages`.

## 3. GitHub Actions and release mechanism

- `validate.yml` (PR, push to `main`): `docker compose -f Apps/Tabernacle/docker-compose.yml config -q` (hard-coded single app), then `IceWhaleTech/build-appstore-action@v1` with the jsDelivr base URL and the two cache files, then `zip -qr dist/tabernacle-appstore.zip Apps category-list.json`, then asserts `index.json`, `store.json` and the zip exist and lists `dist/` in the step summary.
- `release.yml` (tag `v*`): same build, then `peaceiris/actions-gh-pages@v4` replaces the `gh-pages` branch with `dist/`.
- `scripts/build.sh` downloads the action's `build_appstore.py` and `requirements.txt` at the pinned ref (`v1.1.2`), creates a venv under `.cache/build`, runs the same build and zips the same archive.
- Store tags `v0.4.0`, `v0.5.0`, `v0.6.0` mirror Tabernacle's own versions; commits read "Tabernacle 0.6.0". Store versioning is coupled to the single app.

## 4. What works well

- The v1 zip contains all of `Apps/` and `category-list.json`, so a second app folder is included automatically; the v2 build emits every app it finds.
- Serving the zip from `raw.githubusercontent.com` gives CasaOS a real `Content-Length`, which is the only change signal CasaOS v1 uses. The README documents this correctly.
- Lowercase locale keys, absolute asset URLs and a pinned image tag match the current official conventions.
- The build engine is the official one, pinned, and the local script reproduces the release exactly.

## 5. Findings and risks

| # | Finding | Impact | Fix |
| --- | --- | --- | --- |
| 1 | Store identity (name, description, icon) is Tabernacle's | Confusing once a second app appears | Rename the display identity; **keep `store_id`** (the v2 spec requires it to stay stable once users subscribe) |
| 2 | Store tags mirror one app's version | Impossible with two apps | Decouple: deploy on every push to `main`, tag the store with CalVer for traceability; app versions live only in each compose's `x-casaos.version` |
| 3 | Validate workflow hard-codes one compose file | A broken second app would pass CI | Loop over `Apps/*/docker-compose.yml` and lint the fields the protocol relies on |
| 4 | README advertises `index.json` as the v2 URL | ZimaOS ≥ 1.7 subscribes to `store.json`; whether `index.json` is accepted is untested | Advertise `store.json` |
| 5 | Feed on raw (5-minute cache) while `base_url` is jsDelivr (12-hour cache), no purge | After a release, `index.json` can show a new `content_hash` while `compose`/`meta` still serve old files for hours | Add a jsDelivr purge step after deploy, as the official workflow does, or build with the raw base URL |
| 6 | Built `store.json` lacks the `icon` defined in `store-config.json` | Cosmetic in v2 clients | Check the action version; report upstream if reproducible |
| 7 | Service-level `x-casaos` labels are stripped by the v2 build | Only CasaOS (zip) users see env/port/volume descriptions | Expected; keep them for CasaOS, put essentials in `description`/`tips` too |
| 8 | No port-collision or asset-existence checks | A duplicate host port between two apps would only fail at install time | Lint in CI |
| 9 | Only `en_US` in `supported-languages.json` | Fine (deliberate) | Keep |

## 6. Compatibility contract (must not change)

- Repository path `jalmena/tabernacle-appstore` and the `gh-pages` branch.
- `tabernacle-appstore.zip`, `store.json` and `index.json` at the branch root.
- `store_id: jalmena-tabernacle`.
- Compose `name: tabernacle`, `x-casaos.id: io.github.jalmena.tabernacle`, host port 8440.

CasaOS identifies a subscribed store by its URL (cache directory `/var/lib/casaos/appstore/<host>/<md5 of the URL path>`); keeping the URL working is the whole compatibility requirement for CasaOS v1 clients.

## 7. Migration to a multi-app personal store

Two independent, reversible steps.

### Step 1 — content migration (no rename, zero URL risk)

1. `store-config.json`: keep `store_id`; change display `name`, `description` and `icon` to the personal-store identity (to be chosen by the Product Owner).
2. `category-list.json`: keep `Media`; add the v2-legal category neVus will use (`Others` or `Home`; there is no `Health` in the fixed v2 list).
3. `Apps/Nevus/docker-compose.yml` + `icon.svg` + `thumbnail.png` + screenshots, mirroring the Tabernacle file: compose `name: nevus` (v1 store app id; free in the five large stores; chosen once, never renamed), `x-casaos.id: io.github.jalmena.nevus`, lowercase locale keys, absolute asset URLs, pinned semver image tag, `version`/`update_at`/`release_notes` bumped together, `$PUID`/`$PGID`/`$TZ` built-ins, `index: /`, a distinctive host port checked against the official and BigBear stores, HTTPS/reverse-proxy advice in `description` and `tips.before_install`.
4. `validate.yml`: loop over `Apps/*/docker-compose.yml` (`docker compose config -q` each); lint `name` (`^[a-z0-9_-]+$`) and `x-casaos.id` (reverse-domain, ≥ 2 segments); category in the v2 list; lowercase locale keys; semver `version`; quoted `port_map`; every referenced asset exists; no two apps publish the same host port; the pinned tag exists in the registry (`docker manifest inspect`); no `latest`.
5. Store versioning decoupled from app versions: every push to `main` deploys to `gh-pages`, and the `gh-pages` history (one commit per deploy, naming the source commit) is the release log; no store tags. Add a jsDelivr purge step after deploy.
6. README rewrite: personal store, app list, `store.json` advertised as the ZimaOS URL, the unchanged CasaOS zip URL, a per-app publishing checklist.
7. Keep `tabernacle-appstore.zip` and additionally publish `appstore.zip` (same content) so a future rename can advertise a clean canonical URL while the old one keeps working.

Nothing in Step 1 touches a running Tabernacle install; the only observable change for a subscribed CasaOS is a second app card appearing when neVus is published.

### Step 2 — optional repository rename (`jalmena/tabernacle-appstore` → `jalmena/appstore`)

GitHub redirects git, web and raw URLs of renamed repositories as long as no new repository takes the old name, and CasaOS's Go HTTP client follows redirects. The risk is jsDelivr (`base_url` for v2) and cached CDN paths. Do this only after verifying redirect behaviour on a throwaway repository (rename, then `curl -I` the raw and jsDelivr URLs), updating `base-url` in both workflows and `scripts/build.sh`, and documenting the new canonical URL while stating that the old one remains valid. Never create a new repository under the old name.

## 8. Requirements this places on the neVus application

- Answer `GET /` with HTTP 200 (the application shell) even when nobody is logged in; CasaOS's health/open check accepts only 200 or 401 and a redirect to a login page fails it.
- Publish multi-arch images for every architecture declared in `x-casaos.architectures`, or the v2 build fails.
- Tag images with exact semver; CasaOS shows "update available" only when the main service's tag changes.
- Ship a Docker `healthcheck`, honour `PUID`/`PGID`, and keep all state under one data volume so backup is one directory.
- Because there is no "requires HTTPS" flag, explain in `description` and `tips` that live camera capture and PWA installation need HTTPS through the user's reverse proxy, while native-camera upload works over plain HTTP.
