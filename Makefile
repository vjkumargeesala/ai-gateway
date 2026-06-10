.PHONY: help setup install clean format lint type-check test test-cov check run dev up down restart logs build

# Default target — runs when you type just `make`
help:
	@echo "AI Gateway — available commands:"
	@echo ""
	@echo "  Setup"
	@echo "    make setup        Create venv and install all dependencies"
	@echo "    make install      Install dependencies (assumes venv exists)"
	@echo "    make clean        Remove venv, caches, and build artefacts"
	@echo ""
	@echo "  Development"
	@echo "    make run          Run the server (uvicorn, no reload)"
	@echo "    make dev          Run the server with auto-reload"
	@echo ""
	@echo "  Quality"
	@echo "    make format       Auto-format code with black"
	@echo "    make lint         Check formatting without modifying files"
	@echo "    make type-check   Run mypy type checker"
	@echo "    make test         Run all tests"
	@echo "    make test-cov     Run tests with coverage report"
	@echo "    make check        Run all checks (lint + type-check + test-cov)"
	@echo ""
	@echo "  Docker"
	@echo "    make build        Build the Docker image"
	@echo "    make up           Start services with docker-compose"
	@echo "    make down         Stop and remove containers"
	@echo "    make restart      Restart services"
	@echo "    make logs         Tail logs from running containers"

# ─── Setup ──────────────────────────────────────────────────────────────────

setup:
	@echo "Creating venv with Python 3.12..."
	python3.12 -m venv venv
	@echo "Installing dependencies..."
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements-dev.txt
	@echo ""
	@echo "Setup complete. Activate with: source venv/bin/activate"

install:
	./venv/bin/pip install -r requirements-dev.txt

clean:
	rm -rf venv .pytest_cache .coverage htmlcov .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "Cleaned"

# ─── Development ────────────────────────────────────────────────────────────

run:
	./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

dev:
	./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# ─── Quality Checks ─────────────────────────────────────────────────────────

format:
	./venv/bin/black app/ tests/

lint:
	./venv/bin/black --check app/ tests/

type-check:
	./venv/bin/mypy app/ --ignore-missing-imports

test:
	./venv/bin/pytest tests/ -v

test-cov:
	./venv/bin/pytest tests/ --cov=app --cov-report=term-missing --cov-fail-under=80

check: lint type-check test-cov
	@echo ""
	@echo "All checks passed ✓"

# ─── Docker ─────────────────────────────────────────────────────────────────

build:
	docker build -t ai-gateway:1.0.0 .
	@docker images ai-gateway

up:
	docker compose up -d
	@echo ""
	@echo "API running at http://localhost:8000"
	@echo "Docs at http://localhost:8000/docs"
	@echo "View logs with: make logs"

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f