"""Endpoint-level (integration) tests for /api/machines. Owned by 組員 C.

================================================================================
TEMPLATE NOTICE — read this before copying for your own module
================================================================================
This file doubles as the **canonical pattern** for module-level endpoint tests
in the LIMS backend. A / B / D: copy this file into ``tests/<x>_tests/`` and
swap the machine specifics for your own. The structure is what matters:

    1. One test = one behaviour, named ``test_<verb>_<condition>_<expected>``.
    2. Exercise the real HTTP surface through the shared httpx ``AsyncClient``
       fixtures in ``tests/conftest.py`` — never build your own auth.
    3. Assert on BOTH the HTTP status code AND the response envelope:
         success : { "data": ..., "message": ... }
         list    : { "items": [...], "page", "pageSize", "total" }
         error   : { "error": { "code": ..., "message": ... } }
    4. Cover the breadth: list / get / create / update / delete-or-deactivate /
       a domain state-transition / permission gating (401 + 403).
    5. Tests share one seeded DB for the whole session and run in file order.
       Mutating tests must create their OWN rows (unique ids) so they don't
       clobber the stable seed corpus other tests rely on. See conftest docstring.

Module facts this file is pinned to (verified against the source):
  * Routes (app/routes/machines.py):
        GET   /api/machines              -> any authenticated user (read)
        POST  /api/machines              -> requires perm "machines:manage"
        PATCH /api/machines/{id}         -> requires perm "machines:manage"
        PATCH /api/machines/{id}/status  -> requires perm "machines:manage"
    NOTE: the module has NO get-one endpoint and NO DELETE endpoint. Where the
    task asks for "get one" / "delete", we adapt (read-via-list, deactivate via
    status="停用") and call it out inline — your module may have real GET/DELETE,
    in which case use them directly.
  * Permissions (scripts/seed_dev.py): "machines:manage" is held by
    lab_engineer and above; the plant_user (requester) does NOT have it -> 403.
  * Lab scoping (app/common/dependencies/lab_scope.py): a non-admin engineer
    can only see / mutate machines in their OWN lab. engineer@example.com is in
    LAB-A; the admin is cross-lab. Cross-lab access for a non-admin returns 404
    (existence is not leaked), not 403.
  * Valid statuses (app/modules/machines/service.py):
        閒置 / 使用中 / 保養中 / 故障中 / 停用   (新建預設「閒置」)
  * Error codes (app/common/errors.py): NOT_FOUND=404, VALIDATION_ERROR=422,
    CONFLICT=409, FORBIDDEN=403, UNAUTHORIZED=401.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

# asyncio_mode = "auto" (pyproject.toml) means every ``async def test_*`` is
# auto-collected as an asyncio test — no per-function @pytest.mark.asyncio
# needed. We still set the module marker for explicitness / portability.
pytestmark = pytest.mark.asyncio


# A reusable, valid create payload. JSON keys are camelCase to match the
# Pydantic aliases on MachinePayload (machineId / supportedItems / ...).
# Helper instead of a fixture so each test can tweak one field inline.
def _machine_payload(machine_id: str, *, lab: str = "LAB-A", **overrides) -> dict:
    payload = {
        "machineId": machine_id,
        "name": "測試機台",
        "lab": lab,
        "supportedItems": ["SEM"],
        "owner": "李大明",
        "utilization": 50,
        "lastMaintenance": "2025-01-01",
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# LIST  — GET /api/machines
# Verifies the happy path AND the list envelope shape every C/A/B/D list
# endpoint must honour (items / page / pageSize / total).
# ---------------------------------------------------------------------------
async def test_list_machines_as_admin_returns_paginated_envelope(
    admin_client: AsyncClient,
) -> None:
    res = await admin_client.get("/api/machines")
    assert res.status_code == 200, res.text

    body = res.json()
    # Envelope contract: a PageResponse, not a bare list.
    assert set(body.keys()) >= {"items", "page", "pageSize", "total"}
    assert isinstance(body["items"], list)
    # admin sees all labs -> at least the five seeded machines.
    assert body["total"] >= 5
    # Each row uses the camelCase serializer (serializers.machine_dict).
    sample = body["items"][0]
    assert set(sample.keys()) == {
        "machineId",
        "name",
        "lab",
        "status",
        "supportedItems",
        "utilization",
        "owner",
        "lastMaintenance",
    }


async def test_list_machines_is_lab_scoped_for_engineer(
    engineer_a_client: AsyncClient,
) -> None:
    """A non-admin engineer only sees their own lab's machines.

    engineer@example.com is in LAB-A, so LAB-B machines (e.g. IV-B-001) must NOT
    appear. This is the lab-scope guarantee, asserted at the HTTP boundary.
    """
    res = await engineer_a_client.get("/api/machines")
    assert res.status_code == 200, res.text

    labs = {row["lab"] for row in res.json()["items"]}
    assert labs == {"LAB-A"}


# ---------------------------------------------------------------------------
# GET ONE — adapted: the module has no GET /{id} endpoint.
# We "read one" by listing and selecting. If YOUR module has GET /{id}, call
# it directly instead and assert 200 + { "data": ... }.
# The 404 case is exercised against the status endpoint below (closest proxy
# for "operate on a machine that doesn't exist").
# ---------------------------------------------------------------------------
async def test_get_one_machine_via_list_happy_path(admin_client: AsyncClient) -> None:
    res = await admin_client.get("/api/machines")
    items = res.json()["items"]

    # SEM-A-001 is a stable seeded LAB-A machine (see scripts/seed_dev.py).
    seeded = next((m for m in items if m["machineId"] == "SEM-A-001"), None)
    assert seeded is not None, "expected seeded machine SEM-A-001 to be listable"
    assert seeded["lab"] == "LAB-A"
    assert seeded["status"] in {"閒置", "使用中", "保養中", "故障中", "停用"}


async def test_operate_on_missing_machine_is_404(admin_client: AsyncClient) -> None:
    """Acting on a non-existent id returns 404 with the NOT_FOUND code.

    Uses the status endpoint as the "get one"-style 404 proxy since there is no
    GET /{id}. For modules WITH a GET /{id}, assert this on that route instead.
    """
    res = await admin_client.patch(
        "/api/machines/EQ-DOES-NOT-EXIST/status",
        json={"status": "閒置"},
    )
    assert res.status_code == 404, res.text
    assert res.json()["error"]["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# CREATE — POST /api/machines
# Happy path returns 200 + { "data": <machine>, "message": ... }.
# Plus a 422 validation case driven by FastAPI body validation.
# ---------------------------------------------------------------------------
async def test_create_machine_success(admin_client: AsyncClient) -> None:
    payload = _machine_payload("EQ-TEST-CREATE")
    res = await admin_client.post("/api/machines", json=payload)
    assert res.status_code == 200, res.text

    body = res.json()
    assert body["message"]  # non-empty success message
    data = body["data"]
    assert data["machineId"] == "EQ-TEST-CREATE"
    assert data["lab"] == "LAB-A"
    # status omitted in payload -> service applies the default "閒置".
    assert data["status"] == "閒置"


async def test_create_machine_duplicate_id_is_409(admin_client: AsyncClient) -> None:
    """Re-using a seeded machine id is a conflict, not a silent overwrite."""
    payload = _machine_payload("SEM-A-001")  # already seeded in LAB-A
    res = await admin_client.post("/api/machines", json=payload)
    assert res.status_code == 409, res.text
    assert res.json()["error"]["code"] == "CONFLICT"


async def test_create_machine_missing_required_field_is_422(
    admin_client: AsyncClient,
) -> None:
    """Omitting a required field (name) is rejected by Pydantic before the
    service runs. FastAPI surfaces this as 422 — the standard validation case
    every module's create endpoint should have."""
    bad = _machine_payload("EQ-TEST-422")
    del bad["name"]
    res = await admin_client.post("/api/machines", json=bad)
    assert res.status_code == 422, res.text


async def test_create_machine_invalid_status_is_422(admin_client: AsyncClient) -> None:
    """An explicit but invalid status is a domain ValidationError (422,
    code VALIDATION_ERROR) raised by the service — distinct from the Pydantic
    422 above, and worth covering because the error envelope differs."""
    payload = _machine_payload("EQ-TEST-BADSTATUS", status="不存在的狀態")
    res = await admin_client.post("/api/machines", json=payload)
    assert res.status_code == 422, res.text
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


# ---------------------------------------------------------------------------
# UPDATE — PATCH /api/machines/{id}
# Happy path + 404. We create our own row first so we never mutate the seed.
# ---------------------------------------------------------------------------
async def test_update_machine_success(admin_client: AsyncClient) -> None:
    # Arrange: create a throwaway machine to edit.
    await admin_client.post("/api/machines", json=_machine_payload("EQ-TEST-UPDATE"))

    # Act: change its name + utilization.
    updated = _machine_payload("EQ-TEST-UPDATE", name="改名後的機台", utilization=77)
    res = await admin_client.patch("/api/machines/EQ-TEST-UPDATE", json=updated)

    # Assert: 200 + persisted change reflected in the response.
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["name"] == "改名後的機台"
    assert data["utilization"] == 77


async def test_update_missing_machine_is_404(admin_client: AsyncClient) -> None:
    res = await admin_client.patch(
        "/api/machines/EQ-NOPE",
        json=_machine_payload("EQ-NOPE"),
    )
    assert res.status_code == 404, res.text
    assert res.json()["error"]["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# DELETE / DEACTIVATE — adapted: the module has no DELETE endpoint.
# The project models "removal" as a soft deactivate: status -> "停用".
# We verify persistence by reading the machine back through the list endpoint.
# Modules WITH a real DELETE should assert 204/200 then a follow-up 404.
# ---------------------------------------------------------------------------
async def test_deactivate_machine_persists(admin_client: AsyncClient) -> None:
    # Arrange: a fresh machine in the active default state.
    await admin_client.post("/api/machines", json=_machine_payload("EQ-TEST-DEACT"))

    # Act: deactivate via the status transition.
    res = await admin_client.patch(
        "/api/machines/EQ-TEST-DEACT/status",
        json={"status": "停用"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "停用"

    # Assert (verify via subsequent GET): the change survived the commit.
    listed = (await admin_client.get("/api/machines")).json()["items"]
    deactivated = next(m for m in listed if m["machineId"] == "EQ-TEST-DEACT")
    assert deactivated["status"] == "停用"


# ---------------------------------------------------------------------------
# STATUS TRANSITION — PATCH /api/machines/{id}/status
# Valid transition succeeds; invalid status value returns VALIDATION_ERROR.
# The machines module accepts any value within the enum (no from->to matrix),
# so "invalid" means "not a member of the status enum". If YOUR module has a
# real transition graph (e.g. Order/WIP/Issue in docs/flow.md), add a case for
# an illegal *transition* expecting ILLEGAL_STATE (409) as well.
# ---------------------------------------------------------------------------
async def test_status_transition_valid_succeeds(admin_client: AsyncClient) -> None:
    await admin_client.post("/api/machines", json=_machine_payload("EQ-TEST-STATUS"))

    res = await admin_client.patch(
        "/api/machines/EQ-TEST-STATUS/status",
        json={"status": "保養中"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "保養中"


async def test_status_transition_invalid_value_is_422(
    admin_client: AsyncClient,
) -> None:
    await admin_client.post("/api/machines", json=_machine_payload("EQ-TEST-STATUS-BAD"))

    res = await admin_client.patch(
        "/api/machines/EQ-TEST-STATUS-BAD/status",
        json={"status": "亂七八糟"},  # not a member of VALID_STATUSES
    )
    assert res.status_code == 422, res.text
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


# ---------------------------------------------------------------------------
# PERMISSION GATING — the two cases every protected endpoint needs.
#   * unauthenticated request               -> 401
#   * authenticated but unauthorised role   -> 403 (FORBIDDEN)
# ---------------------------------------------------------------------------
async def test_list_machines_unauthenticated_is_401(client: AsyncClient) -> None:
    """``client`` has no auth cookie -> the read endpoint rejects it."""
    res = await client.get("/api/machines")
    assert res.status_code == 401


async def test_create_machine_unauthenticated_is_401(client: AsyncClient) -> None:
    res = await client.post("/api/machines", json=_machine_payload("EQ-TEST-401"))
    assert res.status_code == 401


async def test_create_machine_without_manage_permission_is_403(
    plant_user_client: AsyncClient,
) -> None:
    """plant_user (requester) is authenticated but lacks ``machines:manage``.
    require_permission() must reject with 403 / FORBIDDEN — not a 401, and
    certainly not a 200."""
    res = await plant_user_client.post("/api/machines", json=_machine_payload("EQ-TEST-403"))
    assert res.status_code == 403, res.text
    assert res.json()["error"]["code"] == "FORBIDDEN"


async def test_engineer_cannot_manage_other_labs_machine(
    engineer_a_client: AsyncClient,
) -> None:
    """Lab-scope enforcement on a mutating route: the LAB-A engineer HAS
    machines:manage, but IV-B-001 lives in LAB-B. Existence is not leaked, so
    the service returns 404 (NOT_FOUND), not 403."""
    res = await engineer_a_client.patch(
        "/api/machines/IV-B-001/status",
        json={"status": "閒置"},
    )
    assert res.status_code == 404, res.text
    assert res.json()["error"]["code"] == "NOT_FOUND"
