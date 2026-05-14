---
phase: "∆6"
title: "Grep-Based Surface Research Notes — GS-1 through GS-5"
dimensions: [api-route-surface, session-auth, background-daemon, security-surface, frontend-backend]
method: "training-knowledge + source corpus reads (grep-derived, no graph extraction)"
status: "DEGRADED — no web search; training knowledge only [TRAINING]"
date: 2025-01-27
source: source-repos/ttrss-php/ttrss
---

# ∆6 — Grep-Based Surface Research Notes (GS-1 through GS-5)

⚠ DEGRADED: External search tools unavailable this session.
All findings draw on direct source corpus reads and training knowledge [TRAINING].
Verify version-specific details (Flask routing, Celery 5.x, httpx async) against
current documentation before Phase 2 ADR drafting.

---

## GS-1 — API / Route Surface

### Source files

| File | Role |
|------|------|
| `api/index.php` | JSON API front-controller entry point |
| `classes/api.php` | `API` class — 20+ handler methods |
| `classes/rpc.php` | `RPC` class — article/counter mutation methods |
| `backend.php` | AJAX dispatcher — op= routing to all handler classes |
| `classes/handler.php` | Abstract Handler base |
| `classes/handler/protected.php` | Auth-required handler base |
| `classes/handler/public.php` | Public (no-auth) handler base |

### API method inventory (from `classes/api.php`)

| Method | HTTP equiv | Purpose |
|--------|-----------|---------|
| `login` | POST | Authenticate → returns session_id |
| `logout` | POST | Invalidates session |
| `isLoggedIn` | GET | Session check |
| `getVersion` | GET | Returns TT-RSS version string |
| `getApiLevel` | GET | Returns API protocol version integer |
| `getUnread` | GET | Returns global unread article count |
| `getCounters` | GET | Returns per-feed + per-category unread counts |
| `getFeeds` | GET | Returns feed list (with cat_id filter) |
| `getCategories` | GET | Returns category tree |
| `getHeadlines` | GET | Returns article list for feed/cat/virtual-feed |
| `updateArticle` | POST | Set article flags (starred, read, published, score, note) |
| `getArticle` | GET | Returns full article content |
| `getConfig` | GET | Returns user configuration subset |
| `updateFeed` | POST | Triggers immediate feed update |
| `catchupFeed` | POST | Marks all articles in feed/cat as read |
| `getPref` | GET | Returns value of a user preference |
| `getLabels` | GET | Returns label list with article counts |
| `setArticleLabel` | POST | Assigns / removes a label from an article |
| `shareToPublished` | POST | Publishes an article to the public feed |
| `subscribeToFeed` | POST | Adds a new feed subscription |
| `unsubscribeFeed` | POST | Removes a feed subscription |
| `getFeedTree` | GET | Returns full feed tree (feeds + categories, BFS) |

### Backend.php handler dispatch (from `backend.php` + class listing)

Registered handler classes (op= values):

| op= value | Class | Auth required |
|-----------|-------|--------------|
| `feeds` | `Feeds` | Yes (Handler_Protected) |
| `rpc` | `RPC` | Yes |
| `article` | `Article` | Yes |
| `opml` | `Opml` | Yes |
| `dlg` | `Dlg` | Yes |
| `backend` | `Backend` | Yes |
| `pluginhandler` | `PluginHandler` | Delegated to plugin |
| `pref-feeds` | `Pref_Feeds` | Yes (admin for some) |
| `pref-filters` | `Pref_Filters` | Yes |
| `pref-labels` | `Pref_Labels` | Yes |
| `pref-prefs` | `Pref_Prefs` | Yes |
| `pref-system` | `Pref_System` | Yes (admin) |
| `pref-users` | `Pref_Users` | Yes (admin) |

Public handlers (no session required):

| op= value | Class | Notes |
|-----------|-------|-------|
| `public` | `Handler_Public` | Login form, RSS sharing, PubSubHubbub |
| `api` (via `api/index.php`) | `API` | Uses `sid` session-key auth |

### API authentication contract

```
POST /api/?op=login
  body: { op: "login", user: "admin", password: "xxx" }
  response: { status: 0, content: { session_id: "UUID", api_level: 14 } }

All subsequent calls:
  body: { op: "...", sid: "<session_id>", ... }

The sid maps to $_SESSION via API::before() which sets $_SESSION['uid']
from the session store keyed by sid.
```

### Research findings [TRAINING]

**Source-side patterns:**
- The JSON API uses a single endpoint (`api/index.php?op=`) with
  a session ID (`sid`) parameter for authentication.
  This is a non-standard pattern (not Bearer token, not OAuth).
- The API level (14) is a compatibility version for third-party clients
  (e.g., Fever-compatible apps, FreshRSS-compatible apps).
  Incrementing this version signals API contract changes.
- `getFeedTree` uses a breadth-first traversal of the category hierarchy,
  returning a tree structure with special virtual feeds
  (Starred, Published, Fresh, All Articles, Recently Read, etc.).
  Virtual feed IDs are negative integers: `-1` (Starred), `-2` (Published),
  `-3` (Fresh), `-4` (All Articles), `-6` (Recently Read).

**Special virtual feed IDs (magic numbers):**

| ID | Name | Source |
|----|------|--------|
| -1 | Starred articles | `ttrss_user_entries.marked = true` |
| -2 | Published articles | `ttrss_user_entries.published = true` |
| -3 | Fresh articles | Age < `FRESH_ARTICLE_MAX_AGE` pref |
| -4 | All articles | No filter |
| -6 | Recently read | `ttrss_user_entries.last_read` within 24h |
| < -10 | Labels | `LABEL_BASE_INDEX = -1024`, label IDs < -1024 |
| < -128 | Plugin virtual feeds | `PLUGIN_FEED_BASE_INDEX = -128` |

### Target-side mapping

| PHP construct | Python / Flask equivalent |
|---|---|
| `api/index.php` front-controller | Flask Blueprint `api_bp` with `POST /api/` route |
| `API` class methods | Blueprint view functions or a class-based view dispatcher |
| `op=` dispatch | URL routing: `@api_bp.route('/api/', methods=['POST'])` + `op` field dispatch, OR RESTful decomposition |
| `sid` session auth | Flask-Login session OR custom `sid` Bearer token auth (backwards-compatible) |
| `backend.php` dispatch | Flask Blueprint per handler: `backend_bp`, `rpc_bp`, etc. |
| Virtual feed IDs (negative int) | Python constants: `VIRTUAL_FEED_STARRED = -1` etc.; preserved in API responses |
| `API::wrap(status, reply)` | `jsonify({"status": status, "content": reply})` |
| `api_level` | Integer constant in Python app config |

### Divergences spotted

**D-GS1-01: sid vs Flask-Login session cookie**
- PHP API uses an explicit `sid` parameter (session key) in every request.
  Third-party clients (mobile apps, Newsboat, etc.) rely on `sid`.
- Flask-Login uses a session cookie.
- Gap: Must support `sid`-based auth for backwards-compatible API;
  Flask-Login for browser sessions. Dual auth paths needed.
- Severity: HIGH — breaks all existing third-party clients if not preserved.

**D-GS1-02: API level bump**
- Any change to the JSON API contract (added fields, changed error codes)
  should increment `api_level`.
- Python target starts at `api_level ≥ 14` to be backwards-compatible.
- Severity: LOW — administrative tracking concern.

**D-GS1-03: Virtual feed IDs carry negative-integer contract**
- All API methods that accept `feed_id` must handle negative virtual feed IDs.
  The PHP code has scattered `if ($feed_id < 0)` branching throughout.
- Python: define `VirtualFeedId` enum or constants; centralise virtual-feed query logic.
- Severity: MEDIUM — high frequency of the magic-number pattern.

**D-GS1-04: getFeedTree BFS must produce identical JSON shape**
- TT-RSS clients depend on the exact JSON structure of `getFeedTree` response.
- Python must produce identical `{type, id, name, unread, items: [...]}` structure.
- Severity: HIGH — client compatibility.

### Open questions (Phase 2 ADR items)

1. Should the Python API keep the `op=` single-endpoint convention,
   or decompose into RESTful URLs (`GET /api/feeds`, `POST /api/articles/:id/labels`)?
   The single-endpoint model maintains backwards compatibility with existing clients.
   RESTful decomposition enables standard API documentation but requires client migration.

2. What is the API level of the target?
   If new endpoints are added (Fever API compatibility, Miniflux API compatibility),
   a new API level should be declared.

3. Should `sid` auth and Flask-Login session be unified via a custom
   `LoginManager.request_loader` that checks both cookie and `sid` parameter?

---

## GS-2 — Session / Auth Surface

### Source files

| File | Role |
|------|------|
| `include/sessions.php` | Custom PHP session handler (ttrss_open/close/read/write/destroy/gc) |
| `include/functions.php` | `authenticate_user`, `login_sequence`, `validate_session`, `logout_user` |
| `classes/auth/base.php` | `Auth_Base` abstract class |
| `plugins/auth_internal/init.php` | `Auth_Internal` — default SHA1/argon2 auth plugin |
| `classes/pluginhost.php` | `HOOK_AUTH_USER` hook dispatch |
| `classes/handler/protected.php` | Session validation per-request for protected handlers |
| `index.php` | Calls `login_sequence()` on every web request |
| `include/crypt.php` | Feed credential encryption (mcrypt AES-128-CBC) |

### Auth flow (from source corpus)

```
HTTP Request to index.php / backend.php:
  ├─ require_once "sessions.php"    → registers custom session handlers
  ├─ session_start()                → loads session from ttrss_sessions DB table
  ├─ login_sequence():
  │    ├─ SINGLE_USER_MODE?         → auto-authenticate as user id=1
  │    ├─ $_SESSION['uid']?         → already logged in, validate_session()
  │    │     ├─ version check: $_SESSION['version'] == VERSION_STATIC?
  │    │     ├─ IP check (SESSION_CHECK_ADDRESS mode 0/1/2)?
  │    │     ├─ schema version check (session_get_schema_version)?
  │    │     └─ PASS → serve request | FAIL → destroy session, show login form
  │    └─ $_POST['login']?          → authenticate_user($login, $password):
  │          ├─ run_hooks(HOOK_AUTH_USER, &$user_info)
  │          │     → Auth_Internal::hook_auth_user:
  │          │           ├─ query ttrss_users WHERE login = ?
  │          │           ├─ verify pwd_hash (SHA1 / salted SHA1)
  │          │           ├─ if otp_enabled: verify TOTP code
  │          │           └─ return user_id or false
  │          ├─ if success: session_regenerate_id(true)
  │          │   $_SESSION['uid'] = $user_id
  │          │   $_SESSION['name'] = $login
  │          │   $_SESSION['access_level'] = $access_level
  │          │   $_SESSION['ip_address'] = $_SERVER['REMOTE_ADDR']
  │          │   $_SESSION['version'] = VERSION_STATIC
  │          └─ if fail: show login form / return 403
  └─ load_user_plugins($owner_uid)  → loads per-user plugin set from prefs

API Request to api/index.php:
  ├─ API::before():
  │    ├─ Extract sid from POST body
  │    ├─ query: SELECT owner_uid FROM ttrss_access_keys WHERE access_key = sid
  │    │   OR use standard session cookie path
  │    ├─ set $_SESSION['uid'] = $owner_uid
  │    └─ authenticate = true / 403
  └─ route to API method
```

### Representative constructs

```php
// include/functions.php - authenticate_user (lines 706-772)
function authenticate_user($login, $password, $check_only = false) {
    if (SINGLE_USER_MODE) {
        $user_id = 1;
    } else {
        $auth_module = false;
        foreach (PluginHost::getInstance()->get_hooks(PluginHost::HOOK_AUTH_USER) as $plugin) {
            $user_id = $plugin->authenticate($login, $password);
            if ($user_id) {
                $auth_module = strtolower(get_class($plugin));
                break;
            }
        }
    }
    if ($user_id && !$check_only) {
        $_SESSION["uid"] = $user_id;
        session_regenerate_id(true);
        // ... populate session fields ...
    }
    return $user_id;
}

// include/functions.php - validate_session (lines ~839-882)
function validate_session() {
    if (SINGLE_USER_MODE) return true;
    if (VERSION_STATIC != $_SESSION["version"]) return false;
    // IP check, schema version check...
    return true;
}
```

### Research findings [TRAINING]

**Session token flow:**
- PHP sessions use a server-generated session ID stored in a cookie (`ttrss_sid`
  or `ttrss_sid_ssl` for HTTPS connections).
- The session ID maps to a row in `ttrss_sessions`; the session data is PHP-serialised.
- The API's `sid` is the same session key — clients obtain it via `login` API call,
  then pass it in every subsequent request as `sid=`.
- `ttrss_access_keys` is a DIFFERENT table — it stores per-feed public RSS
  access keys, not session keys. The API `sid` is the PHP session key,
  not an access key. (Potential source of confusion in migration.)

**Multi-user isolation:**
- Every DB query in TT-RSS that touches user data includes
  `AND owner_uid = '$owner_uid'` from `$_SESSION['uid']`.
  This is the primary isolation boundary.
- No row-level security at the DB level — isolation is enforced in PHP.
  ⚠ If `$_SESSION['uid']` is ever wrong, full data leak across users.

**SINGLE_USER_MODE:**
- When enabled, skips all authentication. User is implicitly user ID 1 (admin).
- Used in single-user Docker deployments (most common self-hosted setup).
- Affects: `validate_session`, `authenticate_user`, `login_sequence`,
  `session_get_schema_version`, session checks in `classes/handler/protected.php`.
  ~8 distinct locations need the SINGLE_USER_MODE flag.

### Target-side mapping

| PHP construct | Python / Flask equivalent |
|---|---|
| `ttrss_sessions` DB table | Flask-Session (Redis backend) or signed cookies |
| `session_start()` / custom handlers | Flask-Login + `SessionInterface` |
| `$_SESSION['uid']` | `current_user.id` (Flask-Login) |
| `$_SESSION['access_level']` | `current_user.access_level` |
| `$_SESSION['name']` | `current_user.login` |
| `session_regenerate_id(true)` | `flask.session.regenerate()` or rebuild session dict |
| `authenticate_user()` | Flask-Login `login_user(user_obj, remember=...)` |
| `validate_session()` | `LoginManager.user_loader` + `@login_required` |
| `logout_user()` | `flask_login.logout_user()` |
| `login_sequence()` | Flask before-request hook + login Blueprint |
| `SINGLE_USER_MODE` | `app.config["SINGLE_USER_MODE"]` + custom `request_loader` |
| API `sid` auth | Custom `LoginManager.request_loader` checking `request.json.get("sid")` |
| `load_user_plugins($owner_uid)` | Called after `login_user()` to initialise per-user plugin state |

### Divergences spotted

**D-GS2-01: Session key = PHP session ID = API sid**
- The API `sid` is literally the PHP session ID string.
  In Python, Flask-Login session IDs are opaque (managed by `itsdangerous`).
  Existing API clients that have stored `sid` values will not work
  unless a compatibility layer maps `sid` → Flask session.
- Severity: HIGH — migration path: issue new session on next login;
  no silent migration possible.

**D-GS2-02: Per-request owner_uid isolation**
- Every DB query must carry `owner_uid = current_user.id`.
  In PHP, this is done by passing `$_SESSION['uid']` directly.
  In Python, use `current_user.id` in every SQLAlchemy query.
  Any missed `owner_uid` filter = data leak.
- Consider a SQLAlchemy `Query` subclass that automatically adds
  `owner_uid` filter for user-scoped models.
- Severity: HIGH — security property; must audit all ~150 DB query sites.

**D-GS2-03: OTP TOTP code timing window**
- `Auth_Internal` OTP verification uses `TOTP::verify($otp, time(), 1)` — ±1 window.
  `pyotp.TOTP.verify(otp, valid_window=1)` is equivalent.
- Must explicitly set `valid_window=1`; pyotp default is 0 (strict).
- Severity: MEDIUM — auth regression if not set.

**D-GS2-04: `auth_pass_encrypted` boolean flag on feeds**
- When `ttrss_feeds.auth_pass_encrypted = true`, `auth_pass` holds mcrypt ciphertext.
- Decrypt path must check this flag before using `auth_pass`.
- After mcrypt→Fernet migration, the flag remains meaningful but the ciphertext format changes.
- Severity: MEDIUM — affects all feeds with HTTP Basic Auth credentials.

### Open questions (Phase 2 ADR items)

1. Server-side sessions (Redis) vs signed-cookie sessions (client-side)?
   Redis provides session revocation on logout/account compromise.
   Signed cookies reduce infrastructure dependency.
   Recommendation: Redis for multi-user; allow fallback to cookies for single-user.

2. Should the API `sid` be replaced with a JWT or Bearer token in the Python target?
   If yes, all existing clients break unless a compatibility translation layer is provided.
   If no, the `sid` = session ID semantics must be preserved exactly.

3. How should SINGLE_USER_MODE interact with Flask-Login?
   Option A: `LoginManager.anonymous_user = AdminUser()` always returns user 1.
   Option B: `@before_request` decorator that calls `login_user(admin_user)` when config flag set.
   Option B is cleaner and more testable.

---

## GS-3 — Background Daemon

### Source files

| File | Role |
|------|------|
| `update_daemon2.php` | Master daemon: pcntl_fork loop, SIGCHLD handler, child management |
| `update.php` | Single-shot CLI updater (one update pass, no daemon) |
| `include/rssfuncs.php` | `update_daemon_common()` — batch feed update logic |
| `include/functions.php` | `file_is_locked()`, `make_lockfile()`, `sql_random_function()` |
| `include/ccache.php` | Counter cache updates (called after article storage) |

### Daemon architecture (from source corpus)

```
update_daemon2.php (master process):
  ├─ define(MAX_JOBS, 2)            → max parallel worker slots
  ├─ define(SPAWN_INTERVAL, 120)    → seconds between spawn rounds
  ├─ define(MAX_CHILD_RUNTIME, 1800)→ watchdog timeout per child
  ├─ pcntl_signal(SIGCHLD, sigchld_handler)
  ├─ pcntl_signal(SIGTERM, shutdown)
  ├─ init_database_connection()
  │
  └─ Main loop (infinite):
       ├─ sleep(SPAWN_INTERVAL)
       ├─ reap_children()           → pcntl_waitpid for finished workers
       ├─ check_ctimes()            → SIGKILL children > MAX_CHILD_RUNTIME
       └─ if (running_count < MAX_JOBS):
            ├─ $pid = pcntl_fork()
            └─ child:
                 ├─ make_lockfile("update_daemon-$pid.lock")
                 ├─ update_daemon_common(DAEMON_FEED_LIMIT, false, true)
                 └─ exit(0)

update_daemon_common() (in child process):
  ├─ check SCHEMA_VERSION == expected → die() if mismatch
  ├─ SELECT feeds WHERE last_updated is NULL
  │   OR last_updated + update_interval < NOW()
  │   AND (login_threshold check)
  │   ORDER BY last_updated ASC LIMIT $limit
  ├─ foreach $feed:
  │    ├─ UPDATE ttrss_feeds SET last_update_started = NOW() (claim lock)
  │    ├─ update_rss_feed($feed_id)
  │    │    ├─ fetch_file_contents($feed_url, ...)     → HTTP cURL
  │    │    ├─ run_hooks(HOOK_FETCH_FEED, ...)
  │    │    ├─ run_hooks(HOOK_FEED_FETCHED, ...)
  │    │    ├─ FeedParser::init() → parse articles
  │    │    ├─ run_hooks(HOOK_FEED_PARSED, ...)
  │    │    ├─ foreach article:
  │    │    │    ├─ deduplicate by guid
  │    │    │    ├─ apply user filters (find_article_filters)
  │    │    │    ├─ run_hooks(HOOK_ARTICLE_FILTER, ...)
  │    │    │    ├─ INSERT ttrss_entries + ttrss_user_entries
  │    │    │    └─ ccache_update($feed_id, $owner_uid)
  │    │    └─ UPDATE ttrss_feeds SET last_updated = NOW(), last_error = ''
  │    └─ (next feed)
  └─ housekeeping (periodic):
       ├─ purge_feed() for feeds with purge_interval set
       ├─ run_hooks(HOOK_HOUSE_KEEPING, ...)
       └─ update_feedbrowser_cache() (periodic)
```

### Key constants and timing

| Constant | Default | Purpose |
|----------|---------|---------|
| `DAEMON_FEED_LIMIT` | 500 | Max feeds per daemon run |
| `DAEMON_SLEEP_INTERVAL` | 120 | Seconds between runs |
| `MAX_CHILD_RUNTIME` | 1800 | Child watchdog (30 min) |
| `MAX_JOBS` | 2 | Concurrent update processes |
| `DAEMON_UPDATE_LOGIN_LIMIT` | 30 | Skip feeds of users not logged in within N days |
| `PURGE_INTERVAL` | 3600 | Purge frequency (seconds) |

### Research findings [TRAINING]

**PHP pcntl_fork daemon model:**
- `pcntl_fork()` creates a copy-on-write child process. Each child:
  - Reconnects to the DB (fork inherits open DB connection but it's shared — must reconnect).
  - Processes a batch of feeds.
  - Exits.
- The master never processes feeds; it only spawns, monitors, and reaps children.
- Lock files in `LOCK_DIRECTORY` prevent duplicate daemon runs across server restarts.

**Feed work claiming (DB-level locking):**
- Workers claim feeds by setting `last_update_started = NOW()` atomically.
- No formal DB lock (no `SELECT FOR UPDATE`). Two workers could claim the same feed
  if they query simultaneously — mitigated by `LIMIT MAX_JOBS` and `ORDER BY last_updated`.
- Race condition exists in theory; in practice `MAX_JOBS=2` and the sequential scan
  prevent most collisions.

**Target-side daemon model (Celery):**
- Master daemon → Celery `beat` scheduler with periodic task.
- Worker children → Celery worker processes (`-c 2` for MAX_JOBS=2).
- `update_daemon_common()` → Celery task `update_feeds_batch.delay()`.
- Feed claiming → Redis distributed lock (`redis-py` `SET NX EX`) or
  Celery `task.apply_async` with `countdown` to spread load.
- Lock files → Redis keys with TTL (equivalent to `MAX_CHILD_RUNTIME` seconds).

### Target-side mapping

| PHP construct | Python / Celery equivalent |
|---|---|
| `update_daemon2.php` master loop | Celery Beat scheduler (`beat_schedule`) |
| `pcntl_fork()` child | Celery worker task (`@app.task def update_feeds_batch`) |
| `MAX_JOBS = 2` | Celery worker `-c 2` (concurrency) |
| `SPAWN_INTERVAL = 120` | Beat schedule `run_every=120` seconds |
| `MAX_CHILD_RUNTIME = 1800` | Celery `task_soft_time_limit=1800` |
| `make_lockfile()` | Redis `SET NX EX` distributed lock |
| `file_is_locked()` | Redis `GET` existence check |
| `update_daemon_common()` | `@app.task def update_feeds_batch(limit=500)` |
| `update_rss_feed()` | `@app.task def update_feed(feed_id)` (per-feed subtask) |
| `HOOK_UPDATE_TASK` | Celery `app.on_after_finalize.connect` + beat schedule |
| `HOOK_HOUSE_KEEPING` | Celery `beat_schedule` housekeeping task |
| `update_feedbrowser_cache()` | Celery periodic task `update_feed_browser_cache` |
| `DAEMON_UPDATE_LOGIN_LIMIT` | Filter in `update_feeds_batch` query |

### Divergences spotted

**D-GS3-01: Fork-based parallelism → Celery task fan-out**
- PHP: 2 forked processes run `update_daemon_common()` simultaneously.
- Python: Celery sends `update_feed.delay(feed_id)` for each feed in the batch,
  allowing N workers to process in parallel.
- Semantic change: PHP processes a sequential batch per worker;
  Python can process all feeds in parallel (bounded by worker concurrency).
- Impact: Feed update throughput improves; ordering guarantees change.

**D-GS3-02: DB connection sharing in forks**
- PHP: each child reconnects to DB after fork (fork-safe).
- Python: Celery workers each have their own SQLAlchemy session pool.
  No fork-safety concern (Celery uses processes, not threads by default).
- Impact: LOW — Celery handles this correctly.

**D-GS3-03: `last_update_started` anti-collision logic**
- PHP sets `last_update_started = NOW()` before processing.
  Another worker skips feeds where `last_update_started` is recent.
- Python: Must replicate this logic in the Celery task:
  use Redis lock `SET feed_lock:<feed_id> 1 NX EX 1800` before processing;
  skip if lock exists.
- Impact: MEDIUM — without this, parallel workers double-process feeds.

**D-GS3-04: `DAEMON_UPDATE_LOGIN_LIMIT` query**
- PHP: SQL branch for MySQL vs PostgreSQL date arithmetic.
- Python: SQLAlchemy `func.now() - timedelta(days=DAEMON_UPDATE_LOGIN_LIMIT)`.
  Resolves DB dialect difference via SQLAlchemy.

**D-GS3-05: PubSubHubbub subscription management**
- `update_daemon2.php` handles PubSubHubbub subscription renewal
  (`HOOK_UPDATE_TASK` with PubSub plugin).
- Python: Celery task `renew_pubsub_subscriptions` on a longer interval.

### Open questions (Phase 2 ADR items)

1. Should `update_feeds_batch` be a single Celery task that spawns per-feed subtasks
   (`group([update_feed.si(fid) for fid in feed_ids])`)?
   Or a single task that processes feeds sequentially?
   Fan-out via `group` maximises parallelism; sequential is safer for DB load.

2. What is the Celery beat schedule interval? `SPAWN_INTERVAL=120` seconds means
   feed checking every 2 minutes. This should be configurable.

3. How should the `update.php` single-shot mode be replicated?
   Python equivalent: `flask update-feeds` CLI command via Click/Flask-Script,
   or `celery call ttrss.tasks.update_feeds_batch`.

4. Should `DAEMON_UPDATE_LOGIN_LIMIT` default be preserved (30 days) or
   made configurable per-instance? This affects bandwidth for instances with
   inactive users.

---

## GS-4 — Security Surface

### Source files

| File | Role |
|------|------|
| `include/crypt.php` | Feed credential encryption (mcrypt AES-128-CBC) |
| `include/functions2.php` | `sanitize()` — HTML content purification, XSS prevention |
| `include/functions.php` | `validate_csrf()`, `make_password()`, `authenticate_user()` SHA1 check |
| `include/sessions.php` | Session security: `session_regenerate_id`, `secure` cookie flag |
| `classes/pluginhost.php` | `HOOK_SANITIZE` — plugin-extensible sanitization |
| `plugins/auth_internal/init.php` | SHA1/salted-SHA1 password verification |
| `schema/ttrss_schema_pgsql.sql` | `pwd_hash` default: `SHA1:5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8` |
| `lib/otphp/` | TOTP second factor implementation |
| `lib/phpqrcode/` | QR code for OTP setup |

### Security finding inventory

#### FIND-01: SHA1 password hashing — CRITICAL

**Source location:** `schema/ttrss_schema_pgsql.sql` line 7; `plugins/auth_internal/init.php`

**Description:**
- Default admin password is stored as `SHA1:5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8`
  (SHA1 of the string "password").
- User passwords stored as `SHA1:<sha1(password)>` or `SHA1:<sha1(salt + password)>`.
- SHA1 has been broken for collision resistance since 2005 and is trivially reversible
  via rainbow tables for common passwords. Even the salted variant is weak by modern
  standards — SHA1 is too fast for password hashing.

**PHP pattern:**
```php
// Auth_Internal authentication (inferred)
$expected = "SHA1:" . sha1($password);
// or salted:
$expected = "SHA1:" . sha1($user['salt'] . $password);
if ($user['pwd_hash'] == $expected) { /* authenticated */ }
```

**Python target fix:**
- New passwords: `argon2.PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2).hash(password)`
- Migration on login: detect `SHA1:` prefix → verify SHA1 → re-hash with argon2id → commit.
- `ttrss_users.pwd_hash` column must remain `varchar(250)` (argon2id hashes are ~95 chars).
- Admin default password must be reset in the installer/setup flow.

**Frequency:** All user accounts. Every login until migration complete.
**Risk if missed:** Password database exposure → trivial offline cracking.

#### FIND-02: PHP mcrypt (deprecated + removed) — CRITICAL

**Source location:** `include/crypt.php` (entire file)

**Description:**
- `encrypt_string()` uses `mcrypt_encrypt(MCRYPT_RIJNDAEL_128, $key, $str, MCRYPT_MODE_CBC, $iv)`.
- `mcrypt` was deprecated in PHP 7.1 and **removed in PHP 7.2** (2017).
- Any TT-RSS installation on PHP ≥ 7.2 has non-functional feed credential encryption
  (calls silently fail or produce an error, leaving `auth_pass` unencrypted or corrupted).
- Key derivation: `hash('SHA256', FEED_CRYPT_KEY, true)` — raw binary SHA256 of the key.
- IV: `mcrypt_create_iv(16, MCRYPT_RAND)` — 16-byte random IV.
- Ciphertext format: `base64(iv) . ":" . base64(ciphertext)` — custom format, no HMAC.

**PHP pattern:**
```php
function encrypt_string($str) {
    $key = hash('SHA256', FEED_CRYPT_KEY, true);
    $iv = mcrypt_create_iv(16, MCRYPT_RAND);
    $encstr = mcrypt_encrypt(MCRYPT_RIJNDAEL_128, $key, $str, MCRYPT_MODE_CBC, $iv);
    return base64_encode($iv) . ":" . base64_encode($encstr);
}
```

**Python target fix:**
- New encryption: `cryptography.fernet.Fernet(key).encrypt(data.encode())`.
- Fernet key from env var `FEED_CRYPT_KEY` — must be 32-byte URL-safe base64.
- Migration: existing ciphertext in `ttrss_feeds.auth_pass` (where `auth_pass_encrypted=true`):
  1. Decrypt using `PyCryptodome` `AES.MODE_CBC` with SHA256-derived key.
  2. Re-encrypt with `Fernet`.
  3. Update `auth_pass` and mark `auth_pass_encrypted=true`.
- This requires a one-time data migration (`alembic` revision or CLI command).

**Frequency:** All feeds with HTTP Basic Auth credentials (`auth_pass != ''` AND `auth_pass_encrypted = true`).
**Risk if missed:** Feed credentials stored unencrypted or inaccessible.

#### FIND-03: SQL injection via string interpolation — HIGH

**Source location:** `include/ccache.php`, `include/rssfuncs.php`, `include/functions.php` (widespread)

**Description:**
```php
// ccache.php — direct string interpolation in SQL
db_query("UPDATE ttrss_counters_cache SET value = '$unread', updated = NOW()
    WHERE feed_id = '$feed_id' AND owner_uid = '$owner_uid'");
```
- Many DB calls interpolate variables directly into SQL strings.
- Mitigated by `db_escape_string()` calls at some sites, but not all.
- PostgreSQL's `pg_escape_string` and MySQL's `mysql_real_escape_string` do NOT
  prevent all injection (edge cases with multi-byte charsets, backslash handling).
- Prepared statements (`Db_PDO`) exist but are not universally used.

**Python target fix:**
- SQLAlchemy ORM and Core both use parameterised queries by default.
- Direct `db.session.execute(text("..."), {"param": value})` with bound params.
- Risk is eliminated by SQLAlchemy if raw `text()` strings are not used with f-strings.

**Frequency:** ~50–100 SQL call sites. Severity decreases significantly with SQLAlchemy.
**Risk if missed:** SQL injection potential in ORM bypass paths.

#### FIND-04: CSRF token validation — MEDIUM

**Source location:** `include/functions.php::validate_csrf`, `classes/handler.php::before`

**Description:**
```php
// include/functions.php
function validate_csrf($csrf_token) {
    return ($csrf_token == $_SESSION['csrf_token']);
}

// classes/handler.php::before
if (!$this->csrf_ignore($method)) {
    if (!validate_csrf($_REQUEST["csrf_token"])) {
        die("CSRF check failed.");
    }
}
```
- CSRF tokens are generated per-session (not per-form).
- Token is stored in `$_SESSION['csrf_token']`.
- Some handlers explicitly `csrf_ignore()` (mark themselves CSRF-exempt).
- The API endpoints are CSRF-exempt by design (use `sid` auth instead).

**Python target fix:**
- Flask-WTF `CSRFProtect` extension handles CSRF automatically.
- For AJAX/JSON endpoints: `X-CSRFToken` header checked by Flask-WTF.
- API endpoints remain CSRF-exempt (JWT/sid auth).

**Frequency:** All authenticated backend.php and prefs.php handlers.
**Risk if missed:** CSRF attack on authenticated user sessions.

#### FIND-05: XSS via sanitize() bypass — HIGH

**Source location:** `include/functions2.php::sanitize`

**Description:**
- `sanitize()` uses a custom tag whitelist to strip unsafe HTML from feed article content.
- `HOOK_SANITIZE` allows plugins to modify sanitization behaviour.
- A misbehaving plugin could weaken the sanitizer.
- HTML stored in `ttrss_entries.content` is already sanitized; re-sanitization on display
  is optional but provides defence-in-depth.
- JavaScript in article content (from malicious feeds) is the primary XSS vector.

**Python target fix:**
- Use `lxml.html.clean.Cleaner(allow_tags=ALLOWED_TAGS, remove_unknown_tags=False)`.
- Use `bleach.clean(html, tags=ALLOWED_TAGS, strip=True)` as alternative.
- `HOOK_SANITIZE` pluggy hookspec must preserve the sanitization guarantee
  even when plugins modify the pipeline.

**Frequency:** Every article stored and displayed.
**Risk if missed:** Stored XSS attack via malicious RSS feed content.

#### FIND-06: Session fixation prevention — MEDIUM

**Source location:** `include/functions.php::authenticate_user` line ~760

**Description:**
- `session_regenerate_id(true)` called on successful login.
- `true` parameter destroys the old session (prevents fixation).
- Python: Flask `session.regenerate()` or manually clear and reissue session.

**Frequency:** Each login.
**Risk if missed:** Session fixation attack.

#### FIND-07: SSL/HTTPS cookie flag — LOW

**Source location:** `include/sessions.php` lines ~10–14

**Description:**
```php
if (@$_SERVER['HTTPS'] == "on") {
    $session_name .= "_ssl";
    ini_set("session.cookie_secure", true);
}
```
- Secure cookie flag set only for HTTPS connections.

**Python target:**
- Flask: `SESSION_COOKIE_SECURE = True` when behind HTTPS.
- Use `Flask-Talisman` or similar to enforce HTTPS and set security headers.

### Security remediation priority order

```
P0 (before any code runs): argon2id migration path (FIND-01)
P0: mcrypt → Fernet migration (FIND-02) + data migration script
P1 (during coding): SQLAlchemy parameterised queries everywhere (FIND-03)
P1: Flask-WTF CSRF protection (FIND-04)
P1: lxml/bleach sanitize() replacement (FIND-05)
P2 (deployment): Session fixation prevention (FIND-06)
P2: HTTPS cookie flags + Flask-Talisman (FIND-07)
```

### Divergences spotted

**D-GS4-01: SHA1 upgrade path requires dual-hash detection**
- Must detect `SHA1:` prefix at login time; verify; rehash.
- `ttrss_users.pwd_hash` column must hold both formats during transition.

**D-GS4-02: mcrypt ciphertext → Fernet migration requires raw AES access**
- `PyCryptodome` (`Crypto.Cipher.AES`) can decrypt the mcrypt ciphertext format.
- Key: `hashlib.sha256(FEED_CRYPT_KEY.encode()).digest()` (raw 32 bytes).
- IV: first 16 bytes of `base64.b64decode(stored[:stored.index(":")])`.
- Ciphertext: `base64.b64decode(stored[stored.index(":")+1:])`.
- Must strip PKCS7 padding after decryption.

**D-GS4-03: HOOK_SANITIZE must preserve security guarantee**
- PHP: `sanitize()` calls `strip_tags` + explicit whitelist BEFORE invoking the hook.
  Plugins operate on already-sanitized content.
- Python target should follow same order: apply `lxml.Cleaner` first,
  then invoke `HOOK_SANITIZE` plugins on already-clean HTML.
  Prevents a malicious plugin from bypassing the base sanitizer.

### Open questions (Phase 2 ADR items)

1. argon2id parameters for self-hosted instances (VPS hardware)?
   `argon2-cffi` defaults: `time_cost=2, memory_cost=65536, parallelism=2`.
   Are these appropriate for typical TT-RSS deployment?
   Benchmark against typical login latency budget (~200ms acceptable).

2. Should the Python target add Content-Security-Policy (CSP) headers
   beyond what TT-RSS PHP currently sets (none)?
   CSP would add defence-in-depth against XSS.
   Default-deny CSP + nonce for inline JS is recommended but may break the Dojo frontend.

3. Should `FEED_CRYPT_KEY` migrate from `config.php` constant to environment variable?
   Environment variable is the 12-factor app standard.
   Recommend: check env var first, fall back to config for migration period.

---

## GS-5 — Frontend / Backend Coupling

### Source files

| File | Role |
|------|------|
| `index.php` | SPA shell — renders HTML skeleton + Dojo bootstrap |
| `backend.php` | AJAX request handler (op= dispatch) |
| `js/tt-rss.js` | Main SPA controller (~2500 LOC) |
| `js/FeedList.js` | Feed tree widget |
| `js/Article.js` | Article view widget |
| `js/ArticleList.js` | Article list widget |
| `js/CommonDialogs.js` | Shared dialog widgets |
| `js/Prefs.js` | Preferences modal controller |
| `js/PrefFeedTree.js` | Prefs feed tree widget |
| `js/Headlines.js` | Headlines pane controller |
| `js/App.js` | Application shell (top-level Dojo widget) |
| `css/tt-rss.css` | Main application stylesheet |
| `lib/MiniTemplator.class.php` | Server-side template engine for dialog fragments |

### Frontend stack

**Dojo Toolkit 1.x** (bundled in `js/dojo/`, `js/dijit/`, `js/dojox/`)
- Class system: `dojo.declare("ClassName", [base], {...})`.
- Widget system: `dijit` (Dijit widget library).
- XHR: `dojo.xhrPost`, `dojo.xhrGet` → `backend.php?op=X&method=Y`.
- Event system: `dojo.connect`, `dojo.publish`, `dojo.subscribe`.
- Dialogs: `dijit.Dialog`, `dijit.TooltipDialog`.
- Trees: `dijit.Tree` + custom store for feed tree.

**Communication pattern:**

```javascript
// All AJAX calls use dojo XHR to backend.php
dojo.xhrPost({
    url: "backend.php",
    content: {
        op: "feeds",
        method: "view",
        feed_id: this.feed_id,
        csrf_token: getInitParam("csrf_token")
    },
    load: function(data) {
        // data is HTML fragment OR JSON depending on handler
    }
});
```

- Backend responses are **mixed**: some handlers return HTML fragments
  (Feeds::format_headlines_list returns `<div>` HTML),
  others return JSON (API class always returns JSON,
  RPC returns JSON, some dialog handlers return HTML).
- This dual HTML/JSON response model complicates migration.

### AJAX endpoint inventory (selected)

| Handler | Method | Response type | Purpose |
|---------|--------|---------------|---------|
| `feeds` | `view` | HTML | Render article list for feed |
| `feeds` | `generate_dashboard_feed` | HTML | Dashboard widget content |
| `rpc` | `mark` | JSON | Mark articles read/starred |
| `rpc` | `updateCounters` | JSON | Refresh unread counts |
| `rpc` | `updateFeed` | JSON | Trigger single feed update |
| `article` | `setScore` | JSON | Set article score |
| `article` | `editArticleTags` | JSON | Edit article tags |
| `pref-feeds` | `savefeedorder` | JSON | Save drag-drop feed order |
| `pref-prefs` | `savePrefs` | JSON | Save user preferences |
| `dlg` | `generatedFeed` | HTML | Generated feed preview |
| `backend` | `getRSSData` | JSON | Public RSS sharing data |
| `public` | `login` | HTML redirect | Login form POST handler |
| `public` | `rss` | XML | Public RSS feed for sharing |

### Frontend features

1. **Feed tree**: hierarchical list of categories + feeds with unread counts.
   Drag-drop reordering (Dojo DnD).
   Special items: Starred, Published, Fresh, All Articles.

2. **Article list (headlines)**: paginated, sortable, filterable list of articles.
   Two display modes: split-pane (default) and combined display mode (CDM).

3. **Article view**: rendered article content, previous/next navigation, labelling, scoring.

4. **Preferences modal**: tabbed dialog with General, Interface, Advanced, Digest,
   Feeds (CRUD), Filters (CRUD), Labels (CRUD), Users (admin), System (admin).

5. **Keyboard shortcuts**: configurable hotkeys (HOOK_HOTKEY_MAP extensible).

6. **Mobile detection**: `lib/Mobile_Detect.php` redirects to digest/mobile plugin
   if installed.

### Research findings [TRAINING]

**Dojo Toolkit end-of-life status:**
- Dojo Toolkit 1.x was last updated circa 2020; Dojo 2/Dojo Next was rebranded as
  @dojo/framework but has a small community.
- Using Dojo 1.x today is a technical debt indicator:
  browser compatibility is maintained by modern browsers but
  ecosystem support (plugins, tutorials, community) has largely moved to React/Vue/Vanilla JS.
- Recommendation (from `docs/decisions/ADR-0017`): migrate to Vanilla JS SPA.

**Mixed HTML/JSON response pattern:**
- TT-RSS's `Feeds::format_headlines_list` returns HTML because it was designed
  before single-page app conventions standardised on JSON APIs.
- The HTML includes server-rendered article content, timestamps,
  and per-article tool buttons.
- Migrating to a JSON API + client-side rendering requires:
  1. Python backend returns structured JSON for all endpoints.
  2. JavaScript renders the HTML from the JSON data.
  This is the ADR-0017 approach.

**MiniTemplator:**
- `lib/MiniTemplator.class.php` is a simple block-template engine used
  for dialog box content (e.g., the "import OPML" dialog, the "add feed" dialog).
- These server-rendered fragments are injected into Dijit dialogs via `dialog.setContent(html)`.
- In the Python target, these move to Jinja2 partials served from Flask endpoints.

### Target-side mapping

| PHP / Dojo construct | Python / Vanilla JS equivalent |
|---|---|
| `dojo.xhrPost(backend.php, {op, method, ...})` | `fetch('/api/backend', {method:'POST', body:JSON.stringify({op,method,...})})` |
| `dojo.declare("FeedList", dijit._Widget, {...})` | Vanilla JS class `class FeedList {...}` |
| `dijit.Dialog` | Custom `<dialog>` element or lightweight modal library |
| `dijit.Tree` + DnD | Custom tree component with drag-drop via HTML5 DnD API |
| `dojo.publish/subscribe` | Browser `CustomEvent` or a tiny EventBus |
| `Feeds::format_headlines_list` → HTML | Flask route returns JSON; JS renders `<article>` elements |
| `MiniTemplator` dialogs | Jinja2 templates served as HTML partials OR JSON schemas |
| `lib/Mobile_Detect.php` | CSS media queries + `navigator.userAgentData` |

### Divergences spotted

**D-GS5-01: HTML response → JSON response contract change**
- Existing browser sessions may use older JS that expects HTML responses.
- Python target changes all responses to JSON.
- This is a BREAKING CHANGE for the browser frontend.
- Mitigation: frontend and backend migrate together (atomic).

**D-GS5-02: Dojo events → CustomEvent**
- `dojo.publish("feedlist/update", [data])` and
  `dojo.subscribe("feedlist/update", handler)` are the primary
  inter-component communication mechanism.
- Python/Vanilla JS equivalent: `window.dispatchEvent(new CustomEvent("feedlist:update", {detail: data}))`.
- ~80+ publish/subscribe call sites in JS files.

**D-GS5-03: CSRF token in AJAX**
- PHP: `csrf_token` is POSTed as a form field.
- Python/Flask-WTF: CSRF token sent as `X-CSRFToken` HTTP header.
- JS must change from `content: {csrf_token: ...}` to `headers: {"X-CSRFToken": ...}`.

**D-GS5-04: Keyboard shortcut backend**
- `HOOK_HOTKEY_MAP` returns PHP arrays that are JSON-serialised and passed to Dojo.
- Python target: `GET /api/hotkeys` endpoint returns JSON;
  `HOOK_HOTKEY_MAP` pluggy hook returns dicts that are merged into the response.

**D-GS5-05: Dojo AMD vs ES6 modules**
- Dojo uses a custom AMD (Asynchronous Module Definition) loader.
- Vanilla JS target uses native ES6 `import/export`.
- Module rewrite is required for all `js/*.js` files.

### Open questions (Phase 2 ADR items)

1. Should the Python backend produce HTML fragments for the feed/article views
   (server-side rendering) or JSON for client-side rendering?
   ADR-0017 decision: Vanilla JS SPA with JSON API.
   This means all `Feeds::format_headlines_list` → HTML paths must become JSON endpoints.

2. What is the migration strategy for the Dojo frontend?
   Option A: Incremental migration (Dojo widgets replaced one by one).
   Option B: Big-bang rewrite of all JS alongside Python backend.
   ADR-0017 recommends big-bang for the frontend (it's not separately versioned).

3. Should the JS be bundled (webpack/vite) or served as native ES6 modules?
   Native ES6 modules work in all modern browsers (2023+) without a bundler.
   A bundler improves HTTP/2 performance but adds build toolchain complexity.

4. How should the CSRF token be exposed to JS?
   Flask-WTF: `{{ csrf_token() }}` in Jinja2 template.
   JS stores it in a module-level variable on page load.
   Subsequent AJAX calls set `X-CSRFToken` header.

---

## Cross-surface observations

### Shared divergences (all 5 surfaces)

| ID | Pattern | Impact | Surfaces affected |
|----|---------|--------|-------------------|
| X-01 | `$_SESSION['uid']` → `current_user.id` | ~80+ sites | GS-2, GS-1, GS-3 |
| X-02 | Mixed HTML/JSON responses → all JSON | Frontend rewrite | GS-5, GS-1 |
| X-03 | Magic negative feed IDs (virtual feeds) | Business logic | GS-1, GS-3, GS-5 |
| X-04 | Security remediations (SHA1, mcrypt) | Auth + data migration | GS-2, GS-4 |
| X-05 | DB-type SQL branches → SQLAlchemy | ~20+ branch sites | GS-3, GS-2 |
| X-06 | PHP die() / exit() → Python exceptions | Error handling | GS-1, GS-2, GS-3 |

### Migration sequencing recommendation

```
Phase 1 (Foundation): entity-schema + class-hierarchy + include-graph
  → Build SQLAlchemy models; set up Alembic; scaffold Flask app

Phase 2 (Core logic): call-graph + session-auth + background-daemon
  → Implement Flask-Login; auth flow; Celery; feed fetch/store pipeline

Phase 3 (Business logic): api-route-surface + hook-extension
  → Implement API Blueprint; pluggy hookspecs; backend.php dispatch equivalent

Phase 4 (UI): frontend-backend + security-surface
  → Vanilla JS SPA; JSON endpoints; CSRF; CSP headers

Phase 5 (Semantic verification): all dimensions
  → Parity testing; divergence catalogue validation
```

---

*Sources: direct reads of `api/index.php`, `backend.php`, `index.php`,
`update_daemon2.php`, `include/rssfuncs.php`, `include/functions.php`,
`include/crypt.php`, `include/functions2.php`, `include/sessions.php`,
`classes/pluginhost.php`, `js/tt-rss.js` (structure only).*
*Status: DEGRADED (training knowledge + source reads; no web search).*
