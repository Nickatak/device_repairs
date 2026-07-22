.PHONY: help \
	env-init \
	docker-up docker-down docker-logs \
	db-makemigrations db-migrate superuser seed db-reset-hard \
	docker-shell-backend docker-shell-db \
	local-install local-check-db local-run-backend makemigrations test lint clean

BACKEND_PYTHON := .venv/bin/python
BACKEND_MANAGE := $(BACKEND_PYTHON) backend/manage.py
COMPOSE_BASE_FILE ?= docker-compose.yml
COMPOSE_LOCAL_FILE ?= docker-compose.local.yml
DEV_COMPOSE ?= docker compose -f $(COMPOSE_BASE_FILE) -f $(COMPOSE_LOCAL_FILE)
DB_SERVICE ?= db
BACKEND_SERVICE ?= backend

# ============================================================================
# HELP
# ============================================================================

help:
	@echo "device_repair_website - command reference"
	@echo ""
	@echo "Docker Dev Workflow (.env.local) - primary path"
	@echo "  make docker-up              Start db + backend (detached, with build)"
	@echo "  make docker-down            Stop the stack"
	@echo "  make docker-logs            Stream stack logs"
	@echo "  make db-makemigrations      Generate migrations (runs in backend container)"
	@echo "  make db-migrate             Apply migrations against the dev DB"
	@echo "  make superuser              Create a Django admin user"
	@echo "  make seed                   Seed the 3 real repair-log devices as inventory"
	@echo "  make seed-pricesheet        Seed/refresh the price sheet (lanes + rows + comp pulls)"
	@echo "  make db-reset-hard          Drop the DB volume and recreate the DB container"
	@echo ""
	@echo "  Frontend (Next) is served at http://localhost:3000 by the same stack."
	@echo ""
	@echo "Shell Access"
	@echo "  make docker-shell-backend   bash into the backend container"
	@echo "  make docker-shell-db        psql into the dev DB"
	@echo ""
	@echo "Host-Process Workflow (optional; runs Django on the metal)"
	@echo "  make local-install          Create .venv and install dev dependencies"
	@echo "  make local-run-backend      Wait for DB, then runserver on the host"
	@echo "  make makemigrations         Generate migrations via the host venv"
	@echo "  make test                   Run the backend test suite"
	@echo "  make lint                   ruff check backend/"
	@echo ""
	@echo "Utilities"
	@echo "  make env-init               Activate .env.local as .env"
	@echo "  make clean                  Remove Python build/cache artifacts"

# ============================================================================
# ENV
# ============================================================================

env-init:
	./scripts/toggle-env.sh local

# ============================================================================
# DOCKER DEV (.env.local) - primary path
# ============================================================================

docker-up: env-init
	$(DEV_COMPOSE) up -d --build

docker-down:
	$(DEV_COMPOSE) down --remove-orphans

docker-logs:
	$(DEV_COMPOSE) logs -f --tail=200

db-makemigrations:
	$(DEV_COMPOSE) exec -T $(BACKEND_SERVICE) python manage.py makemigrations

db-migrate:
	$(DEV_COMPOSE) exec -T $(BACKEND_SERVICE) python manage.py migrate

superuser:
	$(DEV_COMPOSE) exec $(BACKEND_SERVICE) python manage.py createsuperuser

seed:
	$(DEV_COMPOSE) exec -T $(BACKEND_SERVICE) python manage.py seed_inventory

seed-pricesheet:
	$(DEV_COMPOSE) exec -T $(BACKEND_SERVICE) python manage.py seed_pricesheet

db-reset-hard:
	@echo "This will destroy the DB volume and all data. Type 'yes' to confirm:"
	@read ans && [ "$$ans" = "yes" ] || (echo "Aborted."; exit 1)
	$(DEV_COMPOSE) down -v --remove-orphans
	$(DEV_COMPOSE) up -d $(DB_SERVICE)

docker-shell-backend:
	$(DEV_COMPOSE) exec $(BACKEND_SERVICE) bash

docker-shell-db:
	$(DEV_COMPOSE) exec $(DB_SERVICE) psql -U $${POSTGRES_USER:-repair} -d $${POSTGRES_DB:-device_repair}

# ============================================================================
# HOST PROCESS (optional)
# ============================================================================

local-install:
	python3 -m venv .venv
	$(BACKEND_PYTHON) -m pip install -r backend/requirements-dev.txt

local-check-db:
	@$(BACKEND_PYTHON) scripts/check_db_connection.py

local-run-backend: local-check-db
	$(BACKEND_MANAGE) runserver

makemigrations:
	$(BACKEND_MANAGE) makemigrations

test:
	$(BACKEND_MANAGE) test repairs --noinput

lint:
	.venv/bin/ruff check backend/

clean:
	find backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find backend -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Clean complete."

.DEFAULT_GOAL := help
