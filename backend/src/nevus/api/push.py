# SPDX-License-Identifier: AGPL-3.0-only
"""Push notifications: the server's public key, this device's subscription, and a message to try it."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from nevus import settings_store
from nevus.auth import service
from nevus.auth.dependencies import AppSettings, CurrentUser, DbSession, client_ip
from nevus.config import Settings
from nevus.db.models import PushSubscription
from nevus.notify import push

router = APIRouter(prefix="/api/push", tags=["push"])

GREETING = {
    "en": ("neVus can reach this device", "Reminders about marks due for a photo will arrive here."),
    "es": ("neVus llega a este dispositivo", "Los recordatorios de marcas pendientes de foto llegarán aquí."),
    "pt": ("O neVus chega a este aparelho", "Os lembretes de marcas com foto pendente chegarão aqui."),
    "ca": ("El neVus arriba a aquest dispositiu", "Els recordatoris de marques pendents de foto arribaran aquí."),
    "gl": ("neVus chega a este dispositivo", "Os recordatorios de marcas pendentes de foto chegarán aquí."),
    "eu": (
        "neVus-ek gailu honetara iristen da",
        "Argazkia behar duten markei buruzko gogorarazpenak hemen iritsiko dira.",
    ),
    "fr": ("neVus peut joindre cet appareil", "Les rappels des marques à photographier arriveront ici."),
    "it": ("neVus raggiunge questo dispositivo", "I promemoria dei segni da fotografare arriveranno qui."),
    "de": ("neVus erreicht dieses Gerät", "Erinnerungen an Stellen, die für ein Foto fällig sind, kommen hier an."),
    "nl": (
        "neVus kan dit apparaat bereiken",
        "Herinneringen voor plekken die aan een foto toe zijn, komen hier binnen.",
    ),
    "pl": (
        "neVus może dotrzeć do tego urządzenia",
        "Przypomnienia o oznaczeniach do sfotografowania będą tu docierać.",
    ),
    "ru": (
        "neVus может связаться с этим устройством",
        "Напоминания о метках, которые пора сфотографировать, будут приходить сюда.",
    ),
    "tr": ("neVus bu cihaza ulaşabiliyor", "Fotoğraf zamanı gelen işaretlerin hatırlatıcıları buraya gelecek."),
    "id": ("neVus dapat menjangkau perangkat ini", "Pengingat tentang tanda yang perlu difoto akan masuk ke sini."),
    "zh": ("neVus 已可通知此设备", "待拍照标记的提醒将发送到这里。"),
    "ja": ("neVusはこのデバイスに通知できます", "撮影の時期になったマークのリマインダーがここに届きます。"),
    "ko": ("neVus가 이 기기에 알림을 보낼 수 있어요", "사진 찍을 표시에 대한 알림이 여기로 도착해요."),
    "hi": ("neVus इस डिवाइस तक पहुँच सकता है", "फ़ोटो के लिए बाकी निशानों के रिमाइंडर यहाँ आएँगे।"),
    "ar": ("يستطيع neVus الوصول إلى هذا الجهاز", "ستصل هنا تذكيرات العلامات التي حان موعد تصويرها."),
}


class PushStatusOut(BaseModel):
    enabled: bool
    public_key: str | None
    subscriptions: int


class KeysIn(BaseModel):
    p256dh: str = Field(min_length=80, max_length=128)
    auth: str = Field(min_length=16, max_length=64)


class SubscriptionIn(BaseModel):
    endpoint: str = Field(min_length=12, max_length=2000, pattern=r"^https?://")
    keys: KeysIn


class EndpointIn(BaseModel):
    endpoint: str = Field(max_length=2000)


class TestOut(BaseModel):
    sent: int
    failed: int


def _enabled(settings: Settings) -> None:
    if not settings.web_push:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Push notifications are off on this server.")


def _status(db: DbSession, user_id: object, settings: Settings) -> PushStatusOut:
    if not settings.web_push:
        return PushStatusOut(enabled=False, public_key=None, subscriptions=0)
    _, public = push.vapid_keys(db, settings)
    count = db.scalar(select(func.count()).select_from(PushSubscription).where(PushSubscription.user_id == user_id))
    return PushStatusOut(enabled=True, public_key=public, subscriptions=int(count or 0))


@router.get("", response_model=PushStatusOut)
def push_status(user: CurrentUser, db: DbSession, settings: AppSettings) -> PushStatusOut:
    return _status(db, user.id, settings)


@router.post("/subscriptions", response_model=PushStatusOut, status_code=status.HTTP_201_CREATED)
def subscribe(
    body: SubscriptionIn, request: Request, user: CurrentUser, db: DbSession, settings: AppSettings
) -> PushStatusOut:
    """This device's subscription, as the browser gave it; the same endpoint again just refreshes it."""
    _enabled(settings)
    if not push.endpoint_allowed(body.endpoint):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Push endpoints are https addresses.")
    row = db.scalar(select(PushSubscription).where(PushSubscription.endpoint == body.endpoint))
    if row is None:
        row = PushSubscription(endpoint=body.endpoint, user_id=user.id, p256dh=body.keys.p256dh, auth=body.keys.auth)
        db.add(row)
    else:
        row.user_id, row.p256dh, row.auth, row.failures = user.id, body.keys.p256dh, body.keys.auth, 0
    row.user_agent = (request.headers.get("user-agent") or "")[:255] or None
    db.flush()
    service.audit(db, "push.subscribe", user, "push_subscription", row.id, client_ip(request, settings))
    return _status(db, user.id, settings)


@router.delete("/subscriptions", status_code=status.HTTP_204_NO_CONTENT)
def unsubscribe(
    body: EndpointIn, request: Request, user: CurrentUser, db: DbSession, settings: AppSettings
) -> Response:
    row = db.scalar(
        select(PushSubscription).where(PushSubscription.endpoint == body.endpoint, PushSubscription.user_id == user.id)
    )
    if row is not None:
        db.delete(row)
        service.audit(db, "push.unsubscribe", user, "push_subscription", row.id, client_ip(request, settings))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/test", response_model=TestOut)
def test_message(request: Request, user: CurrentUser, db: DbSession, settings: AppSettings) -> TestOut:
    """A message to every device of the person, now, so they can see it arrive."""
    _enabled(settings)
    public_url = settings_store.email_config(db, settings).public_url
    private, public = push.vapid_keys(db, settings)
    title, body = GREETING.get(user.language, GREETING["en"])
    payload = json.dumps({"title": title, "body": body, "url": (public_url or "").rstrip("/") + "/"}).encode()
    sent = failed = 0
    for row in db.scalars(select(PushSubscription).where(PushSubscription.user_id == user.id)).all():
        message = push.encrypt(payload, push.unb64url(row.p256dh), push.unb64url(row.auth))
        header = push.vapid_authorization(row.endpoint, push.subject_for(settings, public_url), private, public)
        try:
            code = push.send(row.endpoint, message, header)
        except (OSError, ValueError):
            code = 0
        if 200 <= code < 300:
            sent += 1
        else:
            failed += 1
            if code in (404, 410):
                db.delete(row)
    service.audit(
        db, "push.test", user, "user", user.id, client_ip(request, settings), {"sent": sent, "failed": failed}
    )
    return TestOut(sent=sent, failed=failed)
