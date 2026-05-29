"""Pydantic request DTOs for the machines module. JSON fields use camelCase."""

from pydantic import BaseModel, Field


class MachinePayload(BaseModel):
    """建立 / 更新機台（status — 新建預設為「閒置」）。"""

    machine_id: str = Field(..., alias="machineId")
    name: str
    lab: str
    status: str | None = None
    supported_items: list[str] = Field(default_factory=list, alias="supportedItems")
    owner: str = ""
    utilization: int = Field(default=0, ge=0, le=100)
    last_maintenance: str | None = Field(default=None, alias="lastMaintenance")

    model_config = {"populate_by_name": True}


class MachineStatusBody(BaseModel):
    """更新機台狀態。"""

    status: str
