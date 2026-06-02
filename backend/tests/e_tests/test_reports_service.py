from __future__ import annotations

import uuid
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.common.dependencies.lab_scope import LabScope
from app.common.enums import OrderStatus, ReportStatus, WipStatus
from app.common.enums.role_d_zh import REPORT_ZH
from app.common.errors import ConflictError, ForbiddenError, NotFoundError
from app.db.models import Report, ReportTemplate, ReportVersion, Wip, WipExecution
from app.modules.reports.service import ReportService

pytestmark = pytest.mark.asyncio


LAB_SCOPE = LabScope(role="lab_engineer", lab_name="材料分析實驗室", lab_code="LAB-A")
NO_LAB_SCOPE = LabScope(role="lab_engineer", lab_name=None, lab_code=None)


class FakeScalarSession:
    async def scalar(self, _stmt: object) -> str:
        return "LAB-A"


class FakeReportRepo:
    def __init__(self) -> None:
        self.reports: dict[str, Report] = {}
        self.wips: dict[str, Wip] = {}
        self.execs: dict[str, WipExecution] = {}
        self.templates: dict[int, ReportTemplate] = {}
        self.orders: dict[str, SimpleNamespace] = {}
        self.formal_count = 0
        self.added: list[object] = []
        self.commits = 0
        self._session = FakeScalarSession()

    async def get_report(self, report_id: str) -> Report | None:
        return self.reports.get(report_id)

    async def get_wip(self, wip_id: str) -> Wip | None:
        return self.wips.get(wip_id)

    async def get_exec(self, wip_id: str) -> WipExecution | None:
        return self.execs.get(wip_id)

    async def get_template(self, template_id: int | None) -> ReportTemplate | None:
        return self.templates.get(template_id or -1)

    async def list_reports(
        self, status: str | None, order_id: str | None, lab_filter: str | None
    ) -> list[Report]:
        rows = list(self.reports.values())
        if status:
            rows = [r for r in rows if r.status == status]
        if order_id:
            rows = [r for r in rows if r.order_id == order_id]
        if lab_filter:
            rows = [r for r in rows if self.wips[r.wip_id].lab_name == lab_filter]
        return rows

    async def list_templates(self) -> list[ReportTemplate]:
        return list(self.templates.values())

    async def count_formal_reports_for_wip(self, _wip_id: str, _statuses: list[str]) -> int:
        return self.formal_count

    async def count_reports_for_order(self, order_no: str) -> int:
        return len([r for r in self.reports.values() if r.order_id == order_no])

    async def get_order(self, order_no: str) -> SimpleNamespace | None:
        return self.orders.get(order_no)

    async def add(self, obj: object) -> None:
        self.added.append(obj)
        if isinstance(obj, Report):
            self.reports[obj.report_id] = obj
        if isinstance(obj, ReportTemplate):
            obj.id = obj.id or len(self.templates) + 1
            self.templates[obj.id] = obj

    async def commit(self) -> None:
        self.commits += 1


def wip(wip_id: str = "WIP-1", lab_name: str = "材料分析實驗室") -> Wip:
    return Wip(
        id=uuid.uuid4(),
        wip_no=wip_id,
        sample_id=uuid.uuid4(),
        order_no="ORD-2026-001",
        lab_name=lab_name,
        experiment_item="SEM",
        priority="normal",
        status="completed",
        progress=100,
    )


def execution(
    wip_id: str = "WIP-1",
    status: str = WipStatus.COMPLETED.value,
    *,
    experiment_data: dict | None = None,
) -> WipExecution:
    return WipExecution(
        wip_no=wip_id,
        exec_status=status,
        machine_id="SEM-A-001",
        recipe="SEM-v1",
        operator="Alice",
        check_in_at=datetime(2026, 1, 1, 9, 0),
        check_out_at=datetime(2026, 1, 1, 10, 0),
        result_note="結果正常",
        raw_data_url="raw.csv",
        experiment_data=experiment_data,
        data_verified=True,
    )


def report(report_id: str = "RPT-001", status: str = REPORT_ZH[ReportStatus.DRAFT]) -> Report:
    rpt = Report(
        report_id=report_id,
        order_id="ORD-2026-001",
        wip_id="WIP-1",
        title="SEM 報告",
        summary="summary",
        conclusion="conclusion",
        experiment_data={"SEM": {"value": "1"}},
        status=status,
        created_at=datetime(2026, 1, 1),
        created_by="Alice",
    )
    rpt.versions = [
        ReportVersion(version=1, status=status, at=datetime(2026, 1, 1), actor="Alice", note="init")
    ]
    rpt.attachments = []
    return rpt


def template(template_id: int = 1) -> ReportTemplate:
    return ReportTemplate(
        id=template_id,
        name="SEM 範本",
        order_id="ORD-2026-001",
        summary="範本摘要",
        conclusion="範本結論",
        created_by="Lead",
        created_at=datetime(2026, 1, 1),
    )


async def test_list_reports_respects_restricted_scope_and_lab_filter() -> None:
    repo = FakeReportRepo()
    repo.wips = {"WIP-1": wip(), "WIP-2": wip("WIP-2", "電性測試實驗室")}
    repo.reports = {"R1": report("R1"), "R2": report("R2")}
    repo.reports["R2"].wip_id = "WIP-2"

    assert await ReportService(repo, NO_LAB_SCOPE).list_reports() == []
    rows = await ReportService(repo, LAB_SCOPE).list_reports()
    assert [r["reportId"] for r in rows] == ["R1"]


async def test_get_report_missing_and_cross_lab_access_errors() -> None:
    repo = FakeReportRepo()
    svc = ReportService(repo, LAB_SCOPE)

    with pytest.raises(NotFoundError):
        await svc.get_report("missing")

    repo.wips["WIP-1"] = wip(lab_name="電性測試實驗室")
    repo.reports["R1"] = report("R1")
    with pytest.raises(ForbiddenError):
        await svc.get_report("R1")


async def test_create_report_uses_template_fallback_and_advances_order_on_submit() -> None:
    repo = FakeReportRepo()
    repo.wips["WIP-1"] = wip()
    repo.execs["WIP-1"] = execution(experiment_data={"SEM": {"existing": "data"}})
    repo.templates[1] = template()
    repo.orders["ORD-2026-001"] = SimpleNamespace(status=OrderStatus.COMPLETED.value)

    result = await ReportService(repo, LAB_SCOPE).create_report(
        "WIP-1",
        "Alice",
        template_id=1,
        submit=True,
    )

    assert result["summary"] == "範本摘要"
    assert result["conclusion"] == "範本結論"
    assert result["experimentData"] == {"SEM": {"existing": "data"}}
    assert result["status"] == REPORT_ZH[ReportStatus.PENDING_REVIEW]
    assert repo.orders["ORD-2026-001"].status == OrderStatus.WAITING_REPORT_RETURN.value
    assert repo.commits == 1


async def test_create_report_rejects_missing_invalid_cross_lab_and_formal_duplicate() -> None:
    repo = FakeReportRepo()
    svc = ReportService(repo, LAB_SCOPE)

    with pytest.raises(NotFoundError):
        await svc.create_report("missing", "Alice")

    repo.wips["WIP-1"] = wip(lab_name="電性測試實驗室")
    with pytest.raises(ForbiddenError):
        await svc.create_report("WIP-1", "Alice")

    repo.wips["WIP-1"] = wip()
    repo.execs["WIP-1"] = execution(status=WipStatus.RUNNING.value)
    with pytest.raises(ConflictError):
        await svc.create_report("WIP-1", "Alice")

    repo.execs["WIP-1"] = execution()
    repo.formal_count = 1
    with pytest.raises(ConflictError):
        await svc.create_report("WIP-1", "Alice")


async def test_save_template_can_copy_from_existing_report() -> None:
    repo = FakeReportRepo()
    repo.wips["WIP-1"] = wip()
    repo.reports["R1"] = report("R1")

    result = await ReportService(repo, LAB_SCOPE).save_template(
        "Copied",
        "Lead",
        from_report_id="R1",
    )

    assert result["name"] == "Copied"
    assert result["summary"] == "summary"
    assert result["conclusion"] == "conclusion"
    assert repo.commits == 1


async def test_edit_submit_review_and_publish_status_transitions() -> None:
    repo = FakeReportRepo()
    repo.wips["WIP-1"] = wip()
    repo.orders["ORD-2026-001"] = SimpleNamespace(status=OrderStatus.COMPLETED.value)
    repo.reports["R1"] = report("R1")
    svc = ReportService(repo, LAB_SCOPE)

    edited = await svc.edit_report("R1", "new summary", "new conclusion", "file.pdf")
    assert edited["summary"] == "new summary"
    assert edited["attachments"][0]["name"] == "file.pdf"

    submitted = await svc.submit_report("R1", "Alice")
    assert submitted["status"] == REPORT_ZH[ReportStatus.PENDING_REVIEW]
    assert len(repo.reports["R1"].versions) == 2

    rejected = await svc.review_report("R1", False, "補件", "Lead")
    assert rejected["status"] == REPORT_ZH[ReportStatus.REVISED]
    assert "補件" in repo.reports["R1"].versions[-1].note

    repo.reports["R1"].status = REPORT_ZH[ReportStatus.PENDING_REVIEW]
    approved = await svc.review_report("R1", True, None, "Lead")
    assert approved["status"] == REPORT_ZH[ReportStatus.CONFIRMED]

    published = await svc.publish_report("R1", "Lead")
    assert published["status"] == REPORT_ZH[ReportStatus.RETURNED]
    assert repo.commits == 5


async def test_report_actions_reject_wrong_status() -> None:
    repo = FakeReportRepo()
    repo.wips["WIP-1"] = wip()
    repo.reports["R1"] = report("R1", REPORT_ZH[ReportStatus.PUBLISHED])
    svc = ReportService(repo, LAB_SCOPE)

    with pytest.raises(ConflictError):
        await svc.edit_report("R1", "x", None, None)
    with pytest.raises(ConflictError):
        await svc.submit_report("R1", "Alice")
    with pytest.raises(ConflictError):
        await svc.review_report("R1", True, None, "Lead")
    with pytest.raises(ConflictError):
        await svc.publish_report("R1", "Lead")
