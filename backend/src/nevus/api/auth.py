"""Claiming the instance, signing in and out, the current session, sudo mode and the own account."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from nevus import __version__
from nevus.api.schemas import (
    Credentials,
    InstanceStatus,
    LoginOut,
    PasswordChange,
    RecoveryCodesOut,
    SecondFactorIn,
    SessionOut,
    SudoIn,
    TotpCodeIn,
    TotpSetupOut,
    TotpStatusOut,
    UserOut,
    UserUpdateMe,
)
from nevus.auth import service, totp
from nevus.auth.dependencies import (
    AppSettings,
    CurrentSession,
    DbSession,
    SudoSession,
    client_ip,
    request_is_secure,
)
from nevus.auth.passwords import hash_password
from nevus.auth.proxy import use_emergency_link
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


def _local_only(settings: AppSettings) -> None:
    if settings.auth_mode == "proxy":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This instance signs people in through single sign-on.")


@router.get("/instance", response_model=InstanceStatus)
def instance_status(db: DbSession, settings: AppSettings) -> InstanceStatus:
    return InstanceStatus(
        claimed=service.count_users(db) > 0,
        version=__version__,
        auth_mode=settings.auth_mode,
        logout_url=settings.proxy_logout_url if settings.auth_mode == "proxy" else None,
    )


@router.get("/emergency/{token}", include_in_schema=False)
def emergency(token: str, request: Request, db: DbSession, settings: AppSettings) -> Response:
    """Open a one-use link made with `nevus emergency-login`, for when the identity provider is down."""
    session_token = use_emergency_link(db, settings, token, client_ip(request, settings))
    if session_token is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This link has been used or has expired.")
    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    _set_cookie(response, session_token, request, settings)
    return response


@router.post("/claim", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def claim(body: Credentials, request: Request, response: Response, db: DbSession, settings: AppSettings) -> SessionOut:
    """The first person in claims the instance and becomes its administrator. Refused once anybody exists."""
    _local_only(settings)
    if service.count_users(db) > 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "This instance has already been claimed.")
    user = service.create_user(db, body.username, body.password, ROLE_ADMIN)
    ip = client_ip(request, settings)
    service.audit(db, "instance.claim", user, "user", user.id, ip)
    token = service.create_session(db, user, settings, request.headers.get("user-agent"), ip)
    _set_cookie(response, token, request, settings)
    return SessionOut(user=UserOut.model_validate(user), sudo_until=None)


@router.post("/login", response_model=LoginOut)
def login(body: Credentials, request: Request, response: Response, db: DbSession, settings: AppSettings) -> LoginOut:
    _local_only(settings)
    ip = client_ip(request, settings)
    key = f"{ip}|{service.normalise_username(body.username)}"
    limiter = _limiter(request)
    if not limiter.allow(key):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts. Try again later.")
    user = service.authenticate(db, body.username, body.password)
    if user is None:
        limiter.record_failure(key)
        service.audit(db, "login.failed", None, "user", service.normalise_username(body.username), ip)
        db.commit()  # the refusal rolls the request back; the record of the attempt must stay
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong username or password.")
    limiter.reset(key)
    agent = request.headers.get("user-agent")
    if user.totp_enabled:
        # The password alone opens nothing: a short-lived cookie waits for the code.
        token = service.create_session(
            db,
            user,
            settings,
            agent,
            ip,
            kind=service.SECOND_FACTOR_KIND,
            lifetime=timedelta(minutes=service.SECOND_FACTOR_MINUTES),
        )
        service.audit(db, "login.second_factor_pending", user, "user", user.id, ip)
        _set_cookie(response, token, request, settings)
        return LoginOut(second_factor_required=True)
    token = service.create_session(db, user, settings, agent, ip)
    service.audit(db, "login", user, "user", user.id, ip)
    _set_cookie(response, token, request, settings)
    return LoginOut(session=SessionOut(user=UserOut.model_validate(user), sudo_until=None))


@router.post("/second-factor", response_model=SessionOut)
def second_factor(
    body: SecondFactorIn, request: Request, response: Response, db: DbSession, settings: AppSettings
) -> SessionOut:
    """The code from the authenticator, or a recovery code, once the password has been accepted."""
    _local_only(settings)
    token = request.cookies.get(SESSION_COOKIE)
    pending = service.resolve_session(db, token, settings) if token else None
    if pending is None or pending.kind != service.SECOND_FACTOR_KIND:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in with your password first.")
    user = pending.user
    ip = client_ip(request, settings)
    key = f"second-factor|{ip}|{user.username}"
    limiter = _limiter(request)
    if not limiter.allow(key):
        service.revoke_session(db, pending)
        db.commit()  # the refusal below would roll it back; the password step must be done again
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts. Sign in again later.")
    matched = service.check_second_factor(db, user, settings, body.code, body.recovery_code)
    if matched is None:
        limiter.record_failure(key)
        service.audit(db, "login.second_factor_failed", user, "user", user.id, ip)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong code.")
    limiter.reset(key)
    service.revoke_session(db, pending)
    session_token = service.create_session(db, user, settings, request.headers.get("user-agent"), ip)
    service.audit(db, "login", user, "user", user.id, ip, {"second_factor": matched})
    _set_cookie(response, session_token, request, settings)
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
    """Re-authenticate for a few minutes before destructive actions.

    In proxy mode there is no local password: the proxy authenticated the person, and asking is an
    explicit confirmation in the interface.
    """
    local = settings.auth_mode != "proxy"
    if local and (not body.password or service.authenticate(db, session.user.username, body.password) is None):
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
    _local_only(settings)
    user = session.user
    if service.authenticate(db, user.username, body.current_password) is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong current password.")
    user.password_hash = hash_password(body.new_password)
    for other in list(user.sessions):
        if other.id != session.id:
            db.delete(other)
    service.audit(db, "password.change", user, "user", user.id, client_ip(request, settings))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- the second factor ----------------------------------------------------------------------------


@router.get("/totp", response_model=TotpStatusOut)
def totp_status(session: CurrentSession, db: DbSession, settings: AppSettings) -> TotpStatusOut:
    _local_only(settings)
    user = session.user
    return TotpStatusOut(
        enabled=user.totp_enabled,
        enabled_at=user.totp_enabled_at,
        setting_up=bool(user.totp_secret) and not user.totp_enabled,
        recovery_codes_left=service.recovery_codes_left(db, user) if user.totp_enabled else 0,
    )


@router.post("/totp/setup", response_model=TotpSetupOut)
def totp_setup(request: Request, session: SudoSession, db: DbSession, settings: AppSettings) -> TotpSetupOut:
    """A new secret for an authenticator app; the factor turns on with the first code from it."""
    _local_only(settings)
    user = session.user
    if user.totp_enabled:
        raise HTTPException(status.HTTP_409_CONFLICT, "The second factor is already on. Turn it off first.")
    secret, uri = service.start_totp_setup(db, user, settings)
    service.audit(db, "totp.setup", user, "user", user.id, client_ip(request, settings))
    return TotpSetupOut(secret=secret, otpauth_uri=uri, qr_svg=totp.qr_svg(uri))


@router.post("/totp/enable", response_model=RecoveryCodesOut)
def totp_enable(
    body: TotpCodeIn, request: Request, session: SudoSession, db: DbSession, settings: AppSettings
) -> RecoveryCodesOut:
    """The first code proves the authenticator holds the secret; other sessions end, as after a new password."""
    _local_only(settings)
    user = session.user
    if user.totp_enabled:
        raise HTTPException(status.HTTP_409_CONFLICT, "The second factor is already on.")
    if not user.totp_secret:
        raise HTTPException(status.HTTP_409_CONFLICT, "Set the second factor up first.")
    codes = service.enable_totp(db, user, settings, body.code)
    if codes is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "That code does not match. Check the time on the phone and try the next one."
        )
    for other in list(user.sessions):
        if other.id != session.id:
            db.delete(other)
    service.audit(db, "totp.enable", user, "user", user.id, client_ip(request, settings))
    return RecoveryCodesOut(recovery_codes=codes)


@router.delete("/totp", status_code=status.HTTP_204_NO_CONTENT)
def totp_disable(request: Request, session: SudoSession, db: DbSession, settings: AppSettings) -> Response:
    _local_only(settings)
    service.disable_totp(db, session.user)
    service.audit(db, "totp.disable", session.user, "user", session.user.id, client_ip(request, settings))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/totp/recovery-codes", response_model=RecoveryCodesOut)
def totp_recovery_codes(
    request: Request, session: SudoSession, db: DbSession, settings: AppSettings
) -> RecoveryCodesOut:
    """New recovery codes; the ones not yet used stop working."""
    _local_only(settings)
    user = session.user
    if not user.totp_enabled:
        raise HTTPException(status.HTTP_409_CONFLICT, "The second factor is off.")
    codes = service.issue_recovery_codes(db, user)
    service.audit(db, "totp.recovery_codes", user, "user", user.id, client_ip(request, settings))
    return RecoveryCodesOut(recovery_codes=codes)
