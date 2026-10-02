# SPDX-License-Identifier: AGPL-3.0-only
"""The due list: every mark due for a photo among the persons the user may see."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from fastapi import APIRouter
from pydantic import BaseModel

from nevus.auth.dependencies import CurrentUser, DbSession
from nevus.db.types import utcnow
from nevus.domain.due import due_for_user

router = APIRouter(prefix="/api", tags=["reminders"])


class DueOut(BaseModel):
    lesion_id: uuid.UUID
    label: str | None
    zone: str
    person_id: uuid.UUID
    person_name: str
    next_due_on: date
    overdue_days: int
    last_observed_at: datetime | None


@router.get("/due", response_model=list[DueOut])
def due_list(user: CurrentUser, db: DbSession) -> list[DueOut]:
    today = utcnow().date()
    return [
        DueOut(
            lesion_id=item.lesion.id,
            label=item.lesion.label,
            zone=item.lesion.zone_code,
            person_id=item.person.id,
            person_name=item.person.display_name,
            next_due_on=item.next_due_on,
            overdue_days=(today - item.next_due_on).days,
            last_observed_at=item.last_observed_at,
        )
        for item in due_for_user(db, user.id, today)
    ]
