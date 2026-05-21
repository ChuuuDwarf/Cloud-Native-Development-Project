"""Tests for /api/users CRUD + permission gating."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_unauthenticated_list_users_is_401(client: AsyncClient) -> None:
    response = await client.get("/api/users")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_can_list_users(admin_client: AsyncClient) -> None:
    response = await admin_client.get("/api/users")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 4
    emails = {row["email"] for row in body["items"]}
    assert "admin@example.com" in emails


@pytest.mark.asyncio
async def test_plant_user_cannot_list_users(plant_user_client: AsyncClient) -> None:
    response = await plant_user_client.get("/api/users")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_admin_can_create_user(admin_client: AsyncClient) -> None:
    payload = {
        "email": "new-user@example.com",
        "name": "New Engineer",
        "password": "TempPass1234",
        "roleIds": [],
    }
    response = await admin_client.post("/api/users", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()["data"]
    assert body["email"] == "new-user@example.com"
    assert body["status"] == "active"


@pytest.mark.asyncio
async def test_admin_cannot_create_duplicate_email(admin_client: AsyncClient) -> None:
    payload = {
        "email": "admin@example.com",
        "name": "Dup",
        "password": "Duplicate1234",
    }
    response = await admin_client.post("/api/users", json=payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


@pytest.mark.asyncio
async def test_admin_can_filter_users_by_keyword(admin_client: AsyncClient) -> None:
    response = await admin_client.get("/api/users", params={"keyword": "supervisor"})
    assert response.status_code == 200
    body = response.json()
    emails = {row["email"] for row in body["items"]}
    assert any("supervisor" in email for email in emails)


@pytest.mark.asyncio
async def test_admin_can_disable_user(admin_client: AsyncClient) -> None:
    # Find the seeded engineer
    listed = (await admin_client.get("/api/users", params={"keyword": "engineer"})).json()
    target = next(u for u in listed["items"] if u["email"] == "engineer@example.com")
    user_id = target["id"]

    response = await admin_client.patch(f"/api/users/{user_id}", json={"status": "disabled"})
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["status"] == "disabled"
    assert body["isActive"] is False

    # Re-enable so other tests aren't impacted
    await admin_client.patch(f"/api/users/{user_id}", json={"status": "active"})


@pytest.mark.asyncio
async def test_admin_patch_empty_body_is_noop(admin_client: AsyncClient) -> None:
    """PATCH with no fields should succeed without mutating the user."""
    listed = (await admin_client.get("/api/users", params={"keyword": "admin"})).json()
    target = next(u for u in listed["items"] if u["email"] == "admin@example.com")
    user_id = target["id"]
    before_name = target["name"]

    response = await admin_client.patch(f"/api/users/{user_id}", json={})
    assert response.status_code == 200
    after = response.json()["data"]
    assert after["name"] == before_name
    assert after["email"] == "admin@example.com"


@pytest.mark.asyncio
async def test_admin_patch_nonexistent_user_is_404(admin_client: AsyncClient) -> None:
    import uuid

    ghost = uuid.uuid4()
    response = await admin_client.patch(f"/api/users/{ghost}", json={"name": "Ghost"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_admin_post_user_with_malformed_role_id(admin_client: AsyncClient) -> None:
    payload = {
        "email": "bad-role-id@example.com",
        "name": "Bad Role IDs",
        "password": "AnotherPass1234",
        "roleIds": ["not-a-uuid"],
    }
    response = await admin_client.post("/api/users", json=payload)
    # FastAPI's body validation surfaces 422 with a Pydantic-style envelope
    # before our service ever runs.
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_admin_get_user_by_id_returns_record(admin_client: AsyncClient) -> None:
    listed = (await admin_client.get("/api/users", params={"keyword": "supervisor"})).json()
    target = next(u for u in listed["items"] if u["email"] == "supervisor@example.com")

    response = await admin_client.get(f"/api/users/{target['id']}")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["email"] == "supervisor@example.com"
    assert any(r["name"] == "lab_supervisor" for r in body["roles"])


@pytest.mark.asyncio
async def test_admin_can_filter_users_by_status(admin_client: AsyncClient) -> None:
    response = await admin_client.get("/api/users", params={"status": "active"})
    assert response.status_code == 200
    body = response.json()
    assert all(u["status"] == "active" for u in body["items"])


@pytest.mark.asyncio
async def test_admin_filter_by_lab_id(admin_client: AsyncClient) -> None:
    """supervisor + engineer both seeded into LAB-A — query by that id and
    assert results match the lab assignment."""
    master = (await admin_client.get("/api/master-data")).json()["data"]
    lab_a = next(lab for lab in master["labs"] if lab["code"] == "LAB-A")

    response = await admin_client.get("/api/users", params={"labId": lab_a["id"]})
    assert response.status_code == 200
    body = response.json()
    emails = {u["email"] for u in body["items"]}
    assert {"supervisor@example.com", "engineer@example.com"} <= emails


@pytest.mark.asyncio
async def test_admin_filter_by_department_id(admin_client: AsyncClient) -> None:
    master = (await admin_client.get("/api/master-data")).json()["data"]
    dept_rd = next(d for d in master["departments"] if d["code"] == "DEPT-RD")

    response = await admin_client.get("/api/users", params={"departmentId": dept_rd["id"]})
    assert response.status_code == 200
    body = response.json()
    emails = {u["email"] for u in body["items"]}
    assert "requester@example.com" in emails


@pytest.mark.asyncio
async def test_admin_filter_by_role_name(admin_client: AsyncClient) -> None:
    response = await admin_client.get("/api/users", params={"role": "lab_supervisor"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert all(any(r["name"] == "lab_supervisor" for r in u["roles"]) for u in body["items"])


@pytest.mark.asyncio
async def test_create_user_short_password_is_422(admin_client: AsyncClient) -> None:
    payload = {
        "email": "short-pw@example.com",
        "name": "Short PW",
        "password": "abc",  # < 8
    }
    response = await admin_client.post("/api/users", json=payload)
    assert response.status_code == 422
