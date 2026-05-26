"""Pydantic request DTOs for the dispatches module. JSON fields use camelCase."""

from pydantic import BaseModel, Field


class CreateDispatchPayload(BaseModel):
    """建立派工單（狀態預設「待排程」）。"""

    dispatch_id: str = Field(..., alias="dispatchId")
    wip_id: str = Field(..., alias="wipId")
    order_id: str = Field(..., alias="orderId")
    experiment_item: str = Field(..., alias="experimentItem")
    priority: str
    due_at: str | None = Field(default=None, alias="dueAt")

    model_config = {"populate_by_name": True}


class SuggestBody(BaseModel):
    """執行排程建議。"""

    strategy: str


class ReplanBody(BaseModel):
    """以新策略重新排程。"""

    reason: str
    strategy: str


class AssignDispatchPayload(BaseModel):
    """指派機台 / Recipe 與排程時段（待派工 → 待上機）。"""

    machine_id: str = Field(..., alias="machineId")
    recipe_id: str = Field(..., alias="recipeId")
    scheduled_start: str = Field(..., alias="scheduledStart")
    scheduled_end: str = Field(..., alias="scheduledEnd")

    model_config = {"populate_by_name": True}
