"""Tests for the global exception handlers in ``app/core/error_handlers.py``.

These prove that EVERY error path returns the project's nested envelope::

    {"error": {"code": ..., "message": ...}}

regardless of origin: request validation, a raw ``HTTPException`` raised deep
in the order module, a route that does not exist, or an unhandled bug that
trips the catch-all handler.

The handlers are registered via ``register_exception_handlers(app)`` in
``app.main.create_app``. ``AppError`` (a subclass of ``HTTPException``) is
dispatched to the more-specific inline handler in ``app.main``; only raw
``HTTPException``s reach the global handler here.

``asyncio_mode = "auto"`` (pyproject.toml) auto-collects each ``async def
test_*`` as an asyncio test, so no module marker is needed.
"""

from __future__ import annotations

from httpx import ASGITransport, AsyncClient


async def test_body_validation_returns_nested_envelope(
    admin_client: AsyncClient,
) -> None:
    """A Pydantic body-validation failure (422) uses the nested envelope.

    Before activation this short-circuited to FastAPI's default
    ``{"detail": [ {loc, msg, ...} ]}`` shape; the global
    ``RequestValidationError`` handler now normalizes it.
    """
    # POST /api/machines with an empty body trips request validation for the
    # required fields, exercising the RequestValidationError handler.
    res = await admin_client.post("/api/machines", json={})

    assert res.status_code == 422, res.text
    body = res.json()
    assert "detail" not in body, res.text
    assert body["error"]["code"] == "VALIDATION_ERROR", res.text
    assert isinstance(body["error"]["message"], str)
    assert body["error"]["message"], "message should be non-empty"


async def test_raw_http_exception_404_carries_error_code(
    admin_client: AsyncClient,
) -> None:
    """A raw ``raise HTTPException(404, ...)`` in an order route now nests.

    ``GET /api/orders/{order_no}`` for an unknown order raises a bare
    ``HTTPException(status_code=404, detail="Order not found")`` (app/routes/
    others.py) — NOT an ``AppError`` — so it exercises the global
    ``HTTPException`` handler. It previously fell through to FastAPI's flat
    ``{"detail": "..."}`` with no ``error.code``; it now carries one.

    NOTE: a *non-numeric* order_no is required. There is a second binding
    ``GET /api/orders/{order_id}`` with ``order_id: int`` (app/routes/orders.py);
    a numeric path would match it instead, and a UUID would be rejected by that
    route's int validation with a 422 before reaching this 404 handler.
    """
    res = await admin_client.get("/api/orders/NO-SUCH-ORDER-XYZ")

    assert res.status_code == 404, res.text
    body = res.json()
    assert "detail" not in body, res.text
    assert body["error"]["code"] == "NOT_FOUND", res.text
    # The original raw detail string is preserved as the message.
    assert body["error"]["message"] == "Order not found", res.text


async def test_unknown_route_returns_nested_not_found(
    client: AsyncClient,
) -> None:
    """A request to a path with no matching route returns the nested envelope.

    Starlette raises ``HTTPException(404)`` for unmatched routes; the global
    ``StarletteHTTPException`` handler wraps it. This replaces the old inline
    status-404 handler that used to live in ``app.main``.
    """
    res = await client.get("/api/this-route-truly-does-not-exist")

    assert res.status_code == 404, res.text
    body = res.json()
    assert "detail" not in body, res.text
    assert body["error"]["code"] == "NOT_FOUND", res.text


async def test_catch_all_handler_wraps_unhandled_exception() -> None:
    """An unhandled non-HTTP exception is wrapped by the catch-all handler.

    We mount a throwaway route on the live ``app`` that raises a plain
    ``ValueError`` and drive it with ``raise_app_exceptions=False`` so the ASGI
    transport surfaces the handler's JSON response instead of re-raising.
    """
    from app.main import app

    route_path = "/api/_test_error_handlers_boom"

    @app.get(route_path, include_in_schema=False)
    async def _boom() -> None:
        raise ValueError("intentional boom for catch-all test")

    try:
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get(route_path)

        assert res.status_code == 500, res.text
        body = res.json()
        assert "detail" not in body, res.text
        assert body["error"]["code"] == "INTERNAL_SERVER_ERROR", res.text
    finally:
        # Remove the throwaway route so it cannot leak into other tests.
        app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != route_path]
