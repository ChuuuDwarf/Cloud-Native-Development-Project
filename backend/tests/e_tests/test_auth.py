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


# ---------------------------------------------------------------------------
# Sprint 7 — access + refresh token split.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_sets_both_access_and_refresh_cookies(client: AsyncClient) -> None:
    """Login issues an access cookie AND a refresh cookie."""
    response = await client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "Admin1234"},
    )
    assert response.status_code == 200
    # httpx puts cookies under whatever path the server scoped them to;
    # access is path=/, refresh is path=/api/auth/refresh.
    assert client.cookies.get("access_token", path="/") is not None
    assert client.cookies.get("refresh_token", path="/api/auth/refresh") is not None


@pytest.mark.asyncio
async def test_refresh_without_cookie_is_401(client: AsyncClient) -> None:
    """No refresh cookie = nothing to rotate."""
    response = await client.post("/api/auth/refresh")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rotates_cookies_and_session_continues(client: AsyncClient) -> None:
    """A valid refresh issues a new pair and the new access can still hit /me."""
    await client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "Admin1234"},
    )
    original_access = client.cookies.get("access_token", path="/")
    original_refresh = client.cookies.get("refresh_token", path="/api/auth/refresh")
    assert original_access and original_refresh

    refresh = await client.post("/api/auth/refresh")
    assert refresh.status_code == 200

    new_access = client.cookies.get("access_token", path="/")
    new_refresh = client.cookies.get("refresh_token", path="/api/auth/refresh")
    assert new_access and new_refresh
    # Both rotated — not the same string as before.
    assert new_access != original_access
    assert new_refresh != original_refresh

    me = await client.get("/api/me")
    assert me.status_code == 200


@pytest.mark.asyncio
async def test_refresh_rejects_access_token_in_refresh_slot(client: AsyncClient) -> None:
    """Token-type confusion attack: present an access token as if it were a
    refresh. The wrong-type check at the refresh endpoint must 401 it."""
    await client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "Admin1234"},
    )
    access = client.cookies.get("access_token", path="/")
    assert access
    # Replace the refresh cookie with the access token value.
    client.cookies.set("refresh_token", access, path="/api/auth/refresh")

    response = await client.post("/api/auth/refresh")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_rejects_refresh_token_in_access_slot(client: AsyncClient) -> None:
    """Inverse of the above: present a refresh token as if it were access.
    get_current_user's wrong-type check must 401."""
    await client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "Admin1234"},
    )
    refresh = client.cookies.get("refresh_token", path="/api/auth/refresh")
    assert refresh
    # Swap the access cookie for the refresh token.
    client.cookies.set("access_token", refresh, path="/")

    response = await client.get("/api/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_clears_refresh_too(client: AsyncClient) -> None:
    """After logout, the refresh cookie is gone — refresh endpoint 401s."""
    await client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "Admin1234"},
    )
    await client.post("/api/auth/logout")
    # delete_cookie on Set-Cookie clears the jar entry.
    response = await client.post("/api/auth/refresh")
    assert response.status_code == 401
