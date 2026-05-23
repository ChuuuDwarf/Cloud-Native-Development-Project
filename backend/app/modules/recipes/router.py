"""HTTP routes for /api/recipes. Owned by 組員 C."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/recipes", tags=["Recipes"])


@router.get("")
async def list_recipes() -> dict:
    return {"items": [], "total": 0, "message": "組員 C: implement recipes module"}
