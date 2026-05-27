"""Recipe 管理商業邏輯：建立 / 更新。``updatedAt`` 由 TimestampMixin 自動維護。

Lab scoping: recipes have no ``lab`` column of their own. A recipe is considered
"belonging to a lab" if any of its ``machine_ids`` belong to that lab's
machines. Non-admins see only such recipes; create / update require that ALL
declared ``machine_ids`` are machines the caller's lab owns. ``system_admin``
sees / mutates everything.
"""

from __future__ import annotations

from app.common.dependencies.lab_scope import LabScope
from app.common.errors import ConflictError, ForbiddenError, NotFoundError
from app.db.models import Recipe
from app.modules.recipes.repository import RecipeRepository
from app.modules.recipes.schemas import RecipePayload
from app.modules.recipes.serializers import recipe_dict


class RecipeService:
    def __init__(self, repo: RecipeRepository, scope: LabScope) -> None:
        self._repo = repo
        self._scope = scope

    async def list_recipes(self) -> list[dict]:
        if self._scope.restricted_without_lab:
            return []
        recipes = await self._repo.list_recipes()
        if self._scope.sees_all_labs:
            return [recipe_dict(r) for r in recipes]
        # Filter to recipes whose machine_ids overlap with the user's lab.
        lab_machine_ids = await self._repo.machine_ids_in_lab(self._scope.lab_code or "")
        visible = [
            r for r in recipes if any(mid in lab_machine_ids for mid in (r.machine_ids or []))
        ]
        return [recipe_dict(r) for r in visible]

    async def _require(self, recipe_id: str) -> Recipe:
        recipe = await self._repo.get_by_recipe_id(recipe_id)
        if recipe is None:
            raise NotFoundError(f"找不到 Recipe：{recipe_id}")
        if not self._scope.sees_all_labs:
            lab_machine_ids = await self._repo.machine_ids_in_lab(self._scope.lab_code or "")
            if not any(mid in lab_machine_ids for mid in (recipe.machine_ids or [])):
                # Don't leak existence of out-of-scope recipes.
                raise NotFoundError(f"找不到 Recipe：{recipe_id}")
        return recipe

    async def _ensure_machines_in_scope(self, machine_ids: list[str]) -> None:
        """All ``machine_ids`` must belong to a lab the caller can access."""
        if self._scope.sees_all_labs:
            return
        if not machine_ids:
            # No machines declared — caller would create an orphan recipe nobody
            # can see. Reject to prevent silent invisibility.
            raise ForbiddenError("Recipe 必須至少綁定一個本實驗室機台")
        lab_machine_ids = await self._repo.machine_ids_in_lab(self._scope.lab_code or "")
        out_of_scope = [mid for mid in machine_ids if mid not in lab_machine_ids]
        if out_of_scope:
            raise ForbiddenError(f"以下機台不在本實驗室範圍內：{', '.join(out_of_scope)}")

    async def create(self, payload: RecipePayload) -> dict:
        await self._ensure_machines_in_scope(list(payload.machine_ids))
        existing = await self._repo.get_by_recipe_id(payload.recipe_id)
        if existing is not None:
            machines_info = ", ".join(existing.machine_ids or []) or "未綁定機台"
            raise ConflictError(f"Recipe 編號 {payload.recipe_id} 已存在（機台：{machines_info}）")
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
        await self._ensure_machines_in_scope(list(payload.machine_ids))
        recipe.name = payload.name
        recipe.version = payload.version
        recipe.experiment_item = payload.experiment_item
        recipe.machine_ids = list(payload.machine_ids)
        recipe.method = payload.method
        recipe.parameters = dict(payload.parameters)
        recipe.updated_by = payload.updated_by
        await self._repo.commit()
        return recipe_dict(recipe)
