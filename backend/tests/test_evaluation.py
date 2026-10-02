# SPDX-License-Identifier: AGPL-3.0-only
"""The personal evaluation set: labels, metrics per skin tone, re-analysis that keeps history."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from nevus import evaluation
from nevus.cli.main import main
from nevus.db.models import Analysis
from tests.test_accounts import MEMBER, claim
from tests.test_scale import SAME_ORIGIN
from tests.test_segment import _visit_with_card


def test_overlap_and_diameter_of_outlines() -> None:
    square = [[0, 0], [100, 0], [100, 100], [0, 100]]
    shifted = [[50, 0], [150, 0], [150, 100], [50, 100]]
    iou, dice = evaluation.overlap(square, square)
    assert iou == pytest.approx(1.0, abs=0.02) and dice == pytest.approx(1.0, abs=0.02)
    iou, dice = evaluation.overlap(square, shifted)
    assert iou == pytest.approx(1 / 3, abs=0.02) and dice == pytest.approx(0.5, abs=0.02)
    assert evaluation.equivalent_diameter(square) == pytest.approx(112.8, abs=0.2)


def test_labelling_and_the_summary_per_skin_tone(client: TestClient) -> None:
    claim(client)
    pid, _, image = _visit_with_card(client)
    client.patch(f"/api/persons/{pid}", json={"experimental_analysis": True, "skin_tone": "MST3"}, headers=SAME_ORIGIN)
    client.app.state.jobs.run_until_idle()  # type: ignore[attr-defined]
    photos = client.get("/api/evaluation/photos?only=unlabelled").json()
    assert [p["image_id"] for p in photos] == [image] and photos[0]["proposal"] is not None
    truth = photos[0]["proposal"]
    assert client.put(f"/api/evaluation/photos/{image}/label", json={}, headers=SAME_ORIGIN).status_code == 422
    saved = client.put(
        f"/api/evaluation/photos/{image}/label", json={"outline": truth, "quality": "good"}, headers=SAME_ORIGIN
    )
    assert saved.status_code == 200 and saved.json()["quality"] == "good"
    assert client.get("/api/evaluation/photos?only=unlabelled").json() == []
    report = client.get("/api/evaluation/summary").json()
    tone = report["outline"]["by_tone"]["MST3"]
    assert tone["photos"] == 1 and tone["found"] == 1 and tone["mean_iou"] == pytest.approx(1.0, abs=0.02)
    assert report["quality"]["overall"]["photos"] == 1
    assert client.delete(f"/api/evaluation/photos/{image}/label", headers=SAME_ORIGIN).status_code == 204


def test_only_administrators_label_and_only_their_persons(client: TestClient) -> None:
    claim(client)
    _visit_with_card(client)
    client.post("/api/users", json=MEMBER, headers=SAME_ORIGIN)
    client.post("/api/auth/logout", headers=SAME_ORIGIN)
    client.post("/api/auth/login", json=MEMBER, headers=SAME_ORIGIN)
    assert client.get("/api/evaluation/photos").status_code == 403


def test_reanalysis_adds_results_and_keeps_the_earlier_ones(
    client: TestClient, settings: object, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    claim(client)
    pid, _, image = _visit_with_card(client)
    client.patch(f"/api/persons/{pid}", json={"experimental_analysis": True}, headers=SAME_ORIGIN)
    client.app.state.jobs.run_until_idle()  # type: ignore[attr-defined]
    monkeypatch.setenv("NEVUS_DATA_DIR", str(settings.data_dir))  # type: ignore[attr-defined]
    if not settings.is_sqlite:  # type: ignore[attr-defined]
        monkeypatch.setenv("NEVUS_DATABASE_URL", settings.database_url)  # type: ignore[attr-defined]
    from nevus import config

    config.get_settings.cache_clear()
    assert main(["reanalyze", "--analyzer", "segment"]) == 0
    assert "0 outline analyses" in capsys.readouterr().out, "the current version already ran"
    monkeypatch.setattr("nevus.cv.segment.VERSION", "1.0.1")
    assert main(["reanalyze", "--analyzer", "segment", "--now"]) == 0
    with client.app.state.session_factory() as db:  # type: ignore[attr-defined]
        versions = sorted(
            row.version
            for row in db.scalars(
                select(Analysis).where(Analysis.target_id == uuid.UUID(image), Analysis.analyzer == "segment.auto")
            )
        )
    assert versions == ["1.0.0", "1.0.1"]
    config.get_settings.cache_clear()
