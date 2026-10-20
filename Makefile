.PHONY: help install run test test-cov lint format lint-fix migrate migrate-new migrate-down seed docker-up docker-down docker-logs clean

help:
	@echo "Available commands:"
	@echo "  install      Install dependencies"
	@echo "  run          Run development server"
	@echo "  test         Run tests"
	@echo "  test-cov     Run tests with coverage report"
	@echo "  lint         Run linter check"
	@echo "  format       Format code"
	@echo "  lint-fix     Fix linting errors"
	@echo "  migrate      Run database migrations"
	@echo "  migrate-new  Generate new migration revision (use m='migration message')"
	@echo "  migrate-down Rollback last migration"
	@echo "  seed         Seed database with demo data"
	@echo "  docker-up    Start Docker containers"
	@echo "  docker-down  Stop Docker containers"
	@echo "  docker-logs  Tail API logs from Docker"
	@echo "  clean        Remove cache and coverage artifacts"

install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest -v --tb=short

test-cov:
	pytest -v --tb=short --cov=app --cov-report=term-missing

lint:
	ruff check app tests

format:
	ruff format app tests

lint-fix:
	ruff check --fix app tests

migrate:
	alembic upgrade head

migrate-new:
	alembic revision --autogenerate -m "$(m)"

migrate-down:
	alembic downgrade -1

seed:
	python -m scripts.seed_demo

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f api

clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').glob('.pytest_cache')]; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').glob('.ruff_cache')]; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').glob('htmlcov')]; [p.unlink(missing_ok=True) for p in pathlib.Path('.').glob('.coverage*')]"
