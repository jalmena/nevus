# SPDX-License-Identifier: AGPL-3.0-only
"""The second factor: codes, setting it up, signing in with a code or a recovery code, limits, the way back."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from nevus.auth import service, totp
from nevus.db.models import AuditLog
from tests.test_accounts import ADMIN, MEMBER, claim
from tests.test_scale import SAME_ORIGIN


def _login(client: TestClient, credentials: dict[str, str]) -> dict:  # type: ignore[type-arg]
    response = client.post("/api/auth/login", json=credentials, headers=SAME_ORIGIN)
    assert response.status_code == 200, response.text
    return dict(response.json())


def _enable(client: TestClient, password: str) -> tuple[str, list[str]]:
    """Set the factor up as the signed-in person: sudo, a secret, the first code; returns secret and codes."""
    assert client.post("/api/auth/sudo", json={"password": password}, headers=SAME_ORIGIN).status_code == 200
    setup = client.post("/api/auth/totp/setup", headers=SAME_ORIGIN)
    assert setup.status_code == 200, setup.text
    body = setup.json()
    assert body["otpauth_uri"].startswith("otpauth://totp/neVus:") and "issuer=neVus" in body["otpauth_uri"]
    assert body["qr_svg"].startswith("<svg")
    assert client.get("/api/auth/totp").json()["setting_up"] is True
    code = totp.code_for(body["secret"], totp.current_counter())
    enabled = client.post("/api/auth/totp/enable", json={"code": code}, headers=SAME_ORIGIN)
    assert enabled.status_code == 200, enabled.text
    codes = enabled.json()["recovery_codes"]
    assert len(codes) == 10 and all(len(c) == 11 and c[5] == "-" for c in codes)
    return str(body["secret"]), list(codes)


def _wrong(code: str) -> str:
    return str((int(code[0]) + 1) % 10) + code[1:]


def test_codes_follow_the_reference_vectors() -> None:
    # RFC 6238, appendix B, HMAC-SHA1 with the seed "12345678901234567890", the last six digits.
    secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
    assert totp.code_for(secret, 59 // 30) == "287082"
    assert totp.code_for(secret, 1111111109 // 30) == "081804"
    assert totp.code_for(secret, 1234567890 // 30) == "005924"
    assert totp.code_for(secret, 20000000000 // 30) == "353130"


def test_a_code_is_accepted_one_step_either_side_and_never_twice() -> None:
    secret = totp.new_secret()
    now = 1_700_000_000.0
    counter = int(now // 30)
    assert totp.verify(secret, totp.code_for(secret, counter - 1), at=now) == counter - 1
    assert totp.verify(secret, totp.code_for(secret, counter + 1), at=now) == counter + 1
    assert totp.verify(secret, totp.code_for(secret, counter + 2), at=now) is None
    assert totp.verify(secret, totp.code_for(secret, counter), last_counter=counter, at=now) is None
    assert totp.verify(secret, "abcdef", at=now) is None
    code = totp.code_for(secret, counter)
    assert totp.verify(secret, f"{code[:3]} {code[3:]}", at=now) == counter


def test_signing_in_needs_the_code_once_the_factor_is_on(client: TestClient) -> None:
    claim(client)
    secret, _ = _enable(client, ADMIN["password"])
    assert client.get("/api/auth/session").json()["user"]["totp_enabled"] is True
    status = client.get("/api/auth/totp").json()
    assert status["enabled"] is True and status["setting_up"] is False and status["recovery_codes_left"] == 10
    client.post("/api/auth/logout", headers=SAME_ORIGIN)

    assert _login(client, ADMIN) == {"session": None, "second_factor_required": True}
    assert client.get("/api/auth/session").status_code == 401, "the password alone opens nothing"
    assert client.get("/api/persons").status_code == 401
    # Enabling used the current step's code; the next step's is also accepted, and is not a replay.
    code = totp.code_for(secret, totp.current_counter() + 1)
    wrong = client.post("/api/auth/second-factor", json={"code": _wrong(code)}, headers=SAME_ORIGIN)
    assert wrong.status_code == 401
    client.post("/api/auth/login", json={**ADMIN, "password": "not the right password"}, headers=SAME_ORIGIN)
    with client.app.state.session_factory() as db:  # type: ignore[attr-defined]
        for action in ("login.second_factor_failed", "login.failed"):
            count = db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == action))
            assert count == 1, f"a refused attempt is still recorded: {action}"
    done = client.post("/api/auth/second-factor", json={"code": code}, headers=SAME_ORIGIN)
    assert done.status_code == 200, done.text
    assert done.json()["user"]["username"] == "jose"
    assert client.get("/api/auth/session").status_code == 200

    # The same code does not open a second sign-in.
    client.post("/api/auth/logout", headers=SAME_ORIGIN)
    _login(client, ADMIN)
    assert client.post("/api/auth/second-factor", json={"code": code}, headers=SAME_ORIGIN).status_code == 401
    # Without a pending sign-in there is nothing to complete.
    client.cookies.clear()
    assert client.post("/api/auth/second-factor", json={"code": code}, headers=SAME_ORIGIN).status_code == 401


def test_recovery_codes_work_once_and_can_be_renewed(client: TestClient) -> None:
    claim(client)
    _, codes = _enable(client, ADMIN["password"])
    client.post("/api/auth/logout", headers=SAME_ORIGIN)
    _login(client, ADMIN)
    spaced = codes[0].upper().replace("-", " ")
    first = client.post("/api/auth/second-factor", json={"recovery_code": spaced}, headers=SAME_ORIGIN)
    assert first.status_code == 200
    assert client.get("/api/auth/totp").json()["recovery_codes_left"] == 9
    client.post("/api/auth/logout", headers=SAME_ORIGIN)
    _login(client, ADMIN)
    used = client.post("/api/auth/second-factor", json={"recovery_code": codes[0]}, headers=SAME_ORIGIN)
    assert used.status_code == 401
    assert (
        client.post("/api/auth/second-factor", json={"recovery_code": codes[1]}, headers=SAME_ORIGIN).status_code == 200
    )

    client.post("/api/auth/sudo", json={"password": ADMIN["password"]}, headers=SAME_ORIGIN)
    renewed = client.post("/api/auth/totp/recovery-codes", headers=SAME_ORIGIN).json()["recovery_codes"]
    assert len(renewed) == 10 and not set(renewed) & set(codes)
    client.post("/api/auth/logout", headers=SAME_ORIGIN)
    _login(client, ADMIN)
    old = client.post("/api/auth/second-factor", json={"recovery_code": codes[2]}, headers=SAME_ORIGIN)
    assert old.status_code == 401
    assert (
        client.post("/api/auth/second-factor", json={"recovery_code": renewed[0]}, headers=SAME_ORIGIN).status_code
        == 200
    )


def test_wrong_codes_are_limited_and_end_the_pending_sign_in(client: TestClient, settings) -> None:  # type: ignore[no-untyped-def]
    claim(client)
    _enable(client, ADMIN["password"])
    client.post("/api/auth/logout", headers=SAME_ORIGIN)
    _login(client, ADMIN)
    body = {"recovery_code": "aaaaa-aaaaa"}
    for _ in range(settings.login_attempts):
        assert client.post("/api/auth/second-factor", json=body, headers=SAME_ORIGIN).status_code == 401
    assert client.post("/api/auth/second-factor", json=body, headers=SAME_ORIGIN).status_code == 429
    assert client.post("/api/auth/second-factor", json=body, headers=SAME_ORIGIN).status_code == 401


def test_turning_the_factor_off_oneself_or_by_the_administrator(client: TestClient) -> None:
    claim(client)
    _enable(client, ADMIN["password"])
    client.post("/api/auth/sudo", json={"password": ADMIN["password"]}, headers=SAME_ORIGIN)
    assert client.delete("/api/auth/totp", headers=SAME_ORIGIN).status_code == 204
    assert client.get("/api/auth/totp").json() == {
        "enabled": False,
        "enabled_at": None,
        "setting_up": False,
        "recovery_codes_left": 0,
    }
    client.post("/api/auth/logout", headers=SAME_ORIGIN)
    assert _login(client, ADMIN)["second_factor_required"] is False

    # A member turns the factor on, loses the authenticator, and the administrator turns it off.
    client.post("/api/auth/sudo", json={"password": ADMIN["password"]}, headers=SAME_ORIGIN)
    member = client.post("/api/users", json={**MEMBER, "role": "member"}, headers=SAME_ORIGIN).json()
    client.post("/api/auth/logout", headers=SAME_ORIGIN)
    _login(client, MEMBER)
    _enable(client, MEMBER["password"])
    client.post("/api/auth/logout", headers=SAME_ORIGIN)
    assert _login(client, MEMBER)["second_factor_required"] is True
    client.cookies.clear()
    _login(client, ADMIN)
    assert client.delete(f"/api/users/{member['id']}/totp", headers=SAME_ORIGIN).status_code == 403, "sudo first"
    client.post("/api/auth/sudo", json={"password": ADMIN["password"]}, headers=SAME_ORIGIN)
    assert client.delete(f"/api/users/{member['id']}/totp", headers=SAME_ORIGIN).status_code == 204
    client.cookies.clear()
    answer = _login(client, MEMBER)
    assert answer["second_factor_required"] is False and answer["session"]["user"]["totp_enabled"] is False


def test_the_environment_administrator_reset_clears_the_factor(client: TestClient, settings) -> None:  # type: ignore[no-untyped-def]
    claim(client)
    _enable(client, ADMIN["password"])
    fresh = settings.model_copy(update={"admin_user": ADMIN["username"], "admin_password": "a brand new long password"})
    with client.app.state.session_factory() as db:  # type: ignore[attr-defined]
        service.bootstrap_admin(db, fresh)
        db.commit()
    client.cookies.clear()
    answer = _login(client, {"username": ADMIN["username"], "password": "a brand new long password"})
    assert answer["second_factor_required"] is False


def test_the_setup_needs_sudo_and_a_matching_first_code(client: TestClient) -> None:
    claim(client)
    assert client.post("/api/auth/totp/setup", headers=SAME_ORIGIN).status_code == 403
    client.post("/api/auth/sudo", json={"password": ADMIN["password"]}, headers=SAME_ORIGIN)
    secret = client.post("/api/auth/totp/setup", headers=SAME_ORIGIN).json()["secret"]
    code = totp.code_for(secret, totp.current_counter())
    assert client.post("/api/auth/totp/enable", json={"code": _wrong(code)}, headers=SAME_ORIGIN).status_code == 400
    assert client.get("/api/auth/session").json()["user"]["totp_enabled"] is False
    assert client.post("/api/auth/totp/enable", json={"code": code}, headers=SAME_ORIGIN).status_code == 200
    assert client.post("/api/auth/totp/setup", headers=SAME_ORIGIN).status_code == 409
