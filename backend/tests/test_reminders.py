# SPDX-License-Identifier: AGPL-3.0-only
"""Reminders: the due list, snoozing, and the daily email digest through the operator's SMTP server."""

from __future__ import annotations

import smtplib
from datetime import UTC, date, datetime, timedelta
from email.message import EmailMessage
from typing import Any, ClassVar

import pytest
from fastapi.testclient import TestClient

from nevus import secretbox
from nevus.jobs.registry import JobContext
from nevus.notify import email as email_module
from tests.test_accounts import MEMBER, claim

SAME_ORIGIN = {"sec-fetch-site": "same-origin"}


class FakeSMTP:
    sent: ClassVar[list[EmailMessage]] = []
    logins: ClassVar[list[tuple[str, str]]] = []

    def __init__(self, host: str, port: int, timeout: float = 0) -> None:
        self.host, self.port = host, port

    def __enter__(self) -> FakeSMTP:
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def starttls(self, context: Any = None) -> None:
        return None

    def login(self, user: str, password: str) -> None:
        FakeSMTP.logins.append((user, password))

    def send_message(self, message: EmailMessage) -> None:
        FakeSMTP.sent.append(message)


@pytest.fixture
def smtp(monkeypatch: pytest.MonkeyPatch) -> type[FakeSMTP]:
    FakeSMTP.sent, FakeSMTP.logins = [], []
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    return FakeSMTP


def _mark(client: TestClient, person_id: str, label: str, noticed_days_ago: int, interval: int = 30) -> str:
    noticed = (datetime.now(UTC).date() - timedelta(days=noticed_days_ago)).isoformat()
    response = client.post(
        f"/api/persons/{person_id}/lesions",
        json={
            "label": label,
            "location": {"zone": "1250", "x": 0.4, "y": 0.25},
            "first_noticed_on": noticed,
            "status": "active",
            "interval_days": interval,
        },
        headers=SAME_ORIGIN,
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def _person(client: TestClient, name: str) -> str:
    return str(client.post("/api/persons", json={"display_name": name}, headers=SAME_ORIGIN).json()["id"])


def test_the_due_list_covers_every_person_and_snoozing_hides_a_mark(client: TestClient) -> None:
    claim(client)
    ana, bea = _person(client, "Ana"), _person(client, "Bea")
    old = _mark(client, ana, "Chest", noticed_days_ago=100)
    _mark(client, bea, "Back", noticed_days_ago=40)
    _mark(client, ana, "Arm", noticed_days_ago=5)  # not due yet
    due = client.get("/api/due").json()
    assert [(d["label"], d["person_name"]) for d in due] == [("Chest", "Ana"), ("Back", "Bea")]
    assert due[0]["overdue_days"] == 70

    snoozed = client.post(f"/api/lesions/{old}/snooze", json={"days": 7}, headers=SAME_ORIGIN).json()
    assert snoozed["due"] is False and snoozed["snoozed_until"] == (date.today() + timedelta(days=7)).isoformat()
    assert [d["label"] for d in client.get("/api/due").json()] == ["Back"]

    # A visit ends the snooze and resets the clock.
    client.post(f"/api/lesions/{old}/observations", json={}, headers=SAME_ORIGIN)
    after = client.get(f"/api/lesions/{old}").json()
    assert after["snoozed_until"] is None and after["due"] is False
    assert client.post(f"/api/lesions/{old}/snooze", json={"days": 3}, headers=SAME_ORIGIN).status_code == 422


def test_email_settings_keep_the_password_secret(client: TestClient, settings: Any) -> None:
    claim(client)
    saved = client.put(
        "/api/admin/email",
        json={
            "host": "smtp.example.test",
            "port": 587,
            "security": "starttls",
            "username": "nevus",
            "password": "s3cret-pass",
            "sender": "nevus@example.test",
            "public_url": "https://nevus.example.test",
        },
        headers=SAME_ORIGIN,
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["has_password"] is True and body["ready"] is True and "password" not in body
    # Stored sealed, never in clear.
    with client.app.state.session_factory() as db:  # type: ignore[attr-defined]
        from nevus.db.models import Setting

        stored = db.get(Setting, "notify.email").value
        assert stored["password"].startswith("v1:") and "s3cret" not in stored["password"]
        assert secretbox.open_(settings.secret_key(), stored["password"]) == "s3cret-pass"
    # Saving again without a password keeps it.
    again = client.put(
        "/api/admin/email", json={"host": "smtp2.example.test", "sender": "nevus@example.test"}, headers=SAME_ORIGIN
    )
    assert again.json()["has_password"] is True and again.json()["host"] == "smtp2.example.test"


def test_only_admins_see_instance_settings(client: TestClient) -> None:
    claim(client)
    client.post("/api/users", json=MEMBER, headers=SAME_ORIGIN)
    client.post("/api/auth/logout", headers=SAME_ORIGIN)
    client.post("/api/auth/login", json=MEMBER, headers=SAME_ORIGIN)
    assert client.get("/api/admin/email").status_code == 403
    assert client.get("/api/admin/instance").status_code == 403


def test_a_test_email_goes_out(client: TestClient, smtp: type[FakeSMTP]) -> None:
    claim(client)
    assert (
        client.post("/api/admin/email/test", json={"to": "jose@example.test"}, headers=SAME_ORIGIN).status_code == 409
    )
    client.put(
        "/api/admin/email",
        json={"host": "smtp.example.test", "username": "nevus", "password": "pw", "sender": "nevus@example.test"},
        headers=SAME_ORIGIN,
    )
    assert (
        client.post("/api/admin/email/test", json={"to": "jose@example.test"}, headers=SAME_ORIGIN).status_code == 204
    )
    assert smtp.sent[-1]["To"] == "jose@example.test" and smtp.logins[-1] == ("nevus", "pw")


def test_the_daily_digest_goes_once_to_people_who_asked(
    client: TestClient, smtp: type[FakeSMTP], settings: Any
) -> None:
    claim(client)
    client.put(
        "/api/admin/email",
        json={"host": "smtp.example.test", "sender": "nevus@example.test", "public_url": "https://nevus.example.test"},
        headers=SAME_ORIGIN,
    )
    ana = _person(client, "Ana")
    _mark(client, ana, "Chest", noticed_days_ago=100)
    runner = client.app.state.jobs  # type: ignore[attr-defined]

    def schedule(hour: int) -> int:
        with client.app.state.session_factory() as db:  # type: ignore[attr-defined]
            queued = email_module.schedule_digests(
                JobContext(db, client.app.state.blob_store, settings),  # type: ignore[attr-defined]
                now=datetime.now(UTC).replace(hour=hour, minute=0),
            )
            db.commit()
            return queued

    assert schedule(9) == 0, "nobody asked for email yet"
    client.patch("/api/auth/me", json={"email": "jose@example.test", "email_reminders": True}, headers=SAME_ORIGIN)
    assert schedule(6) == 0, "before the reminder hour"
    assert schedule(9) == 1
    assert runner.run_until_idle() == 1
    message = smtp.sent[-1]
    assert message["To"] == "jose@example.test" and message["Subject"] == "neVus: one mark is due for a photo"
    text = message.get_content()
    assert "Chest (Ana)" in text and "https://nevus.example.test" in text and "does not diagnose" in text
    assert schedule(10) == 0, "one digest a day"


def test_new_accounts_get_the_instance_default_language(client: TestClient) -> None:
    claim(client)
    assert client.get("/api/admin/instance").json() == {"default_language": "en"}
    client.put("/api/admin/instance", json={"default_language": "es"}, headers=SAME_ORIGIN)
    created = client.post("/api/users", json=MEMBER, headers=SAME_ORIGIN).json()
    assert created["language"] == "es"
