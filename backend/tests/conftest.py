"""Pytest fixtures for the LIMS backend.

Strategy
--------
* One test database (env ``TEST_DATABASE_URL``, falling back to a safe default).
* Session-scoped: drop & recreate every table from ``Base.metadata``, then run
  the dev seed once so each test starts from a known-good corpus.
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
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

# Python does not read .env files automatically.
# Load backend/.env manually before importing the app.
load_dotenv(BACKEND_ROOT / ".env")

# Important: point at the test DB *before* importing the app so the engine in
# ``app.core.database`` is created against the right URL.
#
# Recommended backend/.env settings:
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

# Force the app to use the test database during pytest.
os.environ["TEST_DATABASE_URL"] = TEST_DATABASE_URL
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-prod")


async def _ensure_test_database_exists(sqlalchemy_url: str) -> None:
    """Create the test database if it's missing.

    docker-compose only provisions the main DB; the test DB is not created by
    the container's entrypoint, so we connect to the maintenance ``postgres``
    database with asyncpg and issue a plain ``CREATE DATABASE`` when our target
    is missing.
    """

    # Strip the SQLAlchemy ``+asyncpg`` driver tag — asyncpg only understands
    # the bare ``postgresql://`` URL form.
    plain_url = sqlalchemy_url.replace("+asyncpg", "", 1)
    parsed = urlparse(plain_url)
    target_db = (parsed.path or "/").lstrip("/")

    if not target_db:
        return

    conn_kwargs = {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "user": parsed.username or "postgres",
        "password": parsed.password or "",
    }

    # Connect to the maintenance DB (``postgres``) to issue CREATE DATABASE.
    conn = await asyncpg.connect(database="postgres", **conn_kwargs)

    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            target_db,
        )

        if not exists:
            # asyncpg does not allow parameter binding for CREATE DATABASE.
            # target_db comes from DATABASE_URL, not user input, but we still
            # validate it to avoid surprises.
            if not target_db.replace("_", "").replace("-", "").isalnum():
                raise RuntimeError(f"Refusing to CREATE DATABASE with unsafe name: {target_db!r}")

            await conn.execute(f'CREATE DATABASE "{target_db}"')
    finally:
        await conn.close()


# Provision the test database before any module that creates an engine binds
# to it. Importing ``app.core.database`` builds the production engine eagerly.
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
    loop is currently running.
    """

    async def _setup() -> None:
        # Schema reset: own engine, disposed immediately.
        ddl_engine = create_async_engine(
            TEST_DATABASE_URL,
            future=True,
            poolclass=NullPool,
        )

        async with ddl_engine.begin() as conn:
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
            await conn.run_sync(Base.metadata.create_all)

        await ddl_engine.dispose()

        # Rebind the production engine to a NullPool one so connections do not
        # leak across event loops.
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


async def _build_authed_client(email: str, password: str) -> AsyncIterator[AsyncClient]:
    """Build a fresh AsyncClient logged in as the given user."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        assert res.status_code == 200, res.text
        yield ac


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Unauthenticated AsyncClient — for 401 tests and login flows."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def admin_client() -> AsyncIterator[AsyncClient]:
    async for c in _build_authed_client("admin@example.com", "Admin1234"):
        yield c


@pytest.fixture
async def plant_user_client() -> AsyncIterator[AsyncClient]:
    async for c in _build_authed_client("requester@example.com", "Reque1234"):
        yield c


@pytest.fixture
async def engineer_a_client() -> AsyncIterator[AsyncClient]:
    async for c in _build_authed_client("engineer@example.com", "Engin1234"):
        yield c


@pytest.fixture
async def engineer_b_client() -> AsyncIterator[AsyncClient]:
    async for c in _build_authed_client("engineer2@example.com", "Engin1234"):
        yield c


@pytest.fixture
async def supervisor_a_client() -> AsyncIterator[AsyncClient]:
    async for c in _build_authed_client("supervisor@example.com", "Super1234"):
        yield c


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """An AsyncSession against the test database.

    Tests can use this to set up rows that aren't reachable via the public
    API (e.g. notifications, which are produced internally by
    NotificationService.notify and have no POST endpoint). Cleanup is
    handled by the session-scoped DB reset — committed rows persist across
    tests within one pytest session, so tests should assert on presence of
    *their own* rows by title/id, not on collection sizes.
    """
    from app.core import database as db_module

    async with db_module.AsyncSessionLocal() as session:
        yield session
