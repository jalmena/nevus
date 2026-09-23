"""FastAPI dependencies: the current user, administrator checks and sudo mode."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from nevus.auth.service import SESSION_COOKIE, has_sudo, resolve_session
from nevus.config import Settings
from nevus.db.models import AuthSession, User
from nevus.db.session import get_db


def get_settings_dep(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def client_ip(request: Request, settings: Settings) -> str | None:
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()[:45]
    return request.client.host[:45] if request.client else None


def request_is_secure(request: Request, settings: Settings) -> bool:
    if settings.trust_proxy_headers and request.headers.get("x-forwarded-proto", "").lower() == "https":
        return True
    return request.url.scheme == "https"


def current_session(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings_dep)],
) -> AuthSession:
    token = request.cookies.get(SESSION_COOKIE)
    session = resolve_session(db, token, settings) if token else None
    if session is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in to continue.")
    return session


def current_user(session: Annotated[AuthSession, Depends(current_session)]) -> User:
    return session.user


def require_admin(user: Annotated[User, Depends(current_user)]) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Administrator role required.")
    return user


def require_sudo(session: Annotated[AuthSession, Depends(current_session)]) -> AuthSession:
    if not has_sudo(session):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Confirm your password to continue.", headers={"X-Sudo-Required": "1"}
        )
    return session


CurrentUser = Annotated[User, Depends(current_user)]
CurrentSession = Annotated[AuthSession, Depends(current_session)]
AdminUser = Annotated[User, Depends(require_admin)]
SudoSession = Annotated[AuthSession, Depends(require_sudo)]
DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings_dep)]
