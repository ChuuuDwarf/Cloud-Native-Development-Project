"""Tests for /api/auth and /api/me."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success_sets_cookie(client: AsyncClient) -> None:
    response = await client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "Admin1234"},
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["email"] == "admin@example.com"
    assert body["role"] == "system_admin"
    assert "*" in body["permissions"]
    # cookie set in jar
    assert client.cookies.get("access_token")


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient) -> None:
    response = await client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "wrong-pw"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_login_unknown_email(client: AsyncClient) -> None:
    response = await client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "Whatever1"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_without_cookie_is_401(client: AsyncClient) -> None:
    response = await client.get("/api/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_cookie_returns_user(admin_client: AsyncClient) -> None:
    response = await admin_client.get("/api/me")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["email"] == "admin@example.com"
    assert body["role"] == "system_admin"
    assert "*" in body["permissions"]


@pytest.mark.asyncio
async def test_logout_clears_cookie(admin_client: AsyncClient) -> None:
    response = await admin_client.post("/api/auth/logout")
    assert response.status_code == 200
    # cookie cleared from response (jar may still have an empty value)
    after_me = await admin_client.get("/api/me")
    assert after_me.status_code == 401


@pytest.mark.asyncio
async def test_plant_user_permissions_are_scoped(plant_user_client: AsyncClient) -> None:
    """廠區使用者 should not have system_admin's wildcard."""
    me = (await plant_user_client.get("/api/me")).json()["data"]
    assert me["role"] == "plant_user"
    assert "*" not in me["permissions"]
    assert "orders:create" in me["permissions"]
    assert "users:create" not in me["permissions"]
