.PHONY: install db-up db-down migrate migration seed server test

TEST_DATABASE_URL := postgresql+asyncpg://app:app@localhost:5432/app_test
# -T: no TTY, so these also work from scripts and agents.
PSQL := docker compose exec -T db psql -U app -d app -v ON_ERROR_STOP=1

# Install dependencies into .venv
install:
	poetry install

# Start Postgres and wait until it accepts connections
db-up:
	docker compose up -d --wait

# Stop Postgres (data is kept in the pgdata volume; add -v to delete it)
db-down:
	docker compose down

# Apply all migrations
migrate:
	poetry run alembic upgrade head

# Generate a migration from model changes: make migration msg="add foo"
migration:
	poetry run alembic revision --autogenerate -m "$(msg)"

# Insert starter data (does nothing if users already exist)
seed:
	poetry run python -m api.seed

# Apply migrations, then run the dev server with auto-reload on :8000
server: migrate
	poetry run uvicorn api.main:app --reload

# Recreate the app_test database, migrate it, and run the tests against it
test:
	$(PSQL) -c "DROP DATABASE IF EXISTS app_test WITH (FORCE)"
	$(PSQL) -c "CREATE DATABASE app_test"
	DATABASE_URL=$(TEST_DATABASE_URL) poetry run alembic upgrade head
	DATABASE_URL=$(TEST_DATABASE_URL) poetry run pytest
