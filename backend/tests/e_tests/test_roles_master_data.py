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


@pytest.mark.asyncio
async def test_master_data_excludes_inactive_labs(admin_client: AsyncClient) -> None:
    """Disable a lab directly in the DB and verify it falls out of the payload."""
    from sqlalchemy import select

    from app.core import database as db_module
    from app.db.models import Lab

    async with db_module.AsyncSessionLocal() as session:
        lab = (await session.execute(select(Lab).where(Lab.code == "LAB-C"))).scalar_one()
        lab.is_active = False
        await session.commit()
        lab_id = str(lab.id)

    try:
        data = (await admin_client.get("/api/master-data")).json()["data"]
        ids = {lab_["id"] for lab_ in data["labs"]}
        assert lab_id not in ids
        codes = {lab_["code"] for lab_ in data["labs"]}
        assert "LAB-C" not in codes
    finally:
        async with db_module.AsyncSessionLocal() as session:
            lab = (await session.execute(select(Lab).where(Lab.code == "LAB-C"))).scalar_one()
            lab.is_active = True
            await session.commit()


@pytest.mark.asyncio
async def test_master_data_excludes_inactive_departments(
    admin_client: AsyncClient,
) -> None:
    from sqlalchemy import select

    from app.core import database as db_module
    from app.db.models import Department

    async with db_module.AsyncSessionLocal() as session:
        dept = (
            await session.execute(select(Department).where(Department.code == "DEPT-QA"))
        ).scalar_one()
        dept.is_active = False
        await session.commit()

    try:
        data = (await admin_client.get("/api/master-data")).json()["data"]
        codes = {d["code"] for d in data["departments"]}
        assert "DEPT-QA" not in codes
    finally:
        async with db_module.AsyncSessionLocal() as session:
            dept = (
                await session.execute(select(Department).where(Department.code == "DEPT-QA"))
            ).scalar_one()
            dept.is_active = True
            await session.commit()


@pytest.mark.asyncio
async def test_master_data_experiment_items_are_deduplicated(
    admin_client: AsyncClient,
) -> None:
    """Two labs sharing the same capability (e.g. SEM) must appear once in
    ``experimentItems``. We add a duplicate capability and assert the response
    still uses ``distinct()``.
    """
    from sqlalchemy import select

    from app.core import database as db_module
    from app.db.models import Lab, LabCapability

    async with db_module.AsyncSessionLocal() as session:
        lab_b = (await session.execute(select(Lab).where(Lab.code == "LAB-B"))).scalar_one()
        # Add SEM (already on LAB-A) to LAB-B to create a true duplicate.
        existing = (
            await session.execute(
                select(LabCapability).where(
                    LabCapability.lab_id == lab_b.id,
                    LabCapability.experiment_item == "SEM",
                )
            )
        ).scalar_one_or_none()
        added_id = None
        if existing is None:
            cap = LabCapability(lab_id=lab_b.id, experiment_item="SEM")
            session.add(cap)
            await session.commit()
            await session.refresh(cap)
            added_id = cap.id

    try:
        data = (await admin_client.get("/api/master-data")).json()["data"]
        items = data["experimentItems"]
        assert items.count("SEM") == 1, items
    finally:
        if added_id is not None:
            async with db_module.AsyncSessionLocal() as session:
                cap = await session.get(LabCapability, added_id)
                if cap is not None:
                    await session.delete(cap)
                    await session.commit()


@pytest.mark.asyncio
async def test_master_data_includes_storage_locations(admin_client: AsyncClient) -> None:
    data = (await admin_client.get("/api/master-data")).json()["data"]
    codes = {s["code"] for s in data["storageLocations"]}
    assert "STG-A1" in codes


@pytest.mark.asyncio
async def test_list_roles_includes_permissions(admin_client: AsyncClient) -> None:
    body = (await admin_client.get("/api/roles")).json()
    sysadmin = next(r for r in body["items"] if r["name"] == "system_admin")
    codes = {p["code"] for p in sysadmin["permissions"]}
    assert "*" in codes


@pytest.mark.asyncio
async def test_unauthenticated_roles_is_401(client: AsyncClient) -> None:
    res = await client.get("/api/roles")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_permissions_is_401(client: AsyncClient) -> None:
    res = await client.get("/api/permissions")
    assert res.status_code == 401
