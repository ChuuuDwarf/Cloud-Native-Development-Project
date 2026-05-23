from fastapi import APIRouter

from database import get_connection


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    with get_connection() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok", "database": "connected"}
