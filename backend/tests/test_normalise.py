# SPDX-License-Identifier: AGPL-3.0-only
"""The normalised view of a card photo: flat, upright, cropped to the card at a known scale."""

from __future__ import annotations

import io

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


def test_a_photo_without_a_card_has_no_normalised_view() -> None:
    assert normalise.normalise(np.zeros((300, 400, 3), np.uint8), {"found": False}) is None


def test_the_normalised_renditions_are_made_and_the_thumbnail_prefers_them(client: TestClient) -> None:
    claim(client)
    _, _, image_id = _visit_with_card_photo(client, tilt=10.0)
    out = client.get(f"/api/images/{image_id}").json()
    kinds = {r["kind"] for r in out["renditions"]}
    assert {"full", "preview", "thumb", "normalised", "normalised_thumb"} <= kinds
    normalised = next(r for r in out["renditions"] if r["kind"] == "normalised")
    assert abs(normalised["width"] / normalised["height"] - (WINDOW.width + 6) / (WINDOW.height + 6)) < 0.01
    full = client.get(f"/api/images/{image_id}/normalised")
    assert full.status_code == 200 and full.headers["content-type"] == "image/jpeg"
    with Image.open(io.BytesIO(full.content)) as picture:
        assert (picture.width, picture.height) == (normalised["width"], normalised["height"])
    # The thumbnail of a card photo is the normalised view, so lists show the mark and not a card on skin.
    thumb = client.get(f"/api/images/{image_id}/thumb")
    with Image.open(io.BytesIO(thumb.content)) as small:
        assert abs(small.width / small.height - (WINDOW.width + 6) / (WINDOW.height + 6)) < 0.02
