.PHONY: help install install-backend install-frontend \
	dev dev-backend dev-frontend worker beat \
	migrate revision seed \
	test test-backend test-frontend \
	lint lint-backend lint-frontend format \
	up down build infra logs

# ---------------------------------------------------------------------------
# Default target — short, scannable help text
# ---------------------------------------------------------------------------

help:
	@echo "LIMS Makefile targets"
	@echo ""
	@echo "  Local install"
	@echo "    install            install both stacks"
	@echo "    install-backend    pip install requirements + dev"
	@echo "    install-frontend   npm ci"
	@echo ""
	@echo "  Local dev (foreground; run each in its own shell)"
	@echo "    dev-backend        uvicorn app.main:app --reload   (port 8000)"
	@echo "    dev-frontend       next dev                        (port 3000)"
	@echo "    worker             celery -A app.core.celery_app worker"
	@echo "    beat               celery -A app.core.celery_app beat"
	@echo ""
	@echo "  DB"
	@echo "    migrate            alembic upgrade head"
	@echo "    revision msg=...   alembic revision --autogenerate -m \"\$$(msg)\""
	@echo "    seed               python scripts/seed_dev.py"
	@echo ""
	@echo "  Quality"
	@echo "    test               pytest + vitest"
	@echo "    lint               ruff + eslint"
	@echo "    format             ruff format + prettier"
	@echo ""
	@echo "  Docker"
	@echo "    infra              docker compose up postgres redis -d  (just infra)"
	@echo "    up                 docker compose up                    (full stack)"
	@echo "    down               docker compose down"
	@echo "    build              docker compose build"
	@echo "    logs               docker compose logs -f"

# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------

install: install-backend install-frontend

install-backend:
	cd backend && pip install -r requirements.txt -r requirements-dev.txt

install-frontend:
	cd frontend && npm ci

# ---------------------------------------------------------------------------
# Local dev
# ---------------------------------------------------------------------------

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

worker:
	cd backend && celery -A app.core.celery_app worker --loglevel=info

beat:
	cd backend && celery -A app.core.celery_app beat --loglevel=info

dev:
	@echo "在不同 shell 分別執行： make infra && make dev-backend && make dev-frontend && make worker && make beat"

# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------

migrate:
	cd backend && alembic upgrade head

revision:
	@if [ -z "$(msg)" ]; then echo "Usage: make revision msg=\"add foo\""; exit 1; fi
	cd backend && alembic revision --autogenerate -m "$(msg)"

seed:
	cd backend && python scripts/seed_dev.py

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

test: test-backend test-frontend

test-backend:
	cd backend && . .venv/bin/activate && pytest --cov=app

test-frontend:
	cd frontend && npm test --if-present

# ---------------------------------------------------------------------------
# Lint / format
# ---------------------------------------------------------------------------

lint: lint-backend lint-frontend

lint-backend:
	cd backend && ruff check . && ruff format --check . && mypy app

lint-frontend:
	cd frontend && npm run lint && npx tsc --noEmit

format:
	cd backend && ruff format . && ruff check --fix .
	cd frontend && npm run format

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------

infra:
	docker compose up postgres redis -d

up:
	docker compose up

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f
