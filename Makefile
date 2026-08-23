.PHONY: help install migrate seed test test-postgres run lint db-up db-down db-logs reset clean

PYTHON ?= python
POSTGRES_URL ?= postgresql+psycopg://habit:habit@localhost:5433/habit_tracker

help:  ## Show the available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

install:  ## Create a virtualenv and install the project with dev extras
	$(PYTHON) -m venv .venv
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/python -m pip install -e ".[dev]"

migrate:  ## Apply migrations to DATABASE_URL (SQLite by default)
	$(PYTHON) -m alembic upgrade head

seed:  ## Load User A (full board) and User B (empty board); safe to re-run
	$(PYTHON) -m app.seed

test:  ## Run the suite against SQLite
	$(PYTHON) -m pytest

test-postgres: db-up  ## Run the same suite against the docker-compose Postgres
	TEST_DATABASE_URL=$(POSTGRES_URL) $(PYTHON) -m pytest

run:  ## Serve the API (Phase 1 exposes /health only)
	$(PYTHON) -m uvicorn app.main:app --reload

db-up:  ## Start local Postgres and wait for it to accept connections
	docker compose up -d --wait

db-down:  ## Stop local Postgres (data volume is kept)
	docker compose down

db-logs:  ## Tail the Postgres logs
	docker compose logs -f postgres

reset:  ## Delete the local SQLite database, then migrate and seed from scratch
	rm -f habit_tracker.db
	$(MAKE) migrate
	$(MAKE) seed

clean:  ## Remove caches and build artefacts
	rm -rf .pytest_cache **/__pycache__ *.egg-info build dist
