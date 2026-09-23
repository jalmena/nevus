"""Serve the built single-page application, with a placeholder when no build is present.

`GET /` must answer 200 even without a session: CasaOS opens and health-checks the app at its index and
accepts only 200 or 401.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

PLACEHOLDER = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>neVus</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark light">
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#17161A;color:#EDE8E0;
font:500 18px/1.5 system-ui,sans-serif}p{margin:0;color:#B9B3AA}</style></head>
<body><main><h1>neVus</h1><p>The interface has not been built into this image.</p></main></body></html>
"""

# Python does not know these two by default; browsers care about the font one.
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("application/manifest+json", ".webmanifest")

IMMUTABLE = "public, max-age=31536000, immutable"
NO_CACHE = "no-cache"


def mount_frontend(app: FastAPI, static_dir: Path | None) -> None:
    if static_dir is None or not (static_dir / "index.html").is_file():

        @app.get("/", include_in_schema=False)
        def placeholder() -> HTMLResponse:
            return HTMLResponse(PLACEHOLDER, headers={"Cache-Control": NO_CACHE})

        return

    root = static_dir.resolve()
    index = root / "index.html"
    assets = root / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str, request: Request) -> Response:
        if path.startswith("api/"):
            return Response(status_code=404)
        if path:
            candidate = (root / path).resolve()
            if candidate.is_file() and root in candidate.parents:
                uncached = candidate.name in {"index.html", "sw.js", "manifest.webmanifest"}
                return FileResponse(candidate, headers={"Cache-Control": NO_CACHE if uncached else IMMUTABLE})
        return FileResponse(index, headers={"Cache-Control": NO_CACHE})
