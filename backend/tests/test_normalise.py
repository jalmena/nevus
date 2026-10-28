# SPDX-License-Identifier: AGPL-3.0-only
"""The normalised view of a card photo: flat, upright, cropped to the card at a known scale."""

from __future__ import annotations

import io
import uuid

import cv2
import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from nevus.cv import card_detect, normalise
from nevus.cv.card import WINDOW
from tests.scene import photograph
from tests.test_accounts import claim
from tests.test_scale import _visit_with_card_photo


def test_a_tilted_card_photo_is_flattened_cropped_and_upright() -> None:
    photo, px_per_mm = photograph(WINDOW, tilt_deg=20)
    found = card_detect.detect(photo)
    assert found["found"]
    made = normalise.normalise(photo, found)
    assert made is not None
    picture, how = made
    # The frame is the card plus the margin, at the photo's own resolution (20 px/mm here, under the cap).
    assert abs(how["px_per_mm"] - px_per_mm) < 1.0
    assert picture.shape[1] == round((WINDOW.width + 6) * how["px_per_mm"])
    assert picture.shape[0] == round((WINDOW.height + 6) * how["px_per_mm"])
    # Seen again in the normalised picture, the card is flat and its markers sit where they are printed.
    again = card_detect.detect(picture)
    assert again["found"] and again["ids"] == [0, 1, 2, 3]
    assert again["tilt_deg"] < 1.0
    s = how["px_per_mm"]
    assert abs(again["mm_per_px"] - 1 / s) < 0.01
    cx, cy = again["centre_px"]
    assert abs(cx - (WINDOW.centre[0] + 3) * s) < 3 and abs(cy - (WINDOW.centre[1] + 3) * s) < 3
    # The disc in the window lands at the centre: darker than the skin around it.
    centre = picture[int(cy) - 5 : int(cy) + 5, int(cx) - 5 : int(cx) + 5].mean()
    skin = picture[int(cy) - 5 : int(cy) + 5, int(cx) + 100 : int(cx) + 110].mean()
    assert centre < skin - 40
    # Image pixels map onto the normalised picture through the same matrix the renditions were made with.
    mapped = normalise.to_normalised(how["matrix"], np.array([found["centre_px"]]))[0]
    assert abs(mapped[0] - cx) < 2 and abs(mapped[1] - cy) < 2


def test_the_window_is_cut_around_the_mark_and_glare_inside_it_is_flagged() -> None:
    photo, _ = photograph(WINDOW, tilt_deg=8)
    found = card_detect.detect(photo)
    made = normalise.normalise(photo, found)
    assert made is not None
    picture, how = made
    card = normalise.card_named(how["card"])
    assert card is not None
    mark = normalise.window(picture, card, how)
    assert mark is not None
    side = round(2 * 14.0 * how["px_per_mm"])
    assert mark.shape[0] == side and mark.shape[1] == side
    # The disc sits in the middle of the window, darker than the skin beside it.
    c = side // 2
    assert mark[c - 4 : c + 4, c - 4 : c + 4].mean() < mark[c - 4 : c + 4, c + 60 : c + 70].mean() - 40
    assert how["flags"] == [] and how["glare_on_mark"] < 0.01
    # A specular spot on the mark is a flag; the same spot outside the window is not.
    glared = photo.copy()
    cx, cy = (int(v) for v in found["centre_px"])
    cv2.circle(glared, (cx + 30, cy), 28, (255, 255, 255), -1)
    _, how_glared = normalise.normalise(glared, found) or (None, {})
    assert "glare_on_mark" in how_glared["flags"]
    outside = photo.copy()
    cv2.circle(outside, (cx, cy - 420), 28, (255, 255, 255), -1)
    _, how_outside = normalise.normalise(outside, found) or (None, {})
    assert how_outside["flags"] == []


def test_a_photo_without_a_card_has_no_normalised_view() -> None:
    assert normalise.normalise(np.zeros((300, 400, 3), np.uint8), {"found": False}) is None


def test_the_normalised_renditions_are_made_and_the_thumbnail_prefers_them(client: TestClient) -> None:
    claim(client)
    _, _, image_id = _visit_with_card_photo(client, tilt=10.0)
    out = client.get(f"/api/images/{image_id}").json()
    kinds = {r["kind"] for r in out["renditions"]}
    assert {"full", "preview", "thumb", "normalised", "normalised_thumb", "mark", "mark_thumb"} <= kinds
    mark = next(r for r in out["renditions"] if r["kind"] == "mark")
    assert mark["width"] == mark["height"]
    normalised = next(r for r in out["renditions"] if r["kind"] == "normalised")
    assert abs(normalised["width"] / normalised["height"] - (WINDOW.width + 6) / (WINDOW.height + 6)) < 0.01
    full = client.get(f"/api/images/{image_id}/normalised")
    assert full.status_code == 200 and full.headers["content-type"] == "image/jpeg"
    with Image.open(io.BytesIO(full.content)) as picture:
        assert (picture.width, picture.height) == (normalised["width"], normalised["height"])
    # The thumbnail of a card photo is the mark in its window, so lists show the mark and not a card on skin.
    thumb = client.get(f"/api/images/{image_id}/thumb")
    with Image.open(io.BytesIO(thumb.content)) as small:
        assert small.width == small.height
    assert client.get(f"/api/images/{image_id}/mark").status_code == 200
    # Settled: the alias may now be cached for good.
    assert out["analysed_at"] is not None
    assert thumb.headers["cache-control"] == "private, max-age=31536000, immutable"


def test_a_card_photo_thumbnail_is_revalidated_until_the_mark_is_cut(client: TestClient) -> None:
    """A list that fetched the plain thumbnail before the analyses ran must not keep it for a year."""
    claim(client)
    _, _, image_id = _visit_with_card_photo(client, tilt=0.0, run_jobs=False)
    before = client.get(f"/api/images/{image_id}/thumb")
    assert before.status_code == 200 and before.headers["cache-control"] == "private, no-cache"
    assert client.get(f"/api/images/{image_id}").json()["analysed_at"] is None
    client.app.state.jobs.run_until_idle()  # type: ignore[attr-defined]
    after = client.get(f"/api/images/{image_id}/thumb", headers={"if-none-match": before.headers["etag"]})
    assert after.status_code == 200 and after.headers["etag"] != before.headers["etag"]
    assert after.headers["cache-control"] == "private, max-age=31536000, immutable"
    with Image.open(io.BytesIO(after.content)) as small:
        assert small.width == small.height


def test_card_photos_from_before_the_mark_crop_catch_up(client: TestClient) -> None:
    """An instance upgraded from a version without the crop gets it for its old card photos, unasked."""
    from sqlalchemy import delete, select

    from nevus.cv.pipeline import catch_up_normalisation
    from nevus.db.models import Analysis, Job, Rendition
    from nevus.db.models import Image as ImageRow
    from nevus.jobs.registry import JobContext
    from nevus.jobs.runner import default_periodic

    claim(client)
    _, _, image_id = _visit_with_card_photo(client, tilt=0.0)
    app = client.app
    factory, store, settings = app.state.session_factory, app.state.blob_store, app.state.settings  # type: ignore[attr-defined]
    with factory() as db:
        # The state an older version left behind: a card found, the normalised view made, no crop of the mark.
        db.execute(
            delete(Rendition).where(
                Rendition.image_id == uuid.UUID(image_id), Rendition.kind.in_(["mark", "mark_thumb"])
            )
        )
        db.execute(
            delete(Analysis).where(Analysis.target_id == uuid.UUID(image_id), Analysis.analyzer == normalise.NAME)
        )
        db.execute(delete(Job).where(Job.dedupe_key == f"normalise:{image_id}:{normalise.VERSION}"))
        image = db.get(ImageRow, uuid.UUID(image_id))
        assert image is not None
        image.analysed_at = None
        db.commit()
    with factory() as db:
        assert catch_up_normalisation(JobContext(db, store, settings)) == 1
        db.commit()
    client.app.state.jobs.run_until_idle()  # type: ignore[attr-defined]
    out = client.get(f"/api/images/{image_id}").json()
    assert {"mark", "mark_thumb"} <= {r["kind"] for r in out["renditions"]} and out["analysed_at"] is not None
    with factory() as db:
        assert catch_up_normalisation(JobContext(db, store, settings)) == 0  # done is done
        assert db.scalar(select(Analysis.version).where(Analysis.analyzer == normalise.NAME)) == normalise.VERSION
    assert "analysis-catch-up" in {task.name for task in default_periodic()}
