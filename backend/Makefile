# ============================================================
# Flux Backend — Makefile
# Usage:  make <target>
# ============================================================

.PHONY: install install-dev dev test test-unit test-integration lint format migrate

# Install production dependencies
install:
	pip install -r requirements.txt

# Install production + development dependencies
install-dev:
	pip install -r requirements-dev.txt

# Start the FastAPI app (app.main) with auto-reload
dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run the full test suite with verbose output
test:
	pytest tests/ -v

# Run unit tests only (no database required)
test-unit:
	pytest tests/unit/ -v

# Run integration tests only (requires Supabase PostgreSQL)
test-integration:
	pytest tests/integration/ -v

# Check code formatting and lint rules (non-destructive)
lint:
	black dao_service/ --check
	ruff check dao_service/

# Auto-fix formatting and lint issues
format:
	black dao_service/
	ruff check dao_service/ --fix

# Apply database migrations via Alembic
migrate:
	alembic upgrade head
