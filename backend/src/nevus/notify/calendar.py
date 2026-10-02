# SPDX-License-Identifier: AGPL-3.0-only
"""A person's calendar feed (iCalendar, RFC 5545): next photo dates and appointments.

Calendar apps remind natively, which works over a VPN without push services. Events carry the mark's
name, the person's name and dates, never photographs or notes.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from nevus.db.models import Appointment, Lesion, Observation, Person
from nevus.domain import due
from nevus.reports.i18n import Words

TEXT = {
    "en": {
        "calendar": "neVus · {person}",
        "due": "Photo due: {mark} ({person})",
        "appointment": "Appointment: {person}",
        "prepare": "Prepare the appointment in neVus",
        "photograph": "Photograph the mark in neVus",
    },
    "es": {
        "calendar": "neVus · {person}",
        "due": "Toca foto: {mark} ({person})",
        "appointment": "Cita: {person}",
        "prepare": "Prepara la cita en neVus",
        "photograph": "Fotografía la marca en neVus",
    },
    "pt": {
        "calendar": "neVus · {person}",
        "due": "Foto pendente: {mark} ({person})",
        "appointment": "Consulta: {person}",
        "prepare": "Preparar a consulta no neVus",
        "photograph": "Fotografar a marca no neVus",
    },
}


def _escape(text: str) -> str:
    """TEXT values: backslash, semicolon and comma are escaped, line breaks become a literal backslash-n."""
    out = text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
    return out.replace("\r\n", "\\n").replace("\n", "\\n")


def _fold(line: str) -> list[str]:
    """Lines longer than 75 octets continue on the next line after a space, without splitting a character."""
    out: list[str] = []
    current = ""
    for char in line:
        limit = 75 if not out else 74
        if len((current + char).encode()) > limit:
            out.append(current)
            current = char
        else:
            current += char
    out.append(current)
    return [out[0], *(" " + part for part in out[1:])]


def _day(value: date) -> str:
    return value.strftime("%Y%m%d")


def _event(uid: str, on: date, summary: str, stamp: str, url: str | None, alarm: tuple[str, str]) -> list[str]:
    trigger, description = alarm
    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{stamp}",
        f"DTSTART;VALUE=DATE:{_day(on)}",
        f"DTEND;VALUE=DATE:{_day(on + timedelta(days=1))}",
        f"SUMMARY:{_escape(summary)}",
        "TRANSP:TRANSPARENT",
    ]
    if url:
        lines.append(f"URL:{url}")
    lines += [
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        f"DESCRIPTION:{_escape(description)}",
        f"TRIGGER;RELATED=START:{trigger}",
        "END:VALARM",
        "END:VEVENT",
    ]
    return lines


def feed(db: Session, person: Person, language: str, public_url: str | None, now: datetime | None = None) -> str:
    words = Words(language)
    text = TEXT.get(words.language, TEXT["en"])
    stamp = (now or datetime.now(tz=UTC)).astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    base = public_url.rstrip("/") if public_url else None
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//neVus//Calendar 1//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape(text['calendar'].format(person=person.display_name))}",
        "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
        "X-PUBLISHED-TTL:PT6H",
    ]
    lesions = db.scalars(
        select(Lesion).where(Lesion.person_id == person.id, Lesion.deleted_at.is_(None), Lesion.status == "active")
    ).all()
    for lesion in lesions:
        last = db.scalar(
            select(func.max(Observation.captured_at)).where(
                Observation.lesion_id == lesion.id, Observation.deleted_at.is_(None)
            )
        )
        if last is not None and last.tzinfo is None:
            last = last.replace(tzinfo=UTC)
        next_on = due.next_due(lesion, last)
        if next_on is None:
            continue
        if lesion.snoozed_until is not None and lesion.snoozed_until >= next_on:
            next_on = lesion.snoozed_until + timedelta(days=1)
        mark = lesion.label or words.zone(lesion.zone_code)
        lines += _event(
            f"due-{lesion.id}@nevus",
            next_on,
            text["due"].format(mark=mark, person=person.display_name),
            stamp,
            f"{base}/lesions/{lesion.id}" if base else None,
            ("PT9H", text["photograph"]),  # 09:00 on the day
        )
    for appointment in db.scalars(select(Appointment).where(Appointment.person_id == person.id)).all():
        lines += _event(
            f"appointment-{appointment.id}@nevus",
            appointment.date,
            text["appointment"].format(person=person.display_name),
            stamp,
            f"{base}/appointments/{appointment.id}" if base else None,
            ("-P1DT15H", text["prepare"]),  # 09:00 two days before
        )
    lines.append("END:VCALENDAR")
    return "\r\n".join(folded for line in lines for folded in _fold(line)) + "\r\n"
