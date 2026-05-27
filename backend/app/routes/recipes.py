"""HTTP routes for /api/recipes. Owned by 組員 C.

Controller mounted from the central ``app/routes`` registry. Thin router; all
logic lives in :class:`app.modules.recipes.service.RecipeService`. Matches the
frontend client ``frontend/src/services/recipes-api.ts``.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.common.dependencies import CurrentUser, get_current_user, require_permission
from app.common.schemas import ApiResponse, PageResponse
from app.modules.recipes.dependencies import get_recipe_service
from app.modules.recipes.schemas import RecipePayload
from app.modules.recipes.service import RecipeService

router = APIRouter(prefix="/api/recipes", tags=["Recipes"])

RECIPES_READ = "recipes:read"
RECIPES_MANAGE = "recipes:manage"


@router.get("", response_model=PageResponse[dict])
async def list_recipes(
    service: Annotated[RecipeService, Depends(get_recipe_service)],
    _: Annotated[CurrentUser, Depends(get_current_user)],
) -> PageResponse[dict]:
    items = await service.list_recipes()
    return PageResponse(items=items, page=1, pageSize=len(items), total=len(items))


@router.post("", response_model=ApiResponse[dict])
async def create_recipe(
    body: RecipePayload,
    service: Annotated[RecipeService, Depends(get_recipe_service)],
    _: Annotated[CurrentUser, Depends(require_permission(RECIPES_MANAGE))],
) -> ApiResponse[dict]:
    return ApiResponse(data=await service.create(body), message="Recipe 已建立")


@router.patch("/{recipe_id}", response_model=ApiResponse[dict])
async def update_recipe(
    recipe_id: str,
    body: RecipePayload,
    service: Annotated[RecipeService, Depends(get_recipe_service)],
    _: Annotated[CurrentUser, Depends(require_permission(RECIPES_MANAGE))],
) -> ApiResponse[dict]:
    return ApiResponse(data=await service.update(recipe_id, body), message="Recipe 已更新")
