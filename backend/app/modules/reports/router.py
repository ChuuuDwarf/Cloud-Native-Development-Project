"""HTTP routes for /api/reports. Owned by 組員 D."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("")
async def list_reports() -> dict:
    return {"items": [], "total": 0, "message": "組員 D: implement reports module"}
