.PHONY: help install install-backend install-frontend \
	dev dev-backend dev-frontend worker beat \
	migrate revision seed \
	test test-backend test-frontend \
	lint lint-backend lint-frontend format \
	up down build infra logs \
	devcontainer-net devcontainer-up \
	ci ci-backend ci-frontend ci-build ci-e2e ci-down

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
	@echo ""
	@echo "  Devcontainer (Zed / VS Code / Cursor)"
	@echo "    devcontainer-net   create lims_devnet (idempotent; required before compose up)"
	@echo "    devcontainer-up    devcontainer-net + start postgres/redis sidecars"
	@echo ""
	@echo "  CI reproducers (run the same steps as .github/workflows/ci.yml)"
	@echo "    ci-backend         ruff + mypy + alembic + pytest with coverage"
	@echo "    ci-frontend        eslint + tsc + next build + vitest --coverage"
	@echo "    ci-build           docker compose build with CI overlay"
	@echo "    ci-e2e             boot the full stack + run Playwright + dump logs"
	@echo "    ci                 all of the above, in order"
	@echo "    ci-down            tear down the CI stack (volumes + orphans)"

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

infra: devcontainer-net
	docker compose up postgres redis -d

# ---------------------------------------------------------------------------
# Devcontainer helpers
#
# The .devcontainer workspace attaches to an external docker network so it
# can reach the postgres/redis sidecars by service name. These targets give
# you a one-liner setup for the "before I open Zed" step.
# ---------------------------------------------------------------------------

devcontainer-net:
	@docker network inspect lims_devnet >/dev/null 2>&1 \
		|| docker network create lims_devnet

devcontainer-up: devcontainer-net
	docker compose up -d postgres redis

up: devcontainer-net
	docker compose up

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

# ---------------------------------------------------------------------------
# CI reproducers
#
# These targets run the same steps as .github/workflows/ci.yml so you can
# debug a failing pipeline locally without pushing a commit. They assume
# Postgres + Redis are reachable (use `make infra` first, or run ci-e2e
# which brings the whole stack up via docker compose).
# ---------------------------------------------------------------------------

CI_COMPOSE := docker compose -f docker-compose.yml -f docker-compose.ci.yml

ci: ci-backend ci-frontend ci-build ci-e2e

ci-backend:
	cd backend && ruff check . && ruff format --check . && mypy app
	cd backend && alembic upgrade head
	cd backend && pytest --cov=app --cov-report=term-missing \
		--cov-report=xml:coverage.xml --cov-report=html:htmlcov \
		--junitxml=pytest-junit.xml

ci-frontend:
	cd frontend && npm ci
	cd frontend && npm run lint && npm run typecheck && npm run build
	cd frontend && npx vitest run --coverage --passWithNoTests

ci-build:
	$(CI_COMPOSE) build

ci-e2e: devcontainer-net
	cp -n backend/.env.example backend/.env || true
	$(CI_COMPOSE) up -d --build postgres redis backend celery-worker celery-beat frontend
	@echo "Waiting for backend /health..."
	@for i in $$(seq 1 60); do \
		curl -fsS http://localhost:8000/health >/dev/null 2>&1 && break || sleep 2; \
	done
	$(CI_COMPOSE) exec -T backend alembic upgrade head
	$(CI_COMPOSE) exec -T backend python scripts/seed_dev.py
	@echo "Waiting for frontend..."
	@for i in $$(seq 1 60); do \
		code=$$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 || echo "000"); \
		[ "$$code" != "000" ] && [ "$$code" -lt 500 ] && break || sleep 2; \
	done
	cd tests/e2e && npm install && npx playwright install --with-deps chromium
	cd tests/e2e && FRONTEND_URL=http://localhost:3000 npx playwright test
	mkdir -p artifacts && $(CI_COMPOSE) logs --no-color --timestamps > artifacts/compose-logs.txt

ci-down:
	$(CI_COMPOSE) down -v --remove-orphans
