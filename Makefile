.PHONY: up down db test lint backend-dev frontend-dev

up:            ## full stack via Docker Compose (http://localhost:8080)
	docker compose up -d --build

down:
	docker compose down

db:            ## only Postgres and Redis, for local development
	docker compose up -d db redis

backend-dev:   ## Django dev server on :8000
	cd backend && uv run python manage.py migrate && uv run python manage.py runserver

frontend-dev:  ## Next.js dev server on :3000
	cd frontend && npm run dev

test:
	cd backend && uv run pytest -q
	cd frontend && npm test

lint:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run lint-imports
	cd frontend && npm run lint && npm run typecheck
