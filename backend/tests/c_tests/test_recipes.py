"""Endpoint-level (integration) tests for /api/recipes. Owned by 組員 C.

================================================================================
Structure mirrors the canonical template ``tests/c_tests/test_machines.py`` (see
it for the shared conventions): one test = one behaviour, named
``test_<verb>_<condition>_<expected>``; exercise the real HTTP surface through the
shared httpx ``AsyncClient`` fixtures in ``tests/conftest.py``; assert on BOTH the
status code AND the body; create OWN rows with UNIQUE ids so reruns can't collide
with the accumulating session DB; never assert exact collection counts.

CONTRACT FACTS verified against the source (app/routes/recipes.py +
app/modules/recipes/{service,repository,schemas,serializers}.py) AND a live run:

  * ENVELOPES are the PROJECT-STANDARD shared shapes:
        list   GET ""              -> PageResponse {"items", "page", "pageSize", "total"}
        create POST ""             -> 200 + ApiResponse {"data": <recipe>, "message"}
        update PATCH /{recipe_id}  -> 200 + ApiResponse {"data": <recipe>, "message"}
    The router builds the page envelope from the FULL list (pageSize == len(items),
    page == 1) — there is NO real pagination; ``total == pageSize == len(items)``.
    ERROR envelope is the standard nested ``{"error": {"code", "message", "details"}}``
    (global handlers in app/core/error_handlers.py + the AppError handler in app/main.py).

  * AUTH / PERMISSIONS (verified against each route's ``Depends``):
        GET ""                         -> get_current_user (authentication ONLY)
        POST "" , PATCH /{recipe_id}   -> require_permission("recipes:manage")
    READ IS NOT PERMISSION-GATED: ``RECIPES_READ = "recipes:read"`` is declared in
    the router but is DEAD CODE — never passed to ``require_permission`` / any
    ``Depends`` (exactly like machines' dead ``machines:read``). Any logged-in user
    can list; the result is merely lab-scoped.

  * ROLE MAP — recipes:manage is SUPERVISOR-ONLY (scripts/seed_dev.py): it lives in
    ``LAB_SUPERVISOR_EXTRA_PERMS`` (line ~152), NOT in ``LAB_ENGINEER_PERMS`` (which
    holds only ``recipes:read``). This is the OPPOSITE of machines, where the
    engineer can manage. So:
        supervisor_a_client (lab_supervisor, LAB-A)  -> CAN manage recipes.
        engineer_a_client   (lab_engineer,  LAB-A)   -> has recipes:read only -> 403.
        admin_client        (system_admin, cross-lab)-> CAN manage (wildcard ``*``).
        plant_user_client                            -> neither -> 403.

  * LAB SCOPE (app/modules/recipes/service.py): a recipe has no ``lab`` column; it
    "belongs to a lab" iff any of its ``machine_ids`` is a machine in that lab.
    ``system_admin`` sees/mutates everything. A non-admin manager (supervisor_a)
    may only create/update recipes ALL of whose machine_ids are in their OWN lab —
    ``_ensure_machines_in_scope`` raises ForbiddenError (403) otherwise, and also
    rejects an EMPTY machine_ids list (would create an invisible orphan). Reads are
    filtered to recipes overlapping the caller's lab machines; a missing/out-of-scope
    recipe is hidden as 404 (existence not leaked).

  * SEED has NO recipes — the recipes table starts EMPTY. Every listable recipe in
    these tests is one a test created. Seeded LAB-A machines we bind to:
    SEM-A-001 (SEM) / EDX-A-001 (EDX); LAB-B machine IV-B-001 (IV).
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

# NOTE: no ``pytestmark = pytest.mark.asyncio`` — ``asyncio_mode = "auto"``
# (pyproject.toml) already auto-collects every ``async def test_*`` as an
# asyncio test.

LAB_A_MACHINE = "SEM-A-001"  # seeded LAB-A machine, supports SEM
LAB_B_MACHINE = "IV-B-001"  # seeded LAB-B machine, supports IV


def _uid(prefix: str) -> str:
    """A collision-proof recipe id for mutating tests.

    The session DB is seeded once and accumulates every recipe mutating tests
    create; a uuid4 suffix keeps each created id unique per run so reruns can't
    409 against a row an earlier run inserted.
    """
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _recipe_payload(
    recipe_id: str,
    *,
    machine_ids: list[str] | None = None,
    experiment_item: str = "SEM",
    **overrides: object,
) -> dict[str, object]:
    """A reusable, valid create payload (camelCase to match the RecipePayload
    aliases). Defaults bind to the seeded LAB-A machine so a LAB-A manager passes
    the ``_ensure_machines_in_scope`` lab gate."""
    payload: dict[str, object] = {
        "recipeId": recipe_id,
        "name": "測試配方",
        "version": "v1",
        "experimentItem": experiment_item,
        "machineIds": [LAB_A_MACHINE] if machine_ids is None else machine_ids,
        "method": "標準流程",
        "parameters": {"voltage": "5kV"},
        "updatedBy": "譚曉蓉",
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# LIST — GET /api/recipes
# Happy path + the PageResponse envelope. The router has no real pagination:
# pageSize == total == len(items), page == 1.
# ---------------------------------------------------------------------------
async def test_list_recipes_returns_page_envelope(
    supervisor_a_client: AsyncClient,
) -> None:
    # Arrange: guarantee at least one recipe visible to this LAB-A manager.
    recipe_id = _uid("RCP-LIST")
    created = await supervisor_a_client.post("/api/recipes", json=_recipe_payload(recipe_id))
    assert created.status_code == 200, created.text

    res = await supervisor_a_client.get("/api/recipes")
    assert res.status_code == 200, res.text

    body = res.json()
    # Envelope contract: a PageResponse, not a bare list.
    assert set(body.keys()) >= {"items", "page", "pageSize", "total"}
    assert isinstance(body["items"], list)
    assert body["page"] == 1
    # The router builds the page from the full list, so these three agree.
    assert body["pageSize"] == body["total"] == len(body["items"])
    ids = {row["recipeId"] for row in body["items"]}
    assert recipe_id in ids, "the manager's own-lab recipe must be listable"
    # Each row uses the camelCase serializer (serializers.recipe_dict).
    sample = next(r for r in body["items"] if r["recipeId"] == recipe_id)
    assert set(sample.keys()) == {
        "recipeId",
        "name",
        "version",
        "experimentItem",
        "machineIds",
        "method",
        "parameters",
        "updatedBy",
        "updatedAt",
    }


async def test_list_recipes_is_lab_scoped_for_engineer(
    engineer_a_client: AsyncClient,
    admin_client: AsyncClient,
) -> None:
    """A non-admin only sees recipes whose machines are in their lab.

    A recipe bound ONLY to a LAB-B machine must NOT appear for the LAB-A engineer
    (who CAN list — reads are not gated — but is lab-scoped), while the cross-lab
    admin DOES see it. We prove EXCLUSION concretely by pinning a specific LAB-B
    recipe id and confirming the admin sees it but the engineer doesn't.
    """
    lab_b_recipe = _uid("RCP-LABB")
    # Only system_admin can create a LAB-B-only recipe (a LAB-A manager would be
    # blocked by _ensure_machines_in_scope); admin's wildcard bypasses lab scope.
    created = await admin_client.post(
        "/api/recipes",
        json=_recipe_payload(lab_b_recipe, machine_ids=[LAB_B_MACHINE], experiment_item="IV"),
    )
    assert created.status_code == 200, created.text

    eng_ids = {r["recipeId"] for r in (await engineer_a_client.get("/api/recipes")).json()["items"]}
    assert lab_b_recipe not in eng_ids

    admin_ids = {r["recipeId"] for r in (await admin_client.get("/api/recipes")).json()["items"]}
    assert lab_b_recipe in admin_ids


# ---------------------------------------------------------------------------
# CREATE — POST /api/recipes
# Happy path (200 + {data, message}) + a duplicate-id 409 + a framework 422 +
# the lab-scope ForbiddenError (403) for an out-of-lab machine.
# ---------------------------------------------------------------------------
async def test_create_recipe_success(supervisor_a_client: AsyncClient) -> None:
    recipe_id = _uid("RCP-CREATE")
    res = await supervisor_a_client.post("/api/recipes", json=_recipe_payload(recipe_id))
    assert res.status_code == 200, res.text

    body = res.json()
    assert body["message"]  # non-empty success message (Recipe 已建立)
    data = body["data"]
    assert data["recipeId"] == recipe_id
    assert data["experimentItem"] == "SEM"
    assert data["machineIds"] == [LAB_A_MACHINE]
    assert data["parameters"] == {"voltage": "5kV"}


async def test_admin_can_create_recipe(admin_client: AsyncClient) -> None:
    """The cross-lab system_admin also holds recipes:manage (wildcard ``*``) and
    bypasses the lab-scope machine gate, so it can create against any lab's
    machine. Proves the admin manage path independent of the supervisor's lab."""
    recipe_id = _uid("RCP-ADMIN")
    res = await admin_client.post(
        "/api/recipes",
        json=_recipe_payload(recipe_id, machine_ids=[LAB_B_MACHINE], experiment_item="IV"),
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["recipeId"] == recipe_id


async def test_create_recipe_duplicate_id_is_409(supervisor_a_client: AsyncClient) -> None:
    """Re-using an existing recipe id is a conflict, not a silent overwrite.

    We create our OWN row first (unique id), then POST it again so the collision
    is deterministic without depending on any seeded recipe (there are none)."""
    recipe_id = _uid("RCP-DUP")
    first = await supervisor_a_client.post("/api/recipes", json=_recipe_payload(recipe_id))
    assert first.status_code == 200, first.text

    dup = await supervisor_a_client.post("/api/recipes", json=_recipe_payload(recipe_id))
    assert dup.status_code == 409, dup.text
    assert dup.json()["error"]["code"] == "CONFLICT", dup.text


async def test_create_recipe_missing_required_field_is_422(
    supervisor_a_client: AsyncClient,
) -> None:
    """Omitting a required field (name) is rejected by Pydantic before the service
    runs — a FRAMEWORK 422. The custom RequestValidationError handler normalizes it
    into the project's nested envelope (code VALIDATION_ERROR), NOT the raw FastAPI
    ``{"detail": [...]}``; the offending field is summarized into error.message."""
    bad = _recipe_payload(_uid("RCP-422"))
    del bad["name"]
    res = await supervisor_a_client.post("/api/recipes", json=bad)
    assert res.status_code == 422, res.text

    body = res.json()
    assert "detail" not in body, res.text
    assert body["error"]["code"] == "VALIDATION_ERROR", res.text
    assert "name" in body["error"]["message"], res.text


async def test_create_recipe_out_of_lab_machine_is_403(
    supervisor_a_client: AsyncClient,
) -> None:
    """A LAB-A manager binding a recipe to a LAB-B machine trips the service's
    ``_ensure_machines_in_scope`` -> ForbiddenError (403 FORBIDDEN). This is a
    DOMAIN authorization error raised AFTER the route's permission check passed
    (the supervisor HAS recipes:manage) — distinct from the no-permission 403."""
    res = await supervisor_a_client.post(
        "/api/recipes",
        json=_recipe_payload(_uid("RCP-XLAB"), machine_ids=[LAB_B_MACHINE], experiment_item="IV"),
    )
    assert res.status_code == 403, res.text
    assert res.json()["error"]["code"] == "FORBIDDEN", res.text


async def test_create_recipe_empty_machines_is_403(
    supervisor_a_client: AsyncClient,
) -> None:
    """A non-admin manager declaring NO machines would create an orphan recipe
    nobody in their lab could see; ``_ensure_machines_in_scope`` rejects the empty
    list with ForbiddenError (403). (machineIds defaults to [] in the schema, so an
    empty list passes Pydantic and reaches the service.)"""
    res = await supervisor_a_client.post(
        "/api/recipes",
        json=_recipe_payload(_uid("RCP-EMPTY"), machine_ids=[]),
    )
    assert res.status_code == 403, res.text
    assert res.json()["error"]["code"] == "FORBIDDEN", res.text


# ---------------------------------------------------------------------------
# UPDATE — PATCH /api/recipes/{recipe_id}
# Happy path + 404. We create our own row first so we never mutate a shared one.
# ---------------------------------------------------------------------------
@pytest.mark.xfail(
    reason=(
        "KNOWN BUG: RecipeService.update returns recipe_dict(recipe) right after "
        "commit(); the serializer reads recipe.updated_at, which TimestampMixin "
        "mutates with a SERVER-SIDE onupdate=func.now(). After commit the new "
        "server-generated value is unloaded on the instance (even with "
        "expire_on_commit=False, a server-side onupdate column is expired), so the "
        "lazy refresh fires await IO on the async session -> MissingGreenlet -> 500 "
        "DATABASE_ERROR. The recipe IS persisted; only the update RESPONSE "
        "serialization 500s. (create_recipe is NOT affected: on INSERT updated_at "
        "comes from server_default and is populated without a post-commit refresh.) "
        "INTENDED behaviour: update returns 200 with the changed fields. This strict "
        "xfail XPASSes the moment update awaits repo.refresh(recipe) / eager-loads "
        "updated_at (or the serializer stops touching the expired column). Mirrors "
        "D's create_report lazy-load-after-commit bug."
    ),
    strict=True,
)
async def test_update_recipe_success(supervisor_a_client: AsyncClient) -> None:
    """Regression anchor for the update-response post-commit lazy-load bug. We
    assert the INTENDED 200; today it returns 500, so this xfails (strict)."""
    recipe_id = _uid("RCP-UPDATE")
    await supervisor_a_client.post("/api/recipes", json=_recipe_payload(recipe_id))

    updated = _recipe_payload(recipe_id, name="改名後的配方", version="v2")
    res = await supervisor_a_client.patch(f"/api/recipes/{recipe_id}", json=updated)
    assert res.status_code == 200, res.text

    data = res.json()["data"]
    assert data["name"] == "改名後的配方"
    assert data["version"] == "v2"


async def test_update_missing_recipe_is_404(supervisor_a_client: AsyncClient) -> None:
    missing = _uid("RCP-NOPE")
    res = await supervisor_a_client.patch(f"/api/recipes/{missing}", json=_recipe_payload(missing))
    assert res.status_code == 404, res.text
    assert res.json()["error"]["code"] == "NOT_FOUND", res.text


# ---------------------------------------------------------------------------
# PERMISSION / AUTH GATING.
#   * unauthenticated request                       -> 401 UNAUTHORIZED
#   * authenticated lab_engineer (read-only on this -> 403 FORBIDDEN
#     module: has recipes:read, NOT recipes:manage)
#   * authenticated plant_user (no recipe perms)    -> 403 FORBIDDEN
# ---------------------------------------------------------------------------
async def test_list_recipes_unauthenticated_is_401(client: AsyncClient) -> None:
    """``client`` has no auth cookie. Even the un-gated read endpoint requires a
    logged-in user (get_current_user raises UnauthorizedError -> nested
    UNAUTHORIZED), so it 401s. The gate is AUTHENTICATION, not the dead
    ``recipes:read`` permission."""
    res = await client.get("/api/recipes")
    assert res.status_code == 401, res.text
    assert res.json()["error"]["code"] == "UNAUTHORIZED", res.text


async def test_create_recipe_unauthenticated_is_401(client: AsyncClient) -> None:
    res = await client.post("/api/recipes", json=_recipe_payload(_uid("RCP-401")))
    assert res.status_code == 401, res.text
    assert res.json()["error"]["code"] == "UNAUTHORIZED", res.text


async def test_engineer_cannot_manage_recipe_is_403(
    engineer_a_client: AsyncClient,
) -> None:
    """A lab_engineer is authenticated and CAN list recipes (read isn't gated),
    but holds only ``recipes:read`` — NOT ``recipes:manage`` — so create is
    rejected by require_permission with 403 / FORBIDDEN. This is the OPPOSITE of
    machines (where the engineer CAN manage); recipes:manage is supervisor-only."""
    res = await engineer_a_client.post("/api/recipes", json=_recipe_payload(_uid("RCP-ENG")))
    assert res.status_code == 403, res.text
    assert res.json()["error"]["code"] == "FORBIDDEN", res.text


async def test_plant_user_cannot_manage_recipe_is_403(
    plant_user_client: AsyncClient,
) -> None:
    """plant_user has no recipe permissions at all -> 403 on the manage route."""
    res = await plant_user_client.patch(
        f"/api/recipes/{_uid('RCP-PU')}",
        json=_recipe_payload(_uid("RCP-PU")),
    )
    assert res.status_code == 403, res.text
    assert res.json()["error"]["code"] == "FORBIDDEN", res.text
