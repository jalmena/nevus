# SPDX-License-Identifier: AGPL-3.0-only
"""Push notifications: the message encryption against RFC 8291, the signed header, and the server's key."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from fastapi.testclient import TestClient

from nevus.jobs.registry import JobContext
from nevus.notify import push
from tests.test_accounts import claim
from tests.test_notifications import Target, _due_mark
from tests.test_scale import SAME_ORIGIN

# RFC 8291, section 5 and appendix A.
AS_PRIVATE = "yfWPiYE-n46HLnH0KqZOF1fJJU3MYrct3AELtAQ-oRw"
UA_PUBLIC = "BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-AYWXvTBHm4bjyPjs7Vd8pZGH6SRpkNtoIAiw4"
UA_PRIVATE = "q1dXpw3UpT5VOmu_cf_v6ih07Aems3njxI-JWgLcM94"
AUTH_SECRET = "BTBZMqHH6r4Tts7J_aSIgg"
SALT = "DGv6ra1nlYgDCS1FRnbzlw"
HEADER = (
    "DGv6ra1nlYgDCS1FRnbzlwAAEABBBP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27ml"
    "mlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8wEqKK6PBru3jl7A8"
)
CIPHERTEXT = "8pfeW0KbunFT06SuDKoJH9Ql87S1QUrdirN6GcG7sFz1y1sqLgVi1VhjVkHsUoEsbI_0LpXMuGvnzQ"
PLAINTEXT = b"When I grow up, I want to be a watermelon"


def test_the_encryption_reproduces_rfc_8291_to_the_byte() -> None:
    message = push.encrypt(
        PLAINTEXT,
        push.unb64url(UA_PUBLIC),
        push.unb64url(AUTH_SECRET),
        salt=push.unb64url(SALT),
        as_private=push.private_key_from(push.unb64url(AS_PRIVATE)),
    )
    assert message == push.unb64url(HEADER) + push.unb64url(CIPHERTEXT)
    assert (
        push.decrypt(message, push.private_key_from(push.unb64url(UA_PRIVATE)), push.unb64url(AUTH_SECRET)) == PLAINTEXT
    )


def test_every_message_is_encrypted_afresh_and_only_the_device_reads_it() -> None:
    device = ec.generate_private_key(ec.SECP256R1())
    other = ec.generate_private_key(ec.SECP256R1())
    auth = push.unb64url(AUTH_SECRET)
    one = push.encrypt(b"two marks due", push.public_bytes(device.public_key()), auth)
    two = push.encrypt(b"two marks due", push.public_bytes(device.public_key()), auth)
    assert one != two, "a fresh salt and key pair every time"
    assert push.decrypt(one, device, auth) == b"two marks due"
    try:
        push.decrypt(one, other, auth)
    except Exception:
        pass
    else:
        raise AssertionError("another key must not open the message")


def test_the_authorization_header_is_a_token_the_public_key_verifies() -> None:
    private = ec.generate_private_key(ec.SECP256R1())
    public = push.b64url(push.public_bytes(private.public_key()))
    header = push.vapid_authorization(
        "https://push.example.net/send/abc", "https://nevus.example.home", private, public
    )
    assert header.startswith("vapid t=") and header.endswith(f", k={public}")
    token = header[len("vapid t=") : header.index(", k=")]
    head, claims, signature = token.split(".")
    assert json.loads(push.unb64url(head)) == {"typ": "JWT", "alg": "ES256"}
    body = json.loads(push.unb64url(claims))
    assert body["aud"] == "https://push.example.net" and body["sub"] == "https://nevus.example.home"
    raw = push.unb64url(signature)
    der = encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big"))
    private.public_key().verify(der, f"{head}.{claims}".encode(), ec.ECDSA(hashes.SHA256()))


def test_the_server_key_is_made_once_and_kept_sealed(client: TestClient, settings) -> None:  # type: ignore[no-untyped-def]
    with client.app.state.session_factory() as db:  # type: ignore[attr-defined]
        first, public = push.vapid_keys(db, settings)
        db.commit()
    with client.app.state.session_factory() as db:  # type: ignore[attr-defined]
        again, public_again = push.vapid_keys(db, settings)
        from nevus import settings_store

        stored = settings_store.get(db, push.KEYS_KEY)
    assert public == public_again and len(push.unb64url(public)) == 65
    assert first.private_numbers().private_value == again.private_numbers().private_value
    assert str(stored["private"]).startswith("v1:"), "sealed, not the key itself"


def test_only_https_endpoints_are_pushed_to() -> None:
    try:
        push.send("ftp://push.example.net/x", b"", "vapid t=x, k=y")
    except ValueError:
        pass
    else:
        raise AssertionError("a non-https endpoint must be refused")


@pytest.fixture
def receiver() -> Iterator[Target]:
    """A push service of our own: it takes the message and answers what the test tells it to."""
    server = Target()
    yield server
    server.server.shutdown()


def test_devices_subscribe_behind_the_flag_and_get_the_digest_and_a_test_message(
    client: TestClient, settings, receiver: Target
) -> None:  # type: ignore[no-untyped-def]
    target = receiver
    claim(client)
    assert client.get("/api/push").json() == {"enabled": False, "public_key": None, "subscriptions": 0}
    settings.web_push = True  # the application and its runner hold this same object
    status = client.get("/api/push").json()
    assert status["enabled"] is True and len(push.unb64url(status["public_key"])) == 65

    device = ec.generate_private_key(ec.SECP256R1())
    auth = os.urandom(16)
    subscription = {
        "endpoint": f"{target.url}/send/device-1",
        "keys": {"p256dh": push.b64url(push.public_bytes(device.public_key())), "auth": push.b64url(auth)},
    }
    plain = {**subscription, "endpoint": "http://push.example.net/send/1"}
    assert client.post("/api/push/subscriptions", json=plain, headers=SAME_ORIGIN).status_code == 422
    assert client.post("/api/push/subscriptions", json=subscription, headers=SAME_ORIGIN).status_code == 201
    again = client.post("/api/push/subscriptions", json=subscription, headers=SAME_ORIGIN)
    assert again.status_code == 201 and again.json()["subscriptions"] == 1, "the same device once"

    target.status = 201
    assert client.post("/api/push/test", headers=SAME_ORIGIN).json() == {"sent": 1, "failed": 0}
    received = target.requests[-1]
    headers = {name.lower(): value for name, value in received["headers"].items()}  # urllib capitalises names
    assert headers["content-encoding"] == "aes128gcm" and headers["ttl"] == "86400"
    assert headers["authorization"].startswith("vapid t=")
    greeting = json.loads(push.decrypt(received["body"], device, auth))
    assert greeting["title"] == "neVus can reach this device"

    # The daily digest, after the reminder hour, once a day and only when marks are due.
    _due_mark(client)
    zone = ZoneInfo(settings.effective_timezone)
    at = datetime(2026, 10, 2, settings.reminder_hour + 1, 0, tzinfo=zone)
    store = client.app.state.blob_store  # type: ignore[attr-defined]
    with client.app.state.session_factory() as db:  # type: ignore[attr-defined]
        ctx = JobContext(db, store, settings)
        assert push.schedule_push(ctx, at) == 1
        assert push.schedule_push(ctx, at) == 0
        db.commit()
    client.app.state.jobs.run_until_idle()  # type: ignore[attr-defined]
    digest = json.loads(push.decrypt(target.requests[-1]["body"], device, auth))
    assert "Chest, left" in digest["body"] and digest["url"].endswith("/")
    with client.app.state.session_factory() as db:  # type: ignore[attr-defined]
        assert push.schedule_push(JobContext(db, store, settings), at) == 0, "sent today already"

    # A device that left (410) is forgotten; one that unsubscribes is removed on request.
    target.status = 410
    assert client.post("/api/push/test", headers=SAME_ORIGIN).json() == {"sent": 0, "failed": 1}
    assert client.get("/api/push").json()["subscriptions"] == 0
    assert client.post("/api/push/subscriptions", json=subscription, headers=SAME_ORIGIN).status_code == 201
    response = client.request(
        "DELETE", "/api/push/subscriptions", json={"endpoint": subscription["endpoint"]}, headers=SAME_ORIGIN
    )
    assert response.status_code == 204
    assert client.get("/api/push").json()["subscriptions"] == 0
    settings.web_push = False
    assert client.post("/api/push/subscriptions", json=subscription, headers=SAME_ORIGIN).status_code == 404
