# CasaOS / ZimaOS third-party app store conventions (2026)

Date: 2026-09-23. Purpose: establish the authoritative format for a third-party CasaOS/ZimaOS app store before turning the maintainer's single-app store into a multi-app personal store. Claims are marked: **[V-src]** read in source code or configuration; **[V-doc]** stated in official documentation; **[V-meas]** measured directly (HTTP headers, API responses); **[C-meas]** measured and reported by a third party; **[Inf]** inference.

## 0. Two store formats now coexist

- On 2026-06-24 IceWhale refactored the official repository into a **v2 static format**; the README is now titled "ZimaOS AppStore Source" and CONTRIBUTING says the v2 documentation is the source of truth, with the zip kept as "legacy v1 compatibility output" [V-doc]. Sources: <https://github.com/IceWhaleTech/CasaOS-AppStore>, <https://github.com/IceWhaleTech/CasaOS-AppStore/blob/main/CONTRIBUTING.md>.
- **v1** is a zip read by CasaOS ≥ 0.4.4 and older ZimaOS. **v2** is a set of static files (`store.json`, `index.json`, `apps/<id>/…`) built by <https://github.com/IceWhaleTech/build-appstore-action> (created 2026-07-08; current tag v1.1.2) [V-src].
- **ZimaOS 1.7.0 (2026-07-28)** shipped a new App Store UI (<https://github.com/IceWhaleTech/ZimaOS/releases/tag/1.7.0>). A third party found that adding a zip URL returns `HTTP 400 {"message":"Unsupported import method."}` while a v2 `store.json` URL is accepted [C-meas] (<https://github.com/chicohaager/zima-appstore>).
- **CasaOS itself is effectively frozen** [V-meas]: last stable release v0.4.15 (2024-12-19), last pre-release v0.4.17-alpha1 (2025-04-17); CasaOS-AppManagement last pushed 2025-04-17. The v1 behaviour below is therefore stable.

## 1. Official repository layout and the `x-casaos` schema

### 1a. Layout [V-src]

- Root of `main`: `Apps/` (178 apps); v2 files `store-config.json`, `supported-languages.json`; v1 files `category-list.json`, `recommend-list.json`, `featured-apps.json`, `build/` (the sysroot skeleton the v1 zip is built from); tooling and docs `docs/` (VitePress), `scripts/build_dist.sh`, `.github/{actions,workflows,scripts}`, `psd-source/`.
- One app folder, e.g. `Apps/Jellyfin/`: `docker-compose.yml`, `icon.svg`, `icon.png`, `thumbnail.png`, `screenshot-1..3.png`, `changelog.txt`.
- `gh-pages` branch: the built v2 `dist/` (`store.json`, `store.<locale>.json`, `index.json`, `index.<locale>.json`, `apps/<id>/{docker-compose.yml, docker-compose.<arch>.yml, meta.json, assets/}`, `metadata.tar.gz`, `metadata.sha256`), plus `store/main.zip` (v1) and a CNAME for `casaos.app`.
- GitHub Releases also carry `main.zip` and `v2-dist.zip` (latest v2.0.18, 2026-09-22) [V-meas].

### 1b. v2 top-level `x-casaos` fields [V-doc]

From <https://github.com/IceWhaleTech/CasaOS-AppStore/blob/main/docs/specs/compose-and-x-casaos.md>:

| Field | Type | Required | Localised | Built output location |
| --- | --- | --- | --- | --- |
| `id` | string | Yes | No | built compose + `meta.json`/index |
| `main` | string | Yes | No | built compose |
| `index` | string | Yes in practice | No | built compose |
| `port_map` | string | Yes | No | built compose |
| `scheme` | string | No | No | built compose |
| `icon` | string | Yes | No | built compose, rewritten during build |
| `title` | object | Yes | Yes | built compose, resolved per locale |
| `tagline` | object | Recommended | Yes | `meta.json`, index listing |
| `description` | object | Recommended | Yes | `meta.json` |
| `thumbnail` | string | No | No | `meta.json` as built asset path |
| `screenshot_link` | string[] | No | No | `meta.json` as built asset paths |
| `tips` | object | No | Yes | `meta.json` (`tips.before_install.<locale>`) |
| `author`, `developer` | string | Recommended | No | `meta.json`, index listing |
| `category` | string | Yes | No | `meta.json`, index listing |
| `architectures` | string[] | Recommended | No | `meta.json`, index listing |
| `version` | string | Yes | No | `meta.json`, index listing |
| `update_at` | string | No | No | `meta.json` |
| `release_notes` | object | No | Yes | `meta.json.release_note` |
| `website`, `repo`, `support`, `docs` | string | No | No | `meta.json` |

Rules on the same page: `id` is reverse-domain with at least two segments, only `[A-Za-z0-9._-]`, normalised to lowercase, and "the source directory name under `Apps/` is not the protocol identity"; `port_map` must be a quoted YAML string; `category` must be one of `Media, Productivity, Home, Networking, AI, Finance, Social, Developer, Others` (**no Health**); `version` should be semver ("future app upgrade decisions rely on this field"); service-level `services.<name>.x-casaos` blocks "are legacy and removed during v2 build processing".

### 1c. What the v2 build does [V-src]

From `scripts/build_appstore.py` in the action: `COMPOSE_KEEP_FIELDS = {"id","main","index","port_map","scheme","icon","title","version"}` stay in the built compose; everything else moves to `meta.json`; `store_app_id` is dropped; per-service `x-casaos` blocks are deleted; `hostname` ends up in `meta.json`; images are resolved to per-architecture digests and `docker-compose.<arch>.yml` files are emitted (registry authentication follows the generic `WWW-Authenticate` challenge, so ghcr.io works); a declared architecture that the image does not publish is a build error; categories are only lowercased (no whitelist in code).

### 1d. Legacy v1 schema (what CasaOS reads straight out of the zip) [V-doc]

From CONTRIBUTING.md as of 2025-06 (<https://github.com/IceWhaleTech/CasaOS-AppStore/blob/ac08927592/CONTRIBUTING.md>):

```yaml
# Service level
x-casaos:
    envs:
      - container: PUID
        description:
            en_US: Run Syncthing as specified uid.
    ports:
      - container: "8384"
        description:
            en_US: WebUI HTTP Port
    volumes:
        - container: /config
          description:
              en_US: Syncthing config directory.
# Compose app level
x-casaos:
    architectures: [amd64, arm64]
    main: syncthing
    author: CasaOS Team
    category: Backup
    description:
        en_US: ...
    developer: Syncthing
    icon: https://cdn.jsdelivr.net/gh/IceWhaleTech/CasaOS-AppStore@main/Apps/Syncthing/icon.png
    tagline:
        en_US: Free, secure, and distributed file synchronisation tool.
    thumbnail: https://cdn.jsdelivr.net/gh/.../Apps/Jellyfin/thumbnail.jpg
    title:
        en_US: Syncthing
    tips:
        before_install:
            en_US: |
                (notes for the user to read prior to installation; markdown is supported)
    index: /
    port_map: "8384"
```

The same file says: do not use the `latest` tag for `image`; the compose `name` "is used as the store App ID, which should be unique across all apps" and must match `^[a-z0-9][a-z0-9_-]*$`; built-in variables `$PUID`, `$PGID`, `$TZ`, `$AppID` and the magic `${WEBUI_PORT}` are available.

### 1e. Machine-readable schemas

- CasaOS (v1) has no JSON Schema file. Its contract is the OpenAPI model in CasaOS-AppManagement `api/app_management/openapi.yaml` [V-src]: `ComposeAppStoreInfo` requires `author, category, description, developer, icon, screenshot_link, tagline, thumbnail, title, tips, index, port_map`; `scheme` is an enum `http|https` (default http); `architectures`: "If the architecture of the host is not in this list, the compose app will not be installed"; `store_app_id` "might be same as app name most of the time" and is set at install time. The loader does not enforce the `required` list; a missing title falls back to the compose `name`.
- ZimaOS (v2) publishes generated JSON Schemas in <https://github.com/IceWhaleTech/zimaos-schema> (created 2026-09-07) [V-src]: `x-casaos.schema.json`, `repository.schema.json` (requires `x-casaos.id`), `zimaapp-v2app.schema.json`, built on compose-go v1.20.2. Top-level properties: `architectures, author, category, description, developer, hostname, icon, id` (pattern `^[a-z0-9_-]+(?:\.[a-z0-9_-]+)+$`), `image, index, main, port_map, release_note, repo_id, scheme, screenshot_link, tagline, thumbnail, tips (before_install, custom), title, version`. Deprecated: `store_app_id` ("migrate to id … then remove store_app_id") and `is_uncontrolled`. Reserved: `autostart`, `image_drift_check`. Unknown properties are allowed. The working raw URL is `https://raw.githubusercontent.com/IceWhaleTech/zimaos-schema/main/schema/zimaapp/v2/repository.schema.json` [V-meas].

### 1f. Root JSON files

- `store-config.json` (v2) from <https://github.com/IceWhaleTech/CasaOS-AppStore/blob/main/docs/specs/store-config.md> [V-doc]: `version` (int, must be 2), `store_id` (string, required, "should remain stable after users start subscribing"; do not use `zimaos-appstore`), `name` (locale-keyed object, required), `description` (locale-keyed, optional), `maintainer` (required), `url`, `icon` (optional).
- `supported-languages.json` lists candidate locales; a locale file is emitted only when some field defines that locale.
- `category-list.json` (v1): `[{name, font, description}]`, `font` an MDI icon name defaulting to `grid`; CasaOS merges the lists across all subscribed stores; the official list equals the nine v2 categories [V-src].
- `recommend-list.json` (v1): `[{"appid": "<compose name>"}]`, read by CasaOS [V-src]. `featured-apps.json` is packed into the official v1 zip but no reference to it was found in CasaOS-AppManagement or CasaOS-UI, so it is optional [Inf].

### 1g. What the official CI enforces [V-src]

`validate_compose.py` checks the top-level `name` against `^[a-z0-9_-]+$` and `x-casaos.id` against `^[a-z0-9]+(?:[._-][a-z0-9]+)*(?:\.[a-z0-9]+(?:[._-][a-z0-9]+)*)+$`, then runs `docker compose config -q`. Build errors (FAQ): missing asset, invalid id, invalid YAML, declared architecture not supported by the image. Warnings: non-semver `version` (then dropped from `index.json`), registry rate limits.

## 2. How a third-party store is consumed

### 2a. CasaOS (v1 zip) [V-src]

Sources: `service/appstore.go`, `service/appstore_management.go`, `main.go`, `pkg/utils/downloadHelper/getter.go` in CasaOS-AppManagement.

1. Register: App Store → Add Source calls `RegisterAppStore(url)`; the duplicate check is case-insensitive; registration is asynchronous and a failing URL is not saved.
2. Refresh: once at startup, then cron `@every 10m`.
3. Change detection is by `Content-Length` only: `http.Head(url)`; if `res.ContentLength == lastAPPStoreSize` the store is considered unchanged.
4. Download with `hashicorp/go-getter` (`ClientModeAny`) into `<workdir>.tmp`, then swap with backup/rollback. Work directory: `/var/lib/casaos/appstore/<host>/<md5(lower(url.Path))>`, with a `.casaos-appstore` marker holding the URL.
5. Store root: CasaOS walks the extracted tree for the first directory named exactly `Apps`, at any depth; if none, `ErrNotAppStore` (HTTP 400).
6. Catalog: every folder under `Apps/` with a `docker-compose.yml`/`.yaml` becomes an app, parsed with compose-go validation; invalid apps are skipped with a log line; entries are keyed by the compose `name` (folder name irrelevant).
7. Merging across stores: `catalog[storeAppID] = composeApp` while iterating a Go map of stores, so two stores with the same `name` collide and the winner is effectively random [Inf from Go map semantics].
8. Install: `SetStoreAppID(composeApp.Name)`, `$AppID` = that name; defaults `PUID` 1000, `PGID` 1000, `TZ` system, `DefaultUserName` admin, `DefaultPassword` casaos; `WEBUI_PORT` auto-allocated.
9. "Update available": for the `latest` tag a digest comparison; otherwise `currentTag != storeTag` on the **main service only**; `is_uncontrolled: true` means never upgradable; cached 1 h and purged on each catalog refresh.
10. Opening the app: CasaOS-UI builds `${scheme||'http'}://${hostname||<CasaOS host>}:${port_map}${index}`, so `index` must start with `/`. The backend health check requests `scheme://(hostname||127.0.0.1):port_map/index` with TLS verification off and accepts **only 200 or 401**.
11. Locale lookup (`common-i18n.js`): `data['custom'] || data[lang] || data['en_us'] || data['en_US']`; UI language keys are lowercase (e.g. `es_es`), so `en_US` works only as the last fallback.

### 2b. Hosting options, measured [V-meas]

| Zip URL style | `Content-Length` on final HEAD | Caching | Works with the size check |
| --- | --- | --- | --- |
| `raw.githubusercontent.com/<o>/<r>/gh-pages/x.zip` | yes | `max-age=300` | Yes |
| `github.com/<o>/<r>/releases/latest/download/x.zip` | yes (two 302s, then 200) | redirects `no-cache` | Yes, stable URL |
| `cdn.jsdelivr.net/gh/<o>/<r>@gh-pages/x.zip` | yes | `s-maxage=43200` (12 h) | Yes, but up to 12 h stale unless purged |
| `github.com/<o>/<r>/archive/refs/heads/<b>.zip` (codeload) | none | — | No: Go reports −1 both times, so after the first fetch it looks unchanged until the service restarts [Inf] |

### 2c. v1 gotchas

- The URL should end in `.zip` (or carry `?archive=zip`) so go-getter unpacks it [Inf].
- The zip must contain a directory named exactly `Apps` at some depth [V-src].
- Same-size updates are missed; a manifest that grows each release avoids it [V-src].
- The compose `name` is the store app id: lowercase, unique across all subscribed stores, never renamed after publishing (installed apps keep the old name as `store_app_id`), independent of the folder name. Do not write `store_app_id` yourself.
- Asset URLs must be absolute; CasaOS reads the compose straight out of the zip and has no base URL. Official apps use absolute jsDelivr `@main` URLs.

### 2d. v2 consumption (ZimaOS) [V-doc]

- Users add `…/store.json`; "The URL users add should match the build `base-url`."
- `index.json` lists each app with a `content_hash` (first 8 hex characters of the sha256 of the generated files); only apps whose hash changed are re-fetched; `version` communicates upgrades; `metadata.tar.gz` bootstraps the first load.
- The official workflow purges jsDelivr after every `gh-pages` deploy (`release-store.yml`).
- API found by a third party: `POST /v3/app_store/repo {"url": ".../store.json"}`, token sent raw without `Bearer` [C-meas].

## 3. ZimaOS compatibility

- The official ZimaOS store is built from the same repository (`store_id` `zimaos-appstore`). Same source format; the published output differs:

| | v1 (CasaOS) | v2 (ZimaOS ≥ 1.7) |
| --- | --- | --- |
| Subscription URL | `.zip` | `store.json` |
| App identity | compose `name` | `x-casaos.id` (reverse-domain) |
| Categories | free-form `category-list.json` | fixed list of nine (no Health) |
| Service-level `x-casaos` | install-dialog labels | stripped |
| Updates | zip size check + image tag comparison | `content_hash` + `version` |

- The zip route is closed for new sources on ZimaOS 1.7 [C-meas]; `tips.before_install` was not rendered on 1.7.0-beta1 either. "Official store apps and third-party store apps are isolated in ZimaOS and can coexist even when the source `id` matches" [V-doc FAQ]. The ZimaOS runtime is closed source; whether it honours `hostname` from `meta.json` is unverified.

## 4. Community stores

| Store | Feed URLs | Build / publish | Validation | Versions / image bumps |
| --- | --- | --- | --- | --- |
| BigBear (<https://github.com/bigbeartechworld/big-bear-casaos>, 442 apps) | v1 `…/archive/refs/heads/master.zip` (a default source in CasaOS); v2 `https://cdn.jsdelivr.net/gh/bigbeartechworld/big-bear-casaos@gh-pages/store.json` | `release.yml` on push to master: yq lint, official action (SHA-pinned), gh-pages | PR: `lint-casaos-v2.sh` (id must start `com.bigbeartechworld.`, rejects lowercase `en_us`, category in the nine), build check, jest tests | Renovate with `stabilityDays: 3`, auto-merge minor/patch, majors manual; images pinned `tag@sha256`; `name: big-bear-<app>` |
| Play (<https://github.com/Cp0204/CasaOS-AppStore-Play>) | v1 `https://play.cuse.eu.org/Cp0204-AppStore-Play.zip` plus per-arch variants; v2 `https://play.cuse.eu.org/store.json` | per-arch zips filtered on `architectures`, v2 build, Release under a re-created tag, Aliyun OSS, Cloudflare purge | none | deliberately `:latest` |
| LinuxServer (<https://github.com/WisdomSky/LinuxServer-AppStore>) | v1 `https://paodayag.dev/linuxserver/casaos/store.zip`; v2 `https://paodayag.dev/linuxserver/zimaos/store.json` | official action (SHA-pinned), gh-pages | build only | daily bot commits; exact tags; `name: linuxserver-<app>` |
| Coolstore (<https://github.com/WisdomSky/CasaOS-Coolstore>) | v1 only | built off-repo | none | daily bot commits |
| HomeAutomation (<https://github.com/mr-manuel/CasaOS-HomeAutomation-AppStore>, stale since 2025-01) | v1 `…/archive/refs/tags/latest.zip` | recreates tag `latest` on every push | none | manual; source-archive URL has the `Content-Length` problem |

Common pattern among maintained stores: the official action publishes to `gh-pages`; the v1 zip is kept and served from a host that returns `Content-Length`; app names carry a store prefix; updates come from Renovate or a bot.

## 5. Best practice for a multi-app personal store

1. **Compose `name`**: short, lowercase, stable forever (e.g. `tabernacle`, `nevus`); neither appears among the folder names of the five big stores [V-meas]. A store prefix protects against v1 collisions but changes `$AppID`, container names and the data path; choose once.
2. **`x-casaos.id`**: `io.github.<maintainer>.<app>`. Never write `store_app_id`.
3. **`store_id`**: keep the original value even if the store's display name changes.
4. **Images**: pin exact semver tags; v1 detects updates by comparing tag strings and `latest` falls into a digest path; v2 pins digests anyway.
5. **Bump together**: `image:`, `version`, `update_at`, `release_notes`. Automate with Renovate's docker-compose manager plus a regex manager for `x-casaos.version`, or a `repository_dispatch` from the app repository's release [Inf]. Publish multi-arch images for every declared architecture or the v2 build fails.
6. **Healthcheck**: keep a Docker `healthcheck`; make sure `port_map` + `index` return 200 or 401 for CasaOS's own check (never a redirect to a login page).
7. **PUID/PGID/TZ**: use `$PUID`, `$PGID`, `$TZ`; hard-coded `"1000"` is equivalent; `$TZ` beats `UTC`.
8. **Volumes**: `/DATA/AppData/$AppID/...` is the official form; a hard-coded `/DATA/AppData/<name>/...` is the same as long as the name never changes.
9. **Ports and entry**: publish a distinctive host port and set `port_map` to it as a quoted string; `index: /`; `main` pointing at the UI service; add service-level `envs`/`ports`/`volumes` descriptions (CasaOS-only).
10. **HTTPS**: there is no "requires HTTPS" flag in either schema; `scheme: https` only means the container itself serves TLS on `port_map`; CasaOS and ZimaOS have no built-in reverse proxy (users add Nginx Proxy Manager, Caddy, Traefik, Cloudflared or Tailscale); `hostname` can point the tile at a proxy hostname on v1 (ZimaOS support unverified). Write HTTPS requirements in `description`, not only in `tips`. Browser camera capture (`getUserMedia`) needs a secure context; `<input type=file capture>` works over plain HTTP.
11. **Locale keys**: lowercase (`en_us`) works on both CasaOS and v2; `en_US` works on CasaOS only for English via the fallback. Be consistent (BigBear's lint enforces the opposite convention).
12. **Category for a health-tracking app**: `Others` or `Home`, since there is no Health category.

## Key takeaways

- The official repository now builds v2 static files and a legacy v1 zip from one source tree; copy that setup.
- On ZimaOS ≥ 1.7 new sources must be a `store.json`; zips are for CasaOS only.
- CasaOS v1 notices store changes only by HEAD `Content-Length`; raw `gh-pages` and Release `latest/download` URLs work; GitHub source-archive URLs do not.
- In v1 the compose `name` is the store app id (lowercase, globally unique, never renamed); in v2 the identity is `x-casaos.id`; `store_app_id` is deprecated and stripped.
- CasaOS shows "update available" only when the main service's image tag changes; pin exact semver and bump `version` with it.
- Authoritative schemas: `zimaos-schema` for v2, the CasaOS-AppManagement OpenAPI for v1.
- Nine fixed categories and no Health.
- No "requires HTTPS" flag; document it in `description`.
- Well-run community stores use the official action, `gh-pages`, a prefixed `name`, and Renovate or bot bumps; BigBear is the best model.
