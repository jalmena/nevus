from __future__ import annotations

from fastapi.testclient import TestClient

from nevus.web.security import host_is_allowed


def test_security_headers_are_present(client: TestClient) -> None:
    headers = client.get("/healthz").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert headers["Cross-Origin-Resource-Policy"] == "same-origin"
    assert headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]


def test_private_addresses_localhost_and_local_names_are_always_allowed() -> None:
    for host in (
        "localhost",
        "localhost:8080",
        "127.0.0.1",
        "192.168.1.20:8080",
        "10.0.0.5",
        "nas.local",
        "[::1]:8080",
    ):
        assert host_is_allowed(host, []), host


def test_public_names_need_to_be_configured() -> None:
    assert not host_is_allowed("evil.example.com", [])
    assert host_is_allowed("nevus.example.test", ["nevus.example.test"])
    assert host_is_allowed("app.nevus.example.test", ["*.nevus.example.test"])
    assert not host_is_allowed("8.8.8.8", [])


def test_unknown_host_is_refused_with_421(client: TestClient) -> None:
    response = client.get("/healthz", headers={"host": "evil.example.com"})
    assert response.status_code == 421
    response = client.get("/healthz", headers={"host": "nevus.example.test"})
    assert response.status_code == 200
