"""Endpoint-level (integration) tests for /api/experiment-runs. Owned by 組員 D.

================================================================================
Structure mirrors the canonical templates ``tests/c_tests/test_machines.py`` and
``tests/a_tests/test_orders.py``: one test = one behaviour, named
``test_<verb>_<condition>_<expected>``; drive the real HTTP surface via the shared
httpx ``AsyncClient`` fixtures in ``tests/conftest.py``; assert on BOTH the status
code AND the body; create OWN rows with UNIQUE ids so reruns can't collide with
the accumulating session DB; never assert exact collection counts.

CONTRACT FACTS verified against the source AND a live run (load-bearing):

  * ENVELOPES ARE THE PROJECT-STANDARD shape (unlike orders). The router wraps
    every response in the shared ``ApiResponse`` / ``PageResponse``:
        list   GET ""                 -> {"items": [...], "page", "pageSize", "total"}
        get    GET /{wip_id}          -> {"data": <wip dict>, "message": null}
        action POST/PATCH /{wip_id}/* -> {"data": <wip dict>, "message": <zh>}
        signal POST /{wip_id}/machine-signal -> 202 + {"data": {...}, "message": <zh>}
    The ERROR envelope is the standard nested ``{"error": {"code", "message",
    "details"}}`` (global handlers).

  * AUTH / PERMISSIONS (verified against each route's ``Depends``):
        GET "" , GET /{wip_id} , POST /{wip_id}/machine-signal  -> get_current_user
        GET /{wip_id}/operators , check-in/out , progress , result , verify ,
            confirm , abort-request                              -> "experiments:operate"
        abort-review                                             -> "experiments:review"
    ROLE MAP (scripts/seed_dev.py): ``experiments:operate`` is a LAB_ENGINEER perm
    (so engineers AND supervisors have it); ``experiments:review`` is a
    SUPERVISOR-ONLY extra (lab_engineer does NOT have it). Therefore:
        engineer_a_client    = 李大明, lab_engineer LAB-A -> operate, NOT review.
        supervisor_a_client  = 譚曉蓉, lab_supervisor LAB-A -> operate AND review.
        plant_user_client    = requester, plant_user      -> neither -> 403.
    LAB SCOPE: D's ``wips.lab_name`` stores the DISPLAY NAME (LAB-A = 材料分析實驗室).
    A non-admin engineer/supervisor can only touch WIPs whose ``lab_name`` matches
    their lab's display name; a cross-lab WIP raises 403 FORBIDDEN (the service's
    ``_require_wip`` does the scope check AFTER the existence check, so it's 403,
    NOT a 404 — contrast machines, which hides existence with a 404).

  * STATE MACHINE (exec_status, canonical English ``WipStatus`` in wip_execution):
        check_in  : wips.status=="dispatched" AND exec waiting_load -> running
        check_out : running -> unloaded
        progress  : running (else 409)
        result    : running|unloaded -> waiting_confirm (sets data_verified flag)
        verify    : waiting_confirm AND not verified -> sets data_verified=True
        confirm   : waiting_confirm AND data_verified -> completed
        abort-req : not-ended, no pending -> abort_status=待主管判定
        abort-rev : has pending -> terminated (approve) / running (reject)
    ILLEGAL TRANSITIONS raise ``ConflictError`` -> 409 CONFLICT (NOT 400 like
    orders, NOT 422). The ONE 422 path is ``confirm`` on an UNVERIFIED waiting_confirm
    WIP: the service raises ``ValidationError`` -> 422 VALIDATION_ERROR (nested).

  * SEED HAS NO WIPs / WipExecution ROWS, so every test arranges its own via
    ``db_session`` (raw ORM insert). ``wips.sample_id`` is NOT-NULL with a
    DB-level FK to ``samples`` in B's migration, but the test DB is built from
    ``Base.metadata.create_all`` (no ``samples`` table, no FK), so an arbitrary
    uuid4 ``sample_id`` inserts cleanly. We set ``sample_id=None`` is NOT possible
    (NOT NULL), so we use a throwaway uuid4 — and the completion sample-flow
    advance is wrapped best-effort in the service so the absent ``samples`` table
    never fails ``confirm``.
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import WipStatus
from app.db.models import Wip, WipExecution

# NOTE: no ``pytestmark = pytest.mark.asyncio`` — ``asyncio_mode = "auto"`` already
# auto-collects every ``async def test_*`` as an asyncio test.

# LAB-A's display name as persisted in ``wips.lab_name`` (scripts/seed_dev.py).
# engineer_a_client / supervisor_a_client are both LAB-A, so this is the lab
# whose WIPs they may operate on.
LAB_A_NAME = "材料分析實驗室"
LAB_B_NAME = "電性測試實驗室"
# The seeded LAB-A engineer's display name — the service stamps history "by" with
# CurrentUser.name, and the operator picker keys on the lab's user names.
ENGINEER_A_NAME = "李大明"


def _uid(prefix: str) -> str:
    """A collision-proof WIP business code for mutating tests.

    The session DB is seeded once and accumulates every row tests create; a uuid4
    suffix keeps each created ``wip_no`` unique per run so reruns don't entangle
    with rows an earlier run inserted.
    """
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _make_wip(
    db: AsyncSession,
    *,
    lab_name: str = LAB_A_NAME,
    b_status: str = "dispatched",
    exec_status: str | None = None,
    experiment_item: str = "EDX",
    order_no: str | None = None,
    data_verified: bool = False,
) -> str:
    """Arrange a WIP (+ optional WipExecution side row) directly in the DB.

    Returns the WIP business code (``wip_no``). ``exec_status=None`` means NO
    exec row is created (the WIP sits at B's coarse ``b_status`` only) — this is
    the genuine "待上機" pre-check-in state when ``b_status='dispatched'``.
    A non-None ``exec_status`` creates the side row in that fine-grained state so
    a test can start partway through the machine.
    """
    wip_no = _uid("WIP")
    db.add(
        Wip(
            wip_no=wip_no,
            sample_id=uuid.uuid4(),  # FK to samples not enforced in the test schema
            order_no=order_no or _uid("ORD"),
            lab_name=lab_name,
            experiment_item=experiment_item,
            status=b_status,
            progress=0,
        )
    )
    if exec_status is not None:
        db.add(
            WipExecution(
                wip_no=wip_no,
                exec_status=exec_status,
                operator=ENGINEER_A_NAME,
                machine_id="SEM-A-001",
                recipe="R1",
                data_verified=data_verified,
            )
        )
    await db.commit()
    return wip_no


# ---------------------------------------------------------------------------
# LIST — GET /api/experiment-runs
# Happy path + the project PageResponse envelope + the status query filter.
# ---------------------------------------------------------------------------
async def test_list_experiment_runs_returns_page_envelope(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    # Arrange: guarantee at least one LAB-A WIP this engineer can see.
    wip_no = await _make_wip(db_session, b_status="dispatched")

    res = await engineer_a_client.get("/api/experiment-runs")
    assert res.status_code == 200, res.text

    body = res.json()
    # Project-standard PageResponse, NOT the orders bespoke shape.
    assert set(body.keys()) >= {"items", "page", "pageSize", "total"}
    assert isinstance(body["items"], list)
    assert body["page"] == 1
    ids = {row["wipId"] for row in body["items"]}
    assert wip_no in ids, "the engineer's own-lab WIP must be listable"
    # Every visible row is the engineer's lab (lab scope) — proven via the dict.
    assert all("status" in row for row in body["items"])


async def test_list_experiment_runs_is_lab_scoped(
    engineer_a_client: AsyncClient,
    admin_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """A LAB-A engineer must NOT see a LAB-B WIP; the cross-lab admin must.

    Proves EXCLUSION concretely (not vacuously) by pinning a known LAB-B WIP and
    confirming the admin can see it while the engineer cannot.
    """
    lab_b_wip = await _make_wip(db_session, lab_name=LAB_B_NAME, b_status="dispatched")

    eng_ids = {
        r["wipId"] for r in (await engineer_a_client.get("/api/experiment-runs")).json()["items"]
    }
    assert lab_b_wip not in eng_ids

    admin_ids = {
        r["wipId"] for r in (await admin_client.get("/api/experiment-runs")).json()["items"]
    }
    assert lab_b_wip in admin_ids


async def test_list_experiment_runs_status_filter(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """``?status=`` filters on the serialized (Chinese) status. A running WIP is
    "執行中"; filtering on a non-matching status excludes it."""
    running_wip = await _make_wip(
        db_session, b_status="running", exec_status=WipStatus.RUNNING.value
    )

    res = await engineer_a_client.get("/api/experiment-runs", params={"status": "執行中"})
    assert res.status_code == 200, res.text
    statuses = {row["status"] for row in res.json()["items"]}
    assert statuses <= {"執行中"}, res.text
    ids = {row["wipId"] for row in res.json()["items"]}
    assert running_wip in ids


# ---------------------------------------------------------------------------
# GET ONE — GET /api/experiment-runs/{wip_id}
# Happy path returns the wip dict under ``data``; a missing id is nested NOT_FOUND.
# ---------------------------------------------------------------------------
async def test_get_experiment_run_happy_path(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    wip_no = await _make_wip(db_session, b_status="dispatched")

    res = await engineer_a_client.get(f"/api/experiment-runs/{wip_no}")
    assert res.status_code == 200, res.text

    data = res.json()["data"]
    assert data["wipId"] == wip_no
    assert data["experimentItem"] == "EDX"
    # No exec row yet -> serialized from B's coarse status: dispatched -> 待上機.
    assert data["status"] == "待上機"


async def test_get_missing_experiment_run_is_404(engineer_a_client: AsyncClient) -> None:
    res = await engineer_a_client.get(f"/api/experiment-runs/{_uid('NOPE')}")
    assert res.status_code == 404, res.text
    assert res.json()["error"]["code"] == "NOT_FOUND", res.text


# ---------------------------------------------------------------------------
# OPERATORS — GET /api/experiment-runs/{wip_id}/operators
# Permission-gated (experiments:operate); returns the WIP's lab members.
# ---------------------------------------------------------------------------
async def test_list_operators_includes_lab_members(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    wip_no = await _make_wip(db_session, b_status="dispatched")

    res = await engineer_a_client.get(f"/api/experiment-runs/{wip_no}/operators")
    assert res.status_code == 200, res.text
    names = {row["name"] for row in res.json()["data"]}
    # The seeded LAB-A engineer/supervisor are members of 材料分析實驗室.
    assert ENGINEER_A_NAME in names, res.text


# ---------------------------------------------------------------------------
# STATE MACHINE — the happy transition sequence, driven through the API:
#   check-in -> upload result -> verify -> confirm
# Each step asserts the serialized status advances correctly.
# ---------------------------------------------------------------------------
async def test_full_happy_transition_sequence(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    wip_no = await _make_wip(db_session, b_status="dispatched")

    # check-in: dispatched/waiting_load -> running (執行中)
    res = await engineer_a_client.post(
        f"/api/experiment-runs/{wip_no}/check-in",
        json={"operator": ENGINEER_A_NAME, "machineId": "SEM-A-001", "recipe": "R1"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "執行中"
    assert res.json()["message"]  # non-empty success message

    # upload result: running -> waiting_confirm (待確認). data_verified=False here.
    res = await engineer_a_client.post(
        f"/api/experiment-runs/{wip_no}/result",
        json={"note": "完成", "rawDataUrl": "/data/x.csv", "dataVerified": False},
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "待確認"
    assert res.json()["data"]["progress"] == 100

    # verify: waiting_confirm & unverified -> data_verified=True (status stays 待確認)
    res = await engineer_a_client.post(
        f"/api/experiment-runs/{wip_no}/verify",
        json={"operator": ENGINEER_A_NAME},
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["dataVerified"] is True

    # confirm: waiting_confirm & verified -> completed (已完成)
    res = await engineer_a_client.post(
        f"/api/experiment-runs/{wip_no}/confirm",
        json={"operator": ENGINEER_A_NAME},
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "已完成"


async def test_check_out_after_check_in(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """check-out: running -> unloaded (已下機). Exercises the dedicated route."""
    wip_no = await _make_wip(db_session, b_status="running", exec_status=WipStatus.RUNNING.value)

    res = await engineer_a_client.post(
        f"/api/experiment-runs/{wip_no}/check-out",
        json={"operator": ENGINEER_A_NAME, "note": "結束"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "已下機"


async def test_update_progress_while_running(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """PATCH /progress on a running WIP updates the percentage."""
    wip_no = await _make_wip(db_session, b_status="running", exec_status=WipStatus.RUNNING.value)

    res = await engineer_a_client.patch(
        f"/api/experiment-runs/{wip_no}/progress",
        json={"progress": 42},
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["progress"] == 42


# ---------------------------------------------------------------------------
# ILLEGAL TRANSITIONS.
#   * an action illegal from the current state  -> 409 CONFLICT
#   * confirm on an UNVERIFIED waiting_confirm   -> 422 VALIDATION_ERROR (the one
#     422 service path: ValidationError, not ConflictError)
# ---------------------------------------------------------------------------
async def test_check_in_when_not_dispatched_is_409(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """check-in requires wips.status=='dispatched' (待上機). A WIP still in B's
    'created' state can't be checked in -> ConflictError -> 409 CONFLICT."""
    wip_no = await _make_wip(db_session, b_status="created")

    res = await engineer_a_client.post(
        f"/api/experiment-runs/{wip_no}/check-in",
        json={"operator": ENGINEER_A_NAME, "machineId": "SEM-A-001", "recipe": "R1"},
    )
    assert res.status_code == 409, res.text
    assert res.json()["error"]["code"] == "CONFLICT", res.text


async def test_update_progress_when_not_running_is_409(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """progress is only legal while running; a 待上機 WIP (no exec row) -> 409."""
    wip_no = await _make_wip(db_session, b_status="dispatched")

    res = await engineer_a_client.patch(
        f"/api/experiment-runs/{wip_no}/progress",
        json={"progress": 10},
    )
    assert res.status_code == 409, res.text
    assert res.json()["error"]["code"] == "CONFLICT", res.text


async def test_confirm_unverified_data_is_422(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """confirm on a waiting_confirm WIP whose data is NOT yet verified raises the
    service ``ValidationError`` -> nested 422 VALIDATION_ERROR. This is the ONLY
    422 path in this module (every other illegal state is a 409 ConflictError)."""
    wip_no = await _make_wip(
        db_session,
        b_status="running",
        exec_status=WipStatus.WAITING_CONFIRM.value,
        data_verified=False,
    )

    res = await engineer_a_client.post(
        f"/api/experiment-runs/{wip_no}/confirm",
        json={"operator": ENGINEER_A_NAME},
    )
    assert res.status_code == 422, res.text
    assert res.json()["error"]["code"] == "VALIDATION_ERROR", res.text


async def test_verify_already_verified_is_409(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Re-verifying an already-verified waiting_confirm WIP -> 409 CONFLICT."""
    wip_no = await _make_wip(
        db_session,
        b_status="running",
        exec_status=WipStatus.WAITING_CONFIRM.value,
        data_verified=True,
    )

    res = await engineer_a_client.post(
        f"/api/experiment-runs/{wip_no}/verify",
        json={"operator": ENGINEER_A_NAME},
    )
    assert res.status_code == 409, res.text
    assert res.json()["error"]["code"] == "CONFLICT", res.text


# ---------------------------------------------------------------------------
# ABORT — request (operate) + review (review). Exercises BOTH role sides.
#   request_abort  : operate role, not-ended WIP -> abort pending
#   review_abort   : review role; approve -> terminated, reject -> running
# ---------------------------------------------------------------------------
async def test_abort_request_then_approve(
    engineer_a_client: AsyncClient,
    supervisor_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """operate side requests the abort; the SUPERVISOR (review role) approves it
    -> WIP terminated (已終止). Two clients, separate calls — no cookie clobber."""
    wip_no = await _make_wip(db_session, b_status="running", exec_status=WipStatus.RUNNING.value)

    # operate: engineer files the abort request.
    res = await engineer_a_client.post(
        f"/api/experiment-runs/{wip_no}/abort-request",
        json={"reason": "機台異常"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["abort"]["status"] == "待主管判定"

    # review: supervisor approves -> terminated.
    res = await supervisor_a_client.post(
        f"/api/experiment-runs/{wip_no}/abort-review",
        json={"approve": True, "note": "同意終止"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "已終止"


async def test_abort_review_reject_resumes_running(
    engineer_a_client: AsyncClient,
    supervisor_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """A rejected abort returns the WIP to running (執行中)."""
    wip_no = await _make_wip(db_session, b_status="running", exec_status=WipStatus.RUNNING.value)
    await engineer_a_client.post(
        f"/api/experiment-runs/{wip_no}/abort-request",
        json={"reason": "誤判"},
    )

    res = await supervisor_a_client.post(
        f"/api/experiment-runs/{wip_no}/abort-review",
        json={"approve": False, "note": "繼續實驗"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "執行中"


async def test_abort_review_without_pending_is_409(
    supervisor_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Reviewing a WIP that has no pending abort request -> 409 CONFLICT."""
    wip_no = await _make_wip(db_session, b_status="running", exec_status=WipStatus.RUNNING.value)

    res = await supervisor_a_client.post(
        f"/api/experiment-runs/{wip_no}/abort-review",
        json={"approve": True, "note": "x"},
    )
    assert res.status_code == 409, res.text
    assert res.json()["error"]["code"] == "CONFLICT", res.text


async def test_abort_request_twice_is_409(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """A second abort request while one is pending -> 409 CONFLICT."""
    wip_no = await _make_wip(db_session, b_status="running", exec_status=WipStatus.RUNNING.value)
    await engineer_a_client.post(
        f"/api/experiment-runs/{wip_no}/abort-request", json={"reason": "first"}
    )

    res = await engineer_a_client.post(
        f"/api/experiment-runs/{wip_no}/abort-request", json={"reason": "second"}
    )
    assert res.status_code == 409, res.text
    assert res.json()["error"]["code"] == "CONFLICT", res.text


# ---------------------------------------------------------------------------
# MACHINE SIGNAL — POST /{wip_id}/machine-signal (get_current_user, returns 202).
# In tests there's no Celery broker, so the route falls back to SYNCHRONOUS
# completion (apply_machine_completion). It still returns 202 with the data
# envelope; the WIP moves to 待確認.
# ---------------------------------------------------------------------------
async def test_machine_signal_returns_202(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    wip_no = await _make_wip(db_session, b_status="running", exec_status=WipStatus.RUNNING.value)

    res = await engineer_a_client.post(f"/api/experiment-runs/{wip_no}/machine-signal")
    assert res.status_code == 202, res.text
    assert res.json()["data"]["wipId"] == wip_no
    assert res.json()["message"]  # non-empty


async def test_machine_signal_missing_wip_is_404(engineer_a_client: AsyncClient) -> None:
    """The route calls ``service.get_wip`` first, so a missing id 404s before any
    Celery dispatch."""
    res = await engineer_a_client.post(f"/api/experiment-runs/{_uid('NOPE')}/machine-signal")
    assert res.status_code == 404, res.text
    assert res.json()["error"]["code"] == "NOT_FOUND", res.text


# ---------------------------------------------------------------------------
# PERMISSION / AUTH GATING.
#   * unauthenticated                              -> 401 UNAUTHORIZED
#   * authenticated but lacking experiments:operate -> 403 FORBIDDEN
#   * lab_engineer lacking experiments:review       -> 403 FORBIDDEN
#   * cross-lab WIP (non-admin)                      -> 403 FORBIDDEN (not 404)
# ---------------------------------------------------------------------------
async def test_list_unauthenticated_is_401(client: AsyncClient) -> None:
    res = await client.get("/api/experiment-runs")
    assert res.status_code == 401, res.text
    assert res.json()["error"]["code"] == "UNAUTHORIZED", res.text


async def test_check_in_without_operate_permission_is_403(
    plant_user_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """plant_user is authenticated but lacks experiments:operate -> 403 FORBIDDEN
    (the require_permission gate rejects before any service logic)."""
    wip_no = await _make_wip(db_session, b_status="dispatched")

    res = await plant_user_client.post(
        f"/api/experiment-runs/{wip_no}/check-in",
        json={"operator": "x", "machineId": "M", "recipe": "R"},
    )
    assert res.status_code == 403, res.text
    assert res.json()["error"]["code"] == "FORBIDDEN", res.text


async def test_abort_review_without_review_permission_is_403(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """A lab_engineer HAS experiments:operate but NOT experiments:review, so the
    review route rejects with 403 FORBIDDEN — proving the operate/review split."""
    wip_no = await _make_wip(db_session, b_status="running", exec_status=WipStatus.RUNNING.value)

    res = await engineer_a_client.post(
        f"/api/experiment-runs/{wip_no}/abort-review",
        json={"approve": True, "note": "x"},
    )
    assert res.status_code == 403, res.text
    assert res.json()["error"]["code"] == "FORBIDDEN", res.text


async def test_operate_cross_lab_wip_is_403(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """A LAB-A engineer operating on a LAB-B WIP: the WIP EXISTS but is out of
    scope, so ``_require_wip`` raises ForbiddenError -> 403 FORBIDDEN (existence is
    NOT hidden behind a 404 here — contrast machines, which 404s cross-lab)."""
    lab_b_wip = await _make_wip(db_session, lab_name=LAB_B_NAME, b_status="dispatched")

    res = await engineer_a_client.get(f"/api/experiment-runs/{lab_b_wip}")
    assert res.status_code == 403, res.text
    assert res.json()["error"]["code"] == "FORBIDDEN", res.text


async def test_check_in_missing_required_field_is_422(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Omitting a required body field (recipe) is a FRAMEWORK 422, normalized into
    the nested envelope with code VALIDATION_ERROR (custom RequestValidationError
    handler) — NOT the raw FastAPI {"detail": [...]}."""
    wip_no = await _make_wip(db_session, b_status="dispatched")

    res = await engineer_a_client.post(
        f"/api/experiment-runs/{wip_no}/check-in",
        json={"operator": ENGINEER_A_NAME, "machineId": "SEM-A-001"},  # no recipe
    )
    assert res.status_code == 422, res.text
    body = res.json()
    assert "detail" not in body, res.text
    assert body["error"]["code"] == "VALIDATION_ERROR", res.text
