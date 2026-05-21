"""HTTP routes for /api/orders. Owned by 組員 A."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/orders", tags=["Orders"])


@router.get("")
async def list_orders() -> dict:
    return {"items": [], "total": 0, "message": "組員 A: implement orders module"}
