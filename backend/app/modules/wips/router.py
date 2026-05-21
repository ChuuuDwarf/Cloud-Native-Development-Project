"""HTTP routes for /api/wips. Owned by 組員 B."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/wips", tags=["Wips"])


@router.get("")
async def list_wips() -> dict:
    return {"items": [], "total": 0, "message": "組員 B: implement wips module"}
