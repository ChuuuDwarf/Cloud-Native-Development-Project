from datetime import datetime

import psycopg
from fastapi import APIRouter, Header, HTTPException
from psycopg.types.json import Jsonb

from database import get_connection
from dependencies import can_view_all_labs, get_user, require_lab_scope, require_role
from schemas import RecipeCreate
from serializers import list_response, recipe_from_row, response


router = APIRouter()


@router.get("/api/recipes")
def get_recipes(x_user_id: str | None = Header(default=None)) -> dict[str, object]:
    with get_connection() as conn:
        user = get_user(conn, x_user_id)
        if can_view_all_labs(user):
            rows = conn.execute(
                "SELECT * FROM recipes ORDER BY updated_at DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT DISTINCT recipes.*
                FROM recipes
                JOIN machines ON machines.machine_id = ANY(recipes.machine_ids)
                WHERE machines.lab = %s
                ORDER BY updated_at DESC
                """,
                (require_lab_scope(user),),
            ).fetchall()
    return list_response([recipe_from_row(row) for row in rows])


@router.post("/api/recipes")
def create_recipe(
    payload: RecipeCreate, x_user_id: str | None = Header(default=None)
) -> dict[str, object]:
    with get_connection() as conn:
        user = get_user(conn, x_user_id)
        require_role(user, {"實驗室人員", "實驗室小主管"})
        machine_count = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM machines
            WHERE machine_id = ANY(%s)
              AND lab = %s
            """,
            (payload.machineIds, require_lab_scope(user)),
        ).fetchone()["count"]
        if machine_count != len(payload.machineIds):
            raise HTTPException(status_code=400, detail="Some machines do not exist")

        try:
            row = conn.execute(
                """
                INSERT INTO recipes (
                    recipe_id, name, version, experiment_item, machine_ids,
                    method, parameters, updated_by, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    payload.recipeId,
                    payload.name,
                    payload.version,
                    payload.experimentItem,
                    payload.machineIds,
                    payload.method,
                    Jsonb(payload.parameters),
                    user.name,
                    datetime.now(),
                ),
            ).fetchone()
        except psycopg.errors.UniqueViolation as exc:
            raise HTTPException(
                status_code=409, detail="Recipe already exists"
            ) from exc
    return response(recipe_from_row(row), "recipe created")
