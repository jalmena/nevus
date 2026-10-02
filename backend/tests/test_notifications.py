# SPDX-License-Identifier: AGPL-3.0-only
"""Webhooks with their presets, and the per-person calendar feed behind a secret link."""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from collections.abc import Iterator
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from nevus.db.types import utcnow
from nevus.jobs.registry import JobContext
from nevus.notify import webhooks
from tests.test_accounts import MEMBER, claim
from tests.test_scale import SAME_ORIGIN


class Target:
    """A local HTTP server standing in for Home Assistant, n8n, ntfy or Gotify."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.status = 200
        target = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                target.requests.append(
                    {"path": self.path, "headers": dict(self.headers), "body": self.rfile.read(length)}
                )
                self.send_response(target.status)
                self.end_headers()

            def log_message(self, *args: Any) -> None:
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()


@pytest.fixture
def target() -> Iterator[Target]:
    server = Target()
    yield server
    server.server.shutdown()


def _due_mark(client: TestClient, label: str = "Chest, left") -> tuple[str, str]:
    pid = client.post("/api/persons", json={"display_name": "Ana"}, headers=SAME_ORIGIN).json()["id"]
    lesion = client.post(
        f"/api/persons/{pid}/lesions",
        json={
            "label": label,
            "location": {"zone": "1250", "x": 0.4, "y": 0.25},
            "status": "active",
            "interval_days": 90,
            "first_noticed_on": (utcnow().date() - timedelta(days=200)).isoformat(),
        },
        headers=SAME_ORIGIN,
    ).json()
    return pid, lesion["id"]


def _hook(client: TestClient, url: str, preset: str = "generic", secret: str | None = None) -> dict[str, Any]:
    response = client.post(
        "/api/admin/webhooks",
        json={"name": "Home", "preset": preset, "url": url, "secret": secret},
        headers=SAME_ORIGIN,
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


def test_only_a_hint_of_the_address_is_shown_and_members_cannot_add_webhooks(client: TestClient) -> None:
    claim(client)
    made = _hook(client, "https://ha.example/api/webhook/very-secret-webhook-id-0123456789", "home_assistant", "s3")
    assert made["url_hint"].startswith("https://ha.example/api/webhook/") and "0123456789" not in made["url_hint"]
    assert made["has_secret"] is True and "secret" not in made
    assert (
        client.post(
            "/api/admin/webhooks", json={"name": "x", "url": "file:///etc/passwd"}, headers=SAME_ORIGIN
        ).status_code
        == 422
    )
    client.post("/api/users", json=MEMBER, headers=SAME_ORIGIN)
    client.post("/api/auth/logout", headers=SAME_ORIGIN)
    client.post("/api/auth/login", json=MEMBER, headers=SAME_ORIGIN)
    assert client.get("/api/admin/webhooks").status_code == 403
    assert client.post("/api/admin/webhooks", json={"name": "x", "url": "https://x.example"}).status_code == 403


def test_a_test_message_says_whether_it_arrived(client: TestClient, target: Target) -> None:
    claim(client)
    made = _hook(client, f"{target.url}/hook")
    assert client.post(f"/api/admin/webhooks/{made['id']}/test", headers=SAME_ORIGIN).json() == {
        "ok": True,
        "detail": None,
    }
    assert json.loads(target.requests[0]["body"])["event"] == "test"
    target.status = 500
    failed = client.post(f"/api/admin/webhooks/{made['id']}/test", headers=SAME_ORIGIN).json()
    assert failed["ok"] is False and "500" in failed["detail"]
    listed = client.get("/api/admin/webhooks").json()[0]
    assert listed["last_status"] == "failed" and target.url not in (listed["last_error"] or "")


def test_the_daily_digest_reaches_a_signed_generic_webhook_once(client: TestClient, target: Target) -> None:
    claim(client)
    _due_mark(client)
    _hook(client, f"{target.url}/n8n", "n8n", secret="shared secret")
    app = client.app
    zone = ZoneInfo(app.state.settings.effective_timezone)  # type: ignore[attr-defined]
    morning = datetime.now(tz=zone).replace(hour=10)
    with app.state.session_factory() as db:  # type: ignore[attr-defined]
        ctx = JobContext(db, app.state.blob_store, app.state.settings)  # type: ignore[attr-defined]
        assert webhooks.schedule_webhooks(ctx, morning.replace(hour=6)) == 0, "not before the reminder hour"
        assert webhooks.schedule_webhooks(ctx, morning) == 1
        db.commit()
    app.state.jobs.run_until_idle()  # type: ignore[attr-defined]
    request = target.requests[0]
    body = request["body"]
    expected = hmac.new(b"shared secret", body, hashlib.sha256).hexdigest()
    assert request["headers"]["X-Nevus-Signature"] == f"sha256={expected}"
    message = json.loads(body)
    assert message["event"] == "due" and message["count"] == 1
    assert message["items"][0]["mark"] == "Chest, left" and message["items"][0]["zone"] == "Right pectoral"
    with app.state.session_factory() as db:  # type: ignore[attr-defined]
        ctx = JobContext(db, app.state.blob_store, app.state.settings)  # type: ignore[attr-defined]
        assert webhooks.schedule_webhooks(ctx, morning) == 0, "once a day"


def test_ntfy_and_gotify_get_the_shape_they_expect() -> None:
    message = {
        "event": "due",
        "count": 2,
        "url": "https://nevus.home",
        "items": [
            {"mark": "Chest", "person": "Ana María", "due_since": "2026-09-01"},
            {"mark": "Back", "person": "Ana María", "due_since": "2026-09-02"},
        ],
    }
    ntfy = webhooks.request_for("ntfy", "https://ntfy.home/skin", "tk", message, "es")
    assert ntfy["url"] == "https://ntfy.home/skin" and ntfy["headers"]["Authorization"] == "Bearer tk"
    assert ntfy["headers"]["Click"] == "https://nevus.home" and ntfy["headers"]["Title"].isascii()
    assert "Ana María" in ntfy["body"].decode()
    gotify = webhooks.request_for("gotify", "https://gotify.home/", "app-token", message, "en")
    assert gotify["url"] == "https://gotify.home/message" and gotify["headers"]["X-Gotify-Key"] == "app-token"
    sent = json.loads(gotify["body"])
    assert sent["title"] == "neVus: 2 marks are due for a photo" and "Back (Ana María)" in sent["message"]
    assert webhooks._header("Toca fotografía").startswith("=?UTF-8?B?")


def test_a_target_that_is_away_is_reported_without_its_address() -> None:
    with pytest.raises(webhooks.WebhookError) as caught:
        webhooks.send({"url": "http://127.0.0.1:9/hook?token=secret", "headers": {}, "body": b"{}"}, timeout=2)
    assert "127.0.0.1" not in str(caught.value) and "secret" not in str(caught.value)


def test_the_calendar_link_works_without_a_session_and_stops_when_replaced(client: TestClient) -> None:
    claim(client)
    pid, lesion = _due_mark(client, "Chest; left, upper")
    client.post(f"/api/persons/{pid}/appointments", json={"date": "2030-05-20"}, headers=SAME_ORIGIN)
    made = client.post(f"/api/persons/{pid}/calendar", headers=SAME_ORIGIN)
    assert made.status_code == 201
    url = made.json()["url"]
    path = url[url.index("/api/calendar/") :]
    assert client.get(f"/api/persons/{pid}/calendar").json()["exists"] is True
    anonymous = TestClient(client.app, base_url="http://localhost")
    ics = anonymous.get(path)
    assert ics.status_code == 200 and ics.headers["content-type"].startswith("text/calendar")
    text = ics.text
    assert text.startswith("BEGIN:VCALENDAR\r\n") and text.endswith("END:VCALENDAR\r\n")
    assert "SUMMARY:Photo due: Chest\; left\\, upper (Ana)" in text
    assert f"UID:due-{lesion}@nevus" in text and "DTSTART;VALUE=DATE:20300520" in text
    assert all(len(line.encode()) <= 75 for line in text.split("\r\n"))
    client.post(f"/api/persons/{pid}/calendar", headers=SAME_ORIGIN)
    assert anonymous.get(path).status_code == 404, "a new link ends the old one"


def test_the_calendar_link_stops_with_the_access(client: TestClient) -> None:
    claim(client)
    pid, _ = _due_mark(client)
    client.post("/api/users", json=MEMBER, headers=SAME_ORIGIN)
    client.put(
        f"/api/persons/{pid}/access", json={"username": MEMBER["username"], "role": "viewer"}, headers=SAME_ORIGIN
    )
    client.post("/api/auth/logout", headers=SAME_ORIGIN)
    client.post("/api/auth/login", json=MEMBER, headers=SAME_ORIGIN)
    url = client.post(f"/api/persons/{pid}/calendar", headers=SAME_ORIGIN).json()["url"]
    path = url[url.index("/api/calendar/") :]
    assert client.get(path).status_code == 200
    client.post("/api/auth/logout", headers=SAME_ORIGIN)
    client.post("/api/auth/login", json={"username": "jose", "password": "correct horse battery"}, headers=SAME_ORIGIN)
    member = next(a for a in client.get(f"/api/persons/{pid}/access").json() if a["username"] == MEMBER["username"])
    client.delete(f"/api/persons/{pid}/access/{member['user_id']}", headers=SAME_ORIGIN)
    assert client.get(path).status_code == 404
