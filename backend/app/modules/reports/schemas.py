"""Pydantic request DTOs for the reports module.

Ported from Role D's ``app/schemas.py``.
"""

from pydantic import BaseModel, Field


class ReportCreateBody(BaseModel):
    """建立報告草稿（可從實驗結果自動帶入）。"""

    wip_id: str = Field(..., alias="wipId", description="來源 WIP 編號")

    model_config = {"populate_by_name": True}


class ReportEditBody(BaseModel):
    """編輯報告摘要 / 結論 / 附件。"""

    summary: str | None = None
    conclusion: str | None = None
    attachment_name: str | None = Field(
        default=None, alias="attachmentName", description="附件檔名"
    )

    model_config = {"populate_by_name": True}


class ReportReviewBody(BaseModel):
    """主管審核報告。"""

    approve: bool = Field(..., description="True=確認，False=退回")
    comment: str | None = None
