"""Direct unit tests for ``MasterDataService.gather()``.

Hits the service in-process (bypassing the HTTP layer) so coverage can attribute
the gather() body to this test file — pytest-asyncio's per-test event loops can
otherwise lose attribution for code reached via the ASGI transport.
"""

from __future__ import annotations

import pytest

from app.core import database as db_module
from app.modules.master_data.service import MasterDataService


@pytest.mark.asyncio
async def test_gather_returns_enums_and_db_collections() -> None:
    async with db_module.AsyncSessionLocal() as session:
        service = MasterDataService(session)
        payload = await service.gather()

    # Enum bundles
    assert "draft" in payload["orderStatuses"]
    assert "running" in payload["wipStatuses"]
    assert "idle" in payload["machineStatuses"]
    assert "open" in payload["issueStatuses"]
    assert "low" in payload["severities"]

    # DB-backed lookups carry expected seed rows
    assert any(r["name"] == "system_admin" for r in payload["roles"])
    role_with_wildcard = next(r for r in payload["roles"] if r["name"] == "system_admin")
    assert "*" in role_with_wildcard["permissions"]

    lab_codes = {lab["code"] for lab in payload["labs"]}
    assert {"LAB-A", "LAB-B", "LAB-C"} <= lab_codes

    dept_codes = {d["code"] for d in payload["departments"]}
    assert {"DEPT-RD", "DEPT-MFG", "DEPT-QA"} <= dept_codes

    storage_codes = {s["code"] for s in payload["storageLocations"]}
    assert "STG-A1" in storage_codes

    # experimentItems should be a flat, sorted, unique list
    items = payload["experimentItems"]
    assert items == sorted(set(items))
    assert "SEM" in items
