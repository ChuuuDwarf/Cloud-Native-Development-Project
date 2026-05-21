# LIMS Backend (FastAPI)

Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) + Alembic + Celery + Redis + PostgreSQL.

See repo-level `CLAUDE.md` and `docs/integration_contract.md` for the team-wide conventions.

## Local development

```bash
# 1. Bring up Postgres + Redis via docker-compose (one-off, in another shell)
docker compose up postgres redis

# 2. Set up the Python venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# 3. Copy env file
cp .env.example .env

# 4. Generate the first migration from current models, then apply
alembic revision --autogenerate -m "0001 e initial schema"
alembic upgrade head

# 5. Run the API
uvicorn app.main:app --reload --port 8000

# 6. In other shells: Celery worker + beat
celery -A app.core.celery_app worker --loglevel=info
celery -A app.core.celery_app beat --loglevel=info
```

## Layout

```
app/
  main.py              # FastAPI factory
  routes.py            # Central router registry (mounts every module)
  core/                # config / database / security / celery_app / logging
  common/              # enums, schemas, dependencies, middleware, errors
  modules/<name>/      # router.py, schemas.py, service.py, repository.py, dependencies.py
  db/                  # Base + TimestampMixin + SQLAlchemy models
  workers/             # Celery tasks (escalation, email_sender)
alembic/               # Async migration setup; versions/ is .gitkept until first revision
tests/                 # pytest + httpx; E's tests live in tests/e_tests/
```

## Module pattern

`app/modules/users/` is the canonical reference — copy its shape when starting a new module:

| File | Purpose |
|---|---|
| `router.py` | FastAPI `APIRouter` — thin; declares routes + permission deps |
| `schemas.py` | Pydantic DTOs (`Create`, `Update`, `Response`, `Query`) |
| `service.py` | Business logic; orchestrates Repository + AuditLogService |
| `repository.py` | Async DB queries; takes `AsyncSession` |
| `dependencies.py` | FastAPI `Depends(...)` factories |

## Lint / Test

```bash
ruff check .                # lint
ruff format --check .       # format check
mypy app                    # type check
pytest                      # tests
pytest --cov=app            # with coverage
```

## API docs

After `uvicorn app.main:app --reload`:

- Swagger UI: <http://localhost:8000/api-docs>
- ReDoc: <http://localhost:8000/api-redoc>
- OpenAPI JSON: <http://localhost:8000/openapi.json>
- Health: <http://localhost:8000/health>

## Environment variables

See `.env.example`. Critical knobs:

- `DATABASE_URL` — async SQLAlchemy URL (`postgresql+asyncpg://...`)
- `REDIS_URL` — Celery broker + cache + SSE pub/sub
- `JWT_SECRET` — change in prod
- `EMAIL_BACKEND` — `file` (writes to `uploads/email_outbox.jsonl`) or `smtp`
- `UPLOADS_DIR` — where `app/modules/files` stores bytes
