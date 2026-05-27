"""Pydantic request DTOs for the reports module.

Ported from Role D's ``app/schemas.py``.
"""

from pydantic import BaseModel, Field


class ReportCreateBody(BaseModel):
    """建立報告草稿（可從實驗結果自動帶入；也可一次填內容並送審）。"""

    wip_id: str = Field(..., alias="wipId", description="來源 WIP 編號")
    summary: str | None = Field(default=None, description="自填摘要，留空則自動帶入")
    conclusion: str | None = Field(default=None, description="自填結論，留空則用實驗結果")
    experiment_items: list[str] | None = Field(
        default=None,
        alias="experimentItems",
        description="要產生假數據的實驗項目；留空則用 WIP 的實驗項目",
    )
    template_id: int | None = Field(
        default=None, alias="templateId", description="套用的報告範本 id"
    )
    submit: bool = Field(default=False, description="建立後是否直接送審")

    model_config = {"populate_by_name": True}


class ReportTemplateCreateBody(BaseModel):
    """把報告或自填內容存成範本。"""

    name: str = Field(..., description="範本名稱")
    order_id: str | None = Field(default=None, alias="orderId", description="參考的委託單")
    summary: str = Field(default="")
    conclusion: str = Field(default="")
    from_report_id: str | None = Field(
        default=None, alias="fromReportId", description="由現有報告存成範本時帶入"
    )

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
