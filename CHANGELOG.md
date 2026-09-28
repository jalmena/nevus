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
