"""FastAPI dependencies for the recipes module."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import CurrentUser, get_current_user
from app.common.dependencies.lab_scope import build_lab_scope
from app.core.database import get_db
from app.modules.recipes.repository import RecipeRepository
from app.modules.recipes.service import RecipeService


async def get_recipe_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> RecipeService:
    scope = await build_lab_scope(user, session)
    return RecipeService(RecipeRepository(session), scope)
