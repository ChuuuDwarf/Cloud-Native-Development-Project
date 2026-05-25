"""Async DB queries for the recipes module."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Recipe


class RecipeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_recipes(self) -> Sequence[Recipe]:
        result = await self._session.execute(select(Recipe).order_by(Recipe.recipe_id))
        return result.scalars().all()

    async def get_by_recipe_id(self, recipe_id: str) -> Recipe | None:
        result = await self._session.execute(select(Recipe).where(Recipe.recipe_id == recipe_id))
        return result.scalar_one_or_none()

    def add(self, recipe: Recipe) -> None:
        self._session.add(recipe)

    async def flush(self) -> None:
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()
