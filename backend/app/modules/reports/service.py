"""實驗報告商業邏輯：建立草稿、編輯、送審、審核、發布、版本管理。

Ported from Role D's flat ``app/store/reports.py``, converted from sync to async.
Status values use the canonical English enums from ``app.common.enums``.

Status-value mapping (Role D Chinese → canonical English):
    ReportStatus.DRAFT 草稿       → draft
    ReportStatus.PENDING_REVIEW   → pending_review
    ReportStatus.CONFIRMED 已確認 → confirmed
    ReportStatus.PUBLISHED 已發布 → published
    ReportStatus.RETURNED 已回傳  → returned
    ReportStatus.REVISED 已改版   → revised
"""

from __future__ import annotations

import logging
from datetime import datetime

from app.common.enums import OrderStatus, ReportStatus, WipStatus
from app.common.enums.role_d_zh import ORDER_ZH, REPORT_ZH, WIP_ZH
from app.common.errors import ConflictError, NotFoundError
from app.db.models import Report, ReportAttachment, ReportVersion
from app.modules.reports.repository import ReportRepository
from app.modules.reports.serializers import report_dict

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now()


class ReportService:
    def __init__(self, repo: ReportRepository) -> None:
        self._repo = repo

    async def _require_report(self, report_id: str) -> Report:
        rpt = await self._repo.get_report(report_id)
        if rpt is None:
            raise NotFoundError(f"找不到報告：{report_id}")
        return rpt

    async def list_reports(
        self, status: str | None = None, order_id: str | None = None
    ) -> list[dict]:
        reports = await self._repo.list_reports(status, order_id)
        return [report_dict(r) for r in reports]

    async def get_report(self, report_id: str) -> dict:
        rpt = await self._require_report(report_id)
        return report_dict(rpt)

    async def create_report(self, wip_id: str, by: str) -> dict:
        wip = await self._repo.get_wip(wip_id)
        if wip is None:
            raise NotFoundError(f"找不到 WIP：{wip_id}")
        if wip.status not in (WIP_ZH[WipStatus.WAITING_CONFIRM], WIP_ZH[WipStatus.COMPLETED]):
            raise ConflictError("需待結果確認或已完成的 WIP 才能建立報告")

        # Generate report ID
        count = await self._repo.count_reports_for_order(wip.order_id)
        suffix = wip.order_id.split("-")[-1]
        rid = f"RPT-{suffix}-{count + 1:02d}"

        rpt = Report(
            report_id=rid,
            order_id=wip.order_id,
            wip_id=wip_id,
            title=f"{wip.order_id} {wip.order.experiment_item} 報告",
            summary=f"針對 {wip.sample} 進行 {wip.experiment_item}。",
            conclusion=wip.result_note or "",
            status=REPORT_ZH[ReportStatus.DRAFT],
            created_at=_now(),
            created_by=by,
        )
        rpt.versions.append(
            ReportVersion(
                version=1,
                status=REPORT_ZH[ReportStatus.DRAFT],
                at=_now(),
                actor=by,
                note="自實驗結果建立草稿",
            )
        )
        await self._repo.add(rpt)
        await self._repo.commit()
        return report_dict(rpt)

    async def edit_report(
        self,
        report_id: str,
        summary: str | None,
        conclusion: str | None,
        attachment_name: str | None,
    ) -> dict:
        rpt = await self._require_report(report_id)
        if rpt.status not in (REPORT_ZH[ReportStatus.DRAFT], REPORT_ZH[ReportStatus.REVISED]):
            raise ConflictError(f"報告為「{rpt.status}」，僅草稿或已改版可編輯")
        if summary is not None:
            rpt.summary = summary
        if conclusion is not None:
            rpt.conclusion = conclusion
        if attachment_name:
            rpt.attachments.append(ReportAttachment(name=attachment_name, at=_now()))
        await self._repo.commit()
        return report_dict(rpt)

    async def submit_report(self, report_id: str, by: str) -> dict:
        rpt = await self._require_report(report_id)
        if rpt.status not in (REPORT_ZH[ReportStatus.DRAFT], REPORT_ZH[ReportStatus.REVISED]):
            raise ConflictError(f"報告為「{rpt.status}」，僅草稿或已改版可送審")
        rpt.status = REPORT_ZH[ReportStatus.PENDING_REVIEW]
        self._add_version(rpt, "提交審核", by)
        await self._repo.commit()
        return report_dict(rpt)

    async def review_report(
        self, report_id: str, approve: bool, comment: str | None, by: str
    ) -> dict:
        rpt = await self._require_report(report_id)
        if rpt.status != REPORT_ZH[ReportStatus.PENDING_REVIEW]:
            raise ConflictError(f"報告為「{rpt.status}」，僅待審核可審核")
        rpt.status = (
            REPORT_ZH[ReportStatus.CONFIRMED] if approve else REPORT_ZH[ReportStatus.REVISED]
        )
        note = ("主管確認" if approve else "主管退回") + (f"：{comment}" if comment else "")
        self._add_version(rpt, note, by)
        await self._repo.commit()
        return report_dict(rpt)

    async def publish_report(self, report_id: str, by: str) -> dict:
        """發布並回傳使用者；委託單進入待報告回傳。"""
        rpt = await self._require_report(report_id)
        if rpt.status != REPORT_ZH[ReportStatus.CONFIRMED]:
            raise ConflictError(f"報告為「{rpt.status}」，僅已確認可發布")
        rpt.status = REPORT_ZH[ReportStatus.RETURNED]
        self._add_version(rpt, "發布並回傳使用者", by)
        order = await self._repo.get_order(rpt.order_id)
        if order and order.status == ORDER_ZH[OrderStatus.COMPLETED]:
            order.status = ORDER_ZH[OrderStatus.WAITING_REPORT_RETURN]
        await self._repo.commit()
        return report_dict(rpt)

    @staticmethod
    def _add_version(rpt: Report, note: str, by: str) -> None:
        rpt.versions.append(
            ReportVersion(
                version=len(rpt.versions) + 1,
                status=rpt.status,
                at=_now(),
                actor=by,
                note=note,
            )
        )
