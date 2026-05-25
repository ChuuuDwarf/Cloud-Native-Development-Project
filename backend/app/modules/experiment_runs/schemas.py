"""Pydantic request DTOs for the experiment-runs module.

JSON fields use camelCase (development_standards.md §6.3). Response bodies are
plain dicts produced by the serializers + service, wrapped by the shared
``ApiResponse`` / ``PageResponse`` envelopes in the router.

Ported from Role D's ``app/schemas.py``.
"""

from pydantic import BaseModel, Field


class CheckInRequest(BaseModel):
    """上機登記。"""

    operator: str = Field(..., description="操作人")
    machine_id: str = Field(..., alias="machineId", description="機台編號")
    recipe: str = Field(..., description="Recipe 版本")

    model_config = {"populate_by_name": True}


class CheckOutRequest(BaseModel):
    """下機登記。"""

    operator: str = Field(..., description="操作人")
    note: str | None = Field(default=None, description="下機備註")


class ProgressRequest(BaseModel):
    """更新實驗進度。"""

    progress: int = Field(..., ge=0, le=100, description="進度百分比")


class ResultRequest(BaseModel):
    """上傳結果與原始數據連結。"""

    note: str = Field(..., description="結果備註")
    raw_data_url: str | None = Field(default=None, alias="rawDataUrl", description="原始數據連結")
    data_verified: bool = Field(
        default=False, alias="dataVerified", description="數據完整性是否已驗證"
    )

    model_config = {"populate_by_name": True}


class AbortRequestBody(BaseModel):
    """提出中止申請（實驗室人員）。"""

    reason: str = Field(..., description="中止原因")


class AbortReviewBody(BaseModel):
    """主管審核中止申請。"""

    approve: bool = Field(..., description="True=核准終止，False=駁回並繼續實驗")
    note: str | None = Field(default=None, description="主管處理結果說明")
