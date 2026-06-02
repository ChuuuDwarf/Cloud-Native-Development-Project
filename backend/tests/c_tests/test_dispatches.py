"""Endpoint-level (integration) tests for /api/dispatches. Owned by 組員 C.

================================================================================
Structure mirrors the canonical template ``tests/c_tests/test_machines.py`` (see
it for the shared conventions): one test = one behaviour, named
``test_<verb>_<condition>_<expected>``; exercise the real HTTP surface through the
shared httpx ``AsyncClient`` fixtures; assert on BOTH the status code AND the body;
create OWN rows with UNIQUE ids so reruns can't collide with the accumulating
session DB; never assert exact collection counts.

CONTRACT FACTS verified against the source (app/routes/dispatches.py +
app/modules/dispatches/{service,repository,schemas,serializers}.py) AND a live run:

  * ENVELOPES are the PROJECT-STANDARD shared shapes:
        list    GET ""               -> PageResponse {"items", "page", "pageSize", "total"}
        create  POST ""              -> 200 + ApiResponse {"data": <dispatch>, "message"}
        suggest POST /suggest        -> 200 + ApiResponse {"data": [<dispatch>...], "message"}
        replan  POST /replan         -> 200 + ApiResponse {"data": [<dispatch>...], "message"}
        assign  POST /{id}/assign    -> 200 + ApiResponse {"data": <dispatch>, "message"}
    The list router has NO real pagination: pageSize == total == len(items), page == 1.
    ERROR envelope is the standard nested ``{"error": {"code", "message", "details"}}``.

  * AUTH / PERMISSIONS (verified against each route's ``Depends``):
        GET ""                                          -> get_current_user (auth ONLY)
        POST "" , POST /suggest , POST /replan ,
            POST /{id}/assign                           -> require_permission("dispatches:manage")
    READ IS NOT PERMISSION-GATED: ``DISPATCHES_READ = "dispatches:read"`` is declared
    but DEAD CODE (never wired to a Depends), like machines' dead ``machines:read``.

  * ROLE MAP — dispatches:manage is held by LAB_ENGINEER and above (scripts/seed_dev.py
    ``LAB_ENGINEER_PERMS`` line ~129), so this module mirrors MACHINES, NOT recipes:
        engineer_a_client (lab_engineer, LAB-A)  -> CAN manage dispatches.
        supervisor_a_client (lab_supervisor)     -> CAN manage (superset of engineer).
        admin_client (system_admin, cross-lab)   -> CAN manage (wildcard ``*``).
        plant_user_client                        -> NO dispatches perms -> 403.

  * LAB SCOPE: dispatches.lab stores a short CODE (LAB-A), derived on create from the
    source WIP's ``lab_name`` (Chinese display string) via the labs table. A non-admin
    sees only own-lab dispatches; create rejects an out-of-lab WIP with ForbiddenError
    (403); ``_require`` hides a cross-lab dispatch as 404 (existence not leaked).

  * STATE MACHINE (待排程 -> 待派工 -> 待上機), stored verbatim in Chinese
    (service.py STATUS_*):
        create  -> 待排程 (STATUS_PENDING),     and drives source WIP -> waiting_schedule
        suggest -> 待派工 (STATUS_SCHEDULING),  WIP -> scheduled (matches a machine)
        replan  -> 待派工 (re-runs over 待排程 + 待派工)
        assign  -> 待上機 (STATUS_WAITING_LOAD), WIP -> dispatched (strict chain check)
    ILLEGAL assign (dispatch not in 待派工) -> ConflictError -> 409 CONFLICT (NOT 400).
    Invalid strategy on suggest/replan      -> ValidationError -> 422 VALIDATION_ERROR.
    Machine/Recipe item mismatch on assign  -> ValidationError -> 422.
    Missing WIP/dispatch/machine/recipe     -> NotFoundError   -> 404 NOT_FOUND.

  * SEED has NO dispatches / WIPs — both tables start empty. Each test arranges its
    own WIP (and, for assign, a Recipe) via ``db_session`` because the dispatch
    create/assign paths read B's ``wips`` and C's ``recipes`` rows directly. Seeded
    LAB-A machines we assign to: SEM-A-001 (SEM). LAB-B machine: IV-B-001 (IV).
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Recipe, Wip

# NOTE: no ``pytestmark = pytest.mark.asyncio`` — ``asyncio_mode = "auto"`` already
# auto-collects every ``async def test_*`` as an asyncio test.

LAB_A_NAME = "材料分析實驗室"  # labs.name for LAB-A (WIP stores the display name)
LAB_B_NAME = "電性測試實驗室"  # labs.name for LAB-B
LAB_A_MACHINE = "SEM-A-001"  # seeded LAB-A machine, supports SEM
LAB_B_MACHINE = "IV-B-001"  # seeded LAB-B machine, supports IV
ENGINEER_A_NAME = "李大明"

STATUS_PENDING = "待排程"
STATUS_SCHEDULING = "待派工"
STATUS_WAITING_LOAD = "待上機"


def _uid(prefix: str) -> str:
    """A collision-proof id for mutating tests (dispatchId / wipId / recipeId).

    The session DB is seeded once and accumulates every row mutating tests create;
    a uuid4 suffix keeps each created id unique per run so reruns don't entangle
    with rows an earlier run inserted.
    """
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _make_source_wip(
    db: AsyncSession,
    *,
    lab_name: str = LAB_A_NAME,
    status: str = "created",
) -> str:
    """Arrange a B-owned WIP whose lab resolves to ``lab_name``. Returns wip_no.

    ``dispatches.wip_id`` == ``wips.wip_no``. ``create`` derives the dispatch lab
    from this WIP's ``lab_name`` and rejects the create if the caller can't access
    that lab. Status ``created`` keeps the WIP inside the 派工排程 chain so the
    create/suggest/assign WIP-sync steps (which forward-advance the WIP) run.
    """
    wip_no = _uid("WIP")
    db.add(
        Wip(
            wip_no=wip_no,
            sample_id=uuid.uuid4(),
            order_no=_uid("ORD"),
            lab_name=lab_name,
            experiment_item="SEM",
            status=status,
            progress=0,
        )
    )
    await db.commit()
    return wip_no


async def _make_recipe(
    db: AsyncSession,
    *,
    experiment_item: str = "SEM",
    machine_ids: list[str] | None = None,
) -> str:
    """Arrange a Recipe row directly (the recipes manage API is supervisor-only;
    arranging via the session keeps this fixture role-agnostic). Returns recipe_id.

    For an assign to pass the service's matching rules, the recipe's
    ``experiment_item`` must equal the dispatch item AND the target machine must be
    in the recipe's ``machine_ids``."""
    recipe_id = _uid("RCP")
    db.add(
        Recipe(
            recipe_id=recipe_id,
            name="派工配方",
            version="v1",
            experiment_item=experiment_item,
            machine_ids=[LAB_A_MACHINE] if machine_ids is None else machine_ids,
            method="",
            parameters={},
            updated_by=ENGINEER_A_NAME,
        )
    )
    await db.commit()
    return recipe_id


def _create_payload(
    dispatch_id: str,
    wip_id: str,
    *,
    experiment_item: str = "SEM",
    priority: str = "中",
    **overrides: object,
) -> dict[str, object]:
    """A reusable, valid create payload (camelCase to match CreateDispatchPayload)."""
    payload: dict[str, object] = {
        "dispatchId": dispatch_id,
        "wipId": wip_id,
        "orderId": _uid("ORD"),
        "experimentItem": experiment_item,
        "priority": priority,
        "dueAt": "2026-12-31",
    }
    payload.update(overrides)
    return payload


async def _create_dispatch(
    client: AsyncClient,
    db: AsyncSession,
    dispatch_id: str,
    *,
    experiment_item: str = "SEM",
) -> str:
    """Create a 待排程 dispatch through the API (arranging its source WIP). Returns
    the wip_no it's tied to (callers usually only need the dispatch_id they passed)."""
    wip_no = await _make_source_wip(db)
    res = await client.post(
        "/api/dispatches",
        json=_create_payload(dispatch_id, wip_no, experiment_item=experiment_item),
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == STATUS_PENDING
    return wip_no


# ---------------------------------------------------------------------------
# LIST — GET /api/dispatches
# Happy path + the PageResponse envelope (no real pagination: pageSize==total).
# ---------------------------------------------------------------------------
async def test_list_dispatches_returns_page_envelope(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    dispatch_id = _uid("DSP-LIST")
    await _create_dispatch(engineer_a_client, db_session, dispatch_id)

    res = await engineer_a_client.get("/api/dispatches")
    assert res.status_code == 200, res.text

    body = res.json()
    assert set(body.keys()) >= {"items", "page", "pageSize", "total"}
    assert isinstance(body["items"], list)
    assert body["page"] == 1
    assert body["pageSize"] == body["total"] == len(body["items"])
    ids = {row["dispatchId"] for row in body["items"]}
    assert dispatch_id in ids, "the engineer's own-lab dispatch must be listable"
    # Each row uses the camelCase serializer (serializers.dispatch_dict).
    sample = next(d for d in body["items"] if d["dispatchId"] == dispatch_id)
    assert set(sample.keys()) == {
        "dispatchId",
        "wipId",
        "orderId",
        "experimentItem",
        "priority",
        "lab",
        "dueAt",
        "status",
        "suggestedMachineId",
        "assignedMachineId",
        "assignedRecipeId",
        "scheduledStart",
        "scheduledEnd",
        "createdBy",
        "assignedBy",
        "strategy",
        "replanReason",
    }
    assert sample["lab"] == "LAB-A"  # derived from the LAB-A WIP on create


async def test_list_dispatches_is_lab_scoped_for_engineer(
    engineer_a_client: AsyncClient,
    admin_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """A LAB-A engineer must NOT see a LAB-B dispatch; the cross-lab admin must.

    Only the admin can create a LAB-B dispatch here (the LAB-A engineer would be
    403'd by the create lab-gate), so we arrange the LAB-B dispatch via admin and
    confirm the engineer can't see it while the admin can.
    """
    lab_b_wip = await _make_source_wip(db_session, lab_name=LAB_B_NAME)
    lab_b_dispatch = _uid("DSP-LABB")
    created = await admin_client.post(
        "/api/dispatches",
        json=_create_payload(lab_b_dispatch, lab_b_wip, experiment_item="IV"),
    )
    assert created.status_code == 200, created.text
    assert created.json()["data"]["lab"] == "LAB-B"

    eng_ids = {
        d["dispatchId"] for d in (await engineer_a_client.get("/api/dispatches")).json()["items"]
    }
    assert lab_b_dispatch not in eng_ids

    admin_ids = {
        d["dispatchId"] for d in (await admin_client.get("/api/dispatches")).json()["items"]
    }
    assert lab_b_dispatch in admin_ids


# ---------------------------------------------------------------------------
# CREATE — POST /api/dispatches
# Happy path (200 + {data, message}, status 待排程) + duplicate 409 + missing-WIP
# 404 + framework 422 + an out-of-lab WIP 403.
# ---------------------------------------------------------------------------
async def test_create_dispatch_success(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    wip_no = await _make_source_wip(db_session)
    dispatch_id = _uid("DSP-CREATE")
    res = await engineer_a_client.post(
        "/api/dispatches",
        json=_create_payload(dispatch_id, wip_no),
    )
    assert res.status_code == 200, res.text

    body = res.json()
    assert body["message"]  # 派工單已建立
    data = body["data"]
    assert data["dispatchId"] == dispatch_id
    assert data["wipId"] == wip_no
    assert data["status"] == STATUS_PENDING  # new dispatches start 待排程
    assert data["lab"] == "LAB-A"  # derived from the LAB-A WIP
    assert data["createdBy"] == ENGINEER_A_NAME


async def test_create_dispatch_duplicate_id_is_409(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Re-using a dispatch id is a conflict. We create our own row first (unique
    id), then POST it again so the collision is deterministic (seed has none)."""
    dispatch_id = _uid("DSP-DUP")
    await _create_dispatch(engineer_a_client, db_session, dispatch_id)

    # Second create reuses the dispatch_id (a fresh WIP, but the id collides first).
    wip_no = await _make_source_wip(db_session)
    dup = await engineer_a_client.post(
        "/api/dispatches",
        json=_create_payload(dispatch_id, wip_no),
    )
    assert dup.status_code == 409, dup.text
    assert dup.json()["error"]["code"] == "CONFLICT", dup.text


async def test_create_dispatch_missing_wip_is_404(
    engineer_a_client: AsyncClient,
) -> None:
    """A well-formed body whose ``wipId`` isn't a real WIP -> NotFoundError (404)."""
    res = await engineer_a_client.post(
        "/api/dispatches",
        json=_create_payload(_uid("DSP-NOWIP"), _uid("WIP-MISSING")),
    )
    assert res.status_code == 404, res.text
    assert res.json()["error"]["code"] == "NOT_FOUND", res.text


async def test_create_dispatch_missing_required_field_is_422(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Omitting required ``orderId`` is a FRAMEWORK 422, normalized into the nested
    envelope (code VALIDATION_ERROR), NOT the raw FastAPI ``{"detail": [...]}``."""
    wip_no = await _make_source_wip(db_session)
    bad = _create_payload(_uid("DSP-422"), wip_no)
    del bad["orderId"]
    res = await engineer_a_client.post("/api/dispatches", json=bad)
    assert res.status_code == 422, res.text

    body = res.json()
    assert "detail" not in body, res.text
    assert body["error"]["code"] == "VALIDATION_ERROR", res.text
    assert "orderId" in body["error"]["message"], res.text


async def test_create_dispatch_out_of_lab_wip_is_403(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """A LAB-A engineer creating a dispatch for a LAB-B WIP trips the create
    lab-gate (``can_access_lab`` false) -> ForbiddenError (403 FORBIDDEN). This is a
    DOMAIN authorization error raised AFTER the route permission check passed (the
    engineer HAS dispatches:manage) — distinct from the no-permission 403."""
    lab_b_wip = await _make_source_wip(db_session, lab_name=LAB_B_NAME)
    res = await engineer_a_client.post(
        "/api/dispatches",
        json=_create_payload(_uid("DSP-XLAB"), lab_b_wip, experiment_item="IV"),
    )
    assert res.status_code == 403, res.text
    assert res.json()["error"]["code"] == "FORBIDDEN", res.text


# ---------------------------------------------------------------------------
# SUGGEST — POST /api/dispatches/suggest
# Runs the strategy over all 待排程 dispatches: sets a suggested machine + moves
# them to 待派工. Happy path + an invalid-strategy 422.
# ---------------------------------------------------------------------------
async def test_suggest_moves_pending_to_scheduling(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """suggest matches a supporting machine and advances 待排程 -> 待派工.

    Our SEM dispatch should get SEM-A-001 (the seeded LAB-A SEM machine) suggested.
    Other pending dispatches in LAB-A may also be swept up — we assert on OURS only,
    found by dispatchId, never on the collection size.
    """
    dispatch_id = _uid("DSP-SUGGEST")
    await _create_dispatch(engineer_a_client, db_session, dispatch_id, experiment_item="SEM")

    res = await engineer_a_client.post("/api/dispatches/suggest", json={"strategy": "FIFO"})
    assert res.status_code == 200, res.text

    body = res.json()
    assert body["message"]  # 已產生排程建議
    assert isinstance(body["data"], list)
    mine = next((d for d in body["data"] if d["dispatchId"] == dispatch_id), None)
    assert mine is not None, "our pending dispatch must be in the suggestion batch"
    assert mine["status"] == STATUS_SCHEDULING
    assert mine["strategy"] == "FIFO"
    assert mine["suggestedMachineId"] == LAB_A_MACHINE  # SEM-A-001 supports SEM


async def test_suggest_invalid_strategy_is_422(
    engineer_a_client: AsyncClient,
) -> None:
    """An unknown strategy is a domain ValidationError raised by the service
    (``_validate_strategy``) -> nested VALIDATION_ERROR (422). ``strategy`` is a
    free ``str`` in the schema, so the bad value passes Pydantic and the service
    rejects it (NOT a framework 422)."""
    res = await engineer_a_client.post("/api/dispatches/suggest", json={"strategy": "亂猜"})
    assert res.status_code == 422, res.text
    assert res.json()["error"]["code"] == "VALIDATION_ERROR", res.text


# ---------------------------------------------------------------------------
# REPLAN — POST /api/dispatches/replan
# Re-runs suggestion over 待排程 + 待派工 with a new strategy + a reason.
# ---------------------------------------------------------------------------
async def test_replan_records_reason_and_strategy(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """replan re-suggests and records strategy + replanReason on affected rows.

    We create a dispatch, suggest it to 待派工, then replan with a new strategy and
    assert OUR row carries the new strategy + reason and stays in 待派工.
    """
    dispatch_id = _uid("DSP-REPLAN")
    await _create_dispatch(engineer_a_client, db_session, dispatch_id, experiment_item="SEM")
    await engineer_a_client.post("/api/dispatches/suggest", json={"strategy": "FIFO"})

    res = await engineer_a_client.post(
        "/api/dispatches/replan",
        json={"reason": "機台保養", "strategy": "Priority First"},
    )
    assert res.status_code == 200, res.text

    body = res.json()
    assert body["message"]  # 已重新排程
    mine = next((d for d in body["data"] if d["dispatchId"] == dispatch_id), None)
    assert mine is not None, "our 待派工 dispatch must be re-planned"
    assert mine["status"] == STATUS_SCHEDULING
    assert mine["strategy"] == "Priority First"
    assert mine["replanReason"] == "機台保養"


async def test_replan_invalid_strategy_is_422(engineer_a_client: AsyncClient) -> None:
    res = await engineer_a_client.post(
        "/api/dispatches/replan",
        json={"reason": "x", "strategy": "不存在的策略"},
    )
    assert res.status_code == 422, res.text
    assert res.json()["error"]["code"] == "VALIDATION_ERROR", res.text


# ---------------------------------------------------------------------------
# ASSIGN — POST /api/dispatches/{id}/assign  (待派工 -> 待上機)
# Happy path (needs a 待派工 dispatch + a matching machine + a matching recipe) +
# illegal-state 409 + 404 missing dispatch + 422 recipe/item mismatch.
# ---------------------------------------------------------------------------
async def _suggest_dispatch(
    client: AsyncClient, db: AsyncSession, dispatch_id: str, *, experiment_item: str = "SEM"
) -> None:
    """Create a dispatch and run suggest so it lands in 待派工 (assign-ready)."""
    await _create_dispatch(client, db, dispatch_id, experiment_item=experiment_item)
    res = await client.post("/api/dispatches/suggest", json={"strategy": "FIFO"})
    assert res.status_code == 200, res.text


async def test_assign_machine_moves_to_waiting_load(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """assign on a 待派工 dispatch with a supporting machine + a matching recipe
    advances it to 待上機 and records the assignment."""
    dispatch_id = _uid("DSP-ASSIGN")
    await _suggest_dispatch(engineer_a_client, db_session, dispatch_id)
    recipe_id = await _make_recipe(db_session, experiment_item="SEM", machine_ids=[LAB_A_MACHINE])

    res = await engineer_a_client.post(
        f"/api/dispatches/{dispatch_id}/assign",
        json={
            "machineId": LAB_A_MACHINE,
            "recipeId": recipe_id,
            "scheduledStart": "2026-12-01 09:00:00",
            "scheduledEnd": "2026-12-01 12:00:00",
        },
    )
    assert res.status_code == 200, res.text

    data = res.json()["data"]
    assert data["status"] == STATUS_WAITING_LOAD
    assert data["assignedMachineId"] == LAB_A_MACHINE
    assert data["assignedRecipeId"] == recipe_id
    assert data["assignedBy"] == ENGINEER_A_NAME


async def test_assign_on_pending_dispatch_is_409(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Assigning a dispatch still in 待排程 (not yet suggested to 待派工) is an
    illegal state transition -> ConflictError -> 409 CONFLICT (NOT 400). The status
    guard runs in the service BEFORE the machine/recipe lookups."""
    dispatch_id = _uid("DSP-EARLY")
    await _create_dispatch(engineer_a_client, db_session, dispatch_id)  # stays 待排程
    recipe_id = await _make_recipe(db_session, experiment_item="SEM")

    res = await engineer_a_client.post(
        f"/api/dispatches/{dispatch_id}/assign",
        json={
            "machineId": LAB_A_MACHINE,
            "recipeId": recipe_id,
            "scheduledStart": "2026-12-01 09:00:00",
            "scheduledEnd": "2026-12-01 12:00:00",
        },
    )
    assert res.status_code == 409, res.text
    assert res.json()["error"]["code"] == "CONFLICT", res.text


async def test_assign_missing_dispatch_is_404(
    engineer_a_client: AsyncClient,
) -> None:
    res = await engineer_a_client.post(
        f"/api/dispatches/{_uid('DSP-NOPE')}/assign",
        json={
            "machineId": LAB_A_MACHINE,
            "recipeId": _uid("RCP-X"),
            "scheduledStart": "2026-12-01 09:00:00",
            "scheduledEnd": "2026-12-01 12:00:00",
        },
    )
    assert res.status_code == 404, res.text
    assert res.json()["error"]["code"] == "NOT_FOUND", res.text


async def test_assign_recipe_item_mismatch_is_422(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """The machine supports the dispatch item, but the recipe's experiment_item
    differs -> ValidationError (422). Proves the service-layer matching rule
    distinct from the not-found / conflict paths."""
    dispatch_id = _uid("DSP-MISMATCH")
    await _suggest_dispatch(engineer_a_client, db_session, dispatch_id, experiment_item="SEM")
    # Recipe is for a DIFFERENT item (FIB) though bound to the SEM machine.
    recipe_id = await _make_recipe(db_session, experiment_item="FIB", machine_ids=[LAB_A_MACHINE])

    res = await engineer_a_client.post(
        f"/api/dispatches/{dispatch_id}/assign",
        json={
            "machineId": LAB_A_MACHINE,  # supports SEM (the dispatch item)
            "recipeId": recipe_id,  # but recipe is for FIB -> mismatch
            "scheduledStart": "2026-12-01 09:00:00",
            "scheduledEnd": "2026-12-01 12:00:00",
        },
    )
    assert res.status_code == 422, res.text
    assert res.json()["error"]["code"] == "VALIDATION_ERROR", res.text


async def test_assign_unsupported_machine_is_422(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """assign with a same-lab machine that does NOT support the dispatch item ->
    ValidationError (422). FIB-A-002 (LAB-A, supports FIB) can't run a SEM dispatch.
    This guard runs before the recipe lookup."""
    dispatch_id = _uid("DSP-UNSUP")
    await _suggest_dispatch(engineer_a_client, db_session, dispatch_id, experiment_item="SEM")
    recipe_id = await _make_recipe(db_session, experiment_item="SEM")

    res = await engineer_a_client.post(
        f"/api/dispatches/{dispatch_id}/assign",
        json={
            "machineId": "FIB-A-002",  # LAB-A, supports FIB not SEM
            "recipeId": recipe_id,
            "scheduledStart": "2026-12-01 09:00:00",
            "scheduledEnd": "2026-12-01 12:00:00",
        },
    )
    assert res.status_code == 422, res.text
    assert res.json()["error"]["code"] == "VALIDATION_ERROR", res.text


# ---------------------------------------------------------------------------
# PERMISSION / AUTH GATING.
#   * unauthenticated request                  -> 401 UNAUTHORIZED
#   * authenticated plant_user (no perms)      -> 403 FORBIDDEN
# (engineer_a HAS dispatches:manage — proven by every happy-path test above —
#  so this module mirrors machines, NOT recipes.)
# ---------------------------------------------------------------------------
async def test_list_dispatches_unauthenticated_is_401(client: AsyncClient) -> None:
    """Even the un-gated read endpoint requires a logged-in user (get_current_user
    -> UnauthorizedError), so it 401s. The gate is AUTHENTICATION, not the dead
    ``dispatches:read`` permission."""
    res = await client.get("/api/dispatches")
    assert res.status_code == 401, res.text
    assert res.json()["error"]["code"] == "UNAUTHORIZED", res.text


async def test_create_dispatch_unauthenticated_is_401(client: AsyncClient) -> None:
    res = await client.post(
        "/api/dispatches",
        json=_create_payload(_uid("DSP-401"), _uid("WIP-X")),
    )
    assert res.status_code == 401, res.text
    assert res.json()["error"]["code"] == "UNAUTHORIZED", res.text


async def test_plant_user_cannot_manage_dispatch_is_403(
    plant_user_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """plant_user is authenticated but lacks ``dispatches:manage`` -> 403 FORBIDDEN
    before any service logic (require_permission rejects at the route boundary)."""
    wip_no = await _make_source_wip(db_session)
    res = await plant_user_client.post(
        "/api/dispatches",
        json=_create_payload(_uid("DSP-403"), wip_no),
    )
    assert res.status_code == 403, res.text
    assert res.json()["error"]["code"] == "FORBIDDEN", res.text
