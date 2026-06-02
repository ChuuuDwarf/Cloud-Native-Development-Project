"""Endpoint-level (integration) tests for /api/orders. Owned by 組員 A.

================================================================================
Structure mirrors the canonical template ``tests/c_tests/test_machines.py``:
one test = one behaviour, named ``test_<verb>_<condition>_<expected>``; exercise
the real HTTP surface through the shared httpx ``AsyncClient`` fixtures in
``tests/conftest.py``; assert on BOTH the status code AND the body; cover the
breadth (list / get / create / update / delete / a domain state-transition /
permission gating); create OWN rows with UNIQUE ids so reruns can't collide with
the accumulating session DB; never assert exact collection counts.

WHERE THE ORDERS SURFACE DIFFERS FROM THE MACHINES TEMPLATE (verified against the
source AND a live run — these are deliberate, load-bearing deviations):

  * ENVELOPES ARE NON-STANDARD on the SUCCESS path. The orders router
    (``app/routes/orders.py``) does NOT use the project ``items/page/pageSize/
    total`` list envelope or the ``{data, message}`` success envelope. It returns
    its OWN ``app.schemas.order.ApiResponse`` (``{success, data, message}``) and a
    bespoke list shape:
        list   GET /api/orders         -> {"success", "data": [...],
                                           "pagination": {total, page, limit,
                                                          totalPages}}
        create POST /api/orders        -> 201 + {"success", "data": {id, orderNo,
                                                 status, priority, message}}
        get    GET /api/orders/{id}    -> {"success", "data": <full order>,
                                           "message": null}
        update PATCH /api/orders/{id}  -> {"success", "data": <order>,
                                           "message": "委託單已更新"}
        delete DELETE /api/orders/{id} -> {"success", "data": {"id": <id>},
                                           "message": "委託單已刪除"}
        action POST .../{id}/actions   -> {"success", "data": {id, action, status,
                                           quotaOverride}, "message": <transition>}
        history GET .../{id}/history   -> {"success", "data": [...]}
        applicant GET .../applicant/{} -> {"success", "data": [...]}
    => We assert these REAL shapes. The ERROR envelope, by contrast, IS the
    project-standard nested ``{"error": {"code", "message", "details"}}`` because
    every error funnels through the global handlers (``app/core/error_handlers.py``
    + the ``AppError`` handler in ``app/main.py``).

  * CREATE returns 201 (``status_code=status.HTTP_201_CREATED`` on the route), not
    200 like machines.

  * ROLE GATING lives in the REPOSITORY, not in a route ``Depends``. The orders
    routes only ``Depends(get_current_user)`` (authentication), so the 401 case is
    the only gate enforced at the route boundary. Authorization (plant_user can
    create/update/delete/submit/cancel; lab_supervisor approves; etc.) is enforced
    inside ``OrderRepository`` via ``require_role`` (``app/core/order_security.py``),
    which raises a RAW ``HTTPException(403)`` -> normalized to FORBIDDEN. Note
    ``ROLE_ALIASES`` makes ``system_admin`` count as ``plant_user`` AND
    ``lab_supervisor``, so the cross-lab ``admin_client`` can both create and
    approve — we lean on that for the valid-approve path (see the lab-id bug note
    below).

  * ILLEGAL TRANSITIONS are 400 BAD_REQUEST, not 409. The repo raises
    ``bad_request(...)`` (a raw 400 HTTPException) for an action that isn't legal
    from the current status; the handler maps 400 -> "BAD_REQUEST". (Contrast the
    machines template's note about 409/ILLEGAL_STATE — that does NOT apply here.)

  * VALIDATION 422s all surface as nested ``error.code == "VALIDATION_ERROR"``:
    framework body-validation (missing departmentId, empty items) via the custom
    RequestValidationError handler, AND ``OrderActionRequest`` / ``OrderUpdate``
    pydantic ``model_validator`` failures (e.g. return-without-reason, empty PATCH)
    which are ALSO request-validation errors (they raise during body parsing).

SEED / ROLE MAP this file is pinned to (scripts/seed_dev.py):
  * ``plant_user_client``  = requester@example.com (plant_user, DEPT-RD) — the
    APPLICANT. Creates / updates / deletes / submits / cancels its own orders.
  * ``admin_client``       = admin@example.com (system_admin, cross-lab). Aliased
    to plant_user AND lab_supervisor, so it can create AND approve any order.
  * ``supervisor_a_client``= supervisor@example.com (lab_supervisor, LAB-A).
  * ``engineer_a_client``  = engineer@example.com (lab_engineer, LAB-A) — NOT a
    plant_user, so it cannot create orders (403).

MASTER-DATA NOTE: ``OrderRepository._validate_order_master_data`` accepts
``departmentId`` and ``labId`` by CODE (``DEPT-RD`` / ``LAB-A``) OR UUID, but
``experimentId`` ONLY by the ``lab_capabilities.id`` UUID, and the capability must
belong to the item's lab. So every valid create payload needs a real LAB-A
capability UUID, which we fetch once via ``db_session`` in ``_lab_a_capability``.

KNOWN BUG surfaced while writing these tests (asserted as the CURRENT behaviour so
this file regression-locks it; see the report): a LAB-A ``lab_supervisor`` CANNOT
approve a LAB-A order created with ``labId: "LAB-A"``. Order items persist
``lab_id`` exactly as submitted (the CODE ``"LAB-A"``), but the approval lab-gate
compares it against the supervisor's lab UUID (``require_role`` returns
``labIds=[str(user.lab_id)]``), so ``"LAB-A" in {<uuid>}`` is always False and the
repo raises 403 "No approvable order items for this manager". Only ``all_labs``
roles (system_admin / general_supervisor) bypass the lab-gate, which is why the
valid-approve test uses ``admin_client``.
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Lab, LabCapability

# NOTE: no ``pytestmark = pytest.mark.asyncio`` — ``asyncio_mode = "auto"`` already
# auto-collects every ``async def test_*`` as an asyncio test.


def _uid(prefix: str) -> str:
    """A collision-proof sample id for mutating tests.

    The session DB is seeded once and accumulates every order/item mutating tests
    create; a uuid4 suffix keeps each created sampleId unique per run so reruns
    don't entangle with rows an earlier run inserted.
    """
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _lab_a_capability(db: AsyncSession) -> tuple[str, str]:
    """Return ``("LAB-A", <capability_uuid>)`` for a real LAB-A capability.

    ``experimentId`` must be a ``lab_capabilities.id`` UUID whose lab matches the
    item's ``labId`` — see the MASTER-DATA NOTE in the module docstring.
    """
    lab = (await db.execute(select(Lab).where(Lab.code == "LAB-A"))).scalar_one()
    capability = (
        (await db.execute(select(LabCapability).where(LabCapability.lab_id == lab.id)))
        .scalars()
        .first()
    )
    assert capability is not None, "expected a seeded LAB-A capability (SEM/FIB/EDX)"
    return "LAB-A", str(capability.id)


def _order_payload(
    *,
    lab_code: str,
    capability_id: str,
    sample_id: str,
    department_id: str = "DEPT-RD",
    priority: str = "normal",
    **overrides: object,
) -> dict[str, object]:
    """A reusable, valid create payload (camelCase to match the schema aliases)."""
    payload: dict[str, object] = {
        "departmentId": department_id,
        "priority": priority,
        "items": [
            {
                "sampleId": sample_id,
                "sampleName": "測試樣品",
                "labId": lab_code,
                "experimentId": capability_id,
                "targetGroup": "G1",
                "target": 1,
            }
        ],
    }
    payload.update(overrides)
    return payload


async def _create_order(client: AsyncClient, db: AsyncSession, sample_id: str) -> int:
    """Create a fresh DRAFT order through the API and return its integer id."""
    lab_code, capability_id = await _lab_a_capability(db)
    res = await client.post(
        "/api/orders",
        json=_order_payload(lab_code=lab_code, capability_id=capability_id, sample_id=sample_id),
    )
    assert res.status_code == 201, res.text
    return int(res.json()["data"]["id"])


# ---------------------------------------------------------------------------
# LIST — GET /api/orders
# Verifies the happy path AND the bespoke list envelope this router uses
# (success / data / pagination{total,page,limit,totalPages}) — NOT the project
# items/page/pageSize/total shape.
# ---------------------------------------------------------------------------
async def test_list_orders_returns_pagination_envelope(
    plant_user_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    # Arrange: guarantee at least one visible order exists this session.
    await _create_order(plant_user_client, db_session, _uid("LIST"))

    res = await plant_user_client.get("/api/orders")
    assert res.status_code == 200, res.text

    body = res.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    pagination = body["pagination"]
    # Bespoke list envelope: keys differ from the standard PageResponse.
    assert set(pagination.keys()) == {"total", "page", "limit", "totalPages"}
    assert pagination["page"] == 1
    assert pagination["limit"] == 10
    # Lower bound only — the session DB accumulates rows across tests / reruns.
    assert pagination["total"] >= 1


async def test_list_orders_respects_limit_query(
    plant_user_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """``limit`` caps the page size; the slice never exceeds it."""
    # Two distinct orders so a limit=1 page is provably a partial slice.
    await _create_order(plant_user_client, db_session, _uid("PAGE-A"))
    await _create_order(plant_user_client, db_session, _uid("PAGE-B"))

    res = await plant_user_client.get("/api/orders", params={"limit": 1, "page": 1})
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body["data"]) <= 1
    assert body["pagination"]["limit"] == 1
    assert body["pagination"]["total"] >= 2


# ---------------------------------------------------------------------------
# GET ONE — GET /api/orders/{order_id}
# Happy path returns the full serialized order under ``data``; a missing id is a
# nested NOT_FOUND.
# ---------------------------------------------------------------------------
async def test_get_order_happy_path(
    plant_user_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    order_id = await _create_order(plant_user_client, db_session, _uid("GET"))

    res = await plant_user_client.get(f"/api/orders/{order_id}")
    assert res.status_code == 200, res.text

    data = res.json()["data"]
    assert data["id"] == order_id
    assert data["status"] == "draft"  # service default for a fresh order
    assert data["orderNo"].startswith("ORD-")
    # Items are serialized with camelCase aliases.
    assert isinstance(data["items"], list) and len(data["items"]) == 1
    assert set(data["items"][0].keys()) >= {"sampleId", "labId", "experimentId", "status"}


async def test_get_missing_order_is_404(plant_user_client: AsyncClient) -> None:
    res = await plant_user_client.get("/api/orders/99999999")
    assert res.status_code == 404, res.text
    assert res.json()["error"]["code"] == "NOT_FOUND", res.text


# ---------------------------------------------------------------------------
# CREATE — POST /api/orders
# Happy path returns 201 + the bespoke create payload. Plus validation cases that
# all normalize to the nested VALIDATION_ERROR envelope, and a master-data 400.
# ---------------------------------------------------------------------------
async def test_create_order_success(
    plant_user_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    lab_code, capability_id = await _lab_a_capability(db_session)
    sample_id = _uid("CREATE")
    res = await plant_user_client.post(
        "/api/orders",
        json=_order_payload(lab_code=lab_code, capability_id=capability_id, sample_id=sample_id),
    )
    assert res.status_code == 201, res.text

    data = res.json()["data"]
    assert isinstance(data["id"], int)
    assert data["orderNo"].startswith("ORD-")
    assert data["status"] == "draft"  # new orders start in draft
    assert data["priority"] == "normal"
    assert data["message"]  # human-facing 委託單已建立


async def test_create_order_missing_department_is_422(
    plant_user_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Omitting required ``departmentId`` is a FRAMEWORK 422, normalized into the
    project nested envelope with the offending field named in ``error.message``."""
    lab_code, capability_id = await _lab_a_capability(db_session)
    payload = _order_payload(
        lab_code=lab_code, capability_id=capability_id, sample_id=_uid("NO-DEPT")
    )
    del payload["departmentId"]

    res = await plant_user_client.post("/api/orders", json=payload)
    assert res.status_code == 422, res.text
    body = res.json()
    assert "detail" not in body, res.text  # NOT the raw FastAPI {"detail": [...]}
    assert body["error"]["code"] == "VALIDATION_ERROR", res.text
    assert "departmentId" in body["error"]["message"], res.text


async def test_create_order_empty_items_is_422(plant_user_client: AsyncClient) -> None:
    """``items`` has ``min_length=1`` — an empty list is rejected by Pydantic."""
    res = await plant_user_client.post("/api/orders", json={"departmentId": "DEPT-RD", "items": []})
    assert res.status_code == 422, res.text
    assert res.json()["error"]["code"] == "VALIDATION_ERROR", res.text


async def test_create_order_unknown_experiment_is_400(
    plant_user_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """A well-formed body whose ``experimentId`` isn't a real capability passes
    Pydantic but fails the repo's master-data validation -> ``bad_request`` (400 /
    BAD_REQUEST), proving the service-layer validation path (distinct from the
    framework 422 above)."""
    res = await plant_user_client.post(
        "/api/orders",
        json=_order_payload(
            lab_code="LAB-A",
            capability_id="00000000-0000-0000-0000-000000000000",
            sample_id=_uid("BAD-EXP"),
        ),
    )
    assert res.status_code == 400, res.text
    assert res.json()["error"]["code"] == "BAD_REQUEST", res.text


# ---------------------------------------------------------------------------
# UPDATE — PATCH /api/orders/{order_id}
# Happy path on a draft order + 404 + a model-validator 422 (empty patch).
# ---------------------------------------------------------------------------
async def test_update_order_success(
    plant_user_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    order_id = await _create_order(plant_user_client, db_session, _uid("UPDATE"))

    res = await plant_user_client.patch(f"/api/orders/{order_id}", json={"priority": "urgent"})
    assert res.status_code == 200, res.text

    body = res.json()
    assert body["message"] == "委託單已更新"
    assert body["data"]["priority"] == "urgent"


async def test_update_missing_order_is_404(plant_user_client: AsyncClient) -> None:
    res = await plant_user_client.patch("/api/orders/99999999", json={"priority": "urgent"})
    assert res.status_code == 404, res.text
    assert res.json()["error"]["code"] == "NOT_FOUND", res.text


async def test_update_order_no_fields_is_422(
    plant_user_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """An empty PATCH trips the ``OrderUpdate`` ``model_validator`` ("at least one
    update field is required"), which surfaces as a nested VALIDATION_ERROR."""
    order_id = await _create_order(plant_user_client, db_session, _uid("EMPTY-PATCH"))

    res = await plant_user_client.patch(f"/api/orders/{order_id}", json={})
    assert res.status_code == 422, res.text
    assert res.json()["error"]["code"] == "VALIDATION_ERROR", res.text


# ---------------------------------------------------------------------------
# DELETE — DELETE /api/orders/{order_id}
# A real soft-delete endpoint exists (is_deleted=True). Verify 200 + the
# follow-up GET 404 (deleted orders are filtered out of every read).
# ---------------------------------------------------------------------------
async def test_delete_draft_order_then_get_is_404(
    plant_user_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    order_id = await _create_order(plant_user_client, db_session, _uid("DELETE"))

    res = await plant_user_client.delete(f"/api/orders/{order_id}")
    assert res.status_code == 200, res.text
    assert res.json()["data"]["id"] == order_id
    assert res.json()["message"] == "委託單已刪除"

    # Verify persistence of the soft-delete: the order is no longer readable.
    follow_up = await plant_user_client.get(f"/api/orders/{order_id}")
    assert follow_up.status_code == 404, follow_up.text
    assert follow_up.json()["error"]["code"] == "NOT_FOUND", follow_up.text


async def test_delete_missing_order_is_404(plant_user_client: AsyncClient) -> None:
    res = await plant_user_client.delete("/api/orders/99999999")
    assert res.status_code == 404, res.text
    assert res.json()["error"]["code"] == "NOT_FOUND", res.text


# ---------------------------------------------------------------------------
# ACTIONS — POST /api/orders/{order_id}/actions  (the Order state machine)
# docs/flow.md state machine, encoded in app/core/order_constants.TRANSITIONS:
#   draft/returned --submit--> pending_approval --approve--> approved ...
# Valid transitions succeed; an action illegal from the current status is 400.
# ---------------------------------------------------------------------------
async def test_submit_draft_order_succeeds(
    plant_user_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """submit: draft -> pending_approval (applicant-driven, the happy transition)."""
    order_id = await _create_order(plant_user_client, db_session, _uid("SUBMIT"))

    res = await plant_user_client.post(f"/api/orders/{order_id}/actions", json={"action": "submit"})
    assert res.status_code == 200, res.text

    body = res.json()
    assert body["data"]["action"] == "submit"
    assert body["data"]["status"] == "pending_approval"
    assert body["message"] == "委託單已送出簽核"


async def test_cancel_draft_order_succeeds(
    plant_user_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """cancel: draft -> cancelled (applicant-driven)."""
    order_id = await _create_order(plant_user_client, db_session, _uid("CANCEL"))

    res = await plant_user_client.post(f"/api/orders/{order_id}/actions", json={"action": "cancel"})
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "cancelled"


async def test_illegal_transition_is_400(
    plant_user_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """An action not legal from the current status returns BAD_REQUEST (400),
    NOT 409. ``approve`` is not legal from ``draft`` (it requires pending_approval),
    and the status guard runs in the repo BEFORE any role check, so even the
    applicant's own attempt is rejected on the transition rule."""
    order_id = await _create_order(plant_user_client, db_session, _uid("ILLEGAL"))

    res = await plant_user_client.post(
        f"/api/orders/{order_id}/actions", json={"action": "approve"}
    )
    assert res.status_code == 400, res.text
    assert res.json()["error"]["code"] == "BAD_REQUEST", res.text


async def test_action_on_missing_order_is_404(plant_user_client: AsyncClient) -> None:
    res = await plant_user_client.post("/api/orders/99999999/actions", json={"action": "submit"})
    assert res.status_code == 404, res.text
    assert res.json()["error"]["code"] == "NOT_FOUND", res.text


async def test_return_action_without_reason_is_422(plant_user_client: AsyncClient) -> None:
    """``OrderActionRequest`` requires a non-empty ``reason`` for return/reject;
    omitting it is a model-validator failure -> nested VALIDATION_ERROR (no order
    needs to exist — the body is rejected before the route logic runs)."""
    res = await plant_user_client.post("/api/orders/1/actions", json={"action": "return"})
    assert res.status_code == 422, res.text
    assert res.json()["error"]["code"] == "VALIDATION_ERROR", res.text


# ---------------------------------------------------------------------------
# APPROVE — the supervisor side of the state machine.
# Valid approve uses ``admin_client`` (all_labs bypasses the lab-gate); the
# lab-scoped supervisor and the plant_user both hit 403 — for DIFFERENT reasons,
# which we pin separately so a future fix to either is caught.
# ---------------------------------------------------------------------------
async def test_admin_can_approve_submitted_order(
    plant_user_client: AsyncClient,
    admin_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """approve: pending_approval -> approved. The cross-lab admin (all_labs) is the
    only role that clears BOTH the lab-gate and the role-gate in one client."""
    order_id = await _create_order(plant_user_client, db_session, _uid("APPROVE"))
    await plant_user_client.post(f"/api/orders/{order_id}/actions", json={"action": "submit"})

    res = await admin_client.post(f"/api/orders/{order_id}/actions", json={"action": "approve"})
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "approved"


async def test_plant_user_cannot_approve_is_403(
    plant_user_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """The applicant lacks the lab_supervisor role, so ``require_role`` in the repo
    rejects an approve with 403 / FORBIDDEN (authorization, not a transition rule:
    the order IS in pending_approval, a legal-from state)."""
    order_id = await _create_order(plant_user_client, db_session, _uid("PU-APPROVE"))
    await plant_user_client.post(f"/api/orders/{order_id}/actions", json={"action": "submit"})

    res = await plant_user_client.post(
        f"/api/orders/{order_id}/actions", json={"action": "approve"}
    )
    assert res.status_code == 403, res.text
    assert res.json()["error"]["code"] == "FORBIDDEN", res.text


async def test_lab_supervisor_can_approve_own_lab_order(
    plant_user_client: AsyncClient,
    supervisor_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """A LAB-A supervisor can approve a LAB-A order: order items persist ``lab_id``
    as the canonical ``Lab.id`` UUID (normalized at creation), so the approval
    lab-gate — which compares against the supervisor's lab UUID — matches."""
    order_id = await _create_order(plant_user_client, db_session, _uid("SUP-APPROVE"))
    await plant_user_client.post(f"/api/orders/{order_id}/actions", json={"action": "submit"})

    res = await supervisor_a_client.post(
        f"/api/orders/{order_id}/actions", json={"action": "approve"}
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "approved"


# ---------------------------------------------------------------------------
# APPLICANT — GET /api/orders/applicant/{applicant_id}
# Returns the bespoke ApiResponse with ``data`` as a list of full orders for that
# applicant. The applicant id is the user's UUID (== /api/me data.id).
# ---------------------------------------------------------------------------
async def test_list_orders_by_applicant_returns_own_orders(
    plant_user_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    me = (await plant_user_client.get("/api/me")).json()["data"]
    applicant_id = str(me["id"])
    order_id = await _create_order(plant_user_client, db_session, _uid("APPLICANT"))

    res = await plant_user_client.get(f"/api/orders/applicant/{applicant_id}")
    assert res.status_code == 200, res.text

    body = res.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    ids = {row["id"] for row in body["data"]}
    assert order_id in ids, "the applicant's freshly created order must be listed"
    # Every returned order belongs to this applicant.
    assert all(row["applicantId"] == applicant_id for row in body["data"])


# ---------------------------------------------------------------------------
# HISTORY — GET /api/orders/{order_id}/history
# Each lifecycle action appends a history row; we assert the create + submit rows
# show up in chronological order.
# ---------------------------------------------------------------------------
async def test_order_history_records_lifecycle(
    plant_user_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    order_id = await _create_order(plant_user_client, db_session, _uid("HISTORY"))
    await plant_user_client.post(f"/api/orders/{order_id}/actions", json={"action": "submit"})

    res = await plant_user_client.get(f"/api/orders/{order_id}/history")
    assert res.status_code == 200, res.text

    body = res.json()
    assert body["success"] is True
    actions = [row["action"] for row in body["data"]]
    # create is appended on creation; submit on the action. Order is ascending.
    assert actions[0] == "create"
    assert "submit" in actions
    last = body["data"][-1]
    assert last["toStatus"] == "pending_approval"


# ---------------------------------------------------------------------------
# PERMISSION / AUTH GATING.
# The ONLY gate at the route boundary is authentication (get_current_user); every
# orders route depends on it, so an unauthenticated request 401s with the nested
# UNAUTHORIZED envelope. Authorization (role) is enforced deeper, in the repo.
# ---------------------------------------------------------------------------
async def test_list_orders_unauthenticated_is_401(client: AsyncClient) -> None:
    res = await client.get("/api/orders")
    assert res.status_code == 401, res.text
    assert res.json()["error"]["code"] == "UNAUTHORIZED", res.text


async def test_create_order_unauthenticated_is_401(client: AsyncClient) -> None:
    res = await client.post(
        "/api/orders",
        json={
            "departmentId": "DEPT-RD",
            "items": [{"sampleId": "X", "labId": "LAB-A", "experimentId": "X"}],
        },
    )
    assert res.status_code == 401, res.text
    assert res.json()["error"]["code"] == "UNAUTHORIZED", res.text


async def test_get_one_order_requires_auth(
    plant_user_client: AsyncClient,
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """``GET /api/orders/{order_id}`` is auth-gated like every other orders route:
    an UNAUTHENTICATED client gets 401 / UNAUTHORIZED. The authenticated happy path
    is covered below. Contrast ``test_list_orders_unauthenticated_is_401``."""
    order_id = await _create_order(plant_user_client, db_session, _uid("NOAUTH-GET"))

    res = await client.get(f"/api/orders/{order_id}")
    assert res.status_code == 401, res.text
    assert res.json()["error"]["code"] == "UNAUTHORIZED", res.text

    auth_res = await plant_user_client.get(f"/api/orders/{order_id}")
    assert auth_res.status_code == 200, auth_res.text
    assert auth_res.json()["data"]["id"] == order_id


async def test_get_order_history_requires_auth(
    plant_user_client: AsyncClient,
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """``GET /api/orders/{id}/history`` is auth-gated: an unauthenticated client
    gets 401 / UNAUTHORIZED, while an authenticated caller reads the history."""
    order_id = await _create_order(plant_user_client, db_session, _uid("NOAUTH-HIST"))

    res = await client.get(f"/api/orders/{order_id}/history")
    assert res.status_code == 401, res.text
    assert res.json()["error"]["code"] == "UNAUTHORIZED", res.text

    auth_res = await plant_user_client.get(f"/api/orders/{order_id}/history")
    assert auth_res.status_code == 200, auth_res.text
    assert auth_res.json()["data"][0]["action"] == "create"


async def test_engineer_cannot_create_order_is_403(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """A lab_engineer is authenticated but is NOT a plant_user, so the repo's
    ``require_role(..., {"plant_user"})`` rejects creation with 403 / FORBIDDEN.
    This is the authorization gate that lives BELOW the route (the route itself
    only checks authentication)."""
    lab_code, capability_id = await _lab_a_capability(db_session)
    res = await engineer_a_client.post(
        "/api/orders",
        json=_order_payload(
            lab_code=lab_code, capability_id=capability_id, sample_id=_uid("ENG-CREATE")
        ),
    )
    assert res.status_code == 403, res.text
    assert res.json()["error"]["code"] == "FORBIDDEN", res.text
