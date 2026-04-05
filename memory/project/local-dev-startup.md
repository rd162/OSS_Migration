---
name: local-dev-startup
description: How to run the Python app locally for development (test DB on :5433/:6380)
type: project
---

Local dev uses the test Docker containers (docker-compose.test.yml) for Postgres and Redis.

**Why:** No separate dev stack — reuse the already-running test infra.
**How to apply:** Use these env vars and commands when starting the app locally.

## Start infra

```bash
docker compose -f docker-compose.test.yml up -d
```

## Start Flask (port 5001)

```bash
cd target-repos/ttrss-python
SECRET_KEY=dev-secret-key-not-for-production \
DATABASE_URL=postgresql://ttrss_test:ttrss_test@localhost:5433/ttrss_test \
REDIS_URL=redis://localhost:6380/1 \
WTF_CSRF_ENABLED=False \
RATELIMIT_ENABLED=False \
FEED_CRYPT_KEY="" \
.venv/bin/flask --app "ttrss:create_app()" run --port 5001
```

## Start Celery worker (required for feed fetching)

```bash
SECRET_KEY=dev-secret-key-not-for-production \
DATABASE_URL=postgresql://ttrss_test:ttrss_test@localhost:5433/ttrss_test \
REDIS_URL=redis://localhost:6380/1 \
FEED_CRYPT_KEY="" \
.venv/bin/celery -A ttrss.celery_app worker --pool=solo --loglevel=info
```

Note: task_routes was removed so tasks go to default `celery` queue (no -Q needed).

## First-time DB setup

```bash
# Run migrations
SECRET_KEY=... DATABASE_URL=... .venv/bin/alembic upgrade head

# Create admin user + enable API (run once)
SECRET_KEY=... DATABASE_URL=... REDIS_URL=... .venv/bin/python -c "
from ttrss import create_app
from ttrss.extensions import db
from ttrss.models.user import TtRssUser
from ttrss.models.pref import TtRssUserPref
from ttrss.auth.password import hash_password
from datetime import datetime, timezone
cfg = {'TESTING':True,'WTF_CSRF_ENABLED':False,'RATELIMIT_ENABLED':False,
       'DATABASE_URL':'postgresql://ttrss_test:ttrss_test@localhost:5433/ttrss_test',
       'REDIS_URL':'redis://localhost:6380/1'}
app = create_app(cfg)
with app.app_context():
    admin = TtRssUser(login='admin', pwd_hash=hash_password('admin'), salt='',
                      access_level=10, email='admin@localhost', created=datetime.now(timezone.utc))
    db.session.add(admin)
    db.session.flush()
    pref = TtRssUserPref(owner_uid=admin.id, pref_name='ENABLE_API_ACCESS', value='true', profile=None)
    db.session.merge(pref)
    db.session.commit()
    print('Done')
"
```

## Bugs fixed (2026-04-06)

1. `FORCE_HTTPS` defaults to False — Talisman no longer redirects HTTP→HTTPS in dev
2. `dispatch()` wrapped in try/except — server errors return JSON not HTML
3. Celery `task_routes` removed — tasks now go to default queue, no `-Q feeds` needed
