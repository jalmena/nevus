# SPDX-License-Identifier: AGPL-3.0-only
"""Single sign-on through a reverse proxy: the header counts only from the proxy, and emergencies are covered."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from nevus.app import create_app
from nevus.auth.proxy import emergency_link
from nevus.config import Settings

PROXY = ("172.18.0.5", 50000)
STRANGER = ("192.168.1.77", 50000)
SAME_ORIGIN = {"sec-fetch-site": "same-origin"}


def _as(name: str, **extra: str) -> dict[str, str]:
    return {"Remote-User": name, **SAME_ORIGIN, **extra}


@pytest.fixture
def proxy_settings(settings: Settings) -> Settings:
    return settings.model_copy(
        update={"auth_mode": "proxy", "proxy_trusted": ["172.18.0.0/16"], "proxy_logout_url": "https://sso/out"}
    )


@pytest.fixture
def app(proxy_settings: Settings) -> Iterator[Any]:
    application = create_app(proxy_settings)
    with TestClient(application, base_url="http://localhost", client=PROXY):
        yield application


def _client(app: Any, peer: tuple[str, int] = PROXY) -> TestClient:
    return TestClient(app, base_url="http://localhost", client=peer)


def test_proxy_mode_needs_the_proxy_address(settings: Settings) -> None:
    with pytest.raises(ValidationError, match="NEVUS_PROXY_TRUSTED"):
        Settings(data_dir=settings.data_dir, auth_mode="proxy")
    with pytest.raises(ValidationError):
        Settings(data_dir=settings.data_dir, auth_mode="proxy", proxy_trusted="not-an-address")


def test_the_first_person_through_the_proxy_becomes_the_administrator(app: Any) -> None:
    client = _client(app)
    status = client.get("/api/auth/instance").json()
    assert status["auth_mode"] == "proxy" and status["logout_url"] == "https://sso/out" and not status["claimed"]
    first = client.get("/api/auth/session", headers=_as("Jose"))
    assert first.status_code == 200 and first.json()["user"]["username"] == "jose"
    assert first.json()["user"]["role"] == "admin" and "nevus_session" in first.cookies
    second = _client(app).get("/api/auth/session", headers=_as("ana", **{"Remote-Email": "ana@example.home"}))
    assert second.json()["user"]["role"] == "member" and second.json()["user"]["email"] == "ana@example.home"


def test_the_header_is_ignored_from_anywhere_but_the_proxy(app: Any) -> None:
    _client(app).get("/api/auth/session", headers=_as("jose"))
    spoofed = _client(app, STRANGER).get("/api/auth/session", headers=_as("jose"))
    assert spoofed.status_code == 401 and spoofed.headers["x-auth-mode"] == "proxy"


def test_a_session_lasts_only_while_the_proxy_vouches_for_the_same_person(app: Any) -> None:
    client = _client(app)
    client.get("/api/auth/session", headers=_as("jose"))
    assert client.get("/api/persons", headers=_as("jose")).status_code == 200
    assert client.get("/api/persons").status_code == 401, "no header: the cookie alone is not enough"
    switched = client.get("/api/auth/session", headers=_as("ana"))
    assert switched.json()["user"]["username"] == "ana", "someone else signed in at the proxy"


def test_passwords_are_closed_and_sudo_is_a_confirmation(app: Any) -> None:
    client = _client(app)
    client.get("/api/auth/session", headers=_as("jose"))
    assert client.post("/api/auth/login", json={"username": "jose", "password": "x" * 12}).status_code == 403
    assert (
        client.post(
            "/api/auth/me/password",
            json={"current_password": "x" * 12, "new_password": "y" * 12},
            headers=_as("jose"),
        ).status_code
        == 403
    )
    sudo = client.post("/api/auth/sudo", json={}, headers=_as("jose"))
    assert sudo.status_code == 200 and sudo.json()["sudo_until"] is not None


def test_new_accounts_can_be_left_to_the_administrator(proxy_settings: Settings) -> None:
    app = create_app(proxy_settings.model_copy(update={"proxy_auto_create": False}))
    with TestClient(app, base_url="http://localhost", client=PROXY) as client:
        assert client.get("/api/auth/session", headers=_as("jose")).status_code == 200, "the first one claims"
        refused = _client(app).get("/api/auth/session", headers=_as("ana"))
        assert refused.status_code == 403 and "administrator" in refused.json()["detail"]


def test_an_emergency_link_works_once_without_the_proxy(app: Any) -> None:
    _client(app).get("/api/auth/session", headers=_as("jose"))
    with app.state.session_factory() as db:
        token = emergency_link(db, app.state.settings, "jose")
        db.commit()
    direct = _client(app, STRANGER)
    opened = direct.get(f"/api/auth/emergency/{token}", follow_redirects=False)
    assert opened.status_code == 303 and opened.headers["location"] == "/"
    assert direct.get("/api/auth/session").json()["user"]["username"] == "jose", "no header needed"
    again = _client(app, STRANGER).get(f"/api/auth/emergency/{token}", follow_redirects=False)
    assert again.status_code == 404, "a link works once"


def test_the_link_itself_is_not_a_session(app: Any) -> None:
    _client(app).get("/api/auth/session", headers=_as("jose"))
    with app.state.session_factory() as db:
        token = emergency_link(db, app.state.settings, "jose")
        db.commit()
    sneaky = _client(app, STRANGER)
    sneaky.cookies.set("nevus_session", token)
    assert sneaky.get("/api/auth/session").status_code == 401
