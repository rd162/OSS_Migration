# 12 — Semantic Discrepancies Catalogue (Seed)

**Phase 1 divergence catalogue** · TT-RSS PHP → Python
**Status**: seeded from ∆2 (training-knowledge-only) + ∆6 community research
**Note**: This is a seed catalogue; Phase 5 (semantic-verification) extends it.

---

## Format

Each entry:
- **D-XX-NN** — identifier (D = divergence; XX = category; NN = number)
- **Category** — type of divergence
- **Source pattern** — PHP construct
- **Target gotcha** — Python pitfall
- **Grep count** — approximate occurrence frequency in source
- **Phase** — which migration phase is most likely to exercise this

---

## Category: Security (SE)

### D-SE-01 — SQL injection via escape_string()

**Source**: `db_query("SELECT ... WHERE login = '$login'")` throughout codebase
**Target gotcha**: Python SQLAlchemy with string interpolation creates the same risk.
Must use parameterised bindings: `text("SELECT ... WHERE login = :login").bindparams(login=login)`
or ORM: `filter_by(login=login)`.
**Grep count**: >500 occurrences of `db_query(`
**Phase**: Phase 1 (DB layer) — every query must use bound params
**Severity**: CRITICAL
Source: `source-repos/ttrss-php/ttrss/include/db.php`

### D-SE-02 — SHA1 password hashing

**Source**: `ttrss_users.pwd_hash = "SHA1:<hex>"` in `plugins/auth_internal/init.php`
**Target gotcha**: Python must accept SHA1 on first login (migration compatibility)
then silently upgrade to argon2id. If upgrade is skipped, SHA1 hashes persist indefinitely.
**Grep count**: 1 (auth_internal::authenticate)
**Phase**: Phase 1b (auth implementation)
**Severity**: HIGH
Source: `source-repos/ttrss-php/ttrss/plugins/auth_internal/init.php`

### D-SE-03 — mcrypt AES-128-CBC feed credentials

**Source**: `ttrss_feeds.auth_pass = "iv_b64:ciphertext_b64"` produced by `include/crypt.php`
**Target gotcha**: Python `cryptography.fernet.Fernet` token format is incompatible with
mcrypt AES-128-CBC. Existing DB-encrypted credentials cannot be read by Python without
a migration step. If migration is skipped, all authenticated feed fetches fail silently.
**Grep count**: ~20 (decrypt_string call sites in rssfuncs.php)
**Phase**: Phase 3 (feed pipeline — credential decryption at fetch time)
**Severity**: CRITICAL
Source: `source-repos/ttrss-php/ttrss/include/crypt.php`

---

## Category: Request handling (RH)

### D-RH-01 — $_REQUEST superglobal merge

**Source**: `$_REQUEST['param']` merges GET + POST + COOKIE automatically in PHP
**Target gotcha**: Flask separates `request.form` (POST), `request.args` (GET),
`request.cookies`. Code reading `$_REQUEST` must be audited per call site to determine
whether the parameter is expected from GET or POST, then mapped to the correct Flask accessor.
**Grep count**: ~200 occurrences of `$_REQUEST` across classes/
**Phase**: Phase 4 (API + backend handlers)
**Severity**: MEDIUM (correctness risk if GET/POST distinction matters for the operation)
Source: `source-repos/ttrss-php/ttrss/classes/api.php` (pervasive)

### D-RH-02 — Method-string dispatch without whitelist

**Source**: `$handler->$method()` in `Handler::handle()` dispatches any public method
whose name matches the `op` parameter value.
**Target gotcha**: Python must enumerate all valid operations explicitly.
Dynamic method dispatch via `getattr(handler, method)()` without a whitelist is a
security vulnerability (arbitrary method invocation).
**Grep count**: 1 core dispatch + many subclass methods
**Phase**: Phase 1 (foundation — handler routing)
**Severity**: HIGH
Source: `source-repos/ttrss-php/ttrss/classes/handler.php`

### D-RH-03 — PHP session state assumption

**Source**: `$_SESSION["uid"]` is set by PHP session management on every request.
All auth checks test `$_SESSION["uid"]`.
**Target gotcha**: Flask-Login uses `current_user.id` (proxy object, not dict key).
Code that reads `$_SESSION["uid"]` must become `current_user.id`.
Code that reads `$_SESSION["access_level"]` must become `current_user.access_level`.
**Grep count**: ~100 occurrences of `$_SESSION["uid"]`
**Phase**: Phase 1b (auth + session)
**Severity**: MEDIUM (systematic, not subtle)
Source: `source-repos/ttrss-php/ttrss/include/sessions.php`, `classes/api.php`

---

## Category: Database (DB)

### D-DB-01 — Counter cache race condition

**Source**: `ccache_update()` in `include/ccache.php` uses `BEGIN`/`COMMIT` for upsert
atomicity but no row-level lock (`SELECT FOR UPDATE`).
**Target gotcha**: Concurrent Celery workers updating the same feed's counter
can produce lost updates (two workers read old value, both compute +1, both write the same new value).
**Estimated frequency**: High in multi-user deployments with concurrent feed updates.
**Phase**: Phase 3 (core logic — ccache migration)
**Severity**: MEDIUM
Source: `source-repos/ttrss-php/ttrss/include/ccache.php`

### D-DB-02 — VARCHAR preference type coercion

**Source**: All `ttrss_user_prefs.value` stored as VARCHAR; PHP coerces via `(int)`, `(bool)`.
**Target gotcha**: SQLAlchemy returns the raw VARCHAR string.
`if get_pref("ENABLE_API_ACCESS", uid)` passes in PHP (non-empty string is truthy)
but in Python the string `"0"` is also truthy. Must apply explicit type coercion
based on `ttrss_prefs.type` column.
**Grep count**: ~150 calls to `get_pref()`
**Phase**: Phase 2 (core logic — pref system)
**Severity**: MEDIUM (subtle correctness bugs)
Source: `source-repos/ttrss-php/ttrss/include/db-prefs.php`

### D-DB-03 — ttrss_sessions decommission at cutover

**Source**: PHP session data in `ttrss_sessions.data` is PHP-serialised base64.
**Target gotcha**: Python cannot deserialise PHP session data. All active PHP sessions
are invalidated at cutover. Users must re-login. This is expected behaviour but must
be communicated in deployment notes.
**Estimated frequency**: Affects all logged-in users at deployment time.
**Phase**: Phase 1 (session replacement)
**Severity**: HIGH (UX impact, no data loss)
Source: `source-repos/ttrss-php/ttrss/include/sessions.php`

### D-DB-04 — Tag/label cache denormalisation

**Source**: `ttrss_user_entries.tag_cache` and `label_cache` are comma-separated VARCHAR
fields that redundantly cache tag and label data from `ttrss_tags` / `ttrss_user_labels2`.
**Target gotcha**: These caches must be kept in sync. If the Python ORM does not maintain
them (via SQLAlchemy events or explicit updates on tag/label mutation), the `tag_cache`
and `label_cache` columns become stale. API responses that read from these columns
(`getHeadlines` includes tag_cache in output) will serve stale data.
**Grep count**: ~20 sites reading tag_cache/label_cache
**Phase**: Phase 2–3 (entity models + API)
**Severity**: MEDIUM
Source: `source-repos/ttrss-php/ttrss/classes/article.php` (`setArticleTags()`)

---

## Category: API contract (AC)

### D-AC-01 — Label negative-ID encoding

**Source**: TT-RSS API encodes label IDs as negative feed IDs:
`label_feed_id = -(label.id + 11)` in `include/labels.php`.
This formula appears in `classes/api.php` (getFeeds, getCounters),
`include/labels.php`, and the JavaScript frontend.
**Target gotcha**: If the formula is not preserved byte-for-byte, API clients
that use label IDs will send the wrong ID to getHeadlines/updateArticle.
**Grep count**: ~10 occurrences of the formula
**Phase**: Phase 3 (API — getFeeds, getCounters, setArticleLabel)
**Severity**: HIGH (API compatibility)
Source: `source-repos/ttrss-php/ttrss/include/labels.php` (`label_find_id()`)

### D-AC-02 — API sequence number echo

**Source**: `API::wrap()` echoes `$_REQUEST['seq']` in every response:
`json_encode(["seq" => $this->seq, "status" => ..., "content" => ...])`
**Target gotcha**: If Flask `jsonify()` omits or wrong-types the `seq` field,
clients using sequence numbers for request deduplication will malfunction.
**Grep count**: 1 (API::wrap — called for every API response)
**Phase**: Phase 2 (API foundation)
**Severity**: LOW (easy to implement, hard to forget)
Source: `source-repos/ttrss-php/ttrss/classes/api.php:36`

### D-AC-03 — API_LEVEL = 8 must be preserved

**Source**: `const API_LEVEL = 8` in `classes/api.php:5`.
Mobile clients (FeedMe, Reeder, Newsblur, etc.) query `getApiLevel` and may
require `>= 8` or a specific version.
**Target gotcha**: Incrementing API_LEVEL breaks clients that require exactly 8.
Decrementing it makes the API appear downgraded.
**Grep count**: 1 constant + 1 usage in `getApiLevel()`
**Phase**: Phase 2 (API foundation)
**Severity**: HIGH (client compatibility)
Source: `source-repos/ttrss-php/ttrss/classes/api.php:5`

---

## Category: Plugin system (PH)

### D-PH-01 — HOOK_QUERY_HEADLINES SQL fragment

**Source**: `run_hooks(HOOK_QUERY_HEADLINES, ...)` receives raw SQL fragment from plugin.
Used in `classes/api.php:648`, `classes/feeds.php:298`, `classes/pref/filters.php:101`.
**Target gotcha**: SQL string fragments cannot be safely passed to SQLAlchemy ORM queries.
Must redesign the hookspec to accept a `sqlalchemy.Select` object that plugins mutate
via typed `.where()` / `.filter()` calls.
**Grep count**: 3 invocation sites
**Phase**: Phase 4 (API + headline query path)
**Severity**: HIGH (breaking change for PHP plugins using this hook)
Source: `source-repos/ttrss-php/ttrss/classes/api.php:648`

### D-PH-02 — run_hooks() return-value semantics (firstresult vs. broadcast)

**Source**: PHP `run_hooks($type, $method, $args)` iterates plugins and calls each;
the LAST non-null return value from the loop is implicitly used for value-returning hooks.
**Target gotcha**: pluggy `firstresult=True` returns the FIRST non-None result.
If multiple plugins register for HOOK_SANITIZE or HOOK_FETCH_FEED, PHP uses the last one;
Python uses the first. Registration order produces different behaviour.
**Grep count**: Affects 6 value-returning hooks (see dimension 05)
**Phase**: Phase 2 (plugin system foundation)
**Severity**: MEDIUM (only affects multi-plugin deployments)
Source: `source-repos/ttrss-php/ttrss/classes/pluginhost.php:93`

### D-PH-03 — Plugin exception propagation

**Source**: PHP `run_hooks()` has no try/catch — plugin exceptions propagate uncontrolled.
**Target gotcha**: Python target wraps each plugin call in try/except. A PHP plugin that
relies on exception propagation to signal failure (e.g., HOOK_AUTH_USER throws instead
of returning false) will silently fail in Python (exception caught, plugin result = None).
**Grep count**: Affects any plugin using HOOK_AUTH_USER
**Phase**: Phase 2 (plugin system)
**Severity**: LOW (improvement; edge case)
Source: `source-repos/ttrss-php/ttrss/classes/pluginhost.php:93`

### D-PH-04 — UI hooks output raw PHP HTML

**Source**: `HOOK_TOOLBAR_BUTTON`, `HOOK_ACTION_ITEM` expect plugins to call `echo`
or return HTML strings for the Dojo SPA page.
**Target gotcha**: Python target's Vanilla JS SPA (ADR-0017) cannot consume server-rendered
HTML fragments for toolbar items. Hooks must return structured JSON descriptors instead.
**Grep count**: 2 hooks, invoked from `index.php`
**Phase**: Phase 4 (frontend integration)
**Severity**: HIGH for existing PHP plugins; LOW for new Python plugins
Source: `source-repos/ttrss-php/ttrss/index.php`

---

## Category: Daemon / async (DA)

### D-DA-01 — PCNTL fork → Celery task queue

**Source**: `update_daemon2.php` uses `pcntl_fork()` for parallel feed updates.
**Target gotcha**: Python has no direct `pcntl_fork()` equivalent.
Celery replaces the entire process model. Retry semantics, error logging,
max-runtime enforcement, and lock file management all change. 
Celery task deduplication replaces lock files.
**Grep count**: 1 daemon entry point + many `pcntl_*` calls
**Phase**: Phase 1 (foundation — Celery setup)
**Severity**: HIGH (architectural change)
Source: `source-repos/ttrss-php/ttrss/update_daemon2.php`

### D-DA-02 — SIMPLE_UPDATE_MODE HTTP-triggered background tasks

**Source**: `Handler_Public::*()` calls `run_hooks(HOOK_UPDATE_TASK, ...)` and
`run_hooks(HOOK_HOUSE_KEEPING, ...)` as a side effect of HTTP requests.
**Target gotcha**: This anti-pattern must not be replicated in Flask.
Python target should fire `task.apply_async()` (Celery, non-blocking) from the HTTP path,
or use Celery beat for housekeeping regardless of HTTP traffic.
**Grep count**: 2 invocation sites in handler/public.php
**Phase**: Phase 1 (Celery setup)
**Severity**: MEDIUM
Source: `source-repos/ttrss-php/ttrss/classes/handler/public.php:415–421`

---

## Category: Internationalisation (I18N)

### D-I18N-01 — PHP gettext polyfill → Flask-Babel

**Source**: `lib/gettext/gettext.inc` + `lib/accept-to-gettext.php` provide gettext
in PHP environments lacking the native `gettext` extension.
`__($str)` calls the polyfill's `T_gettext($str)`.
**Target gotcha**: Python `flask-babel` uses `gettext(str)` or `lazy_gettext(str)`.
All `__('string')` calls become `_('string')` or `lazy_gettext('string')`.
The `.po`/`.mo` files in `locale/` are reusable in Python after msgfmt recompilation.
**Grep count**: ~200 calls to `__()`
**Phase**: Phase 2 (core logic — i18n infrastructure)
**Severity**: LOW (mechanical replacement)
Source: `source-repos/ttrss-php/ttrss/include/functions.php` (`__()`)

---

## Totals by severity

| Severity | Count |
|---|---|
| CRITICAL | 3 (SF-01 SQL injection, SF-03 mcrypt, SF-02 SHA1-via-D-SE-03) |
| HIGH | 10 |
| MEDIUM | 9 |
| LOW | 4 |
| **Total** | **26 seed entries** |

---

## Phase forward-links

| Phase | Divergences exercised |
|---|---|
| Phase 1 (foundation) | D-DA-01, D-DA-02, D-RH-02, D-RH-03, D-DB-03 |
| Phase 2 (core logic) | D-SE-02, D-DB-02, D-PH-02, D-PH-03, D-I18N-01 |
| Phase 3 (business logic) | D-SE-03, D-DB-01, D-DB-04 |
| Phase 4 (API handlers) | D-RH-01, D-SE-01, D-AC-01, D-AC-02, D-AC-03, D-PH-01, D-PH-04 |
| Phase 5 (semantic verification) | All — cross-verification pass |

Full divergence taxonomy extension (Phase 5): 40-category taxonomy as per
prior Phase 5 semantic verification work. This seed catalogue provides entries
D01–D26; Phase 5 expands to the full D01–D40 set.
