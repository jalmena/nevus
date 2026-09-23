"""Claiming, signing in, sessions, sudo mode, CSRF, rate limiting and account administration."""

from __future__ import annotations

from fastapi.testclient import TestClient

from nevus.auth.service import SESSION_COOKIE

ADMIN = {"username": "Jose", "password": "correct horse battery"}
MEMBER = {"username": "ana", "password": "another long password"}


def claim(client: TestClient) -> None:
    response = client.post("/api/auth/claim", json=ADMIN)
    assert response.status_code == 201, response.text


def test_instance_starts_unclaimed_and_the_first_person_becomes_admin(client: TestClient) -> None:
    assert client.get("/api/auth/instance").json()["claimed"] is False
    response = client.post("/api/auth/claim", json=ADMIN)
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["username"] == "jose"  # usernames are normalised to lowercase
    assert body["user"]["role"] == "admin"
    assert SESSION_COOKIE in client.cookies
    assert client.get("/api/auth/instance").json()["claimed"] is True
    # a second claim is refused
    assert client.post("/api/auth/claim", json=MEMBER).status_code == 409


def test_session_endpoint_requires_a_cookie_and_logout_revokes_it(client: TestClient) -> None:
    assert client.get("/api/auth/session").status_code == 401
    claim(client)
    assert client.get("/api/auth/session").status_code == 200
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/session").status_code == 401


def test_login_with_wrong_password_fails_and_is_rate_limited(client: TestClient, settings) -> None:  # type: ignore[no-untyped-def]
    claim(client)
    client.post("/api/auth/logout")
    for _ in range(settings.login_attempts):
        assert client.post("/api/auth/login", json={**ADMIN, "password": "wrong password here"}).status_code == 401
    assert client.post("/api/auth/login", json=ADMIN).status_code == 429


def test_login_works_and_short_passwords_are_rejected(client: TestClient) -> None:
    claim(client)
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json=ADMIN).status_code == 200
    assert client.post("/api/auth/login", json={"username": "x", "password": "short"}).status_code == 422


def test_cross_site_unsafe_requests_are_refused(client: TestClient) -> None:
    claim(client)
    response = client.post("/api/persons", json={"display_name": "Ana"}, headers={"sec-fetch-site": "cross-site"})
    assert response.status_code == 403
    response = client.post("/api/persons", json={"display_name": "Ana"}, headers={"sec-fetch-site": "same-origin"})
    assert response.status_code == 201
    response = client.post("/api/persons", json={"display_name": "Bea"}, headers={"origin": "https://evil.example.com"})
    assert response.status_code == 403


def test_sudo_is_required_for_destructive_actions(client: TestClient) -> None:
    claim(client)
    person = client.post("/api/persons", json={"display_name": "Ana"}).json()
    assert client.delete(f"/api/persons/{person['id']}").status_code == 403
    assert client.post("/api/auth/sudo", json={"password": "wrong password here"}).status_code == 401
    sudo = client.post("/api/auth/sudo", json={"password": ADMIN["password"]})
    assert sudo.status_code == 200 and sudo.json()["sudo_until"]
    assert client.delete(f"/api/persons/{person['id']}").status_code == 204
    assert client.get(f"/api/persons/{person['id']}").status_code == 404


def test_only_admins_manage_users_and_disabling_ends_sessions(client: TestClient) -> None:
    claim(client)
    created = client.post("/api/users", json={**MEMBER, "role": "member"})
    assert created.status_code == 201
    member_id = created.json()["id"]
    assert client.post("/api/users", json=MEMBER).status_code == 409
    assert len(client.get("/api/users").json()) == 2

    member = TestClient(client.app, base_url="http://localhost")
    assert member.post("/api/auth/login", json=MEMBER).status_code == 200
    assert member.get("/api/users").status_code == 403
    assert member.post("/api/users", json={"username": "eve", "password": "long enough password"}).status_code == 403

    assert client.post(f"/api/users/{member_id}/disable").status_code == 200
    assert member.get("/api/auth/session").status_code == 401
    assert member.post("/api/auth/login", json=MEMBER).status_code == 401
    assert client.post(f"/api/users/{member_id}/enable").status_code == 200
    assert member.post("/api/auth/login", json=MEMBER).status_code == 200


def test_admin_password_reset_and_own_password_change(client: TestClient) -> None:
    claim(client)
    member_id = client.post("/api/users", json=MEMBER).json()["id"]
    assert (
        client.post(f"/api/users/{member_id}/password", json={"new_password": "brand new password"}).status_code == 204
    )
    member = TestClient(client.app, base_url="http://localhost")
    assert member.post("/api/auth/login", json=MEMBER).status_code == 401
    assert member.post("/api/auth/login", json={**MEMBER, "password": "brand new password"}).status_code == 200
    change = member.post(
        "/api/auth/me/password", json={"current_password": "brand new password", "new_password": "my own new password"}
    )
    assert change.status_code == 204
    assert member.get("/api/auth/session").status_code == 200  # the current session survives a password change


def test_preferences_are_stored_with_the_account(client: TestClient) -> None:
    claim(client)
    response = client.patch("/api/auth/me", json={"language": "es", "theme": "dark", "show_uncertainty": False})
    assert response.status_code == 200
    user = client.get("/api/auth/session").json()["user"]
    assert (user["language"], user["theme"], user["show_uncertainty"]) == ("es", "dark", False)
    assert client.patch("/api/auth/me", json={"language": "fr"}).status_code == 422


def test_admin_from_environment_is_created_at_startup(tmp_path, settings) -> None:  # type: ignore[no-untyped-def]
    from nevus.app import create_app

    settings.admin_user = "boot"
    settings.admin_password = "bootstrap password long"
    with TestClient(create_app(settings), base_url="http://localhost") as client:
        assert client.get("/api/auth/instance").json()["claimed"] is True
        assert (
            client.post("/api/auth/login", json={"username": "boot", "password": "bootstrap password long"}).status_code
            == 200
        )
        assert client.get("/api/auth/session").json()["user"]["role"] == "admin"
