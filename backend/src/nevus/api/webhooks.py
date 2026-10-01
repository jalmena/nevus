# SPDX-License-Identifier: AGPL-3.0-only
"""Administrators' outgoing webhooks (FR-REM-03, FR-SET-05): presets for Home Assistant, n8n, ntfy and Gotify."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from nevus import secretbox
from nevus.auth import service
from nevus.auth.dependencies import AdminUser, AppSettings, DbSession, client_ip
from nevus.db.models import Webhook
from nevus.notify import webhooks

router = APIRouter(prefix="/api/admin/webhooks", tags=["admin"])
Preset = Literal["generic", "home_assistant", "n8n", "ntfy", "gotify"]


class WebhookIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    preset: Preset = "generic"
    url: str = Field(min_length=8, max_length=2000)
    secret: str | None = Field(default=None, max_length=500)
    enabled: bool = True


class WebhookUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    preset: Preset | None = None
    url: str | None = Field(default=None, min_length=8, max_length=2000)
    secret: str | None = Field(default=None, max_length=500, description="An empty string removes the secret")
    enabled: bool | None = None


class WebhookOut(BaseModel):
    id: uuid.UUID
    name: str
    preset: Preset
    url_hint: str
    has_secret: bool
    enabled: bool
    last_status: str | None
    last_error: str | None
    last_sent_at: datetime | None
    created_at: datetime


class TestOut(BaseModel):
    ok: bool
    detail: str | None


def _out(hook: Webhook) -> WebhookOut:
    return WebhookOut(
        id=hook.id,
        name=hook.name,
        preset=hook.preset,
        url_hint=hook.url_hint,
        has_secret=hook.sealed_secret is not None,
        enabled=hook.enabled,
        last_status=hook.last_status,
        last_error=hook.last_error,
        last_sent_at=hook.last_sent_at,
        created_at=hook.created_at,
    )


def _check_url(url: str) -> str:
    url = url.strip()
    if not webhooks.valid_url(url):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "The address must start with http:// or https://.")
    return url


def _mine(db: DbSession, webhook_id: uuid.UUID, admin_id: uuid.UUID) -> Webhook:
    hook = db.get(Webhook, webhook_id)
    if hook is None or hook.user_id != admin_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such webhook.")
    return hook


@router.get("", response_model=list[WebhookOut])
def list_webhooks(admin: AdminUser, db: DbSession) -> list[WebhookOut]:
    """Each administrator's own webhooks: each covers the persons its owner owns or manages."""
    rows = db.scalars(select(Webhook).where(Webhook.user_id == admin.id).order_by(Webhook.created_at)).all()
    return [_out(row) for row in rows]


@router.post("", response_model=WebhookOut, status_code=status.HTTP_201_CREATED)
def create_webhook(
    body: WebhookIn, request: Request, admin: AdminUser, db: DbSession, settings: AppSettings
) -> WebhookOut:
    url = _check_url(body.url)
    key = settings.secret_key()
    hook = Webhook(
        user_id=admin.id,
        name=body.name.strip(),
        preset=body.preset,
        sealed_url=secretbox.seal(key, url, purpose=webhooks.URL_PURPOSE),
        url_hint=webhooks.url_hint(url),
        sealed_secret=secretbox.seal(key, body.secret, purpose=webhooks.SECRET_PURPOSE) if body.secret else None,
        enabled=body.enabled,
    )
    db.add(hook)
    db.flush()
    service.audit(
        db, "webhook.create", admin, "webhook", hook.id, client_ip(request, settings), {"preset": body.preset}
    )
    return _out(hook)


@router.patch("/{webhook_id}", response_model=WebhookOut)
def update_webhook(
    webhook_id: uuid.UUID, body: WebhookUpdate, request: Request, admin: AdminUser, db: DbSession, settings: AppSettings
) -> WebhookOut:
    hook = _mine(db, webhook_id, admin.id)
    changes = body.model_dump(exclude_unset=True)
    key = settings.secret_key()
    if changes.get("name"):
        hook.name = changes["name"].strip()
    if changes.get("preset"):
        hook.preset = changes["preset"]
    if changes.get("url"):
        url = _check_url(changes["url"])
        hook.sealed_url = secretbox.seal(key, url, purpose=webhooks.URL_PURPOSE)
        hook.url_hint = webhooks.url_hint(url)
    if "secret" in changes:
        secret = changes["secret"]
        hook.sealed_secret = secretbox.seal(key, secret, purpose=webhooks.SECRET_PURPOSE) if secret else None
    if changes.get("enabled") is not None:
        hook.enabled = changes["enabled"]
    db.flush()
    service.audit(db, "webhook.update", admin, "webhook", hook.id, client_ip(request, settings))
    return _out(hook)


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(
    webhook_id: uuid.UUID, request: Request, admin: AdminUser, db: DbSession, settings: AppSettings
) -> Response:
    hook = _mine(db, webhook_id, admin.id)
    db.delete(hook)
    service.audit(db, "webhook.delete", admin, "webhook", webhook_id, client_ip(request, settings))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{webhook_id}/test", response_model=TestOut)
def test_webhook(webhook_id: uuid.UUID, admin: AdminUser, db: DbSession, settings: AppSettings) -> TestOut:
    """Send a test message now and say plainly whether it arrived."""
    hook = _mine(db, webhook_id, admin.id)
    try:
        webhooks.send(webhooks.test_request(db, settings, hook, admin), timeout=10.0)
    except webhooks.WebhookError as error:
        hook.last_status, hook.last_error = "failed", str(error)[:200]
        return TestOut(ok=False, detail=str(error))
    hook.last_status, hook.last_error = "tested", None
    return TestOut(ok=True, detail=None)
