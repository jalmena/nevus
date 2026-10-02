# SPDX-License-Identifier: AGPL-3.0-only
"""Experimental spot proposals on a session's zone photo, matched against the previous session (FR-SES-03).

When the same zone was photographed in an earlier session and the person confirmed marks there, the
earlier photo is lined up with the new one: by the pattern the spots form (`cv.constellation`), as they
move with the skin and last for years; or, when there are too few spots for a pattern, by image
features on the skin (`cv.align`). Both abstain when unsure. Each earlier mark is then carried over:
a spot near where it lands is proposed as that mark (matched); when nothing is there, the mark is
proposed where it should be, to look at (uncertain). Spots left over are proposed as new. If the
photos cannot be lined up, spots are proposed without a suggestion.
"""

from __future__ import annotations

import math
import uuid
from typing import Any

import cv2
import numpy as np
from sqlalchemy import select

from nevus import analysis
from nevus.cv import align, candidates, constellation
from nevus.cv.imageio import decode, upright
from nevus.db.models import JOB_QUEUED, JOB_RUNNING, BodySession, Image, Job, Person, SessionMark, SessionZone
from nevus.jobs import queue
from nevus.jobs.registry import JobContext, JobKind, register

CANDIDATES_KIND = "analyze.session"
MATCH_RADIUS = 0.02  # of the photo's short side


def _dedupe_key(zone_id: uuid.UUID, image_id: uuid.UUID) -> str:
    return f"session:{zone_id}:{image_id}:{candidates.VERSION}"


def enqueue_candidates(ctx_db: Any, zone: SessionZone, image: Image) -> bool:
    person = ctx_db.get(Person, image.person_id)
    if person is None or not person.experimental_analysis:
        return False
    job = queue.enqueue(
        ctx_db,
        CANDIDATES_KIND,
        {"zone_id": str(zone.id), "image_id": str(image.id)},
        dedupe_key=_dedupe_key(zone.id, image.id),
        priority=2,
    )
    return job is not None


def analysing(db: Any, zone: SessionZone) -> bool:
    """Whether proposals for the zone's current photo are still being made."""
    if zone.image_id is None:
        return False
    status = db.scalar(select(Job.status).where(Job.dedupe_key == _dedupe_key(zone.id, zone.image_id)))
    return status in (JOB_QUEUED, JOB_RUNNING)


def _previous(ctx: JobContext, zone: SessionZone) -> tuple[Image, list[SessionMark]] | None:
    session = ctx.db.get(BodySession, zone.session_id)
    if session is None:
        return None
    rows = ctx.db.execute(
        select(SessionZone, BodySession)
        .join(BodySession, BodySession.id == SessionZone.session_id)
        .where(
            BodySession.person_id == session.person_id,
            BodySession.started_at < session.started_at,
            SessionZone.zone == zone.zone,
            SessionZone.status == "captured",
            SessionZone.image_id.is_not(None),
        )
        .order_by(BodySession.started_at.desc())
    ).all()
    for earlier, _ in rows:
        image = ctx.db.get(Image, earlier.image_id)
        if image is None or image.deleted_at is not None:
            continue
        marks = ctx.db.scalars(
            select(SessionMark).where(
                SessionMark.session_zone_id == earlier.id,
                SessionMark.state == "confirmed",
                SessionMark.lesion_id.is_not(None),
            )
        ).all()
        return image, list(marks)
    return None


def _read(ctx: JobContext, image: Image) -> bytes:
    return ctx.store.path(image.sha256).read_bytes()


def _load(ctx: JobContext, payload: dict[str, Any]) -> dict[str, Any] | None:
    zone = ctx.db.get(SessionZone, uuid.UUID(payload["zone_id"]))
    image = ctx.db.get(Image, uuid.UUID(payload["image_id"]))
    if zone is None or image is None or zone.image_id != image.id or image.deleted_at is not None:
        return None
    person = ctx.db.get(Person, image.person_id)
    if person is None or not person.experimental_analysis:
        return None
    value: dict[str, Any] = {"data": _read(ctx, image), "orientation": image.orientation, "previous": None}
    earlier = _previous(ctx, zone)
    if earlier is not None:
        previous_image, marks = earlier
        value["previous"] = {
            "data": _read(ctx, previous_image),
            "orientation": previous_image.orientation,
            "marks": [{"x": m.x, "y": m.y, "lesion_id": str(m.lesion_id)} for m in marks],
        }
    return value


def line_up(current: Any, spots: list[dict[str, Any]], earlier: Any) -> dict[str, Any]:
    """The transform from the earlier photo to the current one, or an abstention with a reason."""
    found = candidates.detect(earlier)["candidates"]
    (h, w), (eh, ew) = current.shape[:2], earlier.shape[:2]
    by_pattern = constellation.match(found, (ew, eh), spots, (w, h))
    if by_pattern["status"] == "aligned" or by_pattern["reason"] != "too_few_spots":
        return by_pattern
    # Too few spots for a pattern: the skin's own texture, never the background, may still line them up.
    return align.from_features(current, earlier, mask_a=candidates.skin(current), mask_b=candidates.skin(earlier))


def compute(value: dict[str, Any]) -> dict[str, Any]:
    current = upright(decode(value["data"]), int(value["orientation"]))
    found = candidates.detect(current)
    spots = [dict(spot, match="new", lesion_id=None) for spot in found["candidates"]]
    carried: list[dict[str, Any]] = []
    previous = value.get("previous")
    alignment: dict[str, Any] | None = None
    if previous and previous["marks"]:
        earlier = upright(decode(previous["data"]), int(previous["orientation"]))
        alignment = line_up(current, found["candidates"], earlier)  # maps the earlier photo onto this one
        if alignment["status"] == "aligned":
            h, w = current.shape[:2]
            eh, ew = earlier.shape[:2]
            matrix = np.asarray(alignment["matrix"], np.float64)
            points = np.array([[m["x"] * ew, m["y"] * eh] for m in previous["marks"]], np.float64).reshape(-1, 1, 2)
            landed = cv2.perspectiveTransform(points, matrix).reshape(-1, 2)
            radius = MATCH_RADIUS * min(w, h)
            taken: set[int] = set()
            for mark, (x, y) in zip(previous["marks"], landed, strict=True):
                if not (0 <= x < w and 0 <= y < h):
                    continue  # outside this photo's framing
                best, best_distance = None, radius
                for index, spot in enumerate(spots):
                    if index in taken:
                        continue
                    distance = math.hypot(spot["x"] * w - x, spot["y"] * h - y)
                    if distance <= best_distance:
                        best, best_distance = index, distance
                if best is None:
                    carried.append(
                        {
                            "x": round(x / w, 4),
                            "y": round(y / h, 4),
                            "match": "uncertain",
                            "lesion_id": mark["lesion_id"],
                        }
                    )
                else:
                    taken.add(best)
                    spots[best]["match"] = "matched"
                    spots[best]["lesion_id"] = mark["lesion_id"]
        else:
            for spot in spots:
                spot["match"] = None  # could not line the photos up: no suggestion
    return {
        "found": found["found"],
        "reason": found["reason"],
        "aligned": None if alignment is None else alignment["status"] == "aligned",
        "alignment": None
        if alignment is None
        else {key: alignment.get(key) for key in ("status", "method", "reason", "nfa")},
        "proposals": spots + carried,
    }


def _store(ctx: JobContext, payload: dict[str, Any], result: dict[str, Any]) -> None:
    zone = ctx.db.get(SessionZone, uuid.UUID(payload["zone_id"]))
    image = ctx.db.get(Image, uuid.UUID(payload["image_id"]))
    if zone is None or image is None or zone.image_id != image.id:
        return
    row = analysis.record(
        ctx.db,
        target_type="image",
        target_id=image.id,
        analyzer=candidates.NAME,
        version=candidates.VERSION,
        params=candidates.PARAMS,
        input_hash=image.sha256,
        outputs=result,
        decision="pending",
    )
    existing = ctx.db.scalar(select(SessionMark.id).where(SessionMark.analysis_id == row.id))
    if existing is not None:
        return
    for proposal in result["proposals"]:
        ctx.db.add(
            SessionMark(
                session_zone_id=zone.id,
                x=float(proposal["x"]),
                y=float(proposal["y"]),
                lesion_id=uuid.UUID(proposal["lesion_id"]) if proposal.get("lesion_id") else None,
                source="candidate",
                state="pending",
                match=proposal.get("match"),
                analysis_id=row.id,
            )
        )
    ctx.db.flush()


register(JobKind(CANDIDATES_KIND, _load, compute, _store, timeout=240.0))
