---
name: semantic_verification_plan
description: Plan for semantic PHP→Python verification — walk every Python function against its PHP source, identify all discrepancies, fix to 100% semantic equivalence. SME confirmed all generated code is incorrect.
type: project
---

# Semantic Coverage Verification Plan

**Created:** 2026-04-05  
**Trigger:** SME review found all generated Python code incorrect — functional logic,
business rules, and non-functional requirements lost across all modules.  
**Goal:** Every Python function must be 100% semantically equivalent to its PHP source.
No approximations, no "close enough".

---

## Problem Statement

The previous migration produced Python code that:
- Has correct _structure_ (right class/module layout, correct traceability comments)
- Has **incorrect _semantics_**: wrong SQL conditions, missing branches, missing
  auth checks, wrong return formats, missing side effects, missed hook calls
- Was verified only for _comment presence_ (structural audit), not _logic equivalence_

The SME verified a sample and found every checked function had discrepancies.
This plan fixes the entire codebase function by function.

---

## Discrepancy Taxonomy

Every discrepancy found must be classified. This drives fix priority.

| Code | Name | Examples |
|------|------|---------|
| D1 | Missing branch | PHP `if ($user_limit) {...}` entirely absent in Python |
| D2 | Wrong condition | PHP `>= 0` becomes Python `> 0`; PHP `!empty($x)` becomes `if x` |
| D3 | SQL mismatch | Missing JOIN, wrong WHERE column, missing ORDER BY, wrong LIMIT |
| D4 | Missing auth | PHP checks `$_SESSION["uid"]` ownership; Python skips the check |
| D5 | Wrong return | PHP returns `{"status":"OK","content":{...}}`; Python returns different shape |
| D6 | Missing hook | PHP calls `run_hooks(HOOK_*)` at specific point; Python omits it |
| D7 | Missing side effect | PHP UPDATEs a column or invalidates cache; Python skips it |
| D8 | Wrong config | PHP uses `SELF_URL_PATH`; Python uses different constant or hardcodes |
| D9 | Type coercion | PHP `(int)$_REQUEST["id"]` guards; Python allows non-int through |
| D10 | Missing error path | PHP returns specific error on DB failure; Python silently continues |
| D11 | Operation order | PHP invalidates cache AFTER write; Python does it before |
| D12 | Feature absent | Entire sub-feature (e.g., PubSubHubbub ping) not implemented at all |
| D13 | Wrong null/empty | PHP `isset($x) && $x !== ""` vs Python `if x` — different semantics |
| D14 | Session mismatch | PHP reads `$_SESSION["key"]`; Python reads different session key |
| D15 | Missing pagination | PHP LIMIT/OFFSET logic absent or wrong |

---

## Verification Methodology (Per Function)

For each Python function with a `Source:` traceability comment:

### Step 1 — Extract PHP source
Read the exact PHP function body from the source file at the cited lines.

### Step 2 — Read Python implementation
Read the corresponding Python function.

### Step 3 — Compare systematically (checklist)

```
□ Input validation/type coercion (PHP (int), (bool), isset checks)
□ Authentication: is owner_uid / $_SESSION["uid"] enforced?
□ Authorization: any role/admin check present?
□ Every DB query:
    □ Correct table(s)?
    □ Correct columns (SELECT list)?
    □ Correct WHERE conditions (all of them)?
    □ Correct JOINs (type, ON clause)?
    □ Correct ORDER BY?
    □ Correct LIMIT / OFFSET?
    □ Correct UPDATE/INSERT targets?
□ All conditional branches (if/elseif/else, switch/case)?
□ All loop logic (foreach, while — what happens on empty result)?
□ Hook calls (add_hook/run_hooks) present and at correct point?
□ Cache invalidation (ccache_* calls) present and at correct point?
□ Return value: shape, field names, field types, error envelopes?
□ Error handling: what does PHP return/throw on each failure?
□ NULL/empty handling: PHP empty(), isset(), === NULL equivalents?
□ Config/constant references: correct constant names?
□ Side-effect order: do writes come before or after reads/cache?
```

### Step 4 — Document discrepancies
For each mismatch: classify (D1-D15), note PHP lines vs Python lines, note correct value.

### Step 5 — Fix
Rewrite the Python function to match PHP semantics exactly.
Do NOT change the function signature or module structure unless unavoidable.

### Step 6 — Regression test
Run `pytest` after each function fix. All 602 baseline tests must pass.

---

## Verification Workstreams

Ordered by criticality. Each workstream = one PHP source file → one or more Python modules.

---

### WS-A: Authentication & Session (P0 — blocks all other features)

**PHP source:** `ttrss/classes/api.php` (login/session), `ttrss/plugins/auth_internal/init.php`  
**PHP source:** `ttrss/include/functions.php` (validate_session, authenticate_user)  
**Python target:** `ttrss/auth/authenticate.py`, `ttrss/auth/password.py`, `ttrss/auth/session.py`

Critical functions to verify:
- `API::login` → `authenticate_user()` — password check, OTP, session creation, API key
- `API::logout` → session destroy
- `API::isLoggedIn` → session validation
- `Auth_Internal::check_password` → bcrypt + argon2id dual-hash (ADR-0008)
- `authenticate_user` (functions.php) → full auth flow including IP logging
- `validate_session` (functions.php) → session token validation

Known failure modes to watch:
- PHP's `make_password()` creates SHA1; Python should verify SHA1 AND argon2id
- PHP checks `login_failure_count` and `login_failure_reset_time` — rate limiting
- PHP sets `$_SESSION["ref_schema_version"]` on login — Python equivalent?
- `API_DISABLED` check per user must be enforced
- Base64-decoded password fallback (line 73-82 of api.php)

---

### WS-B: API Dispatch & getHeadlines (P0 — core API)

**PHP source:** `ttrss/classes/api.php` (~792 lines)  
**Python target:** `ttrss/blueprints/api/views.py` (~1560 lines — suspiciously 2× longer)

Functions in priority order:
1. `API::getHeadlines` / `api_get_headlines` — most complex, most used
2. `API::getArticle` 
3. `API::updateArticle` (mark read/unread/starred/published)
4. `API::getFeeds` / `api_get_feeds`
5. `API::getCategories`
6. `API::subscribeToFeed`
7. `API::unsubscribeFeed`
8. `API::getFeedTree`
9. `API::getCounters`
10. `API::getPref`
11. `API::setArticleLabel`
12. `API::shareToPublished`
13. `API::getLabels`

**getHeadlines known complexity** (api.php lines 631+):
- `$feed_id` virtual ID handling: 0=all feeds, -1=starred, -2=published, -3=fresh,
  -4=all articles, -6=recently read, negative label feeds (`LABEL_BASE_INDEX`)
- `view_mode`: all_articles, unread, adaptive, marked, published, has_note
- `order_by`: date_reverse, date_default, score
- `search` parameter: delegates to search engine
- `show_excerpt`, `show_content` flags → different fields in response
- `include_attachments` → enclosure data
- `since_id` → only newer than this ID
- `include_nested` → include sub-category feeds
- `sanitize_values` → sanitize HTML before returning
- counter update side effect (read-mark updates adaptive counters)

---

### WS-C: RPC / Backend (P0 — UI interaction)

**PHP source:** `ttrss/classes/rpc.php` (~654 lines), `ttrss/classes/backend.php`  
**Python target:** `ttrss/blueprints/backend/views.py` (~1412 lines)

Functions to verify:
1. `RPC::mark` — mark article read/unread (updates ttrss_user_entries + counters)
2. `RPC::catchup` — catchup feed (marks all read, updates counters)
3. `RPC::markfeed` — mark all articles in feed as read
4. `RPC::getCounters` — unread/fresh counts (complex virtual feed logic)
5. `RPC::setScore` — article score
6. `RPC::edit` — toggle star/publish/note
7. `RPC::getSavedArticles` — published articles with access key
8. `RPC::getlinktitlebyid` — async title fetch
9. `RPC::sanityCheck` — integrity check
10. `RPC::updaterandomfeed` → `updaterandomfeed_real` — update one due feed

**mark/catchup complexity:**
- PHP updates `ttrss_user_entries.unread = false` for specific conditions
- Adaptive counter cache invalidation must follow the write
- `fresh` flag: articles younger than `FRESH_ARTICLE_MAX_AGE` hours

---

### WS-D: Feed Update Engine (P0 — core daemon function)

**PHP source:** `ttrss/include/rssfuncs.php` (~1431 lines)  
**Python target:** `ttrss/tasks/feed_tasks.py`, `ttrss/articles/persist.py`

This is the most complex single function in TT-RSS:

1. `update_rss_feed` — the entire feed update pipeline:
   - HTTP fetch with ETag/Last-Modified caching
   - Feed parsing (feedparser)
   - Deduplication (GUID + title hash)
   - Article persistence (INSERT + UPDATE)
   - Filter application during insert
   - Label assignment
   - Tag extraction
   - Enclosure handling
   - PubSubHubbub ping
   - `last_updated`, `last_modified`, `etag` update on feed record
   - Error handling: set `last_error` on feed
   - Auth credentials (Basic auth, Fernet-encrypted passwords)
   - `update_favicon` call

2. `make_guid_from_title` — exact PHP SHA1 algorithm
3. `assign_article_to_label_filters` — filter → label assignment during save
4. `cleanup_tags` — already partially fixed (functions2.php)

---

### WS-E: Article Operations (P1)

**PHP source:** `ttrss/classes/article.php`, `ttrss/include/functions.php` (article section)  
**Python target:** `ttrss/articles/ops.py`, `ttrss/articles/tags.py`

1. `Article::mark_timestamp` — updates `last_read` timestamp correctly
2. `Article::catchup_feed` — catchup logic (conditions on date, score)
3. `create_published_article` — published feed article creation
4. `get_article_filters` — filter matching against article fields
5. `assign_to_labels_multi` — batch label assignment
6. Tag operations: `Article::_article_complete_tags`, `_article_assign_to_label`

---

### WS-F: Feed Operations (P1)

**PHP source:** `ttrss/classes/feeds.php` (~1163 lines)  
**Python target:** `ttrss/feeds/ops.py`, `ttrss/feeds/browser.py`, `ttrss/feeds/categories.py`

1. `Feeds::view` — main feed view (headlines rendering)
2. `subscribe_to_feed` — validation, dupe check, favicon fetch, initial update trigger
3. `remove_feed` — cascade delete (articles, filters, labels, counters)
4. `feedBrowser` — feed browser/discovery logic
5. `categorize_feed` — move feed to category
6. `add_feed_category` — create category

---

### WS-G: Unread Counters (P1 — visible in UI)

**PHP source:** `ttrss/classes/rpc.php:getCounters`, `ttrss/include/functions.php`  
**Python target:** `ttrss/feeds/counters.py`

The counter system is notoriously complex:
- Real feed unread counts (per feed)
- Category counts (aggregate of feeds in category)
- Virtual feed counts: Starred (-1), Published (-2), Fresh (-3), All Articles (-4)
- Label virtual feeds (LABEL_BASE_INDEX - 1 - label_id)
- `ttrss_counters_cache` table refresh logic
- `global` counter (total unread across all feeds)
- `fresh` count based on `FRESH_ARTICLE_MAX_AGE` config

---

### WS-H: Article Search (P1)

**PHP source:** `ttrss/classes/feeds.php:Feeds::search`, `ttrss/include/functions.php`  
**Python target:** `ttrss/articles/search.py`

- Full-text search via PostgreSQL `tsvector` / `plainto_tsquery`
- Date filter parsing (`d:7` = last 7 days, `d:2020-01-01` = since date)
- `note:` search qualifier
- `star:` search qualifier
- `pub:` (published) qualifier
- `unread:` qualifier
- `feed:N` qualifier (restrict to feed ID)
- `cat:N` qualifier (restrict to category)
- Result ordering by relevance vs date

---

### WS-I: Filter Engine (P1)

**PHP source:** `ttrss/classes/pref/filters.php:Pref_Filters::testFilter`,
`ttrss/include/rssfuncs.php:get_article_filters`, `ttrss/include/functions.php`  
**Python target:** `ttrss/articles/filters.py`, `ttrss/prefs/filters_crud.py`

Filter matching engine:
- Field types: title, content, author, tag, link, forwarded, score
- Match types: contains, not contains, regexp, not regexp
- Case sensitivity flag
- Filter actions: mark read, mark starred, assign label, set score, stop processing
- Multi-rule AND/OR logic
- `inverse` flag on rules
- `enabled` flag on filters
- `feed_id` and `cat_id` scope (filter only applies to certain feeds)

---

### WS-J: OPML Import/Export (P2)

**PHP source:** `ttrss/classes/opml.php` (~523 lines)  
**Python target:** `ttrss/feeds/opml.py`

- Export: category hierarchy → `<outline type="rss">` elements
- Export: label feeds, filter export
- Import: `<outline>` category detection (`type="category"` or no type)
- Import: feed URL normalization
- Import: category creation if not exists
- Import: duplicate feed detection
- Error handling: malformed OPML, inaccessible feeds

---

### WS-K: Article Storage / Persistence (P2)

**PHP source:** `ttrss/include/rssfuncs.php` (article insert/update section)  
**Python target:** `ttrss/articles/persist.py`

- GUID deduplication: check `ttrss_entries.guid` first, then title hash
- `ttrss_user_entries` row creation per user (for multi-user scenarios)
- `score` calculation from filters at insert time
- `updated` vs `date_entered` semantics (feed's `pubDate` vs our insert time)
- Tag extraction and storage in `ttrss_tags`
- Enclosure detection and storage in `ttrss_enclosures`
- Content sanitization before store (lxml/feedparser)
- `source_feed_id` for articles from aggregated feeds

---

### WS-L: Preferences CRUD (P2)

**PHP source:** `ttrss/classes/pref/feeds.php`, `ttrss/classes/pref/prefs.php`,
`ttrss/classes/pref/users.php`, `ttrss/classes/pref/labels.php`  
**Python target:** `ttrss/prefs/feeds_crud.py`, `ttrss/prefs/user_prefs_crud.py`,
`ttrss/prefs/users_crud.py`, `ttrss/prefs/labels_crud.py`

High-risk areas:
- `Pref_Feeds::editsaveops` — bulk feed edit save (complex, many fields)
- `Pref_Feeds::rescore` — rescore feed articles against current filters
- `Pref_Prefs::changepassword` — password change (argon2id + old SHA1 handling)
- `Pref_Prefs::saveconfig` — config save (must validate all keys)
- `Pref_Users::add` — admin user creation
- `Pref_Users::remove` — cascade delete user data

---

### WS-M: Background Tasks (P2)

**PHP source:** `ttrss/include/rssfuncs.php:update_daemon_common`, housekeeping sections  
**Python target:** `ttrss/tasks/feed_tasks.py`, `ttrss/tasks/housekeeping.py`, `ttrss/tasks/digest.py`

- `update_random_feed` — pick a due feed (lock, update, release lock)
- `housekeeping_task` — what PHP's housekeeping does exactly
- `cleanup_tags` — already fixed (functions2.php:2030-2069)
- `purge_orphans` — article purge logic (purge_unread flag, purge_interval)
- Email digest — schedule, format, what articles are included

---

### WS-N: Plugin System (P3)

**PHP source:** `ttrss/classes/pluginhost.php`  
**Python target:** `ttrss/plugins/manager.py`

- `PluginHost::register_plugin` — exactly what fields are stored
- `PluginHost::add_hook` / `del_hook` / `run_hooks` — hook dispatch semantics
- `PluginHost::save_data` / `load_data` — plugin storage format in DB
- `PluginHost::get_link` — URL generation

---

### WS-O: Counter Cache (P3)

**PHP source:** `ttrss/include/ccache.php`  
**Python target:** `ttrss/ccache.py`

- `ccache_update` — exact update SQL
- `ccache_find` — exact find SQL
- `ccache_invalidate` — cascade invalidation (feed → category → global)
- Virtual feed cache entries (labeled feed IDs)

---

## Execution Order

```
P0 (Week 1): WS-A Auth → WS-B API → WS-C RPC → WS-D Feed Update
P1 (Week 2): WS-E Articles → WS-F Feeds → WS-G Counters → WS-H Search → WS-I Filters
P2 (Week 3): WS-J OPML → WS-K Persist → WS-L Prefs CRUD → WS-M Background
P3 (Week 4): WS-N Plugins → WS-O Counter Cache → regression sweep
```

---

## Fix Protocol

For each function:

1. **Read PHP source first** — open the exact lines cited in the Source: comment
2. **Read Python current** — read the full function
3. **List ALL discrepancies** using D1-D15 taxonomy
4. **Rewrite Python** — match PHP semantics exactly:
   - Same SQL logic (translated to SQLAlchemy Core/ORM)
   - Same branch conditions (watch PHP truthiness rules)
   - Same return value structure
   - Same error cases
   - Same side effects in same order
5. **Preserve Python idioms** only where PHP and Python are semantically equivalent
   (e.g., PHP `foreach ($result as $row)` → Python `for row in result` is fine)
6. **Update traceability comment** to cite exact PHP lines verified
7. **Run tests** after every function

---

## Discrepancy Tracking

Track in `docs/semantic_verification_report.md` (created once work begins):

```markdown
## [module_path.py] — [php_source.php]

### func_name() [lines X-Y PHP / lines A-B Python]
Status: [ ] Pending  [x] Verified OK  [!] Fixed

Discrepancies found:
- D3: SQL missing `AND ttrss_user_entries.owner_uid = :uid` (PHP line 45)
- D1: Missing branch: `if (!$feed_id)` error return (PHP lines 23-25)

Fix applied: commit XXXXXXX
```

---

## Test Expansion Required

602 tests currently pass but cover mostly unit/model logic. Semantic verification
needs integration tests for each function:

- Per-function test: given PHP behavior X → Python must produce identical output Y
- Test fixtures must match PHP test data (same DB state)
- For complex functions (getHeadlines, getCounters), snapshot tests against
  known-good PHP output are ideal

As functions are verified and fixed, add regression tests that lock in the
now-correct behavior.

---

## Success Criteria

A function is **verified** when:
1. All discrepancy codes D1-D15 checked and none found (or all found ones fixed)
2. A test exists that exercises the function's main path AND its error paths
3. The Source: comment cites the exact PHP lines verified
4. `pytest` still passes all baseline tests

The codebase is **complete** when:
- All workstreams WS-A through WS-O are verified
- Zero unfixed discrepancies remain in the tracking report
- Test coverage of target code ≥ 80% (line coverage)
- A second SME pass confirms correctness

---

## Notes on PHP→Python Semantic Traps

These patterns consistently cause discrepancies:

| PHP | Python gotcha |
|-----|--------------|
| `empty($x)` | `not x` — but PHP `empty(0)` is true, Python `not 0` is also true. However `empty("")` == `not ""` == True, `empty([])` == `not []` == True. But PHP `empty("0")` is **True**, Python `not "0"` is **False**. |
| `(int)$x` | Must cast: `int(x)` — and handle ValueError |
| `isset($x)` | Must check key existence, not just truthiness |
| `$arr["key"] ?? default` | `arr.get("key", default)` — correct |
| `!== false` | PHP `strpos` returns false not -1 on miss; Python `str.find` returns -1 |
| `$result` in MySQL | SQLAlchemy `result.fetchall()` — must call |
| `$this->dbh->fetch_assoc` returns assoc array | ORM returns Row object — field names case-sensitive |
| PHP truthy: `"0"` is falsy | Python: `"0"` is truthy |
| PHP arrays are ordered maps | Python dicts are ordered from 3.7+ — OK |
| `preg_match` returns 0 (no match) | Python `re.search` returns None — `if not match` works |
| `htmlspecialchars` default mode | `markupsafe.escape` — different defaults |
| PHP `intval` on non-numeric returns 0 | Python `int("abc")` raises ValueError |
