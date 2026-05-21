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
