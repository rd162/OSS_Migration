# Local CI — lint, test, coverage gate.
# All checks run against local .venv; test services (postgres + redis) run in Docker.
#
# Usage:
#   make check          — full suite: lint + test + coverage
#   make lint           — ruff + mypy + alembic drift check
#   make test           — unit tests (no Docker needed, in-memory DB)
#   make test-int       — all tests including integration (starts Docker services)
#   make coverage       — migration coverage gate (must pass with 0 gaps)
#   make services-up    — start postgres + redis for integration tests
#   make services-down  — stop test services
#   make clean          — remove .pytest_cache, coverage artefacts

PYTHON      := .venv/bin/python
PIP         := .venv/bin/pip
PYTEST      := .venv/bin/pytest
RUFF        := .venv/bin/ruff
MYPY        := .venv/bin/mypy
ALEMBIC     := .venv/bin/alembic

# Docker Compose V2 (plugin-based, most modern variant)
DC          := docker compose
TEST_COMPOSE := -f docker-compose.test.yml

# Coverage validator lives one level up (repo root contains source-repos + target-repos)
REPO_ROOT   := $(shell cd ../.. && pwd)
GRAPH_DIR   := $(REPO_ROOT)/tools/graph_analysis/output
PYTHON_DIR  := $(REPO_ROOT)/target-repos/ttrss-python/ttrss
VALIDATOR   := $(REPO_ROOT)/tools/graph_analysis/validate_coverage.py

# Test DB / Redis (from docker-compose.test.yml)
TEST_DB_URL    := postgresql://ttrss_test:ttrss_test@localhost:5433/ttrss_test
TEST_REDIS_URL := redis://localhost:6380/1

.PHONY: check lint test test-int coverage services-up services-down clean venv

# ─── Full suite ──────────────────────────────────────────────────────────────

check: lint test coverage
	@echo ""
	@echo "✓  All checks passed."

# ─── Lint ────────────────────────────────────────────────────────────────────

lint: _venv_check
	@echo "==> ruff"
	$(RUFF) check ttrss/
	@echo "==> mypy"
	$(MYPY) ttrss/ --ignore-missing-imports
	@echo "==> alembic check (migration drift)"
	DATABASE_URL=$(TEST_DB_URL) $(ALEMBIC) upgrade head
	DATABASE_URL=$(TEST_DB_URL) $(ALEMBIC) check
	@echo "✓  Lint passed."

# ─── Unit tests (no Docker) ──────────────────────────────────────────────────

test: _venv_check
	@echo "==> pytest unit"
	$(PYTEST) tests/unit/ -q --tb=short
	@echo "✓  Unit tests passed."

# ─── Integration tests (needs running services) ──────────────────────────────

test-int: services-up _venv_check
	@echo "==> pytest all (unit + integration)"
	DATABASE_URL=$(TEST_DB_URL) \
	REDIS_URL=$(TEST_REDIS_URL) \
	SECRET_KEY=ci-local-only \
	FEED_CRYPT_KEY="" \
	$(PYTEST) tests/ -q --tb=short
	@echo "✓  All tests passed."

# ─── Migration coverage gate ─────────────────────────────────────────────────

coverage: _venv_check
	@echo "==> migration coverage gate"
	@test -f "$(GRAPH_DIR)/call_graph.json" || \
		(echo "ERROR: Graph files not found in $(GRAPH_DIR)"; \
		 echo "       Run: python $(REPO_ROOT)/tools/graph_analysis/build_php_graphs.py"; \
		 exit 1)
	$(PYTHON) $(VALIDATOR) \
		--graph-dir $(GRAPH_DIR) \
		--python-dir $(PYTHON_DIR)
	@echo "✓  Coverage gate passed (0 gaps)."

# ─── Docker service helpers ──────────────────────────────────────────────────

services-up:
	@echo "==> starting test postgres + redis"
	$(DC) $(TEST_COMPOSE) up -d
	@echo "    waiting for postgres…"
	@until $(DC) $(TEST_COMPOSE) exec -T db_test pg_isready -U ttrss_test -q 2>/dev/null; do sleep 1; done
	@echo "✓  Services ready."

services-down:
	$(DC) $(TEST_COMPOSE) down -v

# ─── Helpers ─────────────────────────────────────────────────────────────────

clean:
	rm -rf .pytest_cache htmlcov .coverage coverage.xml test-results.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

venv:
	python3 -m venv .venv
	$(PIP) install -e ".[dev]"

_venv_check:
	@test -f "$(PYTHON)" || \
		(echo "ERROR: .venv not found. Run: make venv"; exit 1)
