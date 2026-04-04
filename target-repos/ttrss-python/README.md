# TT-RSS Python

Python migration of [Tiny Tiny RSS](https://tt-rss.org/) — Flask + SQLAlchemy + Celery.

## Requirements

- Python 3.11+
- PostgreSQL 15
- Redis 7
- Docker (for containerised workflows)

## Development setup

```bash
pip install -e ".[dev]"
```

## Local verification

Run all checks locally without pushing to GitHub. Start the backing services first:

```bash
docker compose -f docker-compose.test.yml up -d
```

### Lint

```bash
ruff check ttrss/
mypy ttrss/ --ignore-missing-imports
DATABASE_URL=postgresql://ttrss_test:ttrss_test@localhost:5433/ttrss_test \
  alembic upgrade head && alembic check
```

### Tests

```bash
DATABASE_URL=postgresql://ttrss_test:ttrss_test@localhost:5433/ttrss_test \
REDIS_URL=redis://localhost:6380/1 \
SECRET_KEY=dev \
FEED_CRYPT_KEY="" \
pytest tests/ -v --tb=short
```

### Migration coverage gate (≥95%)

Run from the project root (`OSS_Migration/`):

```bash
python tools/graph_analysis/build_php_graphs.py
python tools/graph_analysis/validate_coverage.py \
  --graph-dir tools/graph_analysis/output \
  --python-dir target-repos/ttrss-python/ttrss \
  --min-coverage 0.95
```

### Docker build

```bash
docker build .
```

## Production deployment

### 1. Configure secrets

```bash
cp .env.production.example .env.production   # fill in DATABASE_URL, SECRET_KEY, FEED_CRYPT_KEY
cp .env.db.example .env.db                   # fill in POSTGRES_PASSWORD
```

### 2. Build the image

```bash
docker build -t ttrss-python:latest .
```

### 3. Start the stack

```bash
docker compose -f docker-compose.prod.yml up -d
```

### 4. Run migrations

```bash
docker compose -f docker-compose.prod.yml exec web alembic upgrade head
```

### 5. Verify health

```bash
docker compose -f docker-compose.prod.yml ps
curl -sf http://localhost/api/
```

## Data migration from MySQL (TT-RSS PHP)

### Pre-migration audit

```bash
MYSQL_HOST=... MYSQL_USER=... MYSQL_PASS=... MYSQL_DB=... \
  ./scripts/migrate/pre_migration_audit.sh
```

### pgloader (MySQL → PostgreSQL)

```bash
MYSQL_USER=... MYSQL_PASS=... MYSQL_HOST=... MYSQL_DB=... \
PG_USER=... PG_PASS=... PG_HOST=... PG_DB=... \
pgloader --dry-run scripts/migrate/pgloader.load   # verify first

pgloader scripts/migrate/pgloader.load             # full run
```

### Convert PHP-serialized plugin storage

```bash
DATABASE_URL=postgresql://... python scripts/migrate/convert_php_serialized.py
```

## GitHub CI

The CI pipeline (`.github/workflows/ci.yml`) runs lint, tests, Docker build, and the coverage
gate automatically on every push. It is optional for solo use — the local checks above are
equivalent. The deploy workflow (`.github/workflows/deploy.yml`) triggers on `v*` tags and
runs pgloader + blob conversion automatically.
