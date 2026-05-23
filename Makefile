.PHONY: dev-frontend dev-backend dev install lint build up down frontend-format frontend-check backend-check check

BACKEND_PYTHON := backend/venv/bin/python
BACKEND_RUFF := backend/venv/bin/ruff
BACKEND_MYPY := backend/venv/bin/mypy

# 開發
dev-frontend:
	cd frontend && npm run dev

dev-backend:
	cd backend && . venv/bin/activate && uvicorn main:app --reload

install:
	cd frontend && npm install
	$(BACKEND_PYTHON) -m pip install -r backend/requirements.txt


lint:
	cd frontend && npm run lint
	$(BACKEND_RUFF) check backend

# Docker
build:
	docker compose build

up:
	docker compose up

down:
	docker compose down

# 一鍵啟動（需要 tmux 或兩個 terminal）
dev:
	@echo "請分別執行 make dev-frontend 和 make dev-backend"

frontend-format:
	cd frontend && npm run format

frontend-check:
	cd frontend && npm run format:check && npm run lint && npm run typecheck

backend-check:
	$(BACKEND_RUFF) format --check backend
	$(BACKEND_RUFF) check backend
	cd backend && ../$(BACKEND_MYPY) . && ../$(BACKEND_PYTHON) -m pytest

check: frontend-check backend-check
