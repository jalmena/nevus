# SPDX-License-Identifier: AGPL-3.0-only
"""Sending email through the operator's SMTP server, and the daily digest of due marks."""

from __future__ import annotations

import smtplib
import ssl
import uuid
from datetime import datetime
from email.message import EmailMessage
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select

from nevus import settings_store
from nevus.db.models import NotificationDelivery, User
from nevus.domain.due import due_for_user
from nevus.jobs import queue
from nevus.jobs.registry import JobContext, JobKind, register
from nevus.logging import get_logger
from nevus.reports.i18n import Words

log = get_logger(__name__)
DIGEST_KIND = "notify.email.digest"

TEXT = {
    "en": {
        "subject_one": "neVus: one mark is due for a photo",
        "subject_other": "neVus: {n} marks are due for a photo",
        "intro": "These marks are due for a new photo:",
        "due_since": "due since {date}",
        "open": "Open neVus: {url}",
        "footer": "You receive this because email reminders are on in your neVus settings. "
        "neVus is a personal documentation aid; it does not diagnose or assess any disease.",
        "test_subject": "neVus: test message",
        "test_body": "This is a test message from neVus. Email reminders will reach this address.",
    },
    "es": {
        "subject_one": "neVus: toca fotografiar una marca",
        "subject_other": "neVus: toca fotografiar {n} marcas",
        "intro": "Toca hacer una foto nueva de estas marcas:",
        "due_since": "pendiente desde el {date}",
        "open": "Abrir neVus: {url}",
        "footer": "Recibes esto porque tienes activados los recordatorios por correo en los ajustes de neVus. "
        "neVus es una ayuda personal de documentación; no diagnostica ni evalúa ninguna enfermedad.",
        "test_subject": "neVus: mensaje de prueba",
        "test_body": "Este es un mensaje de prueba de neVus. Los recordatorios por correo llegarán a esta dirección.",
    },
}


def send(message: dict[str, Any]) -> None:
    """Deliver one message. Runs in a worker process; everything it needs travels in `message`."""
    email = EmailMessage()
    email["From"] = message["sender"]
    email["To"] = message["to"]
    email["Subject"] = message["subject"]
    email.set_content(message["body"])
    security = message["security"]
    if security == "ssl":
        client: smtplib.SMTP = smtplib.SMTP_SSL(
            message["host"], message["port"], timeout=20, context=ssl.create_default_context()
        )
    else:
        client = smtplib.SMTP(message["host"], message["port"], timeout=20)
    with client:
        if security == "starttls":
            client.starttls(context=ssl.create_default_context())
        if message.get("username"):
            client.login(message["username"], message.get("password") or "")
        client.send_message(email)


def envelope(config: settings_store.EmailConfig, to: str, subject: str, body: str) -> dict[str, Any]:
    return {
        "host": config.host,
        "port": config.port,
        "security": config.security,
        "username": config.username,
        "password": config.password,
        "sender": config.sender,
        "to": to,
        "subject": subject,
        "body": body,
    }


def digest_text(user: User, items: list[Any], public_url: str | None) -> tuple[str, str]:
    text = TEXT.get(user.language, TEXT["en"])
    subject = text["subject_one"] if len(items) == 1 else text["subject_other"].format(n=len(items))
    lines = [text["intro"], ""]
    words = Words(user.language)
    for item in items:
        label = item.lesion.label or words.zone(item.lesion.zone_code)
        lines.append(
            f"- {label} ({item.person.display_name}): {text['due_since'].format(date=item.next_due_on.isoformat())}"
        )
    if public_url:
        lines += ["", text["open"].format(url=public_url.rstrip("/"))]
    lines += ["", text["footer"]]
    return subject, "\n".join(lines)


def schedule_digests(ctx: JobContext, now: datetime | None = None) -> int:
    """Periodic: after the reminder hour, queue one digest per person who wants one and has something due."""
    zone = ZoneInfo(ctx.settings.effective_timezone)
    local = (now or datetime.now(tz=zone)).astimezone(zone)
    if local.hour < ctx.settings.reminder_hour:
        return 0
    today = local.date()
    queued = 0
    users = ctx.db.scalars(
        select(User).where(User.email_reminders.is_(True), User.email.is_not(None), User.disabled_at.is_(None))
    ).all()
    for user in users:
        key = f"due:{today.isoformat()}"
        sent = ctx.db.scalar(
            select(NotificationDelivery.id).where(
                NotificationDelivery.user_id == user.id,
                NotificationDelivery.channel == "email",
                NotificationDelivery.key == key,
            )
        )
        if sent is not None:
            continue
        if not due_for_user(ctx.db, user.id, today, roles=("owner", "manager")):
            continue
        if queue.enqueue(
            ctx.db,
            DIGEST_KIND,
            {"user_id": str(user.id), "date": today.isoformat()},
            dedupe_key=f"digest:{user.id}:{today}",
        ):
            queued += 1
    return queued


def _load(ctx: JobContext, payload: dict[str, Any]) -> dict[str, Any] | None:
    from datetime import date

    user = ctx.db.get(User, uuid.UUID(payload["user_id"]))
    config = settings_store.email_config(ctx.db, ctx.settings)
    if user is None or not user.email or not user.email_reminders or not config.ready:
        return None
    items = due_for_user(ctx.db, user.id, date.fromisoformat(payload["date"]), roles=("owner", "manager"))
    if not items:
        return None
    subject, body = digest_text(user, items, config.public_url)
    return envelope(config, user.email, subject, body)


def _send(message: dict[str, Any]) -> dict[str, Any]:
    send(message)
    return {"ok": True}


def _store(ctx: JobContext, payload: dict[str, Any], result: dict[str, Any]) -> None:
    ctx.db.add(
        NotificationDelivery(
            user_id=uuid.UUID(payload["user_id"]), channel="email", key=f"due:{payload['date']}", status="sent"
        )
    )
    ctx.db.flush()
    log.info("email.digest.sent", user=payload["user_id"])


register(JobKind(DIGEST_KIND, _load, _send, _store, timeout=60.0, max_attempts=4))
