# SPDX-License-Identifier: AGPL-3.0-only
"""Photograph quality checks: each warning on a synthetic photo that deserves it, and none on a good one."""

from __future__ import annotations

import time

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from nevus.app import create_app
from nevus.config import Settings
from nevus.cv import quality
from tests.synthetic import jpeg, skin
from tests.test_accounts import claim

SAME_ORIGIN = {"sec-fetch-site": "same-origin"}


def flags(img: np.ndarray) -> list[str]:
    h, w = img.shape[:2]
    return list(quality.analyze(jpeg(img), w, h)["flags"])


@pytest.fixture(scope="module")
def base() -> np.ndarray:
    return skin()


def test_a_good_close_up_carries_no_warning(base: np.ndarray) -> None:
    assert flags(base) == []


@pytest.mark.parametrize("sigma", [3, 6, 10])
def test_a_blurred_photo_is_called_blurry(base: np.ndarray, sigma: int) -> None:
    assert flags(cv2.GaussianBlur(base, (0, 0), sigma)) == ["blurry"]


def test_an_underexposed_photo_is_dark_but_not_blurry(base: np.ndarray) -> None:
    assert flags((base * 0.22).astype(np.uint8)) == ["too_dark"]


def test_an_overexposed_photo_is_too_bright(base: np.ndarray) -> None:
    assert "too_bright" in flags(np.clip(base.astype(np.int16) + 95, 0, 255).astype(np.uint8))


def test_small_specular_highlights_are_glare(base: np.ndarray) -> None:
    shiny = base.copy()
    cv2.circle(shiny, (1200, 900), 70, (255, 255, 255), -1)
    cv2.circle(shiny, (1800, 1300), 50, (255, 255, 255), -1)
    assert flags(shiny) == ["glare"]


def test_a_large_white_area_is_not_glare(base: np.ndarray) -> None:
    card = base.copy()
    cv2.rectangle(card, (100, 100), (900, 600), (238, 238, 238), -1)  # white paper, well exposed
    assert "glare" not in flags(card)


def test_a_small_photo_has_low_resolution(base: np.ndarray) -> None:
    assert flags(cv2.resize(base, (800, 600), interpolation=cv2.INTER_AREA)) == ["low_resolution"]


def _visit_with_photo(client: TestClient, image: bytes) -> tuple[str, str]:
    pid = client.post("/api/persons", json={"display_name": "Ana"}, headers=SAME_ORIGIN).json()["id"]
    lesion = client.post(
        f"/api/persons/{pid}/lesions",
        json={"location": {"zone": "1250", "x": 0.4, "y": 0.25}, "status": "active", "interval_days": 90},
        headers=SAME_ORIGIN,
    ).json()
    visit = client.post(f"/api/lesions/{lesion['id']}/observations", json={}, headers=SAME_ORIGIN).json()
    upload = client.post(
        f"/api/observations/{visit['id']}/images",
        files={"file": ("photo.jpg", image, "image/jpeg")},
        headers=SAME_ORIGIN,
    )
    assert upload.status_code == 201, upload.text
    return visit["id"], upload.json()["id"]


def test_warnings_reach_the_photo_and_the_visit_after_the_job_runs(client: TestClient) -> None:
    claim(client)
    visit_id, image_id = _visit_with_photo(client, jpeg(cv2.GaussianBlur(skin(), (0, 0), 6)))
    before = client.get(f"/api/images/{image_id}").json()
    assert before["quality_checked_at"] is None and before["quality_flags"] == []

    jobs = client.app.state.jobs  # type: ignore[attr-defined]
    assert jobs.run_until_idle() == 1
    assert jobs.run_until_idle() == 0, "the same check is not queued twice"

    after = client.get(f"/api/images/{image_id}").json()
    assert after["quality_flags"] == ["blurry"] and after["quality_checked_at"] is not None
    assert client.get(f"/api/observations/{visit_id}").json()["quality_flags"] == ["blurry"]

    # Moving the only photo to the trash clears the visit's warning.
    assert client.delete(f"/api/images/{image_id}", headers=SAME_ORIGIN).status_code == 204
    assert client.get(f"/api/observations/{visit_id}").json()["quality_flags"] == []


def test_the_supervisor_runs_checks_in_a_worker_process(settings: Settings) -> None:
    live = settings.model_copy(update={"jobs_enabled": True, "job_poll_seconds": 0.2})
    with TestClient(create_app(live), base_url="http://localhost") as client:
        claim(client)
        _, image_id = _visit_with_photo(client, jpeg(skin(width=1600, height=1200)))
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            image = client.get(f"/api/images/{image_id}").json()
            if image["quality_checked_at"] is not None:
                break
            time.sleep(0.25)
        assert image["quality_checked_at"] is not None, "the background check did not finish in a minute"
        assert image["quality_flags"] == []
