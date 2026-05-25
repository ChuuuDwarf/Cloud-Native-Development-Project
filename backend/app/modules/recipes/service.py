"""Recipe 管理商業邏輯：建立 / 更新。``updatedAt`` 由 TimestampMixin 自動維護。"""

from __future__ import annotations

from app.common.errors import ConflictError, NotFoundError
from app.db.models import Recipe
from app.modules.recipes.repository import RecipeRepository
from app.modules.recipes.schemas import RecipePayload
from app.modules.recipes.serializers import recipe_dict


class RecipeService:
    def __init__(self, repo: RecipeRepository) -> None:
        self._repo = repo

    async def list_recipes(self) -> list[dict]:
        recipes = await self._repo.list_recipes()
        return [recipe_dict(r) for r in recipes]

    async def _require(self, recipe_id: str) -> Recipe:
        recipe = await self._repo.get_by_recipe_id(recipe_id)
        if recipe is None:
            raise NotFoundError(f"找不到 Recipe：{recipe_id}")
        return recipe

    async def create(self, payload: RecipePayload) -> dict:
        if await self._repo.get_by_recipe_id(payload.recipe_id) is not None:
            raise ConflictError(f"Recipe 編號已存在：{payload.recipe_id}")
        recipe = Recipe(
            recipe_id=payload.recipe_id,
            name=payload.name,
            version=payload.version,
            experiment_item=payload.experiment_item,
            machine_ids=list(payload.machine_ids),
            method=payload.method,
            parameters=dict(payload.parameters),
            updated_by=payload.updated_by,
        )
        self._repo.add(recipe)
        await self._repo.commit()
        return recipe_dict(recipe)

    async def update(self, recipe_id: str, payload: RecipePayload) -> dict:
        recipe = await self._require(recipe_id)
        recipe.name = payload.name
        recipe.version = payload.version
        recipe.experiment_item = payload.experiment_item
        recipe.machine_ids = list(payload.machine_ids)
        recipe.method = payload.method
        recipe.parameters = dict(payload.parameters)
        recipe.updated_by = payload.updated_by
        await self._repo.commit()
        return recipe_dict(recipe)
