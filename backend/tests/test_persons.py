"""Persons and per-person access: owner, manager, viewer."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.test_accounts import ADMIN, MEMBER, claim


def login_member(client: TestClient) -> TestClient:
    assert client.post("/api/users", json=MEMBER).status_code == 201
    member = TestClient(client.app, base_url="http://localhost")
    assert member.post("/api/auth/login", json=MEMBER).status_code == 200
    return member


def test_persons_are_scoped_to_the_users_that_may_see_them(client: TestClient) -> None:
    claim(client)
    member = login_member(client)
    person = client.post("/api/persons", json={"display_name": "  Ana  ", "birth_year": 2015}).json()
    assert person["display_name"] == "Ana" and person["my_role"] == "owner"
    assert member.get("/api/persons").json() == []
    assert member.get(f"/api/persons/{person['id']}").status_code == 404
    assert member.patch(f"/api/persons/{person['id']}", json={"display_name": "Eve"}).status_code == 404


def test_owner_shares_a_person_and_roles_limit_what_others_can_do(client: TestClient) -> None:
    claim(client)
    member = login_member(client)
    person_id = client.post("/api/persons", json={"display_name": "Ana"}).json()["id"]

    granted = client.put(f"/api/persons/{person_id}/access", json={"username": "ana", "role": "viewer"})
    assert granted.status_code == 200 and granted.json()["role"] == "viewer"
    assert member.get(f"/api/persons/{person_id}").json()["my_role"] == "viewer"
    assert member.patch(f"/api/persons/{person_id}", json={"display_name": "Eve"}).status_code == 403

    client.put(f"/api/persons/{person_id}/access", json={"username": "ana", "role": "manager"})
    assert member.patch(f"/api/persons/{person_id}", json={"display_name": "Ana María"}).status_code == 200
    # the experimental-analysis switch belongs to the owner alone
    assert member.patch(f"/api/persons/{person_id}", json={"experimental_analysis": True}).status_code == 403
    assert (
        client.patch(f"/api/persons/{person_id}", json={"experimental_analysis": True}).json()["experimental_analysis"]
        is True
    )
    # managers cannot share or delete
    assert (
        member.put(f"/api/persons/{person_id}/access", json={"username": "jose", "role": "viewer"}).status_code == 403
    )
    member.post("/api/auth/sudo", json={"password": MEMBER["password"]})
    assert member.delete(f"/api/persons/{person_id}").status_code == 403

    roles = {row["username"]: row["role"] for row in client.get(f"/api/persons/{person_id}/access").json()}
    assert roles == {"jose": "owner", "ana": "manager"}
    assert (
        client.delete(
            f"/api/persons/{person_id}/access/{client.get('/api/auth/session').json()['user']['id']}"
        ).status_code
        == 400
    )
    member_id = member.get("/api/auth/session").json()["user"]["id"]
    assert client.delete(f"/api/persons/{person_id}/access/{member_id}").status_code == 204
    assert member.get(f"/api/persons/{person_id}").status_code == 404


def test_validation_of_person_fields(client: TestClient) -> None:
    claim(client)
    assert client.post("/api/persons", json={"display_name": "   "}).status_code == 422
    assert client.post("/api/persons", json={"display_name": "Ana", "birth_year": 1800}).status_code == 422
    assert (
        client.put(
            "/api/persons/00000000-0000-0000-0000-000000000000/access", json={"username": "x", "role": "owner"}
        ).status_code
        == 422
    )


__all__ = ["ADMIN"]
