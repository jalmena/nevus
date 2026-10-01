# SPDX-License-Identifier: AGPL-3.0-only
"""Preparing an appointment: the checklist of marks to photograph, and the report to bring."""

from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi.testclient import TestClient

from nevus.db.models import Appointment
from nevus.db.types import utcnow
from nevus.domain import purge
from tests.test_accounts import MEMBER, claim
from tests.test_comparison import _two_visits
from tests.test_reports import _attached
from tests.test_scale import SAME_ORIGIN


def _in(days: int) -> str:
    return (utcnow().date() + timedelta(days=days)).isoformat()


def _setup(client: TestClient) -> tuple[str, str, str]:
    """A person with a photographed mark (due in 90 days) and a mark never photographed."""
    claim(client)
    pid, visit_a, _, _, _ = _two_visits(client)
    photographed = client.get(f"/api/observations/{visit_a}").json()["lesion_id"]
    never = client.post(
        f"/api/persons/{pid}/lesions",
        json={"location": {"zone": "2300", "x": 0.5, "y": 0.45}, "status": "active", "interval_days": 90},
        headers=SAME_ORIGIN,
    ).json()["id"]
    return pid, photographed, never


def test_the_checklist_lists_what_is_due_by_the_date_and_ticks_what_is_done(client: TestClient) -> None:
    pid, photographed, never = _setup(client)
    created = client.post(
        f"/api/persons/{pid}/appointments",
        json={"date": _in(120), "notes": " Dermatology, room 4 "},
        headers=SAME_ORIGIN,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["notes"] == "Dermatology, room 4" and body["can_edit"]
    states = {item["lesion_id"]: item["state"] for item in body["checklist"]}
    assert states == {photographed: "to_photograph", never: "never_photographed"}
    soon = client.post(f"/api/persons/{pid}/appointments", json={"date": _in(10)}, headers=SAME_ORIGIN).json()
    assert [i["lesion_id"] for i in soon["checklist"]] == [never], "not due before a near date"
    client.post(f"/api/lesions/{photographed}/observations", json={}, headers=SAME_ORIGIN)
    again = client.get(f"/api/appointments/{body['id']}").json()
    assert {i["lesion_id"]: i["state"] for i in again["checklist"]}[photographed] == "photographed"
    assert again["checklist"][-1]["state"] == "photographed", "what is done comes last"


def test_upcoming_appointments_and_editing(client: TestClient) -> None:
    pid, _, _ = _setup(client)
    future = client.post(f"/api/persons/{pid}/appointments", json={"date": _in(30)}, headers=SAME_ORIGIN).json()
    past = client.post(f"/api/persons/{pid}/appointments", json={"date": _in(-3)}, headers=SAME_ORIGIN).json()
    assert [a["id"] for a in client.get("/api/appointments/upcoming").json()] == [future["id"]]
    assert [a["id"] for a in client.get(f"/api/persons/{pid}/appointments").json()] == [future["id"], past["id"]]
    moved = client.patch(
        f"/api/appointments/{future['id']}", json={"date": _in(40), "notes": "Dr. Ruiz"}, headers=SAME_ORIGIN
    ).json()
    assert moved["date"] == _in(40) and moved["notes"] == "Dr. Ruiz"
    assert client.delete(f"/api/appointments/{past['id']}", headers=SAME_ORIGIN).status_code == 204
    assert client.get(f"/api/appointments/{past['id']}").status_code == 404


def test_viewers_see_appointments_but_do_not_plan_them(client: TestClient) -> None:
    pid, _, _ = _setup(client)
    made = client.post(f"/api/persons/{pid}/appointments", json={"date": _in(30)}, headers=SAME_ORIGIN).json()
    client.post("/api/users", json=MEMBER, headers=SAME_ORIGIN)
    client.put(
        f"/api/persons/{pid}/access", json={"username": MEMBER["username"], "role": "viewer"}, headers=SAME_ORIGIN
    )
    client.post("/api/auth/logout", headers=SAME_ORIGIN)
    client.post("/api/auth/login", json=MEMBER, headers=SAME_ORIGIN)
    seen = client.get(f"/api/appointments/{made['id']}").json()
    assert seen["can_edit"] is False
    assert (
        client.post(f"/api/persons/{pid}/appointments", json={"date": _in(5)}, headers=SAME_ORIGIN).status_code == 403
    )
    assert client.delete(f"/api/appointments/{made['id']}", headers=SAME_ORIGIN).status_code == 403


def test_the_appointment_report_is_the_summary_and_the_records_of_the_checklist(client: TestClient) -> None:
    pid, photographed, never = _setup(client)
    made = client.post(
        f"/api/persons/{pid}/appointments", json={"date": _in(120), "notes": "Bring glasses"}, headers=SAME_ORIGIN
    ).json()
    report = client.post(f"/api/appointments/{made['id']}/report", json={"language": "es"}, headers=SAME_ORIGIN)
    assert report.status_code == 202, report.text
    assert report.json()["scope"] == "visit"
    client.app.state.jobs.run_until_idle()  # type: ignore[attr-defined]
    ready = client.get(f"/api/reports/{report.json()['id']}").json()
    assert ready["status"] == "ready", ready
    data = _attached(client.get(ready["download_url"]).content)
    assert data["scope"] == "visit" and data["appointment"]["notes"] == "Bring glasses"
    assert set(data["records"]) == {photographed, never}
    with_visits = {m["id"] for m in data["lesions"] if m["visits"]}
    assert with_visits == {photographed}, "a mark never photographed has a record without visits"
    assert client.get(f"/api/appointments/{made['id']}").json()["report_id"] == ready["id"]


def test_purging_the_person_removes_the_appointments(client: TestClient) -> None:
    pid, _, _ = _setup(client)
    made = client.post(f"/api/persons/{pid}/appointments", json={"date": _in(30)}, headers=SAME_ORIGIN).json()
    factory = client.app.state.session_factory  # type: ignore[attr-defined]
    with factory() as db:
        purge.purge_person(db, uuid.UUID(pid))
        db.commit()
        assert db.get(Appointment, uuid.UUID(made["id"])) is None
