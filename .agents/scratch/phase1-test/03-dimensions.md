---
phase: 1
step: "∆3"
title: Dimension Inference
status: complete
app: TT-RSS (Tiny Tiny RSS)
archetype: "Web application + Daemon"
source: source-repos/ttrss-php/ttrss
---

# ∆3 — Dimension Inference

Inferred from: (a) archetype detected in ∆1, (b) ∆2 research grounding,
(c) source inventory evidence (grep-verified).
Every dimension carried forward has at least one concrete source citation.

---

## Archetype detection (from ∆1)

| Archetype            | Evidence                                                                                     |
| -------------------- | -------------------------------------------------------------------------------------------- |
| **Web application**  | `index.php` (HTTP entry), `backend.php` (AJAX dispatch), `prefs.php`, `public.php`          |
| **REST/JSON API**    | `api/index.php` + `classes/api.php` — JSON RPC over HTTP, session-keyed                     |
| **Daemon**           | `update_daemon2.php` — `pcntl_fork()`, `SIGCHLD` handler, lock files, `MAX_JOBS` slots      |
| **Plugin host**      | `classes/pluginhost.php` — 24 named `HOOK_*` constants, `add_hook` / `run_hooks`            |

Primary archetype: **Web application + Plugin host**.
Secondary: **Daemon / background job**.
Tertiary: **REST/RPC API service** (same codebase, separate entry point).

---

## Candidate dimensions evaluated

### Universal dimensions (always carry forward)

| # | Dimension | Evidence | Verdict |
|---|-----------|----------|---------|
| U1 | Call graph | 1 206 nodes, 2 086 edges — extracted by `build_php_graphs.py` | **KEEP** |
| U2 | Module / include graph | 139 nodes, 66 edges — extracted | **KEEP** |
| U3 | Class hierarchy | 81 nodes, 27 edges — extracted | **KEEP** |
| U4 | File inventory | 138 PHP files, 246 SQL, 832 JS — enumerated | **KEEP** (merged into source-index spec) |

### Web-application dimensions

| # | Dimension | Evidence | Verdict |
|---|-----------|----------|---------|
| W1 | Entity / schema graph | `schema/ttrss_schema_pgsql.sql` — 35 `CREATE TABLE` stmts, explicit `REFERENCES` FK constraints, extracted db_table_graph: 60 nodes, 126 edges, 6 communities | **KEEP** |
| W2 | API / route surface | `classes/api.php` — 20 named handler methods; `backend.php` — class dispatch; `classes/rpc.php` — RPC methods | **KEEP** |
| W3 | Session / auth surface | `include/sessions.php` — custom `ttrss_open`/`ttrss_close`; `include/functions.php:authenticate_user` (SHA1); `classes/auth/base.php`; `HOOK_AUTH_USER` | **KEEP** |
| W4 | Plugin / hook graph | `classes/pluginhost.php` — 24 `HOOK_*` constants; hook_graph: 40 nodes, 39 edges, 7 communities | **KEEP** |
| W5 | Caching / counter graph | `include/ccache.php` — `ccache_update`, `ccache_find`; tables `ttrss_counters_cache` + `ttrss_cat_counters_cache` | **MERGED** into entity-schema + caching note |
| W6 | Background-job graph | `update_daemon2.php:pcntl_fork`, `SPAWN_INTERVAL`, `MAX_CHILD_RUNTIME`; `HOOK_UPDATE_TASK`, `HOOK_HOUSE_KEEPING` | **KEEP** |
| W7 | Template / view graph | Dojo toolkit SPA; templates rendered server-side via `lib/MiniTemplator.class.php` | **MERGED** into frontend-backend coupling |
| W8 | Security surface | SHA1 password (`pwd_hash` stores `SHA1:<hash>`); mcrypt AES-128-CBC in `include/crypt.php`; CSRF tokens; XSS via `include/functions2.php:sanitize` | **KEEP** — 3 critical security findings |

### Daemon dimensions

| # | Dimension | Evidence | Verdict |
|---|-----------|----------|---------|
| D1 | Background-job graph | (see W6) | **KEEP** |
| D2 | Concurrency / scheduling | `declare(ticks=1)`, `pcntl_signal`, `MAX_JOBS=2`, lockfiles | **MERGED** into background-daemon spec |

### Cross-cutting dimensions

| # | Dimension | Evidence | Verdict |
|---|-----------|----------|---------|
| X1 | Frontend / backend coupling | Dojo toolkit AJAX calling `backend.php?op=<class>&method=<fn>`; `index.php` renders SPA shell; no SSR templates beyond login page | **KEEP** |
| X2 | Configuration / feature-flag | `EXPECTED_CONFIG_VERSION=26`, `SCHEMA_VERSION=124`, `define_default()` everywhere; `config.php-dist` as template | **MERGED** into entity-schema + deployment note |
| X3 | Internationalisation | `locale/` — 14 languages; `include/functions.php:startup_gettext`; `lib/gettext/` custom gettext | **NOTED** — incorporated in security/auth spec |
| X4 | Security surface | (see W8) | **KEEP** |

---

## Final confirmed dimension set (10)

Named dimensions, in rationale-ordered sequence.
Numbers assigned at synthesis time (∆8).

| # | Dimension slug | Graph artifact | Purpose for modernisation |
|---|----------------|---------------|--------------------------|
| 01 | `call-graph` | `call_graph.json` | Phase-ordering: call-hierarchy drives migration sequence |
| 02 | `entity-schema` | `db_table_graph.json` | Migrate DB layer first; FK DAG determines table bootstrap order |
| 03 | `include-graph` | `include_graph.json` | File-level dependency order; bootstrap vs leaf modules |
| 04 | `class-hierarchy` | `class_graph.json` | Python class mapping; interface → ABC; singleton → module-level |
| 05 | `hook-extension` | `hook_graph.json` | pluggy hookspec mapping; 24 hooks → 24 hookspecs |
| 06 | `api-route-surface` | *(grep-derived)* | Flask Blueprint + route-to-handler mapping |
| 07 | `session-auth` | *(grep-derived)* | Flask-Login + argon2id replacement; OTP TOTP parity |
| 08 | `background-daemon` | *(grep-derived)* | Celery + Redis replaces pcntl_fork; task fan-out model |
| 09 | `security-surface` | *(grep-derived)* | SHA1→argon2id, mcrypt→cryptography.Fernet; CSRF mapping |
| 10 | `frontend-backend` | *(grep-derived)* | Dojo→Vanilla JS SPA; AJAX contract with Flask routes |

**Count: 10 dimensions** — within 6–12 target.

---

## Dimensions dropped with rationale

| Dimension | Reason dropped |
|-----------|---------------|
| File inventory (table only) | Incorporated as §"Source index" in entity-schema spec |
| Counter-cache graph | Fully contained within entity-schema (two cache tables) |
| Template / view graph | MiniTemplator is a thin library; actual view graph is JS SPA — folded into frontend-backend |
| Configuration surface | No separate graph needed; constants documented in each affected spec |
| i18n / l10n | GNU gettext with standard Python `babel`/`gettext` replacement; one-paragraph note in session-auth |
| Concurrency graph | No separate topology; all concurrency is pcntl_fork — fully described in background-daemon |

---

## Dimension interdependencies

```text
entity-schema (level 0 — migrate first)
    ↓ FK DAG determines bootstrap order
class-hierarchy (level 1 — Python model classes from schema)
    ↓ class shapes drive
call-graph (level 2 — function-level migration order)
    ↓ call communities map to
api-route-surface  ←── session-auth
hook-extension     ←── background-daemon
    ↓ all constrained by
security-surface (cross-cutting — remediation in every spec)
frontend-backend (level-max — last; depends on all above)
```

---

## Evidence summary

```text
PHP files:   138 (source-repos/ttrss-php/ttrss/**/*.php)
SQL files:   246 (schema/ttrss_schema_pgsql.sql + versions/)
JS files:    832 (js/*.js — Dojo toolkit SPA)
DB tables:    35 (from CREATE TABLE count in pgsql schema)
Hook consts:  24 (HOOK_ARTICLE_BUTTON … HOOK_HOUSE_KEEPING)
API methods:  20+ (classes/api.php function declarations)
Locales:      14 (locale/ subdirectory count)
```

---

*Generated: ∆3 dimension inference. Input: ∆1 inventory + ∆2 research grounding.*
*Next: ∆4 graph validation, ∆5 community budget.*
