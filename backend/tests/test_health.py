from __future__ import annotations

from fastapi.testclient import TestClient


def test_healthz_reports_ok_with_sqlite_and_writable_storage(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["storage"] == "ok"
    assert body["version"]


def test_index_answers_200_without_a_session(client: TestClient) -> None:
    """CasaOS opens and checks the app at its index and accepts only 200 or 401; a login redirect would fail it."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "neVus" in response.text


def test_static_files_get_the_right_types_and_caching(tmp_path, settings) -> None:  # type: ignore[no-untyped-def]
    from fastapi.testclient import TestClient as Client

    from nevus.app import create_app

    static = tmp_path / "static"
    (static / "fonts").mkdir(parents=True)
    (static / "index.html").write_text("<title>neVus</title>")
    (static / "fonts" / "a.woff2").write_bytes(b"wOF2")
    (static / "manifest.webmanifest").write_text("{}")
    settings.static_dir = static
    with Client(create_app(settings), base_url="http://localhost") as client:
        font = client.get("/fonts/a.woff2")
        assert font.headers["content-type"].startswith("font/woff2")
        assert font.headers["cache-control"] == "public, max-age=31536000, immutable"
        manifest = client.get("/manifest.webmanifest")
        assert manifest.headers["content-type"].startswith("application/manifest+json")
        assert manifest.headers["cache-control"] == "no-cache"
        deep = client.get("/lesions/123")
        assert deep.status_code == 200 and "neVus" in deep.text
        assert client.get("/api/nothing").status_code == 404
