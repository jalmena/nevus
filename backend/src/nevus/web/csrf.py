"""Cross-site request forgery protection for the API.

Sessions live in a SameSite=Lax cookie, so cross-site POSTs already lose the cookie in modern browsers. This
middleware adds the belt to those braces: unsafe requests to /api must come from this origin, proven by the
browser's Sec-Fetch-Site header or, for browsers without it, by an Origin header that matches the Host.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


def request_is_same_site(request: Request) -> bool:
    fetch_site = request.headers.get("sec-fetch-site")
    if fetch_site is not None:
        return fetch_site in {"same-origin", "none"}
    origin = request.headers.get("origin")
    if origin is None:
        return True  # not a browser (curl, tests); the session cookie is still required
    host = request.headers.get("host", "")
    return origin.split("://", 1)[-1].lower() == host.lower()


class CsrfMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if request.method in UNSAFE and request.url.path.startswith("/api/") and not request_is_same_site(request):
            return JSONResponse({"detail": "Cross-site request refused."}, status_code=403)
        return await call_next(request)
