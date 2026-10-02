# SPDX-License-Identifier: AGPL-3.0-only
"""Single sign-on through a reverse proxy (FR-ACC-06): the proxy authenticates, neVus trusts its header.

The header is believed only on connections from the proxy's own addresses (NEVUS_PROXY_TRUSTED); from
anywhere else it is ignored, since anyone could send it. A person signed in by the proxy gets an
ordinary server-side session, so sudo mode and sign-out work as usual; the session is valid only while
the proxy keeps vouching for the same person. Emergency sessions, made with the command line when the
identity provider is down, are the exception.
"""

from __future__ import annotations

import ipaddress
import secrets
from datetime import timedelta
from functools import cache

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from nevus.auth import service
from nevus.auth.passwords import hash_password
from nevus.config import Settings
from nevus.db.models import ROLE_ADMIN, ROLE_MEMBER, AuthSession, User
from nevus.db.types import utcnow

EMERGENCY_LINK_MINUTES = 15
EMERGENCY_SESSION_HOURS = 12


@cache
def _networks(trusted: tuple[str, ...]) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    return tuple(ipaddress.ip_network(n, strict=False) for n in trusted)


def trusted_peer(request: Request, settings: Settings) -> bool:
    """Whether the connection itself comes from the proxy (the peer address, never a forwarded one)."""
    if request.client is None:
        return False
    try:
        peer = ipaddress.ip_address(request.client.host)
    except ValueError:
        return False
    return any(peer in network for network in _networks(tuple(settings.proxy_trusted)))


def identity(request: Request, settings: Settings) -> tuple[str, str | None] | None:
    """The username (and email) the proxy vouches for, or None."""
    if settings.auth_mode != "proxy" or not trusted_peer(request, settings):
        return None
    username = request.headers.get(settings.proxy_user_header, "").strip()
    if not username:
        return None
    email = request.headers.get(settings.proxy_email_header, "").strip() if settings.proxy_email_header else ""
    return service.normalise_username(username)[:64], (email[:254] or None)


def user_for(db: Session, settings: Settings, username: str, email: str | None) -> User:
    """The account for a proxy username, created when allowed. The first account ever is the administrator."""
    user = service.get_user_by_username(db, username)
    if user is None:
        first = service.count_users(db) == 0
        if not first and not settings.proxy_auto_create:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "There is no account for you here yet: ask an administrator to create it."
            )
        # A random password nobody knows: local sign-in stays closed for proxy accounts.
        user = User(
            username=username,
            password_hash=hash_password(secrets.token_urlsafe(32)),
            role=ROLE_ADMIN if first else ROLE_MEMBER,
            email=email,
        )
        db.add(user)
        db.flush()
        service.audit(db, "instance.claim" if first else "user.proxy_create", user, "user", user.id)
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account is disabled.")
    if email and not user.email:
        user.email = email
    return user


def session_for(request: Request, db: Session, settings: Settings, existing: AuthSession | None) -> AuthSession:
    """In proxy mode: keep the session while the proxy vouches for its user, or start one for the new user."""
    if existing is not None and existing.kind == "emergency":
        return existing
    vouched = identity(request, settings)
    if vouched is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Sign in through your single sign-on.",
            headers={"X-Auth-Mode": "proxy"},
        )
    user = user_for(db, settings, *vouched)
    if existing is not None and existing.kind == "proxy" and existing.user_id == user.id:
        return existing
    if existing is not None:
        db.delete(existing)  # a session of someone else, or a local one: the proxy decides now
    ip = request.client.host[:45] if request.client else None
    token = service.create_session(db, user, settings, request.headers.get("user-agent"), ip, kind="proxy")
    user.last_login_at = utcnow()
    service.audit(db, "login.proxy", user, "user", user.id, ip)
    request.state.new_session_token = token
    created = service.resolve_session(db, token, settings)
    if created is None:  # pragma: no cover - the session was just created
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "The session could not be started.")
    return created


def emergency_link(db: Session, settings: Settings, username: str) -> str:
    """For the command line: a one-use token, valid for a quarter of an hour, that opens an emergency session."""
    user = service.get_user_by_username(db, username)
    if user is None or not user.is_active:
        raise LookupError(f"no active account named {username!r}")
    token = service.create_session(db, user, settings, "emergency link", None, kind="emergency_link")
    link = service.resolve_session(db, token, settings)
    if link is not None:
        link.expires_at = utcnow() + timedelta(minutes=EMERGENCY_LINK_MINUTES)
    service.audit(db, "login.emergency_link", None, "user", user.id)
    return token


def use_emergency_link(db: Session, settings: Settings, token: str, ip: str | None) -> str | None:
    """Exchange a link for an emergency session (12 hours at most); the link is gone either way."""
    link = service.resolve_session(db, token, settings)
    if link is None or link.kind != "emergency_link":
        return None
    user = link.user
    db.delete(link)
    session_token = service.create_session(db, user, settings, "emergency", ip, kind="emergency")
    session = service.resolve_session(db, session_token, settings)
    if session is not None:
        session.expires_at = utcnow() + timedelta(hours=EMERGENCY_SESSION_HOURS)
    service.audit(db, "login.emergency", user, "user", user.id, ip)
    return session_token
