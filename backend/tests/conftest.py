"""Pytest fixtures for the LIMS backend.

Strategy
--------
* One test database (env ``TEST_DATABASE_URL``, falling back to ``DATABASE_URL``).
* Session-scoped: drop & recreate every table from ``Base.metadata``, then run
  the dev seed once so each test starts from a known-good corpus (4 roles, 4
  users, 3 labs, 3 departments, 3 storage locations, permission catalog).
* Function-scoped ``client``: httpx ``AsyncClient`` whose cookie jar is reset
  between tests, so a login in one test doesn't bleed into the next.

Tests that need to mutate shared rows should create their own rows; the seed
users are stable identities other tests rely on.
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from urllib.parse import urlparse

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

# Important: point at the test DB *before* importing the app so the engine in
# ``app.core.database`` is created against the right URL.
TEST_DATABASE_URL = os.environ.setdefault(
    "TEST_DATABASE_URL",
    os.environ.get("DATABASE_URL", "postgresql+asyncpg://lims:lims@localhost:5432/lims_test"),
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-prod")


async def _ensure_test_database_exists(sqlalchemy_url: str) -> None:
    """Create the test database if it's missing.

    docker-compose only provisions ``${POSTGRES_DB:-lims}``; the test DB
    (default ``lims_test``) is not created by the container's entrypoint, so
    we connect to the maintenance ``postgres`` database with asyncpg and issue
    a plain ``CREATE DATABASE`` when our target is missing. Keeping this in
    conftest means ``make test-backend`` works out of the box without a
    separate "create the test db" step that students will forget.
    """
    # Strip the SQLAlchemy ``+asyncpg`` driver tag — asyncpg only understands
    # the bare ``postgresql://`` URL form.
    plain_url = sqlalchemy_url.replace("+asyncpg", "", 1)
    parsed = urlparse(plain_url)
    target_db = (parsed.path or "/").lstrip("/")
    if not target_db:
        return

    conn_kwargs = {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "user": parsed.username,
        "password": parsed.password,
    }

    # Connect to the maintenance DB (``postgres``) to issue CREATE DATABASE.
    conn = await asyncpg.connect(database="postgres", **conn_kwargs)
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", target_db)
        if not exists:
            # asyncpg does not allow parameter binding for CREATE DATABASE.
            # target_db comes from the operator-supplied DATABASE_URL, not user
            # input, but we still validate it to avoid surprises.
            if not target_db.replace("_", "").replace("-", "").isalnum():
                raise RuntimeError(f"Refusing to CREATE DATABASE with unsafe name: {target_db!r}")
            await conn.execute(f'CREATE DATABASE "{target_db}"')
    finally:
        await conn.close()


# Provision the test database before any module that creates an engine binds
# to it (importing ``app.core.database`` builds the production engine eagerly).
asyncio.run(_ensure_test_database_exists(TEST_DATABASE_URL))


from app.core import database as db_module  # noqa: E402
from app.db import models  # noqa: F401, E402  -- attach all tables to Base.metadata
from app.db.base import Base  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _prepare_database() -> None:
    """Drop + recreate all tables, then run the dev seed once per session.

    Why this is sync-with-asyncio.run instead of an ``async`` fixture:
    pytest-asyncio's per-test event loops mean any connection created inside a
    session-scoped ``async`` fixture's loop is dead by the time tests run on
    their own loops, producing "attached to a different loop" RuntimeErrors.
    By running setup in its own one-shot loop and disposing every engine before
    returning, we guarantee no pool entries survive into the test loops.

    We also rebind ``db_module.engine`` / ``AsyncSessionLocal`` to a
    ``NullPool`` engine so every request opens a fresh connection on whatever
    loop is currently running — required because each ``async`` test runs in
    its own event loop under ``asyncio_mode = "auto"``.
    """

    async def _setup() -> None:
        # Schema reset (own engine, disposed immediately).
        ddl_engine = create_async_engine(TEST_DATABASE_URL, future=True, poolclass=NullPool)
        async with ddl_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        await ddl_engine.dispose()

        # Rebind the production engine to a NullPool one so connections do not
        # leak across event loops (pytest-asyncio creates a new loop per test).
        db_module.engine = create_async_engine(
            TEST_DATABASE_URL,
            future=True,
            poolclass=NullPool,
        )
        db_module.AsyncSessionLocal = async_sessionmaker(
            bind=db_module.engine,
            expire_on_commit=False,
            class_=AsyncSession,
            autoflush=False,
        )

        from scripts import seed_dev

        await seed_dev.main()

    asyncio.run(_setup())


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def admin_client(client: AsyncClient) -> AsyncClient:
    """A client already logged in as the seeded admin user."""
    res = await client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "Admin1234"},
    )
    assert res.status_code == 200, res.text
    return client


@pytest.fixture
async def plant_user_client(client: AsyncClient) -> AsyncClient:
    """A client logged in as the seeded plant_user (廠區使用者)."""
    res = await client.post(
        "/api/auth/login",
        json={"email": "requester@example.com", "password": "Reque1234"},
    )
    assert res.status_code == 200, res.text
    return client
