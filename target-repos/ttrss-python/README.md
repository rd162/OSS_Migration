# TT-RSS Python

A self-hosted RSS reader web application — a Python reimplementation of [Tiny Tiny RSS](https://tt-rss.org/).

**Stack:** Flask 3 · SQLAlchemy 2 · Celery · PostgreSQL 15 · Redis 7 · Vanilla JS SPA · nginx

## Features

- Full TT-RSS JSON API v14 (17 operations) — compatible with existing TT-RSS mobile clients
- Single-page application — responsive UI, no page reloads
- Background feed fetching via Celery Beat (configurable interval, default 5 min)
- Argon2id password hashing with automatic upgrade from legacy bcrypt/MD5 hashes
- Fernet-encrypted feed credentials at rest
- Extensible plugin system (pluggy, 14 hooks)
- CSRF protection, per-route rate limiting, structured JSON logging
- Multi-stage Docker image + nginx reverse proxy

## Requirements

- Python 3.11+
- PostgreSQL 15
- Redis 7
- Docker + Docker Compose v2
- [`uv`](https://docs.astral.sh/uv/) (recommended) or pip
- [`just`](https://just.systems/) (optional task runner)

## Quick start

### 1. Install dependencies

```bash
uv sync --extra dev
# or: pip install -e ".[dev]"
```

### 2. Start backing services

```bash
docker compose -f docker-compose.test.yml up -d
```

Starts an isolated PostgreSQL on `:5433` and Redis on `:6380`.

### 3. Bootstrap the dev database and admin user

```bash
just dev-setup
```

Creates the `ttrss_dev` database schema and an `admin` / `admin` user with API access enabled.

### 4. Start the app

```bash
just dev          # Flask dev server on http://localhost:5001
```

In a second terminal, start the feed worker:

```bash
DATABASE_URL=postgresql://ttrss_test:ttrss_test@localhost:5433/ttrss_dev \
REDIS_URL=redis://localhost:6380/1 \
FEED_CRYPT_KEY="" \
uv run celery -A ttrss.celery_app worker --pool=solo --loglevel=info
```

Log in at `http://localhost:5001` with `admin` / `admin`.

> `just dev` connects to `ttrss_dev`. Integration tests run `DROP ALL` on `ttrss_test` — never point the dev server there.

## Running tests

```bash
just test              # unit tests only (~2 s, no Docker)
just test-blueprints   # Flask handler tests
just test-int          # integration tests (requires Docker services)
just test-fe           # Playwright E2E (requires live server on :5001)
just check             # lint + unit tests + coverage gate
```

## Production deployment

### 1. Configure secrets

```bash
cp .env.production.example .env.production
cp .env.db.example .env.db
```

Generate required secrets:

```bash
# SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# FEED_CRYPT_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Fill both values into `.env.production`.

### 2. Build and start

```bash
docker build -t ttrss-python:latest .
docker compose -f docker-compose.prod.yml up -d
```

Services started: `nginx` (`:80`) → `web` (gunicorn) + `worker` (Celery) + `beat` (Celery Beat) + `db` + `redis`.

### 3. Run migrations

```bash
docker compose -f docker-compose.prod.yml exec web alembic upgrade head
```

### 4. Create the first admin user

```bash
docker compose -f docker-compose.prod.yml exec web python -c "
from ttrss import create_app
from ttrss.extensions import db
from ttrss.models.user import TtRssUser
from ttrss.auth.password import hash_password
from ttrss.prefs.ops import initialize_user_prefs, set_user_pref
from datetime import datetime, timezone
app = create_app()
with app.app_context():
    u = TtRssUser(login='admin', pwd_hash=hash_password('CHANGE_ME'),
                  access_level=10, email='admin@example.com',
                  created=datetime.now(timezone.utc))
    db.session.add(u)
    db.session.flush()
    initialize_user_prefs(u.id)
    set_user_pref(u.id, 'ENABLE_API_ACCESS', 'true')
    db.session.commit()
    print('Admin created')
"
```

### 5. Verify

```bash
docker compose -f docker-compose.prod.yml ps
curl -sf http://localhost/api/
```

## Configuration

All config is read from environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | — | Flask session signing key (32+ random bytes) |
| `DATABASE_URL` | Yes | — | PostgreSQL DSN `postgresql://user:pass@host/db` |
| `REDIS_URL` | Yes | — | Redis DSN `redis://host:port/db` |
| `FEED_CRYPT_KEY` | Yes (prod) | — | Fernet key for encrypted feed credentials |
| `FORCE_HTTPS` | No | `false` | Redirect HTTP→HTTPS (set `true` only without a proxy) |
| `RATELIMIT_ENABLED` | No | `true` | Enable per-route rate limiting |
| `FEED_UPDATE_INTERVAL` | No | `300` | Seconds between feed update runs |
| `CELERY_CONCURRENCY` | No | `2` | Celery prefork worker count |
| `SESSION_COOKIE_LIFETIME` | No | `86400` | Session lifetime in seconds |

## Migrating data from PHP TT-RSS

If you have an existing PHP TT-RSS installation, the `scripts/migrate/` directory contains tools to move your data:

```bash
# 1. Audit the source MySQL database
MYSQL_HOST=... MYSQL_USER=... MYSQL_PASS=... MYSQL_DB=... \
  ./scripts/migrate/pre_migration_audit.sh

# 2. Transfer MySQL → PostgreSQL
pgloader --dry-run scripts/migrate/pgloader.load   # verify first
pgloader scripts/migrate/pgloader.load

# 3. Convert PHP-serialized plugin storage to JSON
DATABASE_URL=postgresql://... python scripts/migrate/convert_php_serialized.py
```

## CI / CD

- **CI** (`ci.yml`): lint, tests, Docker build, and coverage gate on every push.
- **Deploy** (`deploy.yml`): triggers on `v*` tags — runs migrations and data conversion automatically.

```bash
git tag v1.0.0 && git push origin v1.0.0
```

## Project layout

```
ttrss/
├── __init__.py          # App factory
├── config.py            # 12-factor env-var configuration
├── celery_app.py        # Celery + Beat configuration
├── models/              # SQLAlchemy ORM models
├── auth/                # Password hashing, Flask-Login integration
├── blueprints/
│   ├── api/             # JSON API endpoint (17 operations)
│   ├── backend/         # UI actions (subscribe, OPML, prefs)
│   ├── prefs/           # Preferences modal API
│   └── public/          # SPA shell + static assets
├── feeds/               # Feed parsing, subscription, favicon fetching
├── articles/            # Filtering, labels, HTML sanitisation
├── tasks/               # Celery tasks (feed updates, housekeeping)
├── plugins/             # pluggy hook specs and built-in plugins
└── static/              # Vanilla JS SPA (app.js, style.css)

tests/
├── unit/                # Pure unit tests (no DB required)
├── blueprints/          # Flask test-client handler tests
├── integration/         # Live DB + Redis integration tests
└── frontend/            # Playwright E2E browser tests
```
