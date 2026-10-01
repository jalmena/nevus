# SPDX-License-Identifier: AGPL-3.0-only
"""The experimental outline: evaluation gates per skin tone, abstention, framing, and the proposal flow.

The gates are the ones MODEL_CARD.md reports: on six steps of the Monk Skin Tone scale, with and
without hairs, a clear mark is found and its size is within 5 %; a faint mark is found within 10 % or
the analyzer abstains, and it is never confidently wrong.
"""

from __future__ import annotations

import math

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from nevus.cv import card_detect, segment
from nevus.cv.card import WINDOW
from tests.scene import photograph
from tests.synthetic import MONK, jpeg, toned_skin
from tests.test_accounts import MEMBER, claim
from tests.test_scale import SAME_ORIGIN


def _diameter(outline: list[list[float]]) -> float:
    return 2 * math.sqrt(abs(cv2.contourArea(np.asarray(outline, np.float32))) / math.pi)


@pytest.mark.parametrize("tone", list(MONK))
@pytest.mark.parametrize("hair", [False, True])
def test_a_clear_mark_is_found_on_every_skin_tone(tone: str, hair: bool) -> None:
    for seed in range(2):
        image, truth, _ = toned_skin(MONK[tone], seed, hair)
        result = segment.propose(image, None)
        assert result["found"], (tone, hair, seed, result.get("reason"))
        assert abs(_diameter(result["outline"]) - truth) / truth <= 0.05
        assert result["confidence"] > 0.5


@pytest.mark.parametrize("tone", list(MONK))
def test_a_faint_mark_is_measured_well_or_not_at_all(tone: str) -> None:
    for seed in range(3):
        image, truth, _ = toned_skin(MONK[tone], seed, hair=True, mark_factor=0.85)
        result = segment.propose(image, None)
        if result["found"]:
            assert abs(_diameter(result["outline"]) - truth) / truth <= 0.10, (tone, seed)
        else:
            assert result["reason"] in segment.REASONS


def test_nothing_to_see_abstains() -> None:
    flat = np.full((2250, 3000, 3), (180, 200, 230), np.uint8)
    result = segment.propose(flat, None)
    assert result == {"found": False, "reason": "no_mark_found", "framing_flags": ["no_mark_found"]}


def test_framing_hints_for_the_next_photo() -> None:
    off, _, _ = toned_skin(MONK["MST5"], 1, offset=(700, 0))
    assert "mark_off_centre" in segment.propose(off, None, {"centre_fraction": 0.9})["framing_flags"]
    small, _, _ = toned_skin(MONK["MST5"], 1, offset=(0, 0), mark_scale=0.25)
    assert "mark_small" in segment.propose(small, None)["framing_flags"]
    centred, _, _ = toned_skin(MONK["MST5"], 1, offset=(0, 0))
    assert segment.propose(centred, None)["framing_flags"] == []


def test_the_card_window_is_the_seed_and_the_card_never_is_the_mark() -> None:
    photo, _ = photograph(WINDOW, tilt_deg=8, disc_mm=5.0)
    card = card_detect.detect(photo)
    result = segment.propose(photo, card)
    assert result["found"] and result["seed_method"] == "card_window"
    centre = np.asarray(result["outline"]).mean(axis=0)
    assert np.linalg.norm(centre - np.asarray(card["centre_px"])) < 20


def _visit_with_card(client: TestClient) -> tuple[str, str, str]:
    pid = client.post("/api/persons", json={"display_name": "Ana"}, headers=SAME_ORIGIN).json()["id"]
    lesion = client.post(
        f"/api/persons/{pid}/lesions", json={"location": {"zone": "1250", "x": 0.4, "y": 0.25}}, headers=SAME_ORIGIN
    ).json()
    visit = client.post(f"/api/lesions/{lesion['id']}/observations", json={}, headers=SAME_ORIGIN).json()
    photo, _ = photograph(WINDOW, tilt_deg=0, disc_mm=5.0)
    image = client.post(
        f"/api/observations/{visit['id']}/images",
        files={"file": ("card.jpg", jpeg(photo, 92), "image/jpeg")},
        data={"role": "with_reference"},
        headers=SAME_ORIGIN,
    ).json()
    return pid, visit["id"], image["id"]


def test_proposals_wait_for_the_experimental_switch_and_for_a_decision(client: TestClient) -> None:
    claim(client)
    client.patch("/api/auth/me", json={"card_line_mm": 50.0}, headers=SAME_ORIGIN)
    pid, visit, image = _visit_with_card(client)
    client.app.state.jobs.run_until_idle()  # type: ignore[attr-defined]
    assert client.get(f"/api/images/{image}/proposals").json() == [], "off by default: nothing runs"
    client.patch(f"/api/persons/{pid}", json={"experimental_analysis": True}, headers=SAME_ORIGIN)
    client.app.state.jobs.run_until_idle()  # type: ignore[attr-defined]
    proposals = client.get(f"/api/images/{image}/proposals").json()
    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal["found"] and proposal["decision"] == "pending" and proposal["analyzer"] == "segment.auto"
    assert abs(proposal["size"]["longest_mm"] - 5.0) <= 0.3 and proposal["size"]["scale_kind"] == "card"
    confirmed = client.post(f"/api/proposals/{proposal['id']}/confirm", json={}, headers=SAME_ORIGIN)
    assert confirmed.status_code == 201, confirmed.text
    assert confirmed.json()["method"] == "automatic" and abs(confirmed.json()["longest_mm"] - 5.0) <= 0.3
    assert client.get(f"/api/images/{image}/proposals").json()[0]["decision"] == "confirmed"
    again = client.post(f"/api/proposals/{proposal['id']}/confirm", json={}, headers=SAME_ORIGIN)
    assert again.status_code == 409
    assert client.get(f"/api/observations/{visit}/measurements").json()[0]["method"] == "automatic"


def test_a_rejected_proposal_stays_on_record_and_viewers_cannot_decide(client: TestClient) -> None:
    claim(client)
    pid, _, image = _visit_with_card(client)
    client.patch(f"/api/persons/{pid}", json={"experimental_analysis": True}, headers=SAME_ORIGIN)
    client.app.state.jobs.run_until_idle()  # type: ignore[attr-defined]
    proposal = client.get(f"/api/images/{image}/proposals").json()[0]
    client.post("/api/users", json=MEMBER, headers=SAME_ORIGIN)
    client.put(
        f"/api/persons/{pid}/access", json={"username": MEMBER["username"], "role": "viewer"}, headers=SAME_ORIGIN
    )
    client.post("/api/auth/logout", headers=SAME_ORIGIN)
    client.post("/api/auth/login", json=MEMBER, headers=SAME_ORIGIN)
    assert len(client.get(f"/api/images/{image}/proposals").json()) == 1, "viewers see proposals"
    assert client.post(f"/api/proposals/{proposal['id']}/reject", headers=SAME_ORIGIN).status_code == 403
    client.post("/api/auth/logout", headers=SAME_ORIGIN)
    client.post("/api/auth/login", json={"username": "jose", "password": "correct horse battery"}, headers=SAME_ORIGIN)
    rejected = client.post(f"/api/proposals/{proposal['id']}/reject", headers=SAME_ORIGIN)
    assert rejected.status_code == 200 and rejected.json()["decision"] == "rejected"
