"""camelCase serializer for recipe responses. Output matches the frontend
``Recipe`` contract (``frontend/src/types/recipes.ts``)."""

from __future__ import annotations

from datetime import datetime

from app.db.models import Recipe

TIME_FMT = "%Y-%m-%d %H:%M:%S"


def _fmt(dt: datetime | None) -> str | None:
    return dt.strftime(TIME_FMT) if dt else None


def recipe_dict(r: Recipe) -> dict:
    return {
        "recipeId": r.recipe_id,
        "name": r.name,
        "version": r.version,
        "experimentItem": r.experiment_item,
        "machineIds": list(r.machine_ids or []),
        "method": r.method,
        "parameters": dict(r.parameters or {}),
        "updatedBy": r.updated_by,
        "updatedAt": _fmt(r.updated_at),
    }
