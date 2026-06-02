"""Endpoint-level tests for the order/sample/WIP aggregate routes in
``app/routes/others.py`` (組員 A/B legacy surface).

PURPOSE: lock in the ERROR-ENVELOPE behaviour of the raw ``HTTPException`` paths in
``others.py`` now that the global handlers (``app/core/error_handlers.py``)
normalize EVERY error into the nested ``{"error": {"code", "message", "details"}}``
shape. These tests double as regression coverage for that harmonization.

TEST-ENV REALITY (verified against a live run AND the schema) — this drives which
``others.py`` 404 paths are actually reachable here:

  * The test DB is built from ``Base.metadata.create_all`` (conftest), NOT Alembic.
    ``samples`` is a MIGRATION-ONLY table (組員 B ships it via migration; there is
    no ORM model — see ``app/db/models/wips.py``), so it DOES NOT EXIST in the test
    DB. ``wips`` and ``orders`` DO (they have ORM models). Confirmed:
        SELECT to_regclass('public.samples') -> NULL
        SELECT to_regclass('public.wips')    -> wips
        SELECT to_regclass('public.orders')  -> orders
    => Any ``others.py`` route that touches ``samples`` raises a ``SQLAlchemyError``
    (missing relation), which the global ``SQLAlchemyError`` handler turns into
    500 / ``DATABASE_ERROR`` — BEFORE the route's own raw ``HTTPException(404)`` can
    run. So the sample-dependent raw-404s are MASKED in this environment; we assert
    the 500/DATABASE_ERROR they actually produce and call it out, rather than
    pretending the 404 fires.

  * ``GET /api/orders/{order_no}`` in ``others.py`` is SHADOWED by
    ``app/routes/orders.py``'s ``GET /api/orders/{order_id:int}`` (registered with
    an ``int`` path param + ``get_current_user``). A numeric path hits the orders
    router (auth-gated, NOT_FOUND for an unknown id); a non-numeric path fails int
    parsing -> 422 VALIDATION_ERROR. Either way the ``others.py`` handler's raw 404
    ("Order not found") is UNREACHABLE for this route. Likewise ``others.py``'s
    ``GET /api/labs`` / ``GET /api/master-data`` / ``GET /api/storage-locations``
    are shadowed by the real labs / master_data routers (they return the project
    ``{items,total}`` / ``{data,message}`` envelopes and are AUTH-GATED), so the
    bare-dict ``others.py`` versions are dead code.

REACHABLE raw-404 paths in ``others.py`` (asserted below):
  * POST /api/others/wips/{wip_id}/complete            -> 404 NOT_FOUND (wips exists)
  * POST /api/others/orders/{order_id}/confirm-delivery-> 404 NOT_FOUND (get_real_order
    on the existing ``orders`` table returns None before any samples query)

NOTE: ``others.py`` routes have NO ``get_current_user`` dependency — they resolve
the user from the request cookie via ``resolve_current_user`` WITHOUT raising on
absence. So these are not 401-gated; an authed client is used merely to exercise
the cookie-resolution path.
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient


def _missing_uuid() -> str:
    """A syntactically valid UUID that is guaranteed absent from the DB."""
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# REACHABLE raw-404 paths -> nested NOT_FOUND envelope (the behaviour we lock in).
# ---------------------------------------------------------------------------
async def test_complete_missing_wip_is_nested_404(plant_user_client: AsyncClient) -> None:
    """``POST /api/others/wips/{id}/complete`` for an absent WIP raises a raw
    ``HTTPException(404, "WIP not found")`` which the global handler renders as the
    nested ``{"error": {"code": "NOT_FOUND", ...}}`` envelope. ``wips`` exists in
    the test DB, so this raw-404 path is genuinely reached."""
    res = await plant_user_client.post(f"/api/others/wips/{_missing_uuid()}/complete")
    assert res.status_code == 404, res.text
    body = res.json()
    assert "detail" not in body, res.text  # NOT the raw FastAPI {"detail": "..."}
    assert body["error"]["code"] == "NOT_FOUND", res.text
    assert body["error"]["message"] == "WIP not found", res.text


async def test_confirm_delivery_missing_order_is_nested_404(
    plant_user_client: AsyncClient,
) -> None:
    """``POST /api/others/orders/{id}/confirm-delivery`` for an unknown order hits
    the raw ``HTTPException(404, "Order not found")`` (``get_real_order`` returns
    None) BEFORE any ``samples`` query, so the 404 is reachable and normalized to
    the nested envelope."""
    res = await plant_user_client.post(f"/api/others/orders/{_missing_uuid()}/confirm-delivery")
    assert res.status_code == 404, res.text
    assert res.json()["error"]["code"] == "NOT_FOUND", res.text


# ---------------------------------------------------------------------------
# SHADOWED / MASKED paths — assert the CURRENT (buggy) behaviour so a fix flags.
# ---------------------------------------------------------------------------
async def test_get_order_by_no_route_is_shadowed_by_int_route(
    plant_user_client: AsyncClient,
) -> None:
    """``GET /api/orders/{order_no}`` (others.py, str param) is shadowed by the
    orders router's ``int``-typed ``GET /api/orders/{order_id}``. A non-numeric
    order_no fails int coercion -> 422 VALIDATION_ERROR; the others.py raw-404 for
    a missing order_no never runs. (Documents the route-shadowing inconsistency.)"""
    res = await plant_user_client.get("/api/orders/NOT-A-NUMERIC-ORDER-NO")
    assert res.status_code == 422, res.text
    assert res.json()["error"]["code"] == "VALIDATION_ERROR", res.text


async def test_numeric_unknown_order_is_handled_by_orders_router(
    plant_user_client: AsyncClient,
) -> None:
    """A numeric path is served by the orders router (NOT others.py): unknown id
    -> nested NOT_FOUND, proving which router actually owns this URL."""
    res = await plant_user_client.get("/api/orders/424242")
    assert res.status_code == 404, res.text
    assert res.json()["error"]["code"] == "NOT_FOUND", res.text


async def test_generate_wips_missing_sample_table_is_500_database_error(
    plant_user_client: AsyncClient,
) -> None:
    """``POST /api/others/samples/{id}/generate-wips`` queries the ``samples``
    table, which is migration-only and ABSENT from the ``create_all`` test DB. The
    resulting ``SQLAlchemyError`` is normalized to 500 / DATABASE_ERROR by the
    global handler, BEFORE the route's own raw 404 ("Sample not found") can fire.
    We assert the masked behaviour so a future fix (real samples table in tests, or
    a guarded query) is caught."""
    res = await plant_user_client.post(f"/api/others/samples/{_missing_uuid()}/generate-wips")
    assert res.status_code == 500, res.text
    assert res.json()["error"]["code"] == "DATABASE_ERROR", res.text
