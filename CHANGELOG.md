## v1.5.1 (2026-10-28)

### Fix

- **images**: old card photos get the mark's crop by themselves

## v1.5.0 (2026-10-28)

### Feat

- **bodymap**: hands and feet tell their sides, and the selected zone is named
- **reports**: the mark at a glance, dashes for what is unknown
- **card**: a printable three-dimensional reference card
- **images**: the mark in its window, lined up on the mark, kept out of stale caches

### Fix

- **shell**: the official mark in the app bar and the rail, at a legible size

## v1.4.0 (2026-10-15)

### Feat

- **cv**: the normalised view of a card photo: flat, upright, cropped to the card

## v1.3.0 (2026-10-14)

### Feat

- **design**: the third pass: app bar, rows, one primary action, sheets and menus
- **design-system**: icon button, overflow menu, sheet, chip and page header

### Fix

- **design**: the evaluation's fixes: spacing, the map's height, status lines, one date format, the rail everywhere
- **design**: the action bar keeps its height, the settings rows carry their status, the bars are landmarks

## v1.2.0 (2026-10-05)

### Feat

- **design**: a second pass over every screen, on a phone, a tablet and a desktop

## v1.1.1 (2026-10-05)

### Fix

- **pwa**: a new version takes over at once and reloads the pages it finds open

## v1.1.0 (2026-10-02)

### Feat

- **design**: one action per screen, tools folded, the photograph first, two panes where there is room
- **i18n**: Portuguese, and one list of the languages neVus speaks
- **notify**: push notifications to the device, behind a flag
- **measure**: the shape and the colour of a mark, described with each measurement

### Fix

- **i18n**: Portuguese calls a dated look an "observação", and names the new mark actions

## v1.0.0 (2026-10-02)

### Feat

- **lesions**: a mark can be moved to the trash from its page
- **sessions**: any part of a zone photo can be blurred, and the original is gone at once
- **bodymap**: a tap on a zone zooms in on it before the mark is placed
- **backup**: the latest backup is read back every week to prove it would restore
- **auth**: a second factor with an authenticator app, recovery codes and accounts administration

### Fix

- **i18n**: a visit is a "vistazo" in Spanish
- **bodymap**: a tap on the selected zone or outside the body deselects it, and a selected zone is where a new mark goes
- **a11y**: a main landmark on the sign-in pages, and skipped regions without opacity
- **auth**: the second factor's QR code is a standalone SVG

### Perf

- **frontend**: pages after the home page load when opened, and vendor code apart

## v0.4.0 (2026-10-02)

### Feat

- **frontend**: full-body sessions, marking zone photos and comparing sessions
- **sessions**: full-body sessions zone by zone, with marks linked to the registry
- **analysis**: spots on a body region, and lining two regions up by their pattern

## v0.3.0 (2026-10-02)

### Feat

- **frontend**: experimental proposals, the labelling tool, chosen-mark reports, detail views
- **bodymap**: hands and feet detail views
- **reports**: a report of the marks the person chooses
- **analysis**: experimental outline proposals, the evaluation set and re-analysis

## v0.2.0 (2026-10-02)

### Feat

- **bodymap**: a head detail view, the first of the detail views
- **frontend**: signing in, confirming and signing out behind a single sign-on proxy
- **auth**: single sign-on through the reverse proxy, with an emergency way in
- **frontend**: webhook settings for administrators, and a calendar link per person
- **notifications**: webhooks with Home Assistant, ntfy, Gotify and n8n presets, and a calendar feed
- **frontend**: prepare an appointment from a person's page
- **appointments**: prepare an appointment, with the marks to photograph and a report to bring
- **frontend**: make, follow and download reports from a mark or a person
- **reports**: PDF/A-3 records of a mark and summaries of a person's map, in English and Spanish
- **jobs**: a job kind can be told when its last attempt has failed
- **frontend**: compare visits, and size over time with its uncertainty
- **compare**: line two photos up, or say why not, with an overlay and a difference map

### Fix

- **reports**: a requested report renders before the background analyses
- **frontend**: readable status badges in both themes, links that stay visible on hover

## v0.1.0 (2026-10-01)

### Feat

- **frontend**: offline visits, guided live camera, map zoom and marker clusters
- **api**: client-minted identifiers make visit and photo uploads idempotent
- **frontend**: trash, exports, profile deletion and password re-confirmation
- **data**: trash and purge, encrypted exports, backups with restore
- **frontend**: due list, snoozing, reminder and administrator settings
- **reminders**: due list, snoozing and a daily email digest
- **frontend**: measuring tool, sizes on visits and marks, reference card settings
- **measure**: reference card, coins, known lengths and measurements with uncertainty
- **frontend**: quality warnings on visits, photos and the timeline
- **jobs**: background job queue and photo quality checks

### Fix

- **jobs**: stopping the supervisor cancels running pool work instead of hanging
- **deploy**: stop re-owning /app on every start

## v0.1.0-alpha.1 (2026-09-28)

### Feat

- **release**: publish workflow, deployment guide and store screenshots
- **frontend**: marks on the body map, mark page with visits, visit page with photos
- **api**: lesions and observations
- **frontend**: body map with selectable zones on the person page
- **api**: serve the body map
- **bodymap**: port the MoleMapper zones and build the neVus silhouette
- **frontend**: claim, sign in, persons, camera upload and settings
- **cli**: export the OpenAPI schema and keep the frontend snapshot in step
- **api**: upload photographs and serve them to the people allowed to see them
- **db**: add images and renditions
- **storage**: content-addressed blob store, metadata scrubbing and renditions
- **api**: claim flow, sign-in, account administration and persons with owner, manager and viewer access
- **auth**: local accounts with argon2id, cookie sessions, sudo mode, rate limiting and CSRF protection
- **db**: add accounts, sessions, persons, access, audit log and settings tables

### Fix

- **config**: read NEVUS_ALLOWED_HOSTS as a plain comma-separated list
