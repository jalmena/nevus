# SPDX-License-Identifier: AGPL-3.0-only
"""When a mark is due for a photo: its last visit (or discovery, or creation) plus its interval.

A snoozed mark is not due until the snooze ends; a removed or resolved mark is never due. Adding
a visit is what marks a reminder as done.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from nevus.db.models import Lesion, Observation, Person, PersonAccess


def next_due(lesion: Lesion, last_observed_at: datetime | None) -> date | None:
    if lesion.status != "active":
        return None
    anchor = last_observed_at.date() if last_observed_at else (lesion.first_noticed_on or lesion.created_at.date())
    return anchor + timedelta(days=lesion.interval_days)


def is_due(lesion: Lesion, next_due_on: date | None, today: date) -> bool:
    if next_due_on is None or next_due_on > today:
        return False
    return lesion.snoozed_until is None or lesion.snoozed_until < today


@dataclass(frozen=True)
class DueItem:
    lesion: Lesion
    person: Person
    next_due_on: date
    last_observed_at: datetime | None


def due_for_user(
    db: Session, user_id: uuid.UUID, today: date, *, roles: tuple[str, ...] | None = None
) -> list[DueItem]:
    """Marks due today or earlier among the persons this user may see, oldest due first."""
    query = (
        select(Lesion, Person)
        .join(Person, Person.id == Lesion.person_id)
        .join(PersonAccess, (PersonAccess.person_id == Person.id) & (PersonAccess.user_id == user_id))
        .where(Lesion.deleted_at.is_(None), Person.deleted_at.is_(None), Lesion.status == "active")
    )
    if roles:
        query = query.where(PersonAccess.role.in_(roles))
    rows = db.execute(query).all()
    if not rows:
        return []
    last: dict[uuid.UUID, datetime] = {
        lesion_id: captured_at
        for lesion_id, captured_at in db.execute(
            select(Observation.lesion_id, func.max(Observation.captured_at))
            .where(Observation.lesion_id.in_([lesion.id for lesion, _ in rows]), Observation.deleted_at.is_(None))
            .group_by(Observation.lesion_id)
        ).all()
    }
    items: list[DueItem] = []
    for lesion, person in rows:
        last_at = last.get(lesion.id)
        if last_at is not None and last_at.tzinfo is None:
            last_at = last_at.replace(tzinfo=UTC)
        due_on = next_due(lesion, last_at)
        if due_on is not None and is_due(lesion, due_on, today):
            items.append(DueItem(lesion, person, due_on, last_at))
    return sorted(items, key=lambda item: (item.next_due_on, item.person.display_name))
