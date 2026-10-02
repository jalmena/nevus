# SPDX-License-Identifier: AGPL-3.0-only
"""Outgoing webhooks: the daily digest of due marks for Home Assistant, n8n, ntfy, Gotify or any URL.

Messages carry names and dates, never photographs or notes. A webhook belongs to an administrator
and covers only the persons that administrator owns or manages, as the email digest does.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import urllib.error
import urllib.request
import uuid
from datetime import date, datetime
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from nevus import secretbox, settings_store
from nevus.config import Settings
from nevus.db.models import NotificationDelivery, User, Webhook
from nevus.db.types import utcnow
from nevus.domain.due import DueItem, due_for_user
from nevus.jobs import queue
from nevus.jobs.registry import JobContext, JobKind, register
from nevus.logging import get_logger
from nevus.reports.i18n import Words

log = get_logger(__name__)
WEBHOOK_KIND = "notify.webhook"
URL_PURPOSE = "webhook-url"
SECRET_PURPOSE = "webhook-secret"  # noqa: S105 - a sealing label, not a secret

TEXT = {
    "en": {
        "title_one": "neVus: one mark is due for a photo",
        "title_other": "neVus: {n} marks are due for a photo",
        "line": "{mark} ({person}): due since {date}",
        "test_title": "neVus: test message",
        "test_body": "This webhook works. Due marks will arrive here once a day.",
    },
    "es": {
        "title_one": "neVus: toca fotografiar una marca",
        "title_other": "neVus: toca fotografiar {n} marcas",
        "line": "{mark} ({person}): pendiente desde el {date}",
        "test_title": "neVus: mensaje de prueba",
        "test_body": "Este webhook funciona. Las marcas pendientes llegarán aquí una vez al día.",
    },
    "pt": {
        "title_one": "neVus: uma marca tem foto pendente",
        "title_other": "neVus: {n} marcas têm foto pendente",
        "line": "{mark} ({person}): pendente desde {date}",
        "test_title": "neVus: mensagem de teste",
        "test_body": "Este webhook funciona. As marcas pendentes chegarão aqui uma vez por dia.",
    },
}


class WebhookError(Exception):
    """A delivery that did not reach its target. The message never contains the URL or the secret."""


def url_hint(url: str) -> str:
    """What the interface may show of a URL that may hold a token: scheme, host and the start of the path."""
    parts = urlsplit(url)
    path = parts.path if len(parts.path) <= 24 else parts.path[:24] + "…"
    return f"{parts.scheme}://{parts.netloc}{path}"[:200]


def valid_url(url: str) -> bool:
    parts = urlsplit(url)
    return parts.scheme in ("http", "https") and bool(parts.netloc)


def digest(items: list[DueItem], language: str, public_url: str | None) -> dict[str, Any]:
    words = Words(language)
    base = public_url.rstrip("/") if public_url else None
    return {
        "event": "due",
        "count": len(items),
        "url": base,
        "items": [
            {
                "person": item.person.display_name,
                "mark": item.lesion.label or words.zone(item.lesion.zone_code),
                "zone": words.zone(item.lesion.zone_code),
                "due_since": item.next_due_on.isoformat(),
                "url": f"{base}/lesions/{item.lesion.id}" if base else None,
            }
            for item in items
        ],
    }


def _text(language: str, message: dict[str, Any]) -> tuple[str, str]:
    text = TEXT.get(language, TEXT["en"])
    if message["event"] == "test":
        return text["test_title"], text["test_body"]
    count = message["count"]
    title = text["title_one"] if count == 1 else text["title_other"].format(n=count)
    lines = [text["line"].format(mark=i["mark"], person=i["person"], date=i["due_since"]) for i in message["items"]]
    return title, "\n".join(lines)


def _header(value: str) -> str:
    """Header values travel as Latin-1; anything else is sent RFC 2047-encoded, which ntfy decodes."""
    if value.isascii():
        return value
    return "=?UTF-8?B?" + base64.b64encode(value.encode()).decode() + "?="


def request_for(preset: str, url: str, secret: str | None, message: dict[str, Any], language: str) -> dict[str, Any]:
    """The HTTP request each preset expects. Plain data, so it can be sent from a worker process."""
    title, body = _text(language, message)
    headers = {"User-Agent": "neVus webhook"}
    if preset == "ntfy":
        headers |= {"Title": _header(title), "Tags": "camera"}
        if message.get("url"):
            headers["Click"] = message["url"]
        if secret:
            headers["Authorization"] = f"Bearer {secret}"
        return {"url": url, "headers": headers, "body": body.encode()}
    if preset == "gotify":
        headers["Content-Type"] = "application/json"
        if secret:
            headers["X-Gotify-Key"] = secret
        payload: dict[str, Any] = {"title": title, "message": body, "priority": 5}
        if message.get("url"):
            payload["extras"] = {"client::notification": {"click": {"url": message["url"]}}}
        return {"url": url.rstrip("/") + "/message", "headers": headers, "body": json.dumps(payload).encode()}
    # generic, Home Assistant and n8n take the structured message, signed when a secret is set.
    raw = json.dumps({**message, "title": title, "text": body}, ensure_ascii=False).encode()
    headers["Content-Type"] = "application/json"
    if secret:
        signature = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        headers["X-Nevus-Signature"] = f"sha256={signature}"
    return {"url": url, "headers": headers, "body": raw}


def send(request: dict[str, Any], timeout: float = 15.0) -> dict[str, Any]:
    """Runs in a worker process. Raises WebhookError, without the URL, when the target refuses or is away."""
    if not valid_url(request["url"]):
        raise WebhookError("only http and https addresses are allowed")
    http = urllib.request.Request(  # noqa: S310 - http(s) only, checked above
        request["url"], data=request["body"], headers=request["headers"], method="POST"
    )
    try:
        with urllib.request.urlopen(http, timeout=timeout) as response:  # noqa: S310 - http(s) only, checked above
            return {"status": response.status}
    except urllib.error.HTTPError as error:
        raise WebhookError(f"the target answered {error.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        reason = getattr(error, "reason", error)
        raise WebhookError(f"the target could not be reached ({type(reason).__name__})") from None


def _secrets(settings: Settings, hook: Webhook) -> tuple[str, str | None]:
    key = settings.secret_key()
    url = secretbox.open_(key, hook.sealed_url, purpose=URL_PURPOSE)
    secret = secretbox.open_(key, hook.sealed_secret, purpose=SECRET_PURPOSE) if hook.sealed_secret else None
    return url, secret


def test_request(db: Session, settings: Settings, hook: Webhook, owner: User) -> dict[str, Any]:
    url, secret = _secrets(settings, hook)
    public_url = settings_store.email_config(db, settings).public_url
    message = {"event": "test", "count": 0, "url": public_url, "items": []}
    return request_for(hook.preset, url, secret, message, owner.language)


def schedule_webhooks(ctx: JobContext, now: datetime | None = None) -> int:
    """Periodic: after the reminder hour, queue one digest per enabled webhook whose owner has marks due."""
    zone = ZoneInfo(ctx.settings.effective_timezone)
    local = (now or datetime.now(tz=zone)).astimezone(zone)
    if local.hour < ctx.settings.reminder_hour:
        return 0
    today = local.date()
    queued = 0
    for hook in ctx.db.scalars(select(Webhook).where(Webhook.enabled.is_(True))).all():
        key = f"due:{today.isoformat()}:{hook.id}"
        sent = ctx.db.scalar(
            select(NotificationDelivery.id).where(
                NotificationDelivery.user_id == hook.user_id,
                NotificationDelivery.channel == "webhook",
                NotificationDelivery.key == key,
            )
        )
        if sent is not None or not due_for_user(ctx.db, hook.user_id, today, roles=("owner", "manager")):
            continue
        if queue.enqueue(
            ctx.db,
            WEBHOOK_KIND,
            {"webhook_id": str(hook.id), "date": today.isoformat()},
            dedupe_key=f"webhook:{hook.id}:{today}",
            max_attempts=4,
        ):
            queued += 1
    return queued


def _load(ctx: JobContext, payload: dict[str, Any]) -> dict[str, Any] | None:
    hook = ctx.db.get(Webhook, uuid.UUID(payload["webhook_id"]))
    owner = ctx.db.get(User, hook.user_id) if hook else None
    if hook is None or not hook.enabled or owner is None or owner.disabled_at is not None or not owner.is_admin:
        return None
    items = due_for_user(ctx.db, owner.id, date.fromisoformat(payload["date"]), roles=("owner", "manager"))
    if not items:
        return None
    url, secret = _secrets(ctx.settings, hook)
    public_url = settings_store.email_config(ctx.db, ctx.settings).public_url
    return request_for(hook.preset, url, secret, digest(items, owner.language, public_url), owner.language)


def _store(ctx: JobContext, payload: dict[str, Any], result: dict[str, Any]) -> None:
    hook = ctx.db.get(Webhook, uuid.UUID(payload["webhook_id"]))
    if hook is None:
        return
    ctx.db.add(
        NotificationDelivery(
            user_id=hook.user_id, channel="webhook", key=f"due:{payload['date']}:{hook.id}", status="sent"
        )
    )
    hook.last_status, hook.last_error, hook.last_sent_at = "sent", None, utcnow()
    ctx.db.flush()
    log.info("webhook.sent", webhook=str(hook.id), status=result.get("status"))


def _failed(ctx: JobContext, payload: dict[str, Any], message: str) -> None:
    hook = ctx.db.get(Webhook, uuid.UUID(payload["webhook_id"]))
    if hook is not None:
        hook.last_status = "failed"
        # Only our own sanitised message: the exception text could otherwise echo the URL.
        hook.last_error = message.split(":", 1)[-1].strip()[:200] if message.startswith("nevus.") else "delivery failed"


register(JobKind(WEBHOOK_KIND, _load, send, _store, timeout=60.0, max_attempts=4, on_failure=_failed))
