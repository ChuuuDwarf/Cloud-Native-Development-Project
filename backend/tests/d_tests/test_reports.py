"""Endpoint-level (integration) tests for /api/reports. Owned by 組員 D.

================================================================================
Structure mirrors the canonical templates ``tests/c_tests/test_machines.py`` and
``tests/a_tests/test_orders.py`` (see those for the shared conventions).

CONTRACT FACTS verified against the source AND a live run (load-bearing):

  * ENVELOPES ARE THE PROJECT-STANDARD shape (shared ApiResponse / PageResponse):
        list      GET ""             -> {"items": [...], "page", "pageSize", "total"}
        templates GET /templates     -> {"items": [...], "page", "pageSize", "total"}
        get       GET /{report_id}   -> {"data": <report dict>, "message": null}
        create/edit/submit/review/publish/save-template -> {"data": ..., "message": <zh>}
    ERROR envelope is the standard nested ``{"error": {"code", "message", "details"}}``.

  * REPORT STATUS IS STORED AS A CHINESE DISPLAY STRING (REPORT_ZH in
    app/common/enums/role_d_zh.py), NOT the canonical English enum value the rest
    of the system uses:
        draft 草稿 -> pending_review 待審核 -> confirmed 已確認 -> returned 已回傳
        (review-reject -> revised 已改版).
    So the serialized ``status`` field carries Chinese — we assert on the Chinese
    strings the API actually returns.

  * AUTH / PERMISSIONS (verified against each route's ``Depends``):
        GET "" , GET /templates , GET /{report_id}   -> get_current_user
        POST /templates , POST "" , PATCH /{id} ,
            POST /{id}/submit , POST /{id}/publish    -> "reports:operate"
        POST /{id}/review                             -> "reports:review"
    ROLE MAP (scripts/seed_dev.py): ``reports:operate`` is a LAB_ENGINEER perm;
    ``reports:review`` is a SUPERVISOR-ONLY extra (lab_engineer lacks it). So:
        engineer_a_client    -> operate (create/edit/submit/publish), NOT review.
        supervisor_a_client  -> operate AND review.
        plant_user_client    -> neither -> 403.
    LAB SCOPE: a report's lab is its source WIP's lab (reports.wip_id == wips.wip_no,
    wips.lab_name = display name). A non-admin who can't access that lab -> 403
    FORBIDDEN on get/edit/submit/review/publish (existence not hidden).

  * STATE MACHINE (ReportService), illegal transition -> ``ConflictError`` -> 409:
        create  : source WIP must be waiting_confirm|completed (else 409)
        edit    : only 草稿|已改版 (else 409)
        submit  : only 草稿|已改版 -> 待審核 (else 409)
        review  : only 待審核 -> 已確認 (approve) | 已改版 (reject) (else 409)
        publish : only 已確認 -> 已回傳 (else 409)
    There is NO 422-from-service path here; the only 422s are FRAMEWORK body
    validation (e.g. missing required ``name`` / ``wipId``).

  * SEED HAS NO WIPs / WipExecution / reports. Each test arranges a WIP (+ exec
    row in waiting_confirm/completed) via ``db_session`` so create_report passes
    the source-state gate, then drives the report machine through the API.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import WipStatus
from app.db.models import Wip, WipExecution

LAB_A_NAME = "材料分析實驗室"
LAB_B_NAME = "電性測試實驗室"
ENGINEER_A_NAME = "李大明"


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _make_source_wip(
    db: AsyncSession,
    *,
    lab_name: str = LAB_A_NAME,
    exec_status: str = WipStatus.WAITING_CONFIRM.value,
    experiment_item: str = "EDX",
    raw_data_url: str | None = "/data/auto.csv",
) -> str:
    """Arrange a WIP + WipExecution in a report-eligible state (waiting_confirm or
    completed), so ``create_report`` clears its source-state gate. Returns wip_no.

    NOTE on ``raw_data_url``: we set it by DEFAULT so the created Report gets a
    ``ReportAttachment`` appended in ``create_report``. That is a WORKAROUND for a
    real bug (pinned separately in ``test_create_report_no_attachment_is_500``):
    ``create_report`` returns ``report_dict(rpt)`` right after ``commit()``, and
    the serializer lazy-accesses ``rpt.attachments`` / ``rpt.versions``. When NO
    attachment was appended (i.e. the source exec row had no ``raw_data_url``),
    the empty ``attachments`` collection is unloaded post-commit and the lazy
    load raises ``MissingGreenlet`` on the async session -> 500. Giving the source
    WIP a ``raw_data_url`` forces an attachment to be appended (so that collection
    is in-memory/loaded), letting the create response serialize. This lets the
    downstream machine tests (which need a real created report) run against the
    other routes, which all eager-load via ``repo.get_report`` and are unaffected.
    """
    wip_no = _uid("WIP")
    order_no = _uid("ORD")
    db.add(
        Wip(
            wip_no=wip_no,
            sample_id=uuid.uuid4(),
            order_no=order_no,
            lab_name=lab_name,
            experiment_item=experiment_item,
            status="running",
            progress=100,
        )
    )
    db.add(
        WipExecution(
            wip_no=wip_no,
            exec_status=exec_status,
            operator=ENGINEER_A_NAME,
            machine_id="SEM-A-001",
            recipe="R1",
            data_verified=True,
            result_note="ok",
            raw_data_url=raw_data_url,
        )
    )
    await db.commit()
    return wip_no


async def _create_report(client: AsyncClient, db: AsyncSession, *, submit: bool = False) -> str:
    """Create a report through the API and return its ``report_id``."""
    wip_no = await _make_source_wip(db)
    res = await client.post("/api/reports", json={"wipId": wip_no, "submit": submit})
    assert res.status_code == 200, res.text
    return res.json()["data"]["reportId"]


# ---------------------------------------------------------------------------
# LIST — GET /api/reports + GET /api/reports/templates
# ---------------------------------------------------------------------------
async def test_list_reports_returns_page_envelope(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    report_id = await _create_report(engineer_a_client, db_session)

    res = await engineer_a_client.get("/api/reports")
    assert res.status_code == 200, res.text
    body = res.json()
    assert set(body.keys()) >= {"items", "page", "pageSize", "total"}
    ids = {row["reportId"] for row in body["items"]}
    assert report_id in ids, "the engineer's own-lab report must be listable"


async def test_list_reports_status_filter(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """``?status=`` filters on the stored Chinese status. A fresh report is 草稿."""
    report_id = await _create_report(engineer_a_client, db_session, submit=False)

    res = await engineer_a_client.get("/api/reports", params={"status": "草稿"})
    assert res.status_code == 200, res.text
    statuses = {row["status"] for row in res.json()["items"]}
    assert statuses <= {"草稿"}, res.text
    assert report_id in {row["reportId"] for row in res.json()["items"]}


async def test_list_reports_is_lab_scoped(
    engineer_a_client: AsyncClient,
    admin_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """A LAB-A engineer must NOT see a LAB-B report; the cross-lab admin must."""
    lab_b_wip = await _make_source_wip(db_session, lab_name=LAB_B_NAME)
    res = await admin_client.post("/api/reports", json={"wipId": lab_b_wip})
    assert res.status_code == 200, res.text
    lab_b_report = res.json()["data"]["reportId"]

    eng_ids = {r["reportId"] for r in (await engineer_a_client.get("/api/reports")).json()["items"]}
    assert lab_b_report not in eng_ids

    admin_ids = {r["reportId"] for r in (await admin_client.get("/api/reports")).json()["items"]}
    assert lab_b_report in admin_ids


async def test_list_templates_returns_page_envelope(
    engineer_a_client: AsyncClient,
) -> None:
    res = await engineer_a_client.get("/api/reports/templates")
    assert res.status_code == 200, res.text
    assert set(res.json().keys()) >= {"items", "page", "pageSize", "total"}


# ---------------------------------------------------------------------------
# GET ONE — GET /api/reports/{report_id}
# ---------------------------------------------------------------------------
async def test_get_report_happy_path(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    report_id = await _create_report(engineer_a_client, db_session)

    res = await engineer_a_client.get(f"/api/reports/{report_id}")
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["reportId"] == report_id
    assert data["status"] == "草稿"
    # versions are eager-loaded; a fresh report has its v1 entry.
    assert isinstance(data["versions"], list) and len(data["versions"]) >= 1


async def test_get_missing_report_is_404(engineer_a_client: AsyncClient) -> None:
    res = await engineer_a_client.get(f"/api/reports/{_uid('NOPE')}")
    assert res.status_code == 404, res.text
    assert res.json()["error"]["code"] == "NOT_FOUND", res.text


# ---------------------------------------------------------------------------
# CREATE — POST /api/reports
# Happy path (draft + create-and-submit) + the source-state 409 + 404 missing WIP.
# ---------------------------------------------------------------------------
async def test_create_report_draft_success(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    wip_no = await _make_source_wip(db_session)
    res = await engineer_a_client.post("/api/reports", json={"wipId": wip_no})
    assert res.status_code == 200, res.text

    data = res.json()["data"]
    assert data["reportId"].startswith("RPT-")
    assert data["status"] == "草稿"
    assert data["wipId"] == wip_no
    assert res.json()["message"]  # 已建立報告草稿


async def test_create_report_with_submit_goes_pending_review(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """``submit: true`` creates AND sends to review in one call -> 待審核."""
    wip_no = await _make_source_wip(db_session)
    res = await engineer_a_client.post("/api/reports", json={"wipId": wip_no, "submit": True})
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "待審核"


@pytest.mark.xfail(
    reason=(
        "KNOWN BUG: ReportService.create_report returns report_dict(rpt) right after "
        "commit(); the serializer lazy-accesses rpt.attachments. When the source WIP's "
        "exec row has NO raw_data_url, no ReportAttachment is appended, so the empty "
        "attachments collection is unloaded after commit and the lazy load raises "
        "MissingGreenlet on the async session -> 500 DATABASE_ERROR. The report IS "
        "persisted (a follow-up GET succeeds via the eager-loaded repo path); only the "
        "create RESPONSE serialization 500s. INTENDED behaviour: create returns 200. "
        "This strict xfail XPASSes the moment create_report eager-loads/refreshes the "
        "relationships (or the serializer stops touching unloaded collections)."
    ),
    strict=True,
)
async def test_create_report_no_attachment_is_500(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Regression anchor for the create-response lazy-load bug. We assert the
    INTENDED 200; today it returns 500, so this xfails (strict)."""
    wip_no = await _make_source_wip(db_session, raw_data_url=None)
    res = await engineer_a_client.post("/api/reports", json={"wipId": wip_no})
    assert res.status_code == 200, res.text


async def test_create_report_wip_not_ready_is_409(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """A WIP still running (not waiting_confirm/completed) can't have a report
    created -> ConflictError -> 409 CONFLICT."""
    wip_no = await _make_source_wip(db_session, exec_status=WipStatus.RUNNING.value)

    res = await engineer_a_client.post("/api/reports", json={"wipId": wip_no})
    assert res.status_code == 409, res.text
    assert res.json()["error"]["code"] == "CONFLICT", res.text


async def test_create_report_missing_wip_is_404(
    engineer_a_client: AsyncClient,
) -> None:
    res = await engineer_a_client.post("/api/reports", json={"wipId": _uid("NOPE")})
    assert res.status_code == 404, res.text
    assert res.json()["error"]["code"] == "NOT_FOUND", res.text


async def test_create_report_missing_wip_id_is_422(
    engineer_a_client: AsyncClient,
) -> None:
    """Omitting required ``wipId`` is a FRAMEWORK 422, normalized to the nested
    envelope (code VALIDATION_ERROR), NOT the raw FastAPI {"detail": [...]}."""
    res = await engineer_a_client.post("/api/reports", json={})
    assert res.status_code == 422, res.text
    body = res.json()
    assert "detail" not in body, res.text
    assert body["error"]["code"] == "VALIDATION_ERROR", res.text


# ---------------------------------------------------------------------------
# EDIT — PATCH /api/reports/{report_id}
# ---------------------------------------------------------------------------
async def test_edit_draft_report_success(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    report_id = await _create_report(engineer_a_client, db_session)

    res = await engineer_a_client.patch(
        f"/api/reports/{report_id}",
        json={"summary": "改寫摘要", "conclusion": "新結論"},
    )
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["summary"] == "改寫摘要"
    assert data["conclusion"] == "新結論"


# ---------------------------------------------------------------------------
# STATE MACHINE — submit -> review(approve) -> publish, the happy chain.
# Two roles: engineer (operate) submits/publishes; supervisor (review) approves.
# ---------------------------------------------------------------------------
async def test_full_report_lifecycle(
    engineer_a_client: AsyncClient,
    supervisor_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    report_id = await _create_report(engineer_a_client, db_session)

    # submit (operate): 草稿 -> 待審核
    res = await engineer_a_client.post(f"/api/reports/{report_id}/submit")
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "待審核"

    # review/approve (review role = supervisor): 待審核 -> 已確認
    res = await supervisor_a_client.post(
        f"/api/reports/{report_id}/review", json={"approve": True, "comment": "OK"}
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "已確認"

    # publish (operate): 已確認 -> 已回傳
    res = await engineer_a_client.post(f"/api/reports/{report_id}/publish")
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "已回傳"


async def test_review_reject_sets_revised(
    engineer_a_client: AsyncClient,
    supervisor_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """A rejected review moves the report to 已改版 (revisable again)."""
    report_id = await _create_report(engineer_a_client, db_session, submit=True)

    res = await supervisor_a_client.post(
        f"/api/reports/{report_id}/review",
        json={"approve": False, "comment": "請補充"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "已改版"


# ---------------------------------------------------------------------------
# ILLEGAL TRANSITIONS — all 409 CONFLICT.
# ---------------------------------------------------------------------------
async def test_submit_already_submitted_is_409(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Submitting a report that's already in 待審核 -> 409 CONFLICT."""
    report_id = await _create_report(engineer_a_client, db_session, submit=True)

    res = await engineer_a_client.post(f"/api/reports/{report_id}/submit")
    assert res.status_code == 409, res.text
    assert res.json()["error"]["code"] == "CONFLICT", res.text


async def test_review_draft_report_is_409(
    engineer_a_client: AsyncClient,
    supervisor_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Reviewing a report still in 草稿 (not 待審核) -> 409 CONFLICT."""
    report_id = await _create_report(engineer_a_client, db_session, submit=False)

    res = await supervisor_a_client.post(f"/api/reports/{report_id}/review", json={"approve": True})
    assert res.status_code == 409, res.text
    assert res.json()["error"]["code"] == "CONFLICT", res.text


async def test_publish_unconfirmed_report_is_409(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Publishing a report that is not yet 已確認 (here still 草稿) -> 409."""
    report_id = await _create_report(engineer_a_client, db_session, submit=False)

    res = await engineer_a_client.post(f"/api/reports/{report_id}/publish")
    assert res.status_code == 409, res.text
    assert res.json()["error"]["code"] == "CONFLICT", res.text


async def test_edit_submitted_report_is_409(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Editing a report once it's in 待審核 (only 草稿/已改版 are editable) -> 409."""
    report_id = await _create_report(engineer_a_client, db_session, submit=True)

    res = await engineer_a_client.patch(f"/api/reports/{report_id}", json={"summary": "x"})
    assert res.status_code == 409, res.text
    assert res.json()["error"]["code"] == "CONFLICT", res.text


# ---------------------------------------------------------------------------
# TEMPLATES — POST /api/reports/templates (operate-gated).
# ---------------------------------------------------------------------------
async def test_save_template_success(engineer_a_client: AsyncClient) -> None:
    name = _uid("TMPL")
    res = await engineer_a_client.post(
        "/api/reports/templates",
        json={"name": name, "summary": "範本摘要", "conclusion": "範本結論"},
    )
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["name"] == name
    assert isinstance(data["id"], int)


async def test_save_template_missing_name_is_422(engineer_a_client: AsyncClient) -> None:
    res = await engineer_a_client.post("/api/reports/templates", json={"summary": "x"})
    assert res.status_code == 422, res.text
    assert res.json()["error"]["code"] == "VALIDATION_ERROR", res.text


# ---------------------------------------------------------------------------
# PERMISSION / AUTH GATING.
# ---------------------------------------------------------------------------
async def test_list_reports_unauthenticated_is_401(client: AsyncClient) -> None:
    res = await client.get("/api/reports")
    assert res.status_code == 401, res.text
    assert res.json()["error"]["code"] == "UNAUTHORIZED", res.text


async def test_create_report_without_operate_permission_is_403(
    plant_user_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """plant_user lacks reports:operate -> 403 FORBIDDEN before any service logic."""
    wip_no = await _make_source_wip(db_session)
    res = await plant_user_client.post("/api/reports", json={"wipId": wip_no})
    assert res.status_code == 403, res.text
    assert res.json()["error"]["code"] == "FORBIDDEN", res.text


async def test_review_without_review_permission_is_403(
    engineer_a_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """A lab_engineer HAS reports:operate but NOT reports:review, so the review
    route rejects with 403 FORBIDDEN — proving the operate/review split."""
    report_id = await _create_report(engineer_a_client, db_session, submit=True)

    res = await engineer_a_client.post(f"/api/reports/{report_id}/review", json={"approve": True})
    assert res.status_code == 403, res.text
    assert res.json()["error"]["code"] == "FORBIDDEN", res.text


async def test_get_cross_lab_report_is_403(
    engineer_a_client: AsyncClient,
    admin_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """A LAB-A engineer reading a LAB-B report: the report exists but is out of
    scope -> 403 FORBIDDEN (existence not hidden behind a 404)."""
    lab_b_wip = await _make_source_wip(db_session, lab_name=LAB_B_NAME)
    lab_b_report = (await admin_client.post("/api/reports", json={"wipId": lab_b_wip})).json()[
        "data"
    ]["reportId"]

    res = await engineer_a_client.get(f"/api/reports/{lab_b_report}")
    assert res.status_code == 403, res.text
    assert res.json()["error"]["code"] == "FORBIDDEN", res.text
