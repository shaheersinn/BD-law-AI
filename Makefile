# ORACLE — BD for Law · Makefile
# Run `make help` to see all commands.

.PHONY: help up down build seed migrate shell logs test lint \
        dev-api dev-front dev-worker dev-beat \
        train-churn train-urgency \
        install install-backend install-frontend \
        makemigration create-admin

# ── Help ──────────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "  ORACLE — BD for Law"
	@echo ""
	@echo "  ── Docker ────────────────────────────────────────────────────"
	@echo "  make up              Start all 6 services"
	@echo "  make down            Stop all services"
	@echo "  make build           Rebuild Docker images (after dep changes)"
	@echo "  make seed            Seed database with demo data"
	@echo "  make migrate         Run Alembic migrations"
	@echo "  make logs            Tail API + worker logs"
	@echo "  make shell           Python shell in API container"
	@echo ""
	@echo "  ── Local dev (no Docker) ─────────────────────────────────────"
	@echo "  make dev-api         FastAPI dev server (port 8000)"
	@echo "  make dev-front       Vite dev server (port 5173)"
	@echo "  make dev-worker      Celery worker"
	@echo "  make dev-beat        Celery beat scheduler"
	@echo ""
	@echo "  ── Tests & quality ───────────────────────────────────────────"
	@echo "  make test            Run all 45 tests"
	@echo "  make lint            Run ruff + mypy"
	@echo ""
	@echo "  ── ML training ───────────────────────────────────────────────"
	@echo "  make train-churn     Train churn XGBoost from CSV"
	@echo "  make train-urgency   Train urgency LightGBM from CSV"
	@echo ""
	@echo "  ── Setup ─────────────────────────────────────────────────────"
	@echo "  make install         Install Python + Node deps"
	@echo "  make create-admin    Create admin user (interactive)"
	@echo "  make makemigration MSG=\"description\"  Auto-generate migration"
	@echo ""

# ── Docker ────────────────────────────────────────────────────────────────────

up:
	docker compose up -d
	@echo ""
	@echo "  Dashboard:  http://localhost:3000"
	@echo "  API docs:   http://localhost:8000/api/docs"
	@echo "  Health:     http://localhost:8000/api/health"
	@echo ""

down:
	docker compose down

build:
	docker compose build --no-cache

seed:
	docker compose exec api python -m scripts.seed_db

migrate:
	docker compose exec api alembic upgrade head

shell:
	docker compose exec api python

logs:
	docker compose logs -f api worker

# ── Local dev ─────────────────────────────────────────────────────────────────

dev-api:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-front:
	cd frontend && npm run dev

dev-worker:
	cd backend && celery -A app.tasks.celery_app:celery_app worker --loglevel=info

dev-beat:
	cd backend && celery -A app.tasks.celery_app:celery_app beat --loglevel=info

# ── Tests & quality ───────────────────────────────────────────────────────────

test:
	cd backend && python -m pytest tests/ -v --tb=short

lint:
	cd backend && python -m ruff check app/ && python -m mypy app/ --ignore-missing-imports

# ── ML training ───────────────────────────────────────────────────────────────

train-churn:
	@echo "Training churn classifier..."
	@echo "Expected CSV: backend/data/churn_training_data.csv"
	@echo "Columns: total_billed, yoy_billing_change, matters_opened,"
	@echo "         days_since_last_matter, disputes_this_year, writeoff_pct,"
	@echo "         gc_changed, days_since_last_contact, practice_area_count, label"
	cd backend && python -m app.ml.churn_model --train --csv data/churn_training_data.csv

train-urgency:
	@echo "Training urgency model..."
	@echo "Expected CSV: backend/data/urgency_training_data.csv"
	cd backend && python -m app.ml.urgency_model --train --csv data/urgency_training_data.csv

# ── Setup ─────────────────────────────────────────────────────────────────────

install-backend:
	cd backend && pip install -r requirements.txt
	cd backend && python -m spacy download en_core_web_sm

install-frontend:
	cd frontend && npm install

install: install-backend install-frontend
	@echo "All dependencies installed."

create-admin:
	@echo "Creating admin user (requires running API)..."
	@read -p "Email: " EMAIL; \
	 read -p "Full name: " NAME; \
	 read -s -p "Password: " PASS; \
	 echo ""; \
	 curl -s -X POST http://localhost:8000/api/auth/users \
	   -H "Content-Type: application/json" \
	   -H "Authorization: Bearer $$(curl -s -X POST http://localhost:8000/api/auth/login \
	     -H 'Content-Type: application/json' \
	     -d '{"email":"admin@halcyon.legal","password":"admin123"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')" \
	   -d "{\"email\":\"$$EMAIL\",\"full_name\":\"$$NAME\",\"password\":\"$$PASS\",\"role\":\"admin\"}" | python3 -m json.tool

# ── Database ──────────────────────────────────────────────────────────────────

makemigration:
	@if [ -z "$(MSG)" ]; then echo "Usage: make makemigration MSG=\"description\""; exit 1; fi
	cd backend && alembic revision --autogenerate -m "$(MSG)"
