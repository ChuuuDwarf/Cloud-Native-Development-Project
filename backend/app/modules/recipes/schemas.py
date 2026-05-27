"""Pydantic request DTOs for the recipes module. JSON fields use camelCase."""

from pydantic import BaseModel, Field


class RecipePayload(BaseModel):
    """建立 / 更新 Recipe（``updatedAt`` 由伺服器端寫入時設定）。"""

    recipe_id: str = Field(..., alias="recipeId")
    name: str
    version: str
    experiment_item: str = Field(..., alias="experimentItem")
    machine_ids: list[str] = Field(default_factory=list, alias="machineIds")
    method: str = ""
    parameters: dict[str, str] = Field(default_factory=dict)
    updated_by: str = Field(default="", alias="updatedBy")

    model_config = {"populate_by_name": True}
