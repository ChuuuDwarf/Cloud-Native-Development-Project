"""WIP execution side table — **D-owned**.

B's ``wips`` schema models the sample-flow lifecycle but NOT D's execution
concerns (machine/recipe load, operator, raw-data upload + verify, and the
embedded abort request). Rather than bloat B's table or relax its CHECK, D keeps
those fields here, keyed 1:1 by B's business code ``wip_no``. See
[[cd-yields-to-ab-models]].

There is no DB-level FK to ``wips`` (B uses a UUID PK; we join on the business
code ``wip_no``). D's repository resolves the pair explicitly by ``wip_no``.
``abort_status`` mirrors D's original free-form string ('pending' / '已終止' /
'已駁回' bridged in the service layer).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, TIMESTAMP, Boolean, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WipExecution(Base):
    __tablename__ = "wip_execution"

    wip_no: Mapped[str] = mapped_column(String(50), primary_key=True)
    # D's fine-grained execution status (canonical English WipStatus value, e.g.
    # ``waiting_load`` / ``unloaded`` / ``waiting_confirm``). B's ``wips.status``
    # CHECK does not allow these, so they live here; the service maps to a
    # coarse CHECK-valid value when it touches ``wips.status``.
    exec_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="waiting_load"
    )
    machine_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    recipe: Mapped[str | None] = mapped_column(String(32), nullable=True)
    operator: Mapped[str | None] = mapped_column(String(64), nullable=True)
    check_in_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    check_out_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    result_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_data_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # 機台收集的量測數據（{實驗項目: {欄位: 顯示字串}}），於機台完成/上傳結果時產生並保存；
    # 驗證數據時顯示給人員確認，報告建立時沿用同一份（不再重骰）。
    experiment_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    data_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    # 中止申請（D 內嵌於 WIP，現移至側表）
    abort_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    abort_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    abort_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    abort_requested_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    abort_resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 進度自動推進排程：背景任務每隔隨機 3/5/8 秒把 running WIP 進度 +1%，
    # 到時間才 tick。NULL 表示不排（非 running 或已達 100%）。
    next_progress_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, server_default=func.now()
    )
