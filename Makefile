.PHONY: help install dev-api dev-front dev-worker dev-beat \
        migrate seed test lint typecheck security audit up down

help:
	@echo "ORACLE — BD for Law"
	@echo ""
	@echo "  make up           Start all services (Docker)"
	@echo "  make down         Stop all services"
	@echo "  make install      Install all dependencies"
	@echo "  make migrate      Run Alembic migrations"
	@echo "  make seed         Seed database"
	@echo "  make dev-api      Run FastAPI dev server"
	@echo "  make dev-front    Run React dev server"
	@echo "  make dev-worker   Run Celery worker"
	@echo "  make dev-beat     Run Celery beat scheduler"
	@echo "  make test         Run all tests"
	@echo "  make audit        Full code audit (lint + types + security)"

up:
	docker compose up

down:
	docker compose down

install:
	cd backend && pip install -r requirements-dev.txt --break-system-packages
	cd frontend && npm install

migrate:
	cd backend && alembic upgrade head

seed:
	cd backend && python -m scripts.seed_db

dev-api:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-front:
	cd frontend && npm run dev

dev-worker:
	cd backend && celery -A app.tasks.celery_app:celery_app worker --loglevel=info --concurrency=2

dev-beat:
	cd backend && celery -A app.tasks.celery_app:celery_app beat --loglevel=info --scheduler redbeat.RedBeatScheduler

test:
	cd backend && python -m pytest tests/ -v --cov=app --cov-report=term-missing

lint:
	cd backend && ruff check app/ tests/ && ruff format --check app/ tests/

typecheck:
	cd backend && mypy app/

security:
	cd backend && bandit -r app/ -ll

audit: lint typecheck security
	@echo "✅ All audits passed"
