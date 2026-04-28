.PHONY: dev-frontend dev-backend dev install lint build up down

# 開發
dev-frontend:
	cd frontend && npm run dev

dev-backend:
	cd backend && source venv/bin/activate && uvicorn main:app --reload

install:
	cd frontend && npm install
	cd backend && pip install -r requirements.txt


lint:
	cd frontend && npm run lint
	cd backend && ruff check .

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