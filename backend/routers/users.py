from fastapi import APIRouter

from database import get_connection
from serializers import list_response, user_from_row


router = APIRouter()


@router.get("/api/users")
def get_users() -> dict[str, object]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY user_id").fetchall()
    return list_response([user_from_row(row) for row in rows])
