"""Claiming the instance, signing in and out, the current session, sudo mode and the own account."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status

from nevus import __version__
from nevus.api.schemas import Credentials, InstanceStatus, PasswordChange, SessionOut, SudoIn, UserOut, UserUpdateMe
from nevus.auth import service
from nevus.auth.dependencies import AppSettings, CurrentSession, DbSession, client_ip, request_is_secure
from nevus.auth.passwords import hash_password
from nevus.auth.ratelimit import LoginRateLimiter
from nevus.auth.service import SESSION_COOKIE
from nevus.db.models import ROLE_ADMIN

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _limiter(request: Request) -> LoginRateLimiter:
    limiter: LoginRateLimiter = request.app.state.login_limiter
    return limiter


def _set_cookie(response: Response, token: str, request: Request, settings: AppSettings) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_max_days * 86400,
        httponly=True,
        samesite="lax",
        secure=request_is_secure(request, settings),
        path="/",
    )


@router.get("/instance", response_model=InstanceStatus)
def instance_status(db: DbSession) -> InstanceStatus:
    return InstanceStatus(claimed=service.count_users(db) > 0, version=__version__)


@router.post("/claim", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def claim(body: Credentials, request: Request, response: Response, db: DbSession, settings: AppSettings) -> SessionOut:
    """The first person in claims the instance and becomes its administrator. Refused once anybody exists."""
    if service.count_users(db) > 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "This instance has already been claimed.")
    user = service.create_user(db, body.username, body.password, ROLE_ADMIN)
    ip = client_ip(request, settings)
    service.audit(db, "instance.claim", user, "user", user.id, ip)
    token = service.create_session(db, user, settings, request.headers.get("user-agent"), ip)
    _set_cookie(response, token, request, settings)
    return SessionOut(user=UserOut.model_validate(user), sudo_until=None)


@router.post("/login", response_model=SessionOut)
def login(body: Credentials, request: Request, response: Response, db: DbSession, settings: AppSettings) -> SessionOut:
    ip = client_ip(request, settings)
    key = f"{ip}|{service.normalise_username(body.username)}"
    limiter = _limiter(request)
    if not limiter.allow(key):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts. Try again later.")
    user = service.authenticate(db, body.username, body.password)
    if user is None:
        limiter.record_failure(key)
        service.audit(db, "login.failed", None, "user", service.normalise_username(body.username), ip)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong username or password.")
    limiter.reset(key)
    token = service.create_session(db, user, settings, request.headers.get("user-agent"), ip)
    service.audit(db, "login", user, "user", user.id, ip)
    _set_cookie(response, token, request, settings)
    return SessionOut(user=UserOut.model_validate(user), sudo_until=None)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, session: CurrentSession, db: DbSession) -> Response:
    service.revoke_session(db, session)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return Response(status_code=status.HTTP_204_NO_CONTENT, headers=response.headers)


@router.get("/session", response_model=SessionOut)
def session_info(session: CurrentSession) -> SessionOut:
    return SessionOut(user=UserOut.model_validate(session.user), sudo_until=session.sudo_until)


@router.post("/sudo", response_model=SessionOut)
def sudo(body: SudoIn, request: Request, session: CurrentSession, db: DbSession, settings: AppSettings) -> SessionOut:
    """Re-authenticate for a few minutes before destructive actions."""
    if service.authenticate(db, session.user.username, body.password) is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong password.")
    service.grant_sudo(session, settings)
    service.audit(db, "sudo", session.user, "user", session.user.id, client_ip(request, settings))
    return SessionOut(user=UserOut.model_validate(session.user), sudo_until=session.sudo_until)


@router.patch("/me", response_model=UserOut)
def update_me(body: UserUpdateMe, session: CurrentSession, db: DbSession) -> UserOut:
    user = session.user
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.flush()
    return UserOut.model_validate(user)


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: PasswordChange, request: Request, session: CurrentSession, db: DbSession, settings: AppSettings
) -> Response:
    user = session.user
    if service.authenticate(db, user.username, body.current_password) is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong current password.")
    user.password_hash = hash_password(body.new_password)
    for other in list(user.sessions):
        if other.id != session.id:
            db.delete(other)
    service.audit(db, "password.change", user, "user", user.id, client_ip(request, settings))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
