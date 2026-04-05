# Plan 001 — Foundation

**Status:** DONE  
**Completed:** 2026-04-03 (1a), 2026-04-04 (1b)  
**Spec ref:** specs/001-foundation/spec.md  
**Constitution check:** P1 ✓ P2 ✓ P3 ✓ P4 ✓

---

## Technical Context

### Technology Stack

| Component | Choice | ADR |
|-----------|--------|-----|
| Language | Python 3.11 | — |
| Web framework | Flask 3.x | 0002 |
| ORM | SQLAlchemy 2.x (ORM + hybrid Core) | 0006 |
| DB | PostgreSQL (psycopg2 sync driver) | 0003 |
| Migrations | Alembic | 0006 |
| Plugin system | pluggy + importlib directory discovery | 0010 |
| Background workers | Celery + Redis (two-task fan-out) | 0011 |
| Session store | Redis (Flask-Login server-side sessions) | 0007 |
| Password hashing | argon2id (passlib), SHA1 dual-hash upgrade | 0008 |
| Credential encryption | Fernet (cryptography), MultiFernet key rotation | 0009 |
| Security headers | flask-talisman | 0002 |
| CSRF | Flask-WTF | 0002 |
| Feed parsing | feedparser + lxml (stubs in Phase 1; wired in Phase 2) | 0014 |
| HTTP client | httpx async (Celery workers only) | 0015 |
| Containerization | Docker Compose (dev) | — |

### PHP Source Files Covered

- `ttrss/schema/ttrss_schema_pgsql.sql` — 31 active tables modeled
- `ttrss/classes/pluginhost.php` — 24 hookspecs extracted
- `ttrss/classes/db.php` — Flask-SQLAlchemy replacement
- `ttrss/include/functions.php` — security functions (Phase 1a stubs)
- `ttrss/update.php` + `ttrss/include/rssfuncs.php` — Celery task stubs

---

## Graph Gate: Foundation Dimensions

Two graph dimensions gate Phase 1 completion:

### DB_TABLE Dimension

- Source: `tools/graph_analysis/output/db_table_graph.json`
- Gate: all 31 model tables appear in DB_TABLE graph; every table in graph has a model
- 7 communities authoritative for service boundaries in later phases
- 4 deprecated pre-v124 tables excluded by design (not a gap)

### Hook Dimension

- Source: `tools/graph_analysis/output/hook_graph.json`
- Gate: 24/24 hookspecs detected, IDs match PHP `HOOK_*` constants
- `firstresult=True` exclusively on `hook_auth_user` (1 REGISTERS edge in hook graph)
- 7 hook communities map to plugin groupings

---

## Phase 1a — Walking Skeleton

**Goal:** Runnable app with 10 core models, auth, and Docker.

**Modules created:**

```
ttrss/
├── __init__.py          # create_app() factory
├── config.py            # Environment-based config
├── extensions.py        # Flask extension instances (db, login_manager, celery)
├── models/
│   ├── feed.py          # ttrss_feeds
│   ├── entry.py         # ttrss_entries
│   ├── user.py          # ttrss_users
│   ├── user_entry.py    # ttrss_user_entries
│   ├── category.py      # ttrss_categories
│   ├── tag.py           # ttrss_tags
│   ├── label.py         # ttrss_labels
│   ├── user_label.py    # ttrss_user_labels2
│   ├── pref.py          # ttrss_prefs
│   └── pref_user.py     # ttrss_user_prefs (seed data)
├── auth/
│   └── security.py      # argon2id + Fernet + Flask-Login setup
└── tasks/
    └── feed_tasks.py    # Celery stubs (dispatch_feed_updates, update_feed)
docker-compose.yml       # PostgreSQL + Redis + Flask + Celery
```

**Gate:** App starts; 33 unit tests pass; DB_TABLE graph pending validation.

---

## Phase 1b — Complete Foundation

**Goal:** All 31 models, 24 hookspecs, Alembic baseline, Celery wired.

**Modules added:**

```
ttrss/models/
├── access_key.py        # ttrss_access_keys
├── archived_feed.py     # ttrss_archived_feeds
├── counters_cache.py    # ttrss_counters_cache
├── enclosure.py         # ttrss_enclosures
├── error_log.py         # ttrss_error_log
├── feedbrowser_cache.py # ttrss_feedbrowser_cache
├── filter.py            # ttrss_filters
├── filter_actions.py    # ttrss_filter_actions
├── filter_rules.py      # ttrss_filter_rules
├── label2.py            # ttrss_user_labels2 (extended)
├── plugin_storage.py    # ttrss_plugin_storage
├── saved_filters.py     # ttrss_saved_filters
├── sessions.py          # ttrss_sessions
└── (8 more tables...)   # remaining to 31
ttrss/plugins/
├── hookspecs.py         # 24 pluggy hookspecs
└── manager.py           # PluginManager Flask extension
migrations/
└── versions/001_baseline.py  # Alembic initial migration
```

**Gate:** DB_TABLE gate PASSED, Hook gate PASSED, Alembic baseline PASSED.

---

## Validation Workflow

```bash
# After Phase 1b code committed:
python tools/graph_analysis/validate_coverage.py \
    --graph-dir tools/graph_analysis/output \
    --python-dir target-repos/ttrss-python/ttrss

# Expected: 31/31 models matched in DB_TABLE, 24/24 hookspecs in Hook dimension
# Then: pytest --cov=ttrss --cov-fail-under=80
```

---

## Status: DONE

Both graph gates passed. Alembic baseline runs. 24/24 hookspecs confirmed. Phase 2 authorized.
