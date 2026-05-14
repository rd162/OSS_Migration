---
phase: ∆2
status: DEGRADED — training knowledge only; no web search tools available during this session
date: 2025-01-27
fan-outs: 3 (source-platform | target-platform | modernization-pitfalls)
---

# ∆2 — External Knowledge Grounding

⚠ DEGRADED: All external search tools returned "server shut down" errors.
This note draws exclusively on training knowledge.
Claims below are marked [TRAINING] and should be spot-checked against
current sources (Flask docs, SQLAlchemy docs, Celery docs) before Phase 2 ADR drafting.

---

## Fan-out 1 — Source-Platform Patterns (PHP Web App + Daemon archetype)

**Application type confirmed:** TT-RSS is a multi-user, self-hosted RSS aggregator.
Archetype: Web Application + CLI Daemon (pcntl_fork multi-process worker).

### PHP Request Lifecycle [TRAINING]

- PHP processes are **stateless per request** — every HTTP request spawns
  a fresh PHP interpreter context.
- There is NO persistent in-process state between requests (contrast Python WSGI).
- `require_once` is effectively "import on first call per process lifetime";
  in a multi-process model this means each forked worker re-includes all files.
- Global variables (`$link`, `$_SESSION`, `$_POST`) are process-local.
- PHP sessions are typically file-backed or DB-backed;
  TT-RSS uses custom session handlers (`ttrss_open`, `ttrss_close`)
  backed by the `ttrss_sessions` table.

### PHP Front-Controller Pattern [TRAINING]

- `index.php` → bootstrap → `login_sequence()` → render SPA shell.
- `backend.php` → AJAX dispatcher — `op=` parameter routes to handler class.
- `api/index.php` → JSON API dispatcher — `op=` parameter routes to `API` class method.
- `update.php` / `update_daemon2.php` → CLI entry points (no HTTP).
- Pattern is a hand-rolled front controller, not an MVC framework.

### PHP Singleton / DB Abstraction [TRAINING]

- `Db::get()` returns a singleton DB wrapper (supports MySQL/MySQLi/PDO/PostgreSQL).
- Global wrapper functions (`db_query`, `db_fetch_assoc`, `db_num_rows`, etc.)
  delegate to the singleton, allowing procedural code in include files to
  call DB without explicit dependency injection.
- This pattern (global-function DB facade over a singleton) is the primary
  PHP anti-pattern that makes direct PHP → Python porting non-trivial.

### PHP Plugin / Hook System [TRAINING]

- `PluginHost` is a singleton registry with 24 named hook constants.
- Plugins extend `Plugin` abstract class; loaded via `require_once`
  in a directory scan (`load_user_plugins`).
- Hook invocation: `run_hooks($hook_id, &$param)` passes a reference;
  PHP's pass-by-reference semantics allow in-place mutation of the hook parameter.
- No formal plugin isolation — plugins can call any global function.

### PHP Daemon (update_daemon2.php) [TRAINING]

- Uses `pcntl_fork()` to create `MAX_JOBS` worker children.
- Master process loops with `sleep(SPAWN_INTERVAL)`, reaps children via `SIGCHLD`.
- Each child calls `update_daemon_common()` → updates a batch of feeds.
- Lock files in `LOCK_DIRECTORY` prevent overlapping runs.
- No message queue; workers pull from DB (`ttrss_feeds.last_updated`,
  `last_update_started`) to claim work.

### PHP Security Patterns (TT-RSS specific) [TRAINING]

- **Password hash**: `SHA1:<sha1(password)>` stored in `ttrss_users.pwd_hash`.
  Salted variant: `SHA1:<sha1(salt + password)>` with salt in `ttrss_users.salt`.
  ⚠ SHA1 is cryptographically broken for password hashing.
- **Feed credential encryption**: `crypt.php` uses PHP `mcrypt` extension
  (removed in PHP 7.2) with AES-128-CBC. ⚠ Deprecated / removed.
- **CSRF**: manual token in `$_SESSION['csrf_token']` validated via `validate_csrf()`.
- **XSS**: `sanitize()` in `include/functions2.php` uses HTML purification.
- **Session fixation**: `session_regenerate_id()` called on login.

---

## Fan-out 2 — Target-Platform Best Practices (Python / Flask) [TRAINING]

### Flask Application Architecture

- Flask uses WSGI; a single process serves multiple requests via a thread pool
  (or gevent/gunicorn workers). State CAN persist between requests in worker memory.
- Request context: `flask.g` (per-request), `flask.session` (cookie/Redis-backed),
  `flask.request` (incoming), `flask.current_app` (application).
- Blueprint-based routing replaces the hand-rolled `op=` dispatcher.
- Application factory pattern (`create_app()`) replaces global state at module level.

### SQLAlchemy ORM

- Declarative models replace `CREATE TABLE` SQL and global `db_query()` calls.
- `Session` object (per-request via `scoped_session` or Flask-SQLAlchemy) manages
  transactions; explicit `commit()` / `rollback()` replaces PHP `db_query("BEGIN")`.
- FK relationships expressed as `relationship()` with `backref`.
- `Alembic` manages schema migrations (replaces `DbUpdater` / `schema/versions/`).

### Flask-Login

- `LoginManager`, `login_user()`, `logout_user()`, `current_user` proxy.
- `UserMixin` + `load_user` callback replace PHP `validate_session()` / `$_SESSION`.
- Session stored in signed cookie (client-side) or Redis (server-side).
- Multi-user support: `current_user.id` replaces `$_SESSION['uid']`.

### Celery + Redis (daemon replacement)

- `Celery` app with `beat` scheduler replaces `update_daemon2.php`.
- Task `@app.task def update_feeds_task()` replaces `update_daemon_common()`.
- `MAX_JOBS` concurrency → Celery worker concurrency (`-c N`).
- Redis as broker and result backend.
- Lock/deduplication: Redis `SET NX EX` or Celery `task.apply_async(countdown=...)`.

### Password Hashing

- `argon2-cffi` (`argon2.PasswordHasher`) replaces SHA1.
- Dual-hash migration path: on login, verify old SHA1; if match, re-hash with argon2id.

### Feed Credential Encryption

- `cryptography` package with `Fernet` (AES-128-GCM + HMAC) replaces mcrypt AES-128-CBC.
- Key stored in environment variable `FEED_CRYPT_KEY`; not in config.php.

### Feed Parsing

- `feedparser` library (Python) handles Atom 1.0, RSS 2.0, RSS 0.9x.
- `lxml` for HTML sanitization replacing TT-RSS's custom `sanitize()`.
- `httpx` (async) for feed HTTP fetching inside Celery workers.

### Plugin System

- `pluggy` (PyPI) replaces PluginHost — supports hook specifications,
  caller-side wrappers, and `firstresult` / `historic` modes.
- Plugins as installable packages or directory-discovered Python files.
- `importlib.import_module()` for directory-based plugin discovery.

---

## Fan-out 3 — Modernization Pitfalls (PHP → Python) [TRAINING]

### Category 1: Statelessness Inversion

- **PHP**: stateless per request (re-initialise everything).
  **Python/Flask**: stateful worker process (module-level objects persist).
- **Trap**: PHP singletons (`Db::get()`, `PluginHost::getInstance()`,
  `Logger::get()`) are re-created per request in PHP but persist in Python.
  → Must convert to Flask application-context singletons or use DI.
- **Frequency**: Every call to `Db::get()`, `PluginHost::getInstance()`,
  or any global function that uses `$GLOBALS`. Affects ~100% of codebase.

### Category 2: Pass-by-Reference Hook Parameters

- **PHP**: `run_hooks($hook_id, &$param)` passes by reference — plugins mutate in place.
  **Python**: no pass-by-reference for scalars/strings; mutable containers only.
- **Trap**: Hook parameter passed as a Python string gets replaced not mutated.
  → Use a container (dict or list wrapper) for hook parameters; or pluggy's
  `firstresult` / chaining patterns.
- **Frequency**: All 24 hooks. Affects hook-heavy paths (HOOK_SANITIZE, HOOK_FEED_PARSED).

### Category 3: SQL Portability

- **PHP**: TT-RSS has MySQL/PostgreSQL SQL branches (e.g., `SUBSTRING_FOR_DATE`,
  `DATE_SUB` vs `NOW() - INTERVAL`).
  **Python**: SQLAlchemy dialect abstraction handles most differences.
- **Trap**: Raw SQL strings with MySQL-only or PostgreSQL-only syntax
  embedded in procedural functions — must be converted to SQLAlchemy expressions.
- **Frequency**: ~50+ db_query() call sites with inline SQL.

### Category 4: PHP Boolean / NULL Handling

- **PHP**: `sql_bool_to_bool()` converts DB strings `'t'/'f'` (pgsql) or `1/0` (mysql).
  **Python/SQLAlchemy**: Boolean columns return Python `True`/`False` directly.
- **Trap**: Comparison logic `if ($row['unread'] == 'f')` → must be rewritten.
- **Frequency**: ~30+ call sites in `include/functions.php`, `include/functions2.php`.

### Category 5: mcrypt → cryptography Library

- **PHP**: `mcrypt_encrypt` / `mcrypt_decrypt` with MCRYPT_RIJNDAEL_128.
  **Python**: `Fernet` or `cryptography.hazmat.primitives.ciphers.AES`.
- **Trap**: IV handling differs; PHP `mcrypt_create_iv` → Python `os.urandom(16)`.
  Ciphertext format (`$iv_base64:$encstr_base64`) must be preserved
  for existing encrypted credentials or a migration step performed.
- **Frequency**: `crypt.php` encrypt_string / decrypt_string. Low frequency (feed auth).

### Category 6: SHA1 Password Migration

- **PHP**: `SHA1:<sha1>` or `SHA1:<sha1(salt+pass)>` stored raw.
  **Python**: argon2id via `argon2-cffi`.
- **Trap**: Existing user passwords must be migrated without forcing password resets.
  → Dual-hash path: detect `SHA1:` prefix on login, verify, re-hash with argon2id.
- **Frequency**: All user logins until migration complete. One-time concern.

### Category 7: pcntl_fork → Celery

- **PHP**: Fork-based parallelism, lock files, SIGCHLD/SIGTERM handlers.
  **Python**: Celery task queue with Redis broker.
- **Trap**: "Last update started" anti-collision logic in DB must be replicated
  in Celery as a task lock (Redis SET NX or Celery single-instance task).
- **Frequency**: All feed update scheduling logic in `update_daemon2.php`.

### Category 8: PHP Sessions → Flask-Login + Redis

- **PHP**: Custom session handlers writing to `ttrss_sessions` table.
  **Python**: Flask-Login + Redis (server-side) or signed cookie (client-side).
- **Trap**: `$_SESSION['uid']` accessed globally across all handler code.
  Must be replaced with `current_user.id` everywhere.
  SINGLE_USER_MODE special case must be preserved.
- **Frequency**: ~80+ session accesses throughout the codebase.

### Category 9: PHP Array → Python list/dict

- **PHP**: Arrays are ordered hashmaps serving as both list and dict.
  `array_push`, `array_map`, `array_filter`, `array_keys`, etc.
  **Python**: Separate `list` and `dict` types with different APIs.
- **Trap**: PHP `array('key' => val, ...)` → Python `{'key': val}`;
  PHP `array(val, ...)` → Python `[val, ...]`.
  `array_map` → list comprehension or `map()`.
- **Frequency**: Very high — every function returning data uses arrays.

### Category 10: Gettext i18n

- **PHP**: `_()` / `__()` GNU gettext via custom gettext reader.
  **Python**: `flask_babel` or `python-gettext`; `_()` function registered globally.
- **Trap**: TT-RSS uses a custom PHP gettext reader (`lib/gettext/`).
  Python `gettext` stdlib or Babel/flask-babel can read the same `.mo` files.
- **Frequency**: ~150+ `__()` call sites throughout templates and PHP.

---

## Research Saturation Assessment

L5 topics: sessions, auth, DB-abstraction, hooks, daemon, feed-parsing, security, i18n
L4 areas: PHP-MVC, plugin-host, pcntl-daemon, ORM, task-queue, auth-session
L3 fields: Flask+Blueprint, SQLAlchemy, Celery, pluggy, Flask-Login, argon2, feedparser
L2 disciplines: security (SHA1, mcrypt), concurrency (fork→tasks), i18n (gettext)
L1 domains: web-application-modernization ✓

Gaps (would require web research to fill):
- Current Flask-Login version API changes post-2023
- Celery 5.x vs 4.x API differences
- Current pluggy version hook signature requirements
- feedparser 6.x Atom edge cases vs PHP FeedParser behaviour
- Python lxml sanitize vs TT-RSS sanitize() behavioural parity

All gaps flagged as Phase 2 ADR research items.

Status: PARTIAL — core patterns covered; version-specific details unverified.
