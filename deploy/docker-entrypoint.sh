#!/bin/sh
# Start as root only long enough to make the data directory writable by the requested uid/gid, then drop
# privileges. PUID/PGID is how a NAS or CasaOS install writes to a host bind mount owned by another user.
set -eu

PUID="${PUID:-1000}"
PGID="${PGID:-1000}"

if [ "$(id -u)" = "0" ]; then
    if [ "$(id -g nevus)" != "$PGID" ]; then groupmod -o -g "$PGID" nevus; fi
    if [ "$(id -u nevus)" != "$PUID" ]; then usermod -o -u "$PUID" nevus; fi
    mkdir -p "${NEVUS_DATA_DIR:-/data}"
    chown -R "$PUID:$PGID" "${NEVUS_DATA_DIR:-/data}" /app
    exec setpriv --reuid="$PUID" --regid="$PGID" --init-groups "$@"
fi

exec "$@"
