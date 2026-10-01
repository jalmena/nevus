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

`/data` inside the container holds everything neVus owns: `nevus.sqlite3` (the database, with its `-wal` and `-shm` companions), `blobs/` (the photographs, addressed by content hash, never rewritten), `secret.key` (signs sessions and seals the few secrets kept in the database, such as the mail password), `backups/` and `exports/`.

## Backups

Set a passphrase and neVus writes an encrypted backup every night after 03:00 in the instance time zone, keeping the newest one of each of the last 30 days and of each of the last 12 months:

```
NEVUS_BACKUP_PASSPHRASE: "a long sentence only you know"
NEVUS_BACKUP_HOUR: "3"
```

Backups land in `/data/backups/` as `nevus-backup-<date>.tar.age`. Copy that directory to another machine with your usual tool: a backup on the same disk does not survive the disk. The files are in the standard [age](https://age-encryption.org) format, so they open without neVus (`age -d backup.tar.age | tar -t`).

By hand, and to restore:

```sh
docker exec -it nevus nevus backup            # asks for a passphrase, or reads NEVUS_BACKUP_PASSPHRASE
docker exec -it nevus nevus verify            # every stored photo present and intact?
# Restore into a fresh, empty data directory (stop the old container first):
docker run --rm -it -v /DATA/AppData/nevus/data:/data ghcr.io/jalmena/nevus:<version> \
       nevus restore /data/backups/nevus-backup-20261001T030000Z.tar.age
```

`nevus restore` refuses a data directory that is not empty unless you pass `--force`. The database is copied with SQLite's online backup API, so a backup taken while neVus runs is consistent.

**With an external PostgreSQL** the backup holds the photographs and the server secret only; back the database up yourself, for example nightly with `pg_dump -Fc -d nevus -f /backups/nevus-$(date +%F).dump`, and restore both together.

## Trash, quotas and exports

Deleted marks, visits and photos stay in the trash for 30 days (`NEVUS_TRASH_DAYS`); a daily task then removes them and the files nobody refers to any more. `NEVUS_PERSON_QUOTA_BYTES` sets a soft per-person limit: uploads are never refused for it, the person's page says when it is exceeded. Encrypted exports stay downloadable for 7 days (`NEVUS_EXPORT_DAYS`).

## Email reminders

An administrator fills in the mail server under Settings, or you set it here; the interface values win:

```
NEVUS_SMTP_HOST: "smtp.example.home"
NEVUS_SMTP_PORT: "587"
NEVUS_SMTP_SECURITY: "starttls"     # starttls, ssl or none
NEVUS_SMTP_USERNAME: "nevus"
NEVUS_SMTP_PASSWORD: "..."
NEVUS_SMTP_FROM: "nevus@example.home"
NEVUS_PUBLIC_URL: "https://nevus.example.home"   # for the link in the email
```

People who turn reminders on receive at most one email a day, after 08:00 (`NEVUS_REMINDER_HOUR`), listing names and dates; photographs never leave the server.

## Updating and removing

Updating never touches the data directory; database migrations run at start-up. To remove neVus, remove the container and delete the data directory. Nothing else is written anywhere.

## Reporting a security problem

See `SECURITY.md` at the repository root.
