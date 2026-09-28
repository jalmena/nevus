"""Administration of accounts. Registration is closed: administrators create everyone else."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select

from nevus.api.schemas import PasswordReset, UserCreate, UserOut
from nevus.auth import service
from nevus.auth.dependencies import AdminUser, AppSettings, DbSession, client_ip
from nevus.auth.passwords import hash_password
from nevus.db.models import User
from nevus.db.types import utcnow

router = APIRouter(prefix="/api/users", tags=["users"])


def _get_user(db: DbSession, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such user.")
    return user


@router.get("", response_model=list[UserOut])
def list_users(_: AdminUser, db: DbSession) -> list[UserOut]:
    return [UserOut.model_validate(u) for u in db.scalars(select(User).order_by(User.username))]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, request: Request, admin: AdminUser, db: DbSession, settings: AppSettings) -> UserOut:
    if service.get_user_by_username(db, body.username) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "That username is taken.")
    user = service.create_user(db, body.username, body.password, body.role, body.email)
    service.audit(db, "user.create", admin, "user", user.id, client_ip(request, settings), {"role": body.role})
    return UserOut.model_validate(user)


@router.post("/{user_id}/disable", response_model=UserOut)
def disable_user(
    user_id: uuid.UUID, request: Request, admin: AdminUser, db: DbSession, settings: AppSettings
) -> UserOut:
    user = _get_user(db, user_id)
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot disable your own account.")
    user.disabled_at = utcnow()
    service.revoke_all_sessions(db, user)
    service.audit(db, "user.disable", admin, "user", user.id, client_ip(request, settings))
    return UserOut.model_validate(user)


@router.post("/{user_id}/enable", response_model=UserOut)
def enable_user(
    user_id: uuid.UUID, request: Request, admin: AdminUser, db: DbSession, settings: AppSettings
) -> UserOut:
    user = _get_user(db, user_id)
    user.disabled_at = None
    service.audit(db, "user.enable", admin, "user", user.id, client_ip(request, settings))
    return UserOut.model_validate(user)


@router.post("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    user_id: uuid.UUID, body: PasswordReset, request: Request, admin: AdminUser, db: DbSession, settings: AppSettings
) -> Response:
    user = _get_user(db, user_id)
    user.password_hash = hash_password(body.new_password)
    service.revoke_all_sessions(db, user)
    service.audit(db, "user.password_reset", admin, "user", user.id, client_ip(request, settings))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
