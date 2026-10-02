# SPDX-License-Identifier: AGPL-3.0-only
"""Push notifications to installed apps, behind a flag (`NEVUS_WEB_PUSH`).

A browser's push service relays a message to the device. It sees the endpoint and that a message
was sent, never the content: the payload is encrypted for the subscription's own keys (RFC 8291,
`aes128gcm`) and the request is signed with the server's key (VAPID, RFC 8292). The server sends
one message a day per device when marks are due, after the reminder hour, as the email and webhook
digests do; nothing else ever goes out. Everything is done with `cryptography`; no other party.
"""

from __future__ import annotations

import base64
import json
import os
import struct
import time
import urllib.error
import urllib.request
import uuid
from datetime import date, datetime
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy import select
from sqlalchemy.orm import Session

from nevus import secretbox, settings_store
from nevus.config import Settings
from nevus.db.models import NotificationDelivery, PushSubscription, User
from nevus.db.types import utcnow
from nevus.domain.due import due_for_user
from nevus.jobs import queue
from nevus.jobs.registry import JobContext, JobKind, register
from nevus.logging import get_logger
from nevus.notify.email import digest_text

log = get_logger(__name__)
PUSH_KIND = "notify.push"
KEYS_KEY = "notify.push"
RECORD_SIZE = 4096
TTL_SECONDS = 86_400
MAX_FAILURES = 5
LOOPBACK = ("127.0.0.1", "localhost", "::1")


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def unb64url(text: str) -> bytes:
    text = text.strip().replace(" ", "")
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


# --- the server's key -----------------------------------------------------------------------------


def private_key_from(raw: bytes) -> ec.EllipticCurvePrivateKey:
    return ec.derive_private_key(int.from_bytes(raw, "big"), ec.SECP256R1())


def public_bytes(key: ec.EllipticCurvePublicKey) -> bytes:
    return key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)


def vapid_keys(db: Session, settings: Settings) -> tuple[ec.EllipticCurvePrivateKey, str]:
    """The server's signing key, made once and kept sealed in the settings store, and its public key."""
    stored = dict(settings_store.get(db, KEYS_KEY) or {})
    if not stored.get("private"):
        key = ec.generate_private_key(ec.SECP256R1())
        raw = key.private_numbers().private_value.to_bytes(32, "big")
        stored = {
            "private": secretbox.seal(settings.secret_key(), b64url(raw), purpose="push"),
            "public": b64url(public_bytes(key.public_key())),
        }
        settings_store.put(db, KEYS_KEY, stored, encrypted=True)
    raw = unb64url(secretbox.open_(settings.secret_key(), str(stored["private"]), purpose="push"))
    return private_key_from(raw), str(stored["public"])


def vapid_authorization(
    endpoint: str, subject: str, private: ec.EllipticCurvePrivateKey, public_b64: str, now: float | None = None
) -> str:
    """The `Authorization` header of a push request: a signed token for the push service's origin."""
    parts = urlsplit(endpoint)
    audience = f"{parts.scheme}://{parts.netloc}"
    header = b64url(json.dumps({"typ": "JWT", "alg": "ES256"}, separators=(",", ":")).encode())
    claims = {"aud": audience, "exp": int((now or time.time()) + 12 * 3600), "sub": subject}
    body = b64url(json.dumps(claims, separators=(",", ":")).encode())
    signing_input = f"{header}.{body}".encode()
    r, s = decode_dss_signature(private.sign(signing_input, ec.ECDSA(hashes.SHA256())))
    token = f"{header}.{body}.{b64url(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))}"
    return f"vapid t={token}, k={public_b64}"


# --- the message -------------------------------------------------------------------------------------


def _keys(shared: bytes, auth_secret: bytes, ua_public: bytes, as_public: bytes, salt: bytes) -> tuple[bytes, bytes]:
    key_info = b"WebPush: info\x00" + ua_public + as_public
    ikm = HKDF(hashes.SHA256(), 32, salt=auth_secret, info=key_info).derive(shared)
    cek = HKDF(hashes.SHA256(), 16, salt=salt, info=b"Content-Encoding: aes128gcm\x00").derive(ikm)
    nonce = HKDF(hashes.SHA256(), 12, salt=salt, info=b"Content-Encoding: nonce\x00").derive(ikm)
    return cek, nonce


def encrypt(
    plaintext: bytes,
    ua_public: bytes,
    auth_secret: bytes,
    *,
    salt: bytes | None = None,
    as_private: ec.EllipticCurvePrivateKey | None = None,
) -> bytes:
    """RFC 8291 with `aes128gcm` (RFC 8188): one record holding the plaintext and the delimiter."""
    salt = salt or os.urandom(16)
    as_private = as_private or ec.generate_private_key(ec.SECP256R1())
    as_public = public_bytes(as_private.public_key())
    receiver = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ua_public)
    cek, nonce = _keys(as_private.exchange(ec.ECDH(), receiver), auth_secret, ua_public, as_public, salt)
    header = salt + struct.pack(">I", RECORD_SIZE) + bytes([len(as_public)]) + as_public
    return header + AESGCM(cek).encrypt(nonce, plaintext + b"\x02", None)


def decrypt(message: bytes, ua_private: ec.EllipticCurvePrivateKey, auth_secret: bytes) -> bytes:
    """The receiving side, as a browser does it; here for the tests."""
    salt, idlen = message[:16], message[20]
    as_public, body = message[21 : 21 + idlen], message[21 + idlen :]
    sender = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), as_public)
    ua_public = public_bytes(ua_private.public_key())
    cek, nonce = _keys(ua_private.exchange(ec.ECDH(), sender), auth_secret, ua_public, as_public, salt)
    padded = AESGCM(cek).decrypt(nonce, body, None).rstrip(b"\x00")
    if not padded or padded[-1] not in (1, 2):
        raise ValueError("the record has no delimiter")
    return padded[:-1]


def endpoint_allowed(endpoint: str) -> bool:
    """Push services are reached over HTTPS; plain HTTP only on this machine, for the tests."""
    parts = urlsplit(endpoint)
    return parts.scheme == "https" or (parts.scheme == "http" and parts.hostname in LOOPBACK)


def send(endpoint: str, body: bytes, authorization: str, ttl: int = TTL_SECONDS) -> int:
    """Hand the message to the push service; the HTTP status comes back. 404 and 410 mean the device left."""
    if not endpoint_allowed(endpoint):
        raise ValueError("push endpoints are https")
    request = urllib.request.Request(  # noqa: S310 - scheme checked above
        endpoint,
        data=body,
        method="POST",
        headers={
            "Authorization": authorization,
            "Content-Encoding": "aes128gcm",
            "Content-Type": "application/octet-stream",
            "TTL": str(ttl),
            "Urgency": "normal",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
            return int(response.status)
    except urllib.error.HTTPError as error:
        return int(error.code)


def message_for(user: User, items: list[Any], public_url: str | None) -> bytes:
    """What the device shows: the digest's title, the first marks, and where to open."""
    subject, body = digest_text(user, items, public_url)
    lines = [line[2:] for line in body.splitlines() if line.startswith("- ")]
    text = "\n".join(lines[:4]) + ("\n…" if len(lines) > 4 else "")
    payload = {"title": subject, "body": text, "url": (public_url or "").rstrip("/") + "/"}
    return json.dumps(payload, ensure_ascii=False).encode()


def subject_for(settings: Settings, public_url: str | None) -> str:
    """Who the push service may contact about this server's traffic."""
    return settings.web_push_subject or public_url or "mailto:nevus@localhost"


# --- the daily job -----------------------------------------------------------------------------------


def _load(ctx: JobContext, payload: dict[str, Any]) -> dict[str, Any] | None:
    subscription = ctx.db.get(PushSubscription, uuid.UUID(payload["subscription_id"]))
    user = ctx.db.get(User, subscription.user_id) if subscription else None
    if subscription is None or user is None or user.disabled_at is not None or not ctx.settings.web_push:
        return None
    items = due_for_user(ctx.db, user.id, date.fromisoformat(payload["date"]), roles=("owner", "manager"))
    if not items:
        return None
    public_url = settings_store.email_config(ctx.db, ctx.settings).public_url
    private, public = vapid_keys(ctx.db, ctx.settings)
    message = encrypt(message_for(user, items, public_url), unb64url(subscription.p256dh), unb64url(subscription.auth))
    return {
        "endpoint": subscription.endpoint,
        "body": b64url(message),
        "authorization": vapid_authorization(
            subscription.endpoint, subject_for(ctx.settings, public_url), private, public
        ),
    }


def _send(value: dict[str, Any]) -> dict[str, Any]:
    return {"status": send(value["endpoint"], unb64url(value["body"]), value["authorization"])}


def _store(ctx: JobContext, payload: dict[str, Any], result: dict[str, Any]) -> None:
    subscription = ctx.db.get(PushSubscription, uuid.UUID(payload["subscription_id"]))
    if subscription is None:
        return
    status = int(result["status"])
    if status in (404, 410):
        log.info("push.device_left", subscription=str(subscription.id))
        ctx.db.delete(subscription)
        return
    ok = 200 <= status < 300
    subscription.failures = 0 if ok else subscription.failures + 1
    if ok:
        subscription.last_sent_at = utcnow()
    ctx.db.add(
        NotificationDelivery(
            user_id=subscription.user_id,
            channel="push",
            key=f"due:{payload['date']}:{subscription.id}",
            status="sent" if ok else "failed",
            error=None if ok else f"HTTP {status}",
        )
    )
    if subscription.failures >= MAX_FAILURES:
        log.info("push.subscription_dropped", subscription=str(subscription.id), failures=subscription.failures)
        ctx.db.delete(subscription)
    ctx.db.flush()


register(JobKind(PUSH_KIND, _load, _send, _store, timeout=60.0, max_attempts=2))


def schedule_push(ctx: JobContext, now: datetime | None = None) -> int:
    """Periodic: after the reminder hour, one message per subscribed device whose owner has marks due."""
    if not ctx.settings.web_push:
        return 0
    zone = ZoneInfo(ctx.settings.effective_timezone)
    local = (now or datetime.now(tz=zone)).astimezone(zone)
    if local.hour < ctx.settings.reminder_hour:
        return 0
    today = local.date()
    queued = 0
    for subscription in ctx.db.scalars(select(PushSubscription)).all():
        key = f"due:{today.isoformat()}:{subscription.id}"
        sent = ctx.db.scalar(
            select(NotificationDelivery.id).where(
                NotificationDelivery.user_id == subscription.user_id,
                NotificationDelivery.channel == "push",
                NotificationDelivery.key == key,
            )
        )
        if sent is not None or not due_for_user(ctx.db, subscription.user_id, today, roles=("owner", "manager")):
            continue
        if queue.enqueue(
            ctx.db,
            PUSH_KIND,
            {"subscription_id": str(subscription.id), "date": today.isoformat()},
            dedupe_key=f"push:{subscription.id}:{today}",
            max_attempts=2,
        ):
            queued += 1
    return queued
