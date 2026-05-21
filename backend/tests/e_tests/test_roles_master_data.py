"""Tests for /api/roles, /api/permissions, /api/master-data."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_roles(admin_client: AsyncClient) -> None:
    response = await admin_client.get("/api/roles")
    assert response.status_code == 200
    body = response.json()
    names = {r["name"] for r in body["items"]}
    assert {"system_admin", "lab_supervisor", "lab_engineer", "plant_user"} <= names


@pytest.mark.asyncio
async def test_list_permissions(admin_client: AsyncClient) -> None:
    response = await admin_client.get("/api/permissions")
    assert response.status_code == 200
    body = response.json()
    codes = {p["code"] for p in body["items"]}
    assert "users:create" in codes
    assert "orders:approve" in codes
    assert "*" in codes


@pytest.mark.asyncio
async def test_master_data_includes_enums_and_db_lookups(admin_client: AsyncClient) -> None:
    response = await admin_client.get("/api/master-data")
    assert response.status_code == 200
    data = response.json()["data"]

    # Enum bundles
    assert "draft" in data["orderStatuses"]
    assert "running" in data["wipStatuses"]
    assert "idle" in data["machineStatuses"]

    # DB-backed lookups
    assert len(data["roles"]) >= 4
    assert len(data["labs"]) >= 3
    assert len(data["departments"]) >= 3
    assert "SEM" in data["experimentItems"] or len(data["experimentItems"]) > 0


@pytest.mark.asyncio
async def test_master_data_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/master-data")
    assert response.status_code == 401
