# Deploying neVus

neVus runs as one container with one data directory. Nothing else is required: the database is SQLite inside that directory unless you point neVus at your own PostgreSQL. It has no cloud dependencies and makes no outbound connections.

## From the personal app store (CasaOS, ZimaOS)

1. In CasaOS, open the App Store, click the three dots next to "More Apps" and add the source
   `https://raw.githubusercontent.com/jalmena/jalmena-appstore/gh-pages/appstore.zip` (on ZimaOS 1.7 or later:
   `https://cdn.jsdelivr.net/gh/jalmena/jalmena-appstore@gh-pages/store.json`).
2. Install **neVus**. Before confirming, set `PUID` and `PGID` to the owner of `/DATA/AppData/nevus/data` (`id -u`, `id -g` on the host) and `TZ` to your time zone.
3. Open the app card. The first visit shows "Claim this instance": the account you create there is the administrator, and there is no open registration afterwards.

The store shows "update available" when a new version is published; updating keeps the data directory.

## With Docker Compose

```sh
mkdir nevus && cd nevus
curl -fsSLO https://raw.githubusercontent.com/jalmena/nevus/main/deploy/compose.yaml
mkdir data && chown "$(id -u):$(id -g)" data
docker compose up -d
```

Then open `http://<host>:8455`. Edit the `PUID`, `PGID` and `TZ` values in the file if they differ from the defaults. The image tag in the file is the exact released version; to update, change it and run `docker compose up -d` again.

## HTTPS and the camera

Uploading a photo taken with the phone's camera works over plain HTTP. Live camera capture inside the page and installing neVus as an app on the home screen need a secure context, so put a reverse proxy with TLS in front. A Caddy site block with its internal certificate authority is enough on a home network:

```
nevus.example.home {
    tls internal
    reverse_proxy nevus:8080
}
```

Trust the proxy's root certificate on the phones that will use neVus, and tell neVus which public hostnames it should answer to:

```
NEVUS_ALLOWED_HOSTS: "nevus.example.home"
```

Private addresses, `localhost` and `.local` names are always accepted. Unknown public names get `421 Misdirected Request`, which blocks DNS rebinding. Set `NEVUS_TRUST_PROXY_HEADERS: "true"` only when the proxy is the sole way in, so that the audit log and the login rate limiter see the real client address.

## Settings

Every setting is an environment variable prefixed with `NEVUS_`. The ones an operator usually touches:

| Variable | Default | Meaning |
| --- | --- | --- |
| `NEVUS_ALLOWED_HOSTS` | empty | Comma-separated public hostnames the server answers to |
| `NEVUS_DATABASE_URL` | SQLite in the data directory | External PostgreSQL, e.g. `postgresql+psycopg://nevus:secret@db:5432/nevus` |
| `NEVUS_ADMIN_USER`, `NEVUS_ADMIN_PASSWORD` | unset | Create or reset the administrator at start-up (for recovery; remove afterwards) |
| `NEVUS_MAX_UPLOAD_BYTES` | 30 MiB | Largest accepted photograph |
| `NEVUS_MIN_FREE_BYTES` | 2 GiB | Uploads are refused below this free space |
| `NEVUS_LOG_LEVEL` | `info` | `debug`, `info`, `warning` or `error` |

The full list is in `backend/src/nevus/config.py`.

## The data directory

`/data` inside the container holds everything neVus owns: `nevus.sqlite3` (the database, with its `-wal` and `-shm` companions), `blobs/` (the photographs, addressed by content hash, never rewritten), and `secret.key` (the server secret that signs sessions; keep it with the data, or every session ends on restore). Back up the directory and you have backed up everything. Until the built-in backup command ships, stop the container before copying, or copy the SQLite file with a tool that understands WAL mode.

With an external PostgreSQL, the database is yours to back up; neVus only owns `blobs/` and `secret.key`.

## Updating and removing

Updating never touches the data directory; database migrations run at start-up. To remove neVus, remove the container and delete the data directory. Nothing else is written anywhere.

## Reporting a security problem

See `SECURITY.md` at the repository root.
