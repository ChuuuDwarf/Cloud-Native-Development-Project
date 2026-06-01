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
    3. Assert on BOTH the HTTP status code AND the response body. EVERY error in
       this app uses ONE nested envelope (the global handlers normalize them):
         success         : { "data": ..., "message": ... }
         list            : { "items": [...], "page", "pageSize", "total" }
         any error       : { "error": { "code": ..., "message": ... } }
    4. Cover the breadth: list / get / create / update / delete-or-deactivate /
       a domain state-transition / permission gating (401 + 403) + lab scope.
    5. Tests share one seeded DB for the whole session and run in file order.
       Mutating tests must create their OWN rows with UNIQUE ids — we suffix
       every created id with a uuid4 via ``_uid()`` so re-running a single test
       after a full session can't 409 against a row an earlier run inserted —
       so they don't clobber the stable seed corpus other tests rely on. Never
       assert exact row counts: the session DB accumulates rows across tests and
       reruns. Assert ``total >= N`` or a known-subset membership instead.

Module facts this file is pinned to (verified against the source AND a live run):
  * Routes (app/routes/machines.py):
        GET   /api/machines              -> ANY authenticated user
        POST  /api/machines              -> requires perm "machines:manage"
        PATCH /api/machines/{id}         -> requires perm "machines:manage"
        PATCH /api/machines/{id}/status  -> requires perm "machines:manage"
    AUTH NOTE — READ IS NOT PERMISSION-GATED. ``GET /api/machines`` depends only
    on ``get_current_user``, so any logged-in user (including the plant_user
    requester, who has NO machines:* perms) can list machines; the result is
    merely lab-scoped, never blocked by a permission. The constant
    ``MACHINES_READ = "machines:read"`` exists in the router but is DEAD CODE —
    it is never passed to ``require_permission`` / any ``Depends``. Do NOT model
    a read-permission gate for this module. If YOUR module truly gates reads,
    assert the 403 — but read the route's ``Depends`` and confirm first.
    NOTE: the module has NO get-one endpoint and NO DELETE endpoint. Where the
    task asks for "get one" / "delete", we adapt (read-via-list, deactivate via
    status="停用") and call it out inline — your module may have real GET/DELETE,
    in which case use them directly.
  * Permissions (scripts/seed_dev.py): "machines:manage" is held by
    lab_engineer and above; the plant_user (requester) does NOT have it -> 403.
  * Lab scoping (app/common/dependencies/lab_scope.py): a non-admin engineer
    can only see / mutate machines in their OWN lab. engineer@example.com is a
    LAB-A lab_engineer (HAS machines:manage); the admin is cross-lab. Cross-lab
    access for a non-admin returns 404 (existence is not leaked), not 403.
  * Seed corpus (scripts/seed_dev.py): 11 distinct machines exist at session
    start — 5 LAB-A / 3 LAB-B / 3 LAB-C. Stable ids referenced below:
    SEM-A-001 (LAB-A) and IV-B-001 (LAB-B).
  * Valid statuses (app/modules/machines/service.py):
        閒置 / 使用中 / 保養中 / 故障中 / 停用   (新建預設「閒置」)
  * ERROR ENVELOPE — there is ONE shape for EVERY error. ``app/main.py`` wires
    a handler for ``AppError`` (the domain exceptions in app/common/errors.py)
    AND calls ``register_exception_handlers(app)`` (app/core/error_handlers.py),
    which registers global handlers for raw ``HTTPException`` /
    ``StarletteHTTPException`` / ``RequestValidationError`` / ``SQLAlchemyError``
    / unhandled ``Exception``. All render the NESTED shape
    ``{"error": {"code": <CODE>, "message": <str>, "details": ...}}``.
      - DOMAIN errors (AppError subclasses) -> nested ``error.code``:
            401 -> UNAUTHORIZED   403 -> FORBIDDEN   404 -> NOT_FOUND
            409 -> CONFLICT       422 -> VALIDATION_ERROR  (service-raised)
      - FRAMEWORK 422 (Pydantic body validation, e.g. a missing required field)
        is handled by the custom RequestValidationError handler, so it ALSO uses
        the nested envelope with ``error.code == "VALIDATION_ERROR"``; the per-
        field errors are summarized into ``error.message``.
    => framework-422 and service-422 now share the SAME nested envelope.
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient

# NOTE: no ``pytestmark = pytest.mark.asyncio`` here — ``asyncio_mode = "auto"``
# (pyproject.toml) already auto-collects every ``async def test_*`` as an
# asyncio test, so the module marker would be pure redundancy.


def _uid(prefix: str) -> str:
    """A collision-proof machine id for mutating tests.

    The session DB is seeded once and accumulates every row mutating tests
    create; re-running a single test after a full session would 409 on a static
    id the earlier run already inserted. A uuid4 suffix makes each created id
    unique per run. (hex[:8] is ample — these ids live only for the session.)
    """
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# A reusable, valid create payload. JSON keys are camelCase to match the
# Pydantic aliases on MachinePayload (machineId / supportedItems / ...).
# Helper instead of a fixture so each test can tweak one field inline.
def _machine_payload(
    machine_id: str,
    *,
    lab: str = "LAB-A",
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
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
    # The seed plants 11 machines (5 LAB-A / 3 LAB-B / 3 LAB-C) and the admin is
    # cross-lab, so all of them are visible. We assert ``>=`` (not ``==``)
    # deliberately: this session DB accumulates rows from every mutating test
    # and every rerun, so an exact count would be flaky. Never assert exact
    # counts here — use a lower bound or known-subset membership instead.
    assert body["total"] >= 11
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
    admin_client: AsyncClient,
) -> None:
    """A non-admin engineer only sees their own lab's machines.

    engineer@example.com is a LAB-A engineer, so LAB-B machines (e.g. IV-B-001)
    must NOT appear. This is the lab-scope guarantee, asserted at the HTTP
    boundary. We prove EXCLUSION concretely — not merely "every row is LAB-A",
    which could be trivially true on an empty set or if IV-B-001 didn't exist —
    by pinning a specific LAB-B id and confirming the admin CAN see it while the
    engineer cannot.
    """
    eng_items = (await engineer_a_client.get("/api/machines")).json()["items"]
    eng_ids = {row["machineId"] for row in eng_items}
    eng_labs = {row["lab"] for row in eng_items}

    # Only LAB-A rows, and a known LAB-B machine is absent for the engineer.
    assert eng_labs == {"LAB-A"}
    assert "IV-B-001" not in eng_ids

    # Control: the same LAB-B machine IS visible to the cross-lab admin, proving
    # IV-B-001 genuinely exists and was actively filtered out for the engineer
    # (so the exclusion above is a real lab-scope effect, not a vacuous truth).
    admin_ids = {
        row["machineId"] for row in (await admin_client.get("/api/machines")).json()["items"]
    }
    assert "IV-B-001" in admin_ids


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
        f"/api/machines/{_uid('EQ-MISSING')}/status",
        json={"status": "閒置"},
    )
    assert res.status_code == 404, res.text
    assert res.json()["error"]["code"] == "NOT_FOUND", res.text


# ---------------------------------------------------------------------------
# CREATE — POST /api/machines
# Happy path returns 200 + { "data": <machine>, "message": ... }.
# Plus a 422 validation case driven by FastAPI body validation.
# ---------------------------------------------------------------------------
async def test_create_machine_success(admin_client: AsyncClient) -> None:
    machine_id = _uid("EQ-CREATE")
    payload = _machine_payload(machine_id)
    res = await admin_client.post("/api/machines", json=payload)
    assert res.status_code == 200, res.text

    body = res.json()
    assert body["message"]  # non-empty success message
    data = body["data"]
    assert data["machineId"] == machine_id
    assert data["lab"] == "LAB-A"
    # status omitted in payload -> service applies the default "閒置".
    assert data["status"] == "閒置"


async def test_engineer_can_manage_own_lab_machine(
    engineer_a_client: AsyncClient,
) -> None:
    """A non-admin lab_engineer CAN create a machine in their own lab.

    Every other mutating-success test here uses the cross-lab ``admin_client``,
    which sails past lab-scope checks. This proves the SCOPED manage path:
    engineer@example.com (a LAB-A engineer holding machines:manage) creates a
    LAB-A machine and it lands in LAB-A — i.e. machines:manage + same-lab is
    sufficient, no admin wildcard required.
    """
    machine_id = _uid("EQ-ENG-A")
    payload = _machine_payload(machine_id, lab="LAB-A")
    res = await engineer_a_client.post("/api/machines", json=payload)

    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["machineId"] == machine_id
    assert data["lab"] == "LAB-A"


async def test_create_machine_duplicate_id_is_409(admin_client: AsyncClient) -> None:
    """Re-using a seeded machine id is a conflict, not a silent overwrite.

    Static id on purpose: this test MUST collide, so it targets the stable
    seeded SEM-A-001 rather than a uuid-suffixed ``_uid()`` id.
    """
    payload = _machine_payload("SEM-A-001")  # already seeded in LAB-A
    res = await admin_client.post("/api/machines", json=payload)
    assert res.status_code == 409, res.text
    assert res.json()["error"]["code"] == "CONFLICT", res.text


async def test_create_machine_missing_required_field_is_422(
    admin_client: AsyncClient,
) -> None:
    """Omitting a required field (name) is rejected by Pydantic before the
    service runs — a FRAMEWORK 422.

    The app wires a custom RequestValidationError handler (registered via
    ``register_exception_handlers`` in ``app/main.py``), so the framework 422 is
    normalized into the project's nested envelope ``{"error": {"code":
    "VALIDATION_ERROR", "message": ...}}`` — the SAME shape the service-raised
    422 uses (contrast the next test). The offending field name is summarized
    into ``error.message``.
    """
    bad = _machine_payload(_uid("EQ-422"))
    del bad["name"]
    res = await admin_client.post("/api/machines", json=bad)
    assert res.status_code == 422, res.text

    body = res.json()
    # The global RequestValidationError handler normalizes body-validation
    # failures into the nested envelope, summarizing the per-field errors into
    # error.message. We verify the envelope and that the missing required field
    # is named in the message.
    assert "detail" not in body, res.text
    assert body["error"]["code"] == "VALIDATION_ERROR", res.text
    assert "name" in body["error"]["message"], res.text


async def test_create_machine_invalid_status_is_422(admin_client: AsyncClient) -> None:
    """An explicit but invalid status is a domain ValidationError raised by the
    service (app/common/errors.py ValidationError -> AppError) — a DIFFERENT
    code path from the framework 422 above.

    Because it's an AppError, ``app/main.py``'s handler renders the project's
    nested envelope with ``error.code == "VALIDATION_ERROR"``. This is the
    handler/shape that diverges from the framework 422 in the previous test.
    """
    payload = _machine_payload(_uid("EQ-BADSTATUS"), status="不存在的狀態")
    res = await admin_client.post("/api/machines", json=payload)
    assert res.status_code == 422, res.text
    assert res.json()["error"]["code"] == "VALIDATION_ERROR", res.text


# ---------------------------------------------------------------------------
# UPDATE — PATCH /api/machines/{id}
# Happy path + 404. We create our own row first so we never mutate the seed.
# ---------------------------------------------------------------------------
async def test_update_machine_success(admin_client: AsyncClient) -> None:
    # Arrange: create a throwaway machine (unique id) to edit.
    machine_id = _uid("EQ-UPDATE")
    await admin_client.post("/api/machines", json=_machine_payload(machine_id))

    # Act: change its name + utilization.
    updated = _machine_payload(machine_id, name="改名後的機台", utilization=77)
    res = await admin_client.patch(f"/api/machines/{machine_id}", json=updated)

    # Assert: 200 + persisted change reflected in the response.
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["name"] == "改名後的機台"
    assert data["utilization"] == 77


async def test_update_missing_machine_is_404(admin_client: AsyncClient) -> None:
    missing = _uid("EQ-NOPE")
    res = await admin_client.patch(
        f"/api/machines/{missing}",
        json=_machine_payload(missing),
    )
    assert res.status_code == 404, res.text
    assert res.json()["error"]["code"] == "NOT_FOUND", res.text


# ---------------------------------------------------------------------------
# DELETE / DEACTIVATE — adapted: the module has no DELETE endpoint.
# The project models "removal" as a soft deactivate: status -> "停用".
# We verify persistence by reading the machine back through the list endpoint.
# Modules WITH a real DELETE should assert 204/200 then a follow-up 404.
# ---------------------------------------------------------------------------
async def test_deactivate_machine_persists(admin_client: AsyncClient) -> None:
    # Arrange: a fresh machine (unique id) in the active default state.
    machine_id = _uid("EQ-DEACT")
    await admin_client.post("/api/machines", json=_machine_payload(machine_id))

    # Act: deactivate via the status transition.
    res = await admin_client.patch(
        f"/api/machines/{machine_id}/status",
        json={"status": "停用"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "停用"

    # Assert (verify via subsequent GET): the change survived the commit.
    listed = (await admin_client.get("/api/machines")).json()["items"]
    deactivated = next(m for m in listed if m["machineId"] == machine_id)
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
    machine_id = _uid("EQ-STATUS")
    await admin_client.post("/api/machines", json=_machine_payload(machine_id))

    res = await admin_client.patch(
        f"/api/machines/{machine_id}/status",
        json={"status": "保養中"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "保養中"


async def test_status_transition_invalid_value_is_422(
    admin_client: AsyncClient,
) -> None:
    machine_id = _uid("EQ-STATUS-BAD")
    await admin_client.post("/api/machines", json=_machine_payload(machine_id))

    # The status body field is a free ``str`` schema-wise, so an out-of-set
    # value passes Pydantic and is rejected by the service -> domain 422 with
    # the nested ``error.code`` envelope (NOT the framework ``{"detail": [...]}``).
    res = await admin_client.patch(
        f"/api/machines/{machine_id}/status",
        json={"status": "亂七八糟"},  # not a member of VALID_STATUSES
    )
    assert res.status_code == 422, res.text
    assert res.json()["error"]["code"] == "VALIDATION_ERROR", res.text


# ---------------------------------------------------------------------------
# PERMISSION GATING — the two cases every protected endpoint needs.
#   * unauthenticated request               -> 401
#   * authenticated but unauthorised role   -> 403 (FORBIDDEN)
# ---------------------------------------------------------------------------
async def test_list_machines_unauthenticated_is_401(client: AsyncClient) -> None:
    """``client`` has no auth cookie -> even the un-gated read endpoint requires
    a logged-in user, so it 401s. The gate here is AUTHENTICATION, not the dead
    ``machines:read`` permission. ``get_current_user`` raises UnauthorizedError
    (an AppError), so the body is the nested envelope with code UNAUTHORIZED —
    verified empirically; we assert that, not just the status."""
    res = await client.get("/api/machines")
    assert res.status_code == 401, res.text
    assert res.json()["error"]["code"] == "UNAUTHORIZED", res.text


async def test_create_machine_unauthenticated_is_401(client: AsyncClient) -> None:
    res = await client.post("/api/machines", json=_machine_payload(_uid("EQ-401")))
    assert res.status_code == 401, res.text
    assert res.json()["error"]["code"] == "UNAUTHORIZED", res.text


async def test_create_machine_without_manage_permission_is_403(
    plant_user_client: AsyncClient,
) -> None:
    """plant_user (requester) is authenticated but lacks ``machines:manage``.
    require_permission() must reject with 403 / FORBIDDEN — not a 401, and
    certainly not a 200. (Note: the SAME plant_user CAN call GET /api/machines,
    because reads are not permission-gated — only this mutation is.)"""
    res = await plant_user_client.post("/api/machines", json=_machine_payload(_uid("EQ-403")))
    assert res.status_code == 403, res.text
    assert res.json()["error"]["code"] == "FORBIDDEN", res.text


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
    assert res.json()["error"]["code"] == "NOT_FOUND", res.text
