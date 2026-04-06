# 14 — Semantic Discrepancy Catalog

## Purpose

This document catalogs **every known category of semantic discrepancy** between the PHP source and the Python migration of TT-RSS. It is the authoritative reference for what "behavioral equivalence" (constraint C3 from the project charter) means at the code level.

Unlike spec 12 (testing strategy), which defines HOW to test, this spec defines WHAT to test for: the specific patterns that cause PHP and Python to behave differently despite superficially similar code.

The catalog covers 40 discrepancy categories (D01–D40) organized by domain, 40 semantic traps specific to PHP→Python translation, 8 integration pipeline contracts for cross-function verification, and model verification depth checks for all 37 ORM classes.

---

## 1. Discrepancy Taxonomy (40 Categories)

### 1A. SQL & Query Semantics (D01–D10)

| Code | Name | Description | Example from codebase |
|------|------|-------------|----------------------|
| D01 | **SQL join topology** | PHP uses tables A,B,C in FROM (implicit cross-join); Python uses explicit JOIN but with a different table set, changing the result set semantics | `catchup_feed` label path: PHP inner query joins `ttrss_entries, ttrss_user_entries, ttrss_user_labels2` (3-table cross-join); Python queries only `TtRssUserLabel2` (1 table). PHP's implicit join requires a matching `ttrss_user_entries` row; Python's subquery doesn't |
| D02 | **SQL computation locus** | PHP computes a value in the database (`NOW() - INTERVAL '1 day'`); Python computes it in the application (`datetime.now(tz=utc) - timedelta(days=1)`). If DB and app server clocks differ, results differ | `catchup_feed` date cutoff: PHP `NOW() - INTERVAL` (DB time); Python `datetime.now()` (app time) |
| D03 | **SQL column mismatch** | SELECT list, WHERE columns, or UPDATE targets differ between PHP and Python | `queryFeedHeadlines`: PHP selects `favicon_avg_color` from `ttrss_feeds`; Python omits it. Frontend expecting this column gets `undefined` |
| D04 | **SQL subquery nesting** | PHP uses a derived-table wrapper `SELECT ... FROM (SELECT ... ) AS tmp` for MySQL compatibility; Python uses a flat `scalar_subquery()`, changing query optimizer behavior | `catchup_feed`: PHP nested `ref_id IN (SELECT id FROM (SELECT id FROM ...) as tmp)` absent in Python |
| D05 | **SQL WHERE condition** | A WHERE clause references a different table or column | `catchup_feed` tag path: PHP filters `ttrss_user_entries.owner_uid`; Python filters `ttrss_tags.owner_uid`. Both are "owner_uid" but different tables may have different row coverage |
| D06 | **SQL ORDER BY / LIMIT / OFFSET** | Pagination or ordering logic differs | `queryFeedHeadlines`: when `VFEED_GROUP_BY_FEED` pref is true, PHP prepends `ttrss_feeds.title` to ORDER BY; Python skips this entirely |
| D07 | **SQL dialect remnant** | MySQL-specific syntax surviving where it shouldn't, or PostgreSQL-specific syntax missing | Feed update daemon: `DB_TYPE` conditional branches for `INTERVAL` syntax; Python should only have PostgreSQL path (ADR-0003) |
| D08 | **SQL transaction boundary** | Different commit granularity — per-row vs per-batch | `update_rss_feed`: PHP does `BEGIN`/`COMMIT` per article insert (allows partial success); Python does a single `session.commit()` per feed (all-or-nothing) |
| D09 | **SQL validation** | PHP validates dynamically-constructed SQL fragments (e.g., filter regex) via a test query before using them; Python doesn't | `queryFeedHeadlines`: PHP runs `SELECT true AS true_val FROM ... WHERE $filter_query_part LIMIT 1` to catch bad regex; on failure falls back to `"false AND"`. Python applies filters directly — bad regex causes unhandled exception |
| D10 | **SQL parameter type** | PHP casts input before interpolation (`(int)$_REQUEST["id"]`); Python passes raw form value | API handlers: PHP `intval()` guarantees integer; Python `request.form.get()` returns string — if fed to SQL without cast, type mismatch errors or incorrect comparisons |

### 1B. Type System & Coercion (D11–D16)

| Code | Name | Description | Example |
|------|------|-------------|---------|
| D11 | **Systemic type coercion** | A core utility function returns differently-typed values in PHP (native bool/int) vs Python (raw string), affecting ALL callers | `get_pref`: PHP `Db_Prefs::convert()` returns native PHP `true`/`false`/`int`; Python `get_user_pref()` always returns raw string. Every pref consumer (`make_init_params`, `sanitize`, `queryFeedHeadlines`, etc.) is affected |
| D12 | **PHP falsy divergence** | PHP `empty("0")` is `true`, `(bool)"0"` is `false`; Python `bool("0")` is `True`, `not "0"` is `False` | Pref boolean coercion: PHP `(int) get_pref("BOOL_PREF")` where value is `"0"` → 0; Python manual check may treat `"0"` as truthy |
| D13 | **Null/empty/isset** | PHP `isset($x)` checks existence AND not-null; `!empty($x)` checks existence AND not-null AND not-falsy. Python `if x` conflates None, 0, "", [] | Session fallback: `if (!$owner_uid) $owner_uid = $_SESSION['uid']` — PHP falsy catches 0, null, false, ""; Python `if not owner_uid` same for 0/None/"" but NOT for `"0"` |
| D14 | **Numeric boundary** | Off-by-one in comparison operators: `<` vs `<=`, `>` vs `>=` | `catchup_feed` line 438: PHP `$feed < LABEL_BASE_INDEX` (strictly less); Python `nfeed <= LABEL_BASE_INDEX` (less-or-equal). If nfeed equals exactly LABEL_BASE_INDEX, PHP takes the else-path (tag), Python takes the label path |
| D15 | **intval/int() divergence** | PHP `intval("abc")` returns 0; Python `int("abc")` raises `ValueError` | Any `(int)$_REQUEST["param"]` in PHP silently accepts garbage; Python must wrap in try/except or guard |
| D16 | **Array/dict semantics** | PHP arrays are ordered maps with integer and string keys coexisting; `array_merge()` renumbers numeric keys; `+` preserves keys. Python dicts and lists are separate types | OPML filter import: nested PHP arrays serialized as JSON have mixed-key behavior that Python dicts handle differently |

### 1C. Data Flow & Content (D17–D22)

| Code | Name | Description | Example |
|------|------|-------------|---------|
| D17 | **Content priority inversion** | PHP extracts field A first and falls back to B; Python extracts B first and falls back to A — semantically opposite priority | `update_rss_feed`: PHP `$entry_content = $item->get_content(); if (!$entry_content) $entry_content = $item->get_description()` (full content first). Python `entry.get("summary") or content[0]["value"]` (summary first). Articles with both will show different text |
| D18 | **GUID construction** | PHP applies transformations (owner prefix, hashing) to article GUIDs; Python uses raw feedparser ID — changes the deduplication model | `update_rss_feed`: PHP GUID is `SHA1:` + `owner_uid` + raw_guid; Python uses `entry["id"]` directly. Same article in two users' feeds has different GUIDs in PHP but identical GUIDs in Python |
| D19 | **Field truncation** | PHP truncates string fields to match DB column length; Python doesn't — potential `DataError` on INSERT | `update_rss_feed`: PHP `mb_substr($entry_guid, 0, 245)`, `mb_substr($entry_comments, 0, 245)`, `mb_substr($entry_author, 0, 245)`. Python: no truncation |
| D20 | **Timestamp validation** | PHP validates article timestamps and corrects invalid ones; Python uses raw values | `update_rss_feed`: PHP rejects timestamps that are `-1`, falsy, or in the future, falling back to `time()`. Python uses feedparser's raw `published_parsed` as-is |
| D21 | **Encoding normalization** | PHP applies multi-level charset correction (detect, convert, strip invalid bytes); Python relies on feedparser's built-in encoding handling, which has different heuristics | `FeedParser` constructor: PHP has 3-level fallback: (1) extract encoding from XML declaration, (2) `mb_convert_encoding`, (3) strip invalid unicode ranges via regex |
| D22 | **String interpolation** | PHP inline variable expansion `"$var-$var2"` vs Python f-strings — watch for missing variables, different concatenation, or HTML entity context | Error messages, template rendering, URL construction |

### 1D. Session, Config & Global State (D23–D28)

| Code | Name | Description | Example |
|------|------|-------------|---------|
| D23 | **Session state elimination** | PHP reads `$_SESSION["key"]` for values that have no Python equivalent — these values are simply absent in the Python output | `make_init_params`: PHP returns 13+ session/config values (`bw_limit`, `csrf_token`, `cookie_lifetime`, `icons_url`, `php_platform`, `php_version`, `sanity_checksum`, `max_feed_id`, `num_feeds`, `widescreen`, `simple_update`, `theme`, `plugins`). Python omits all of them |
| D24 | **Session fallback** | PHP function parameter defaults to session value when caller passes null/0; Python requires explicit parameter | `get_pref`: PHP `if (!$user_id) $user_id = $_SESSION["uid"]`; Python `owner_uid` is required. `catchup_feed` similarly |
| D25 | **Config constant mapping** | PHP uses `define()`d constants (`SELF_URL_PATH`, `ICONS_URL`, `SESSION_COOKIE_LIFETIME`, `SINGLE_USER_MODE`, `DB_TYPE`, `DAEMON_UPDATE_LOGIN_LIMIT`, `CACHE_DIR`, `SCHEMA_VERSION`, etc.); Python must map each to Flask config | `make_init_params`: multiple constants not mapped |
| D26 | **Profile-aware queries** | PHP pref queries include `$_SESSION["profile"]` in WHERE; Python may not join profile context | `get_pref`: PHP adds `AND (profile = '$profile' OR profile IS NULL)` when schema >= 63 |
| D27 | **Global variable** | PHP uses `global` keyword for cross-function state (`$fetch_last_error`, `$fetch_last_error_code`, `$utc_tz`, `$user_tz`); Python uses module-level variables or omits them | HTTP client error reporting: PHP sets `global $fetch_last_error` on fetch failure; Python may raise instead |
| D28 | **In-memory cache elimination** | PHP caches data in-process (pref singleton, feed XML file cache); Python hits DB or network every time | `get_pref`: PHP `Db_Prefs` singleton loads ALL prefs once per request into `$this->cache`. Python queries DB per call. `update_rss_feed`: PHP caches feed XML to `CACHE_DIR/simplepie/sha1.xml` for 30-second reuse |

### 1E. Return Value & API Contract (D29–D33)

| Code | Name | Description | Example |
|------|------|-------------|---------|
| D29 | **Return shape divergence** | Function returns different keys, extra/missing fields, or different types | `make_init_params`: 13 missing keys. `queryFeedHeadlines`: PHP returns `$feed_title`, `$feed_site_url`, `$last_error`, `$last_updated` metadata alongside the cursor; Python returns only the row list |
| D30 | **Return materialization** | PHP returns a database cursor (streams rows lazily); Python returns a fully-materialized list (loads all into memory) | `queryFeedHeadlines`: PHP `db_query()` returns a result resource (row-by-row fetch). Python `session.execute(stmt).all()` loads entire result set. For 10K+ articles, memory behavior differs significantly |
| D31 | **Error envelope** | PHP returns specific error array/message on failure; Python raises exception or returns None | `get_pref`: PHP `user_error($msg, E_USER_ERROR)` (fatal) for unknown pref name. Python returns `None` silently. API callers expecting a crash for bad pref names get silent corruption instead |
| D32 | **HTTP response headers** | PHP sets `Content-Type`, `Content-Disposition`, `Cache-Control` explicitly; Python may not | OPML export: PHP `header("Content-Type: application/xml")`. RSS feed: PHP `header("Content-Type: text/xml")` |
| D33 | **JSON response structure** | API error/success wrappers, seq echoing, field naming conventions | API dispatch: PHP returns `{"seq": $seq, "status": 0, "content": {...}}`. Verify Python matches exactly, including error codes (`API_E_LOGIN_ERROR`, `API_E_INCORRECT_USAGE`, etc.) |

### 1F. Feature & Behavior (D34–D40)

| Code | Name | Description | Example |
|------|------|-------------|---------|
| D34 | **Feature absent** | An entire sub-feature is not implemented in Python | PubSubHubbub subscription (hub discovery + HMAC verification), Sphinx full-text search, favicon refresh + `favicon_avg_color` computation, image caching (`cache_images()`), article language detection (`Text_LanguageDetect`), `bw_limit` image stripping, search term highlighting (`highlight_words`), N-gram duplicate detection, feed XML file caching |
| D35 | **Hook argument mismatch** | PHP `run_hooks(HOOK_X, $a, $b, $c, $d, $e)` passes N arguments; Python hookspec declares N-1 (or different) arguments | `sanitize`: PHP passes 5 args to `hook_sanitize($doc, $site_url, $allowed_elements, $disallowed_attributes, $article_id)`; Python passes 4 (omits `article_id`). Plugins using `article_id` in sanitize hooks silently lose context |
| D36 | **Hook call site missing** | PHP calls `run_hooks(HOOK_X)` at a specific execution point; Python omits the call entirely | Feed update: PHP calls `HOOK_FEED_FETCHED` after HTTP response, `HOOK_FEED_PARSED` after XML parse, `HOOK_ARTICLE_FILTER` during filter application. Verify all are present in Python |
| D37 | **Side effect order** | PHP performs side effects (cache invalidation, counter update, DB write) in a specific order; Python changes the order | Counter cache: PHP invalidates cache AFTER article state write commits. If Python invalidates before write, cache is recomputed with stale data |
| D38 | **Error recovery model** | PHP logs error and continues (returns error value); Python raises exception (potentially triggering Celery retry) — fundamentally different failure semantics | `update_rss_feed`: PHP writes `last_error` to `ttrss_feeds` and returns (feed stays in DB). Python raises, triggering Celery autoretry — same feed may be retried N times, or left in "updating" state |
| D39 | **DOM/parsing model** | PHP `DOMDocument::loadHTML()` creates full HTML document with `<html>`, `<body>`, DOCTYPE; Python `lxml.html.fragment_fromstring(create_parent="div")` creates fragment wrapped in `<div>` | `sanitize`: output wrapped in `<div>` in Python, in `<html><body>` in PHP. PHP line 930 explicitly removes DOCTYPE; Python has no DOCTYPE to remove |
| D40 | **Transactional semantics** | PHP per-row `BEGIN`/`COMMIT` allows partial success (some articles saved, others fail); Python all-or-nothing per feed | `update_rss_feed`: PHP commits each article individually — a parse error on article 50 still saves articles 1-49. Python's single commit means a failure on article 50 rolls back all 49 |

---

## 2. PHP→Python Semantic Traps

These patterns consistently cause discrepancies and must be checked in EVERY function during verification.

### 2A. Type & Comparison Traps

| # | PHP Pattern | Python Gotcha | Estimated frequency in codebase |
|---|-------------|---------------|-------------------------------|
| 1 | `empty($x)` | PHP `empty("0")` → true, `empty([])` → true, `empty(0)` → true. Python `not "0"` → False. **"0" is the killer — truthy in Python, falsy in PHP.** | ~50 call sites |
| 2 | `(int)$x` / `intval($x)` | PHP `intval("abc")` → 0, `intval("3abc")` → 3. Python `int("abc")` → ValueError. | ~30 call sites |
| 3 | `isset($x)` | Checks key exists AND not-null. Python `if x` doesn't check existence. Equivalent: `"key" in dict and dict["key"] is not None`. | ~40 call sites |
| 4 | `$x == false` (loose) | PHP: `0 == false` → true, `"" == false` → true, `"0" == false` → true, `null == false` → true. Python: `"" == False` → False, `"0" == False` → False. | ~20 call sites |
| 5 | `$x === false` (strict) | PHP strict equals used after `strpos()` (returns 0 vs false). Python `str.find()` returns 0 vs -1 (both integers). Must use `!= -1` not truthiness. | ~15 call sites |
| 6 | `$a ?? $b` (null coalescing) | PHP: only replaces null. `"" ?? "default"` → `""`, `0 ?? "default"` → 0. Python `x or "default"` replaces ALL falsy. Must use `x if x is not None else "default"`. | ~25 call sites |
| 7 | `(bool)$x` | PHP: `(bool)"0"` → false. Python: `bool("0")` → True. | ~10 call sites |
| 8 | `array_key_exists($k, $a)` vs `isset($a[$k])` | `array_key_exists` returns true even for null values; `isset` returns false. Python `k in d` is like `array_key_exists`. | ~10 call sites |

### 2B. String & Regex Traps

| # | PHP Pattern | Python Gotcha | Frequency |
|---|-------------|---------------|-----------|
| 9 | `mb_substr($s, 0, 245)` | Both count characters (not bytes) when encoding is UTF-8. The trap: if PHP's `mb_internal_encoding` isn't set, PHP counts bytes. Python always counts characters. Also: Python `s[:245]` has no equivalent of `mb_strimwidth` (truncate to width). | ~8 call sites |
| 10 | `preg_match($pat, $str, $matches)` | Returns 0/1 (int), not boolean. Python `re.search()` returns None/Match. Captures in `$matches[1]` vs `m.group(1)`. PHP returns 0 on regex error too (check `preg_last_error()`); Python raises `re.error`. | ~20 call sites |
| 11 | `preg_replace($pat, $rep, $str)` | PHP returns null on error; Python `re.sub()` raises `re.error`. Modifier mapping: `/s` → `re.DOTALL`, `/i` → `re.IGNORECASE`, `/u` → default in Python 3, `/e` → **no equivalent (eval mode, dangerous)**. | ~15 call sites |
| 12 | `htmlspecialchars($s, ENT_QUOTES, "UTF-8")` | With `ENT_QUOTES`: escapes `& < > " '`. `markupsafe.escape()` escapes same set. BUT: PHP default (without `ENT_QUOTES`) only escapes `"` not `'` — check which mode is actually used at each call site. | ~12 call sites |
| 13 | `strip_tags($s)` | PHP strips ALL tags. Python: no built-in equivalent; use `lxml.html.clean` or regex. Behavior on malformed HTML (unclosed tags, nested scripts) differs between engines. | ~5 call sites |
| 14 | `str_replace(array(...), array(...), $s)` | PHP array `str_replace` applies replacements sequentially (output of replacement 1 is input to replacement 2 — cascading). Python has no built-in cascade; `re.sub` or explicit loop needed. | ~8 call sites |
| 15 | `sprintf("%d", $x)` | PHP `sprintf("%d", "abc")` → `"0"`. Python `"%d" % "abc"` → TypeError. | ~5 call sites |
| 16 | `explode(",", $s, $limit)` | PHP `explode(",", "a,b,c", 2)` → `["a", "b,c"]` (limit=N means N elements). Python `"a,b,c".split(",", 1)` → `["a", "b,c"]` (maxsplit = N-1). Off-by-one in the limit parameter. | ~10 call sites |

### 2C. Date & Time Traps

| # | PHP Pattern | Python Gotcha | Frequency |
|---|-------------|---------------|-----------|
| 17 | `strtotime($s)` | Parses "2 days ago", "next Monday", "Jan 1, 2025", etc. Python `datetime.fromisoformat()` only handles ISO 8601. Need `dateutil.parser.parse()` for equivalent flexibility. | ~8 call sites |
| 18 | `date("Y/m/d H:i:s", $ts)` | Format codes differ: PHP `i` = minutes, Python `%M` = minutes (NOT `%i`). PHP `G` = 24-hour no padding, Python `%-H`. PHP `D` = short weekday, Python `%a`. Full mapping required per call site. | ~10 call sites |
| 19 | `new DateTimeZone($tz_string)` | PHP throws `Exception` on invalid timezone. Python `pytz.timezone()` or `zoneinfo.ZoneInfo()` raises specific exceptions. Both need try/catch → fallback to UTC. Verify Python has the fallback. | ~3 call sites |
| 20 | `time()` | PHP: integer seconds. Python `time.time()`: float. `int(time.time())` is equivalent but code using `datetime.now()` instead produces a `datetime` object, not epoch int. | ~15 call sites |
| 21 | `mktime()` | PHP: local time components → unix timestamp. Python: `datetime(..., tzinfo=...).timestamp()`. Trap: timezone context must be explicit in Python; PHP uses server default tz. | ~2 call sites |

### 2D. Database & ORM Traps

| # | PHP Pattern | Python Gotcha | Frequency |
|---|-------------|---------------|-----------|
| 22 | `$this->dbh->affected_rows()` | SQLAlchemy `result.rowcount`. Same for DML. But: for `INSERT ... ON CONFLICT DO NOTHING`, rowcount may differ (PHP counts attempted, SQLAlchemy counts actually inserted). | ~8 call sites |
| 23 | `db_escape_string($s)` | SQLAlchemy parameterized queries handle escaping automatically. Trap: any f-string interpolation into raw SQL (`text(f"... {user_input} ...")`) is a SQL injection vulnerability. | ~30 call sites in PHP |
| 24 | `while ($line = db_fetch_assoc($result))` | PHP streams rows one at a time. Python `session.execute(stmt).all()` loads all into memory. For large results (feed update scanning 10K articles), memory pressure differs significantly. | ~40 iteration patterns |
| 25 | `db_num_rows($result)` | PHP: count of result rows (works for SELECT). SQLAlchemy: `len(result.all())` but materializes. For DML use `result.rowcount`. | ~10 call sites |
| 26 | `db_query("BEGIN"); ... db_query("COMMIT")` | PHP: explicit transaction control, supports nesting (inner BEGINs are silently ignored). SQLAlchemy: `session.begin()`/`session.commit()`, nested transactions require explicit SAVEPOINTs. | ~5 explicit transaction sites |
| 27 | Dynamic SQL string concatenation | PHP: `$query .= " AND field = '$var'"`. SQLAlchemy: `stmt = stmt.where(col == var)`. Semantic equivalence depends on whether ALL conditional WHERE fragments are translated — easy to miss one. | ~60 patterns |

### 2E. HTTP, Session & Environment Traps

| # | PHP Pattern | Python Gotcha | Frequency |
|---|-------------|---------------|-----------|
| 28 | `$_REQUEST["key"]` | Merges GET + POST + COOKIE with COOKIE priority (configurable via `request_order`). Flask `request.values` merges GET + POST with GET priority (MultiDict). Different merge order, no cookies. | ~50 call sites |
| 29 | `$_POST["key"]` / `$_GET["key"]` | Flask `request.form["key"]` / `request.args["key"]`. PHP returns null for missing key; Flask raises `KeyError`. Must use `.get()` with default. | ~30 call sites |
| 30 | `$_SESSION["uid"]` and 12+ other keys | Flask-Login `current_user.id` for uid. But PHP session stores `bw_limit`, `ref_schema_version`, `clientTzOffset`, `daemon_stamp_check`, `prefs_filter_search`, etc. — no Flask-Login equivalent for these. | ~40 read sites |
| 31 | `header("Content-Type: application/xml")` | Flask: `make_response(data, 200, {"Content-Type": "..."})` or `response.content_type = "..."`. Must set explicitly; Flask defaults to `text/html`. | ~5 call sites |
| 32 | `die("error")` / `exit()` | PHP `die` stops ALL execution immediately. Python `abort(500)` only stops the request handler; cleanup code still runs, `finally` blocks execute. | ~8 call sites |
| 33 | `@file_get_contents($url)` | PHP `@` suppresses errors (returns false silently). Python must wrap in `try/except` and explicitly suppress. If PHP code checks `=== false` after, Python must check the exception path. | ~5 call sites |
| 34 | `$_SERVER["REMOTE_ADDR"]` / `$_SERVER["HTTP_USER_AGENT"]` | Flask: `request.remote_addr`, `request.user_agent.string`. Also: PHP stores hashed user agent in session (`sha1($_SERVER['HTTP_USER_AGENT'])`); verify Python does the same for session validation. | ~3 call sites |

### 2F. Architecture & Framework Traps

| # | PHP Pattern | Python Gotcha | Frequency |
|---|-------------|---------------|-----------|
| 35 | `Db::get()` singleton | SQLAlchemy session via Flask-SQLAlchemy. Lifetime differs: PHP singleton lives for entire request; Flask-SQLAlchemy session is scoped per request but disposed via `db.session.remove()` at teardown. | Global pattern |
| 36 | `$this->dbh` implicit in class methods | SQLAlchemy `session` passed explicitly as parameter. Every Python function that touches DB needs `session` — if a new caller forgets to pass it, runtime error (not caught at import time). | Global pattern |
| 37 | `PluginHost::getInstance()` | Python `get_plugin_manager()`. PHP singleton is always available. Python may not initialize in all contexts (Celery workers, CLI scripts, test fixtures) — must verify plugin manager availability in every execution context. | ~20 call sites |
| 38 | PHP class autoloading | Python explicit imports. A class referenced in PHP that was never imported in Python gives `NameError` at runtime. PHP autoload is transparent; Python imports fail loudly. | Global pattern |
| 39 | `T_sprintf(...)` | PHP i18n translation. Python needs `gettext` or passthrough. If passthrough, strings aren't translated; if `gettext`, the message catalog must match. | ~15 call sites |
| 40 | `CACHE_DIR . "/images/" . sha1($url) . ".png"` | File system caching paths. Python may use different path structure, or the entire caching layer may be absent (see D34). | ~5 patterns |

---

## 3. Integration Pipeline Contracts

Individual function verification catches ~60% of bugs. The remaining ~40% come from **data flowing through multiple functions with incompatible assumptions at boundaries**.

### Pipeline 1: Feed Update (CRITICAL — 12 steps)

```
fetch URL → parse XML → iterate entries → build GUID → check existence →
compute content hash → apply filters → insert/update entry → create user_entry →
persist enclosures → update counter cache → purge old articles
```

**Cross-function contracts to verify:**

| Boundary | Contract | Risk if broken |
|----------|----------|---------------|
| `update_feed` → `upsert_entry` | GUID format must match DB lookup | ALL dedup breaks (D18) |
| `update_feed` → `sanitize` | Content field must be the right one (content vs summary) | Wrong text sanitized (D17) |
| `apply_filter_actions` → `upsert_user_entry` | Filter action type codes must match | Scores/labels wrong |
| `persist_article` commit → `ccache_update` | Cache recount must see committed data | Stale counters (D37) |
| `update_feed` → DB INSERT | Fields must be truncated to column length | DataError on INSERT (D19) |
| `update_feed` → timestamp storage | Validated timestamps (no future dates) | Sorting broken (D20) |

### Pipeline 2: Article Search (HIGH — 8 steps)

```
parse search query → build qualifiers (d:, note:, star:, pub:, unread:, feed:N, cat:N) →
construct base query → apply view_mode filter → apply feed/category filter →
apply search filter → apply order/limit → return results
```

**Key contracts:**

| Boundary | Contract | Risk |
|----------|----------|------|
| `search_to_sql` → `queryFeedHeadlines` | SQL fragment must be valid SQLAlchemy | Crash on search |
| Virtual feed ID → query | Each of -1, -2, -3, -4, 0 needs different JOIN/WHERE | Wrong articles shown |
| Label ID → `feed_to_label_id` | Off-by-one in conversion → wrong label | Wrong label articles (D14) |
| Filter SQL → test query validation | Invalid regex must not crash production query | Unhandled exception (D09) |

### Pipeline 3: API Request Lifecycle (HIGH — 6 steps)

```
receive JSON → extract op → authenticate via sid → dispatch to handler →
handler executes → wrap response {seq, status, content} → return JSON
```

**Key contracts:**

| Boundary | Contract | Risk |
|----------|----------|------|
| `dispatch` → handler | `sid` validation must match PHP session checks | Unauthenticated access (D23) |
| Handler → `_ok`/`_err` | Error codes must match PHP `API_E_*` constants | Client misinterprets errors (D33) |
| `_handle_getHeadlines` → `queryFeedHeadlines` | Return shape must have expected columns | Formatter reads wrong fields (D29) |
| `_handle_login` → session setup | ALL session variables set on login | Missing state downstream (D23) |

### Pipeline 4: Auth Flow (HIGH — 5 steps)

```
receive credentials → authenticate via plugin hooks → create session →
set session variables (12+ keys) → redirect to index
```

**Key contracts:**

| Boundary | Contract | Risk |
|----------|----------|------|
| `authenticate_user` → `hook_auth_user` | Hook signature must match PHP | Plugin auth breaks (D35) |
| `initialize_user` → pref readers | ALL default prefs must be created | `get_user_pref` returns None (D11) |
| Session setup → app lifecycle | 12+ session keys set on login | Missing state everywhere (D23) |

### Pipeline 5: Counter Cache (MEDIUM — 4 steps)

```
article state change → invalidate cache → recount feed articles → store count
```

**Key contracts:**

| Boundary | Contract | Risk |
|----------|----------|------|
| Catchup/mark → `ccache_update` or `ccache_remove` | Invalidation AFTER UPDATE commits | Stale counts (D37) |
| `_count_feed_articles` → `getFeedArticles` | Same WHERE logic | UI counts diverge |
| Virtual feed counters (-1, -2, -3) | Each uses different counting SQL | Wrong badge numbers |

### Pipeline 6: OPML Import/Export Roundtrip (MEDIUM)

```
Export: query feeds → build category tree → serialize XML → include prefs/filters/labels
Import: parse XML → create categories → subscribe feeds → import prefs/filters/labels
```

**Key contracts:** Filter rules serialized as JSON in XML attributes must survive roundtrip. Category hierarchy recursion depth must match. Label color attribute names (`fg_color`/`bg_color`) must be identical.

### Pipeline 7: Digest Generation (MEDIUM)

```
select eligible users → query fresh articles → format HTML/text → send email → catchup
```

**Key contracts:** Preferred send time comparison must use same timezone. Article query SQL must match PHP (date/score filters). Email MIME structure must be compatible.

### Pipeline 8: Plugin Lifecycle (LOW)

```
discover plugins → load & register → dispatch hooks at call sites
```

**Key contracts:** Load order determines hook priority. EVERY `run_hooks` call site in PHP must have a Python equivalent. Hook argument counts must match.

---

## 4. Model Verification Depth (37 ORM classes)

Beyond "columns match DDL" — full schema equivalence checklist:

### Per-Model Checks

| Category | Checks |
|----------|--------|
| **Columns** | Names, types (`Integer`, `String(N)`, `Text`, `Boolean`, `DateTime`), defaults, NOT NULL, match `ttrss_schema_pgsql.sql` |
| **Primary keys** | Single vs composite, autoincrement/sequence |
| **Unique constraints** | All DDL `UNIQUE` present in ORM |
| **Foreign keys** | Target table + column, `ON DELETE` action (CASCADE/SET NULL/RESTRICT), `ON UPDATE` |
| **Indexes** | All DDL indexes present, column order for composites, partial indexes |
| **Relationships** | Direction (parent→child), `backref`/`back_populates`, lazy loading strategy, cascade config |
| **Computed** | `@hybrid_property` matches PHP derived columns, `server_default` vs Python-side default |
| **Behavioral** | Fernet getter/setter on `Feed.auth_pass`, no validators stricter than PHP, `__repr__` doesn't leak secrets |

### Critical Models (require deeper audit)

| Model | Columns | Why critical |
|-------|---------|-------------|
| `TtRssFeed` | 30+ | Core entity, Fernet `auth_pass`, `favicon_avg_color` |
| `TtRssUserEntry` | 15+ | Most-queried table, `label_cache` JSON, `int_id` autoincrement |
| `TtRssEntry` | 10+ | Content storage, `guid` 245-char constraint, `content_hash` |
| `TtRssFilter2` / `Rule` / `Action` | 3 tables | Complex multi-table filter system with FKs |
| `TtRssUserPref` | 5 | Queried every page, composite PK `(owner_uid, pref_name, profile)` |
| `TtRssPref` | 5 | System defaults, `type_id` FK to `ttrss_prefs_types` |
| `TtRssUser` | 10+ | Auth, `access_level` (0=user, 10=admin), `pwd_hash`, `salt` |

---

## 5. Audit Procedure (MANDATORY)

> **Root cause of 2026-04-06 regression:** The `save_rules_and_actions` indentation bug (rules insertion block outside its for-loop) was missed because the Tier 2 sweep used a summarising agent instead of reading raw source. Summaries hide structural bugs. **The tier system below is a prioritisation guide only — the physical reading requirement applies to ALL tiers.**

### Non-negotiable reading rule

**For every function audited, at every tier:**

1. **Open the PHP file and read the raw source.** Quote at least the key lines (loop heads, SQL, conditionals, return statements) verbatim. Do not paraphrase.
2. **Open the Python file and read the raw source.** Quote the corresponding lines verbatim.
3. **Compare structure, not intent.** Check:
   - Loop body boundaries: count indentation levels. Every statement that belongs inside a `for`/`while` must be indented further than the loop keyword. One wrong dedent = bug.
   - SQL `SELECT` columns, `WHERE` clauses, `JOIN` conditions, `ORDER BY` — column by column.
   - Return value shape — keys, types, nesting.
   - `owner_uid` / access-level guards present on every DB query.
4. **Never accept "logic is equivalent" from a summarising agent.** Require the agent to output the actual line numbers and quoted code from both files before declaring VERIFIED.

### Tier 1: DEEP AUDIT — 52 functions (≥50 lines, complex SQL, security-critical)

Read every PHP line. Compare line-by-line against Python. Check all 40 D-codes.

Key functions: `update_feed`, `queryFeedHeadlines`, `sanitize`, `catchup_feed`, `_handle_getHeadlines`, `_handle_login`, `persist_article`, `dispatch_feed_updates`, `get_feed_tree`, `opml_export_full`, `opml_import_category`, `prepare_headlines_digest`, `make_init_params`, `get_article_filters`.

### Tier 2: STANDARD AUDIT — ~150 functions (20–50 lines, moderate SQL, branching)

Same raw-reading requirement as Tier 1. Additionally check:
- Every `for`/`while` loop: confirm all operations that depend on the loop variable are **inside** the loop body (correct indentation).
- SQL correctness: column list, WHERE conditions, JOIN topology, ORDER BY.
- Return shape: same keys/fields as PHP.
- Session/config access: each PHP `$_SESSION["x"]` and `get_pref()` call has a Python equivalent.
- PHP falsy traps: `empty()`, `isset()`, `(int)$x` at each branch.

### Tier 3: QUICK CHECK — ~270 functions (<20 lines, simple logic)

Read both sides. Verify:
- Return type matches.
- SQL table names and WHERE owner_uid filter present.
- No loop body dedented outside its loop.
- Traceability `# Source:` comment names the PHP function (not just the file).
- No obvious `intval`/`empty` trap.

### Tier 4: MODEL DEEP CHECK — 37 classes

Per-model checklist from Section 4. Read the DDL (`ttrss_schema_pgsql.sql`) and the ORM class side-by-side.

---

## 6. Audit Execution Rules

These rules govern how the audit is run, not just what is checked.

| Rule | Requirement |
|------|-------------|
| **No summary substitution** | An agent that says "logic is equivalent" without quoting line numbers from both files has NOT verified the function. Re-run with explicit line-quote requirement. |
| **Loop body verification** | For every `for`/`while`/`foreach` loop, explicitly state: "Loop starts at line N, body runs lines N+1–M, loop ends at line M+1." If Python indentation puts any operation after M+1, it is outside the loop — file a discrepancy. |
| **SQL column-by-column** | List each column in the PHP SELECT and confirm it is present in the Python query. List each WHERE condition in PHP and confirm Python has it. Missing = discrepancy. |
| **Security guard check** | Every function that touches user data: confirm `owner_uid` filter is in the query, not just checked at call-site. |
| **Quote before VERIFIED** | A function may only be marked VERIFIED after the auditor has written both the PHP excerpt and the Python excerpt into the audit record. |
| **Deployment config out of scope** | Runtime environment issues (wrong port, missing env var, wrong DB URL) are NOT semantic discrepancies. They must be caught by deployment runbooks and smoke tests, not by code comparison. |

---

## Cross-References

| Spec/ADR | Relationship |
|----------|-------------|
| `12-testing-strategy.md` | Testing strategy defines HOW to test; this spec defines WHAT to test for |
| `11-business-rules.md` | Business rules are a subset of the semantics verified here |
| `ADR-0016` | Methodology decision for applying this taxonomy |
| `ADR-0003` | PostgreSQL-only: D07 (SQL dialect) should find no MySQL remnants |
| `ADR-0006` | SQLAlchemy ORM: D22-D27 traps are consequences of this choice |
| `ADR-0007` | Flask-Login: D23-D24-D30 are consequences of session model change |
| `ADR-0008` | Password migration: verify `hash_password`/`verify_password` handle dual-hash |
| `ADR-0014` | feedparser: D17 (content priority), D18 (GUID), D20 (timestamps) are feedparser-specific |
| `ADR-0015` | httpx: D27 (global error state), D28 (feed XML cache) relate to HTTP client change |
