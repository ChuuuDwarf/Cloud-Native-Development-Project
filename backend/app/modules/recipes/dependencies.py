"""FastAPI dependencies for the recipes module."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.recipes.repository import RecipeRepository
from app.modules.recipes.service import RecipeService


def get_recipe_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RecipeService:
    return RecipeService(RecipeRepository(session))
