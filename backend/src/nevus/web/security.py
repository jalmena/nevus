"""Security middleware: host allowlist against DNS rebinding, and response headers."""

from __future__ import annotations

import ipaddress
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; "
    "style-src 'self' 'unsafe-inline'; font-src 'self'; connect-src 'self'; "
    "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)


def host_is_allowed(host: str, allowed: list[str]) -> bool:
    """Private addresses, localhost and .local names are always answered; public names must be configured.

    A hostile web page can point its own hostname at a private address and reach this server from inside
    the network (DNS rebinding); refusing unknown public names closes that hole with no configuration.
    """
    hostname = host.rsplit(":", 1)[0].lower() if not host.startswith("[") else host.split("]")[0].strip("[")
    if hostname in {"localhost", "127.0.0.1", "::1"} or hostname.endswith(".localhost") or hostname.endswith(".local"):
        return True
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return hostname in allowed or any(
            hostname.endswith("." + a.lstrip("*.")) for a in allowed if a.startswith("*.")
        )
    return address.is_private or address.is_loopback or address.is_link_local


class HostAllowlistMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Callable[..., Awaitable[None]], allowed_hosts: list[str]) -> None:
        super().__init__(app)
        self.allowed_hosts = [h.lower() for h in allowed_hosts]

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        host = request.headers.get("host", "")
        if not host or not host_is_allowed(host, self.allowed_hosts):
            return PlainTextResponse("This server does not answer to that name.", status_code=421)
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)
        response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Permissions-Policy", "camera=(self), microphone=(), geolocation=()")
        return response
