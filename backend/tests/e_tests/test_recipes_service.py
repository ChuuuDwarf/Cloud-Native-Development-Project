from __future__ import annotations

import pytest

from app.common.dependencies.lab_scope import LabScope
from app.common.errors import ConflictError, ForbiddenError, NotFoundError
from app.db.models import Recipe
from app.modules.recipes.schemas import RecipePayload
from app.modules.recipes.service import RecipeService

pytestmark = pytest.mark.asyncio


LAB_SCOPE = LabScope(role="lab_engineer", lab_name="材料分析實驗室", lab_code="LAB-A")
NO_LAB_SCOPE = LabScope(role="lab_engineer", lab_name=None, lab_code=None)


class FakeRecipeRepo:
    def __init__(self) -> None:
        self.recipes: dict[str, Recipe] = {}
        self.lab_machine_ids = {"LAB-A": ["SEM-A-001"], "LAB-B": ["IV-B-001"]}
        self.added: list[Recipe] = []
        self.commits = 0

    async def list_recipes(self) -> list[Recipe]:
        return list(self.recipes.values())

    async def get_by_recipe_id(self, recipe_id: str) -> Recipe | None:
        return self.recipes.get(recipe_id)

    async def machine_ids_in_lab(self, lab_code: str) -> list[str]:
        return self.lab_machine_ids.get(lab_code, [])

    def add(self, recipe: Recipe) -> None:
        self.added.append(recipe)
        self.recipes[recipe.recipe_id] = recipe

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, recipe: Recipe) -> None:
        # No-op: the in-memory fake holds the live object, nothing to reload.
        # Mirrors RecipeRepository.refresh (added to fix the post-commit
        # MissingGreenlet on the server-side ``updated_at`` column).
        return None


def recipe(recipe_id: str, machine_ids: list[str]) -> Recipe:
    return Recipe(
        recipe_id=recipe_id,
        name=f"Recipe {recipe_id}",
        version="v1",
        experiment_item="SEM",
        machine_ids=machine_ids,
        method="method",
        parameters={"temp": "100C"},
        updated_by="Alice",
    )


def payload(recipe_id: str = "R-1", **overrides: object) -> RecipePayload:
    data = {
        "recipeId": recipe_id,
        "name": "SEM recipe",
        "version": "v2",
        "experimentItem": "SEM",
        "machineIds": ["SEM-A-001"],
        "method": "updated",
        "parameters": {"voltage": "5V"},
        "updatedBy": "Bob",
    }
    data.update(overrides)
    return RecipePayload.model_validate(data)


async def test_list_recipes_filters_to_lab_owned_machines_and_no_lab_returns_empty() -> None:
    repo = FakeRecipeRepo()
    repo.recipes = {
        "A": recipe("A", ["SEM-A-001"]),
        "B": recipe("B", ["IV-B-001"]),
        "orphan": recipe("orphan", []),
    }

    assert [r["recipeId"] for r in await RecipeService(repo, LAB_SCOPE).list_recipes()] == ["A"]
    assert await RecipeService(repo, NO_LAB_SCOPE).list_recipes() == []


async def test_system_scope_lists_all_recipes() -> None:
    repo = FakeRecipeRepo()
    repo.recipes = {"A": recipe("A", ["SEM-A-001"]), "B": recipe("B", ["IV-B-001"])}

    result = await RecipeService(repo, LabScope.system()).list_recipes()

    assert {r["recipeId"] for r in result} == {"A", "B"}


async def test_create_recipe_success_duplicate_and_machine_scope() -> None:
    repo = FakeRecipeRepo()
    svc = RecipeService(repo, LAB_SCOPE)

    result = await svc.create(payload("R-new"))
    assert result["recipeId"] == "R-new"
    assert result["machineIds"] == ["SEM-A-001"]
    assert repo.commits == 1

    with pytest.raises(ConflictError):
        await svc.create(payload("R-new"))
    with pytest.raises(ForbiddenError):
        await svc.create(payload("R-empty", machineIds=[]))
    with pytest.raises(ForbiddenError):
        await svc.create(payload("R-cross", machineIds=["IV-B-001"]))


async def test_update_recipe_enforces_visibility_and_machine_scope() -> None:
    repo = FakeRecipeRepo()
    repo.recipes = {"A": recipe("A", ["SEM-A-001"]), "B": recipe("B", ["IV-B-001"])}
    svc = RecipeService(repo, LAB_SCOPE)

    result = await svc.update("A", payload("A", name="new name"))
    assert result["name"] == "new name"
    assert repo.commits == 1

    with pytest.raises(NotFoundError):
        await svc.update("missing", payload("missing"))
    with pytest.raises(NotFoundError):
        await svc.update("B", payload("B", machineIds=["IV-B-001"]))
    with pytest.raises(ForbiddenError):
        await svc.update("A", payload("A", machineIds=["IV-B-001"]))
