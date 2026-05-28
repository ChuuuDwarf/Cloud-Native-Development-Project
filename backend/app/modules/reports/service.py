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

from app.common.dependencies.lab_scope import LabScope
from app.common.enums import OrderStatus, ReportStatus, WipStatus
from app.common.enums.role_d_zh import REPORT_ZH
from app.common.errors import ConflictError, ForbiddenError, NotFoundError
from app.db.models import (
    Report,
    ReportAttachment,
    ReportTemplate,
    ReportVersion,
    Wip,
    WipExecution,
)
from app.modules.dashboard.publisher import publish_report_returned
from app.modules.reports.fake_data import generate_for_items
from app.modules.reports.repository import ReportRepository
from app.modules.reports.serializers import report_dict, template_dict

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now()


def _build_summary(wip: Wip, exec_row: WipExecution) -> str:
    """組出報告摘要，自動帶入前面實驗的數值（機台/Recipe/操作人/上下機/驗證）。"""
    parts = [f"針對 WIP {wip.wip_no}（{wip.experiment_item}）的實驗結果。"]
    if exec_row.machine_id:
        parts.append(f"機台：{exec_row.machine_id}")
    if exec_row.recipe:
        parts.append(f"Recipe：{exec_row.recipe}")
    if exec_row.operator:
        parts.append(f"操作人：{exec_row.operator}")
    if exec_row.check_in_at:
        parts.append(f"上機：{exec_row.check_in_at:%Y-%m-%d %H:%M}")
    if exec_row.check_out_at:
        parts.append(f"下機：{exec_row.check_out_at:%Y-%m-%d %H:%M}")
    parts.append(f"數據驗證：{'已驗證' if exec_row.data_verified else '未驗證'}")
    return "；".join(parts)


class ReportService:
    def __init__(self, repo: ReportRepository, scope: LabScope) -> None:
        self._repo = repo
        self._scope = scope

    async def _check_report_access(self, rpt: Report) -> None:
        """A report's lab is its source WIP's lab; enforce lab scoping."""
        if self._scope.sees_all_labs:
            return
        wip = await self._repo.get_wip(rpt.wip_id) if rpt.wip_id else None
        if not self._scope.can_access_lab(wip.lab_name if wip else None):
            raise ForbiddenError("無權存取其他實驗室的報告")

    async def _require_report(self, report_id: str) -> Report:
        rpt = await self._repo.get_report(report_id)
        if rpt is None:
            raise NotFoundError(f"找不到報告：{report_id}")
        await self._check_report_access(rpt)
        return rpt

    async def list_reports(
        self, status: str | None = None, order_id: str | None = None
    ) -> list[dict]:
        if self._scope.restricted_without_lab:
            return []
        reports = await self._repo.list_reports(status, order_id, self._scope.list_lab_filter())
        return [report_dict(r) for r in reports]

    async def get_report(self, report_id: str) -> dict:
        rpt = await self._require_report(report_id)
        return report_dict(rpt)

    async def create_report(
        self,
        wip_id: str,
        by: str,
        *,
        summary: str | None = None,
        conclusion: str | None = None,
        experiment_items: list[str] | None = None,
        template_id: int | None = None,
        submit: bool = False,
    ) -> dict:
        wip = await self._repo.get_wip(wip_id)
        if wip is None:
            raise NotFoundError(f"找不到 WIP：{wip_id}")
        if not self._scope.can_access_lab(wip.lab_name):
            raise ForbiddenError("無權為其他實驗室的 WIP 建立報告")
        exec_row = await self._repo.get_exec(wip_id)
        if exec_row is None or exec_row.exec_status not in (
            WipStatus.WAITING_CONFIRM.value,
            WipStatus.COMPLETED.value,
        ):
            raise ConflictError("需待結果確認或已完成的 WIP 才能建立報告")

        # 已有正式報告（已確認/已發布/已回傳）的實驗不可再開新報告，避免重複；
        # 要改內容請走既有報告的「建立修訂版」。
        if await self._repo.count_formal_reports_for_wip(
            wip_id,
            [
                REPORT_ZH[ReportStatus.CONFIRMED],
                REPORT_ZH[ReportStatus.PUBLISHED],
                REPORT_ZH[ReportStatus.RETURNED],
            ],
        ):
            raise ConflictError("此實驗已有正式報告，不可重複開立")

        tmpl = await self._repo.get_template(template_id) if template_id else None

        # Generate report ID
        count = await self._repo.count_reports_for_order(wip.order_no)
        suffix = wip.order_no.split("-")[-1]
        rid = f"RPT-{suffix}-{count + 1:02d}"

        # 量測數據：優先沿用實驗執行時保存、且已驗證的同一份；只有在指定了其他實驗項目
        # 或執行階段未留存數據時，才依實驗項目重新產生。
        if exec_row.experiment_data and not experiment_items:
            exp_data = exec_row.experiment_data
        else:
            items = experiment_items or ([wip.experiment_item] if wip.experiment_item else [])
            exp_data = generate_for_items(items)

        # 內容優先序：自填 > 範本 > 自動帶入。
        final_summary = summary or (tmpl.summary if tmpl and tmpl.summary else None)
        if not final_summary:
            final_summary = _build_summary(wip, exec_row)
        final_conclusion = conclusion or (tmpl.conclusion if tmpl and tmpl.conclusion else None)
        if final_conclusion is None:
            final_conclusion = exec_row.result_note or ""

        status_zh = REPORT_ZH[ReportStatus.PENDING_REVIEW if submit else ReportStatus.DRAFT]
        rpt = Report(
            report_id=rid,
            order_id=wip.order_no,
            wip_id=wip_id,
            title=f"{wip.order_no} {wip.experiment_item} 報告",
            summary=final_summary,
            conclusion=final_conclusion,
            experiment_data=exp_data,
            status=status_zh,
            created_at=_now(),
            created_by=by,
        )
        if exec_row.raw_data_url:
            rpt.attachments.append(
                ReportAttachment(name=f"原始數據：{exec_row.raw_data_url}", at=_now())
            )
        note = "建立並直接送審" if submit else "自實驗結果建立草稿（已帶入機台/Recipe/數據）"
        rpt.versions.append(
            ReportVersion(version=1, status=status_zh, at=_now(), actor=by, note=note)
        )
        await self._repo.add(rpt)
        if submit:
            # 直接送審 → 委託單 已完成 → 待報告回傳。flow.md。
            await self._advance_order(
                wip.order_no,
                (OrderStatus.COMPLETED.value,),
                OrderStatus.WAITING_REPORT_RETURN.value,
            )
        await self._repo.commit()
        return report_dict(rpt)

    async def list_templates(self) -> list[dict]:
        return [template_dict(t) for t in await self._repo.list_templates()]

    async def save_template(
        self,
        name: str,
        by: str,
        *,
        order_id: str | None = None,
        summary: str = "",
        conclusion: str = "",
        from_report_id: str | None = None,
    ) -> dict:
        """把自填內容或現有報告存成範本。"""
        if from_report_id:
            rpt = await self._require_report(from_report_id)  # scope-checked
            summary = summary or rpt.summary
            conclusion = conclusion or rpt.conclusion
            order_id = order_id or rpt.order_id
        tmpl = ReportTemplate(
            name=name,
            order_id=order_id,
            summary=summary,
            conclusion=conclusion,
            created_by=by,
            created_at=_now(),
        )
        await self._repo.add(tmpl)
        await self._repo.commit()
        return template_dict(tmpl)

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

    async def _advance_order(
        self, order_no: str, from_statuses: tuple[str, ...], to_status: str
    ) -> None:
        """委託單狀態連動（只在預期的來源狀態才前進，避免回退）。見 flow.md 委託單狀態機。"""
        order = await self._repo.get_order(order_no)
        if order and order.status in from_statuses:
            order.status = to_status

    async def submit_report(self, report_id: str, by: str) -> dict:
        rpt = await self._require_report(report_id)
        if rpt.status not in (REPORT_ZH[ReportStatus.DRAFT], REPORT_ZH[ReportStatus.REVISED]):
            raise ConflictError(f"報告為「{rpt.status}」，僅草稿或已改版可送審")
        rpt.status = REPORT_ZH[ReportStatus.PENDING_REVIEW]
        self._add_version(rpt, "提交審核", by)
        # 已完成 → 待報告回傳（報告送審中，等待確認並回傳）。flow.md。
        await self._advance_order(
            rpt.order_id,
            (OrderStatus.COMPLETED.value,),
            OrderStatus.WAITING_REPORT_RETURN.value,
        )
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
        """發布並回傳使用者；報告回傳後委託單進入「待取件」（flow.md）。"""
        rpt = await self._require_report(report_id)
        if rpt.status != REPORT_ZH[ReportStatus.CONFIRMED]:
            raise ConflictError(f"報告為「{rpt.status}」，僅已確認可發布")
        rpt.status = REPORT_ZH[ReportStatus.RETURNED]
        self._add_version(rpt, "發布並回傳使用者", by)
        # 報告回傳 → 委託單 (已完成 / 待報告回傳) → 待取件。flow.md 待報告回傳 → 待取件。
        await self._advance_order(
            rpt.order_id,
            (OrderStatus.COMPLETED.value, OrderStatus.WAITING_REPORT_RETURN.value),
            OrderStatus.WAITING_PICKUP.value,
        )
        await self._repo.commit()

        # Best-effort dashboard SSE fanout. lab_name is the WIP's display
        # name (Chinese) since publisher channels are keyed by display name.
        # Publisher swallows Redis errors; we wrap the wip lookup too.
        try:
            wip = await self._repo.get_wip(rpt.wip_id) if rpt.wip_id else None
            await publish_report_returned(wip.lab_name if wip else None)
        except Exception:
            logger.exception("dashboard publish_report_returned failed report=%s", rpt.report_id)

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
