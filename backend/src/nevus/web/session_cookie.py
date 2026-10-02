# SPDX-License-Identifier: AGPL-3.0-only
"""Hands out the session cookie when a request started a session without a sign-in form (proxy mode).

The session is created inside the request (in a dependency), but endpoints that return files build
their own responses, so the cookie is set here, on whatever response leaves.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from nevus.auth.dependencies import request_is_secure
from nevus.auth.service import SESSION_COOKIE
from nevus.config import Settings


class SessionCookieMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)
        token = getattr(request.state, "new_session_token", None)
        if token:
            settings: Settings = request.app.state.settings
            response.set_cookie(
                SESSION_COOKIE,
                token,
                max_age=settings.session_max_days * 86400,
                httponly=True,
                samesite="lax",
                secure=request_is_secure(request, settings),
                path="/",
            )
        return response
