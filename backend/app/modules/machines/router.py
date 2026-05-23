"""HTTP routes for /api/machines. Owned by 組員 C."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/machines", tags=["Machines"])


@router.get("")
async def list_machines() -> dict:
    return {"items": [], "total": 0, "message": "組員 C: implement machines module"}
