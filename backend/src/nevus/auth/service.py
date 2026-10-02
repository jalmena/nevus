"""Account and session operations. Routers call these; tests exercise them through the API."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from nevus import secretbox
from nevus.auth import totp
from nevus.auth.passwords import hash_password, needs_rehash, verify_password
from nevus.config import Settings
from nevus.db.models import ROLE_ADMIN, AuditLog, AuthSession, User, UserRecoveryCode
from nevus.db.types import utcnow

SESSION_COOKIE = "nevus_session"
SECOND_FACTOR_KIND = "second_factor"
SECOND_FACTOR_MINUTES = 5


def normalise_username(username: str) -> str:
    return username.strip().lower()


def count_users(db: Session) -> int:
    return int(db.scalar(select(func.count()).select_from(User)) or 0)


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == normalise_username(username)))


def create_user(db: Session, username: str, password: str, role: str, email: str | None = None) -> User:
    user = User(username=normalise_username(username), password_hash=hash_password(password), role=role, email=email)
    db.add(user)
    db.flush()
    return user


def authenticate(db: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(db, username)
    if user is None or not user.is_active or not verify_password(user.password_hash, password):
        return None
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    user.last_login_at = utcnow()
    return user


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(
    db: Session,
    user: User,
    settings: Settings,
    user_agent: str | None,
    ip: str | None,
    kind: str = "local",
    lifetime: timedelta | None = None,
) -> str:
    """Create a session and return the raw token for the cookie; only its hash is stored."""
    token = secrets.token_urlsafe(32)
    now = utcnow()
    session = AuthSession(
        token_hash=_hash_token(token),
        user_id=user.id,
        created_at=now,
        last_seen_at=now,
        expires_at=now + (lifetime or timedelta(days=settings.session_max_days)),
        user_agent=(user_agent or "")[:255] or None,
        ip=ip,
        kind=kind,
    )
    db.add(session)
    db.flush()
    return token


def resolve_session(db: Session, token: str, settings: Settings) -> AuthSession | None:
    """Return the live session for a cookie token, touching last_seen_at; expired or idle sessions are deleted."""
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == _hash_token(token)))
    if session is None:
        return None
    now = utcnow()
    idle_limit = session.last_seen_at + timedelta(days=settings.session_idle_days)
    if now >= session.expires_at or now >= idle_limit or not session.user.is_active:
        db.delete(session)
        return None
    if now - session.last_seen_at > timedelta(minutes=1):
        session.last_seen_at = now
    return session


def revoke_session(db: Session, session: AuthSession) -> None:
    db.delete(session)


def revoke_all_sessions(db: Session, user: User) -> None:
    for session in list(user.sessions):
        db.delete(session)


def grant_sudo(session: AuthSession, settings: Settings) -> None:
    session.sudo_until = utcnow() + timedelta(minutes=settings.sudo_minutes)


def has_sudo(session: AuthSession) -> bool:
    return session.sudo_until is not None and session.sudo_until > utcnow()


def audit(
    db: Session,
    action: str,
    actor: User | None,
    target_type: str | None = None,
    target_id: uuid.UUID | str | None = None,
    ip: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor.id if actor else None,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            ip=ip,
            details=details,
        )
    )


def bootstrap_admin(db: Session, settings: Settings) -> None:
    """Create or reset the administrator named in the environment. Read at start-up only."""
    if not settings.admin_user or not settings.admin_password:
        return
    user = get_user_by_username(db, settings.admin_user)
    if user is None:
        user = create_user(db, settings.admin_user, settings.admin_password, ROLE_ADMIN)
        audit(db, "user.bootstrap", None, "user", user.id)
    else:
        user.password_hash = hash_password(settings.admin_password)
        user.role = ROLE_ADMIN
        user.disabled_at = None
        disable_totp(db, user)  # the way back in for an administrator who lost the authenticator
        audit(db, "user.bootstrap_reset", None, "user", user.id)


# --- the second factor ----------------------------------------------------------------------------


def totp_secret_of(user: User, settings: Settings) -> str | None:
    if not user.totp_secret:
        return None
    return secretbox.open_(settings.secret_key(), user.totp_secret, purpose="totp")


def start_totp_setup(db: Session, user: User, settings: Settings) -> tuple[str, str]:
    """A fresh secret for the authenticator; the factor stays off until a first code confirms it."""
    secret = totp.new_secret()
    user.totp_secret = secretbox.seal(settings.secret_key(), secret, purpose="totp")
    user.totp_enabled_at = None
    user.totp_last_counter = None
    db.flush()
    return secret, totp.provisioning_uri(secret, user.username)


def enable_totp(db: Session, user: User, settings: Settings, code: str) -> list[str] | None:
    """Turn the factor on once a code proves the authenticator was set up; returns the recovery codes."""
    secret = totp_secret_of(user, settings)
    counter = totp.verify(secret, code) if secret else None
    if counter is None:
        return None
    user.totp_enabled_at = utcnow()
    user.totp_last_counter = counter
    return issue_recovery_codes(db, user)


def issue_recovery_codes(db: Session, user: User) -> list[str]:
    """New codes replace whatever was left; they are returned once and stored hashed."""
    db.execute(delete(UserRecoveryCode).where(UserRecoveryCode.user_id == user.id))
    codes = totp.new_recovery_codes()
    for code in codes:
        db.add(UserRecoveryCode(user_id=user.id, code_hash=totp.hash_recovery_code(code)))
    db.flush()
    return codes


def recovery_codes_left(db: Session, user: User) -> int:
    query = (
        select(func.count())
        .select_from(UserRecoveryCode)
        .where(UserRecoveryCode.user_id == user.id, UserRecoveryCode.used_at.is_(None))
    )
    return int(db.scalar(query) or 0)


def disable_totp(db: Session, user: User) -> None:
    user.totp_secret = None
    user.totp_enabled_at = None
    user.totp_last_counter = None
    db.execute(delete(UserRecoveryCode).where(UserRecoveryCode.user_id == user.id))


def check_second_factor(
    db: Session, user: User, settings: Settings, code: str | None, recovery_code: str | None
) -> str | None:
    """Which factor matched, "totp" or "recovery", or None. Neither kind of code is accepted twice."""
    if code:
        secret = totp_secret_of(user, settings)
        counter = totp.verify(secret, code, user.totp_last_counter) if secret else None
        if counter is None:
            return None
        user.totp_last_counter = counter
        return "totp"
    if recovery_code:
        row = db.scalar(
            select(UserRecoveryCode).where(
                UserRecoveryCode.user_id == user.id,
                UserRecoveryCode.code_hash == totp.hash_recovery_code(recovery_code),
                UserRecoveryCode.used_at.is_(None),
            )
        )
        if row is None:
            return None
        row.used_at = utcnow()
        return "recovery"
    return None
