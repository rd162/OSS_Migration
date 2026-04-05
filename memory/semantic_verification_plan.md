---
name: semantic_verification_plan
description: "DEEP semantic PHP→Python verification plan v3 — 40-category discrepancy taxonomy proven against real code samples, 8 integration pipelines, complexity-tiered triage, cross-function contract checks, ALL 472 functions + 37 models"
type: project
---

# Semantic Verification Plan (v3 — Deep)

**Created:** 2026-04-05
**Revised:** 2026-04-05 (v3 — complete rewrite of methodology; v2 had good inventory but
shallow taxonomy and no integration/cross-function verification)
**Trigger:** SME confirmed ALL generated Python code semantically incorrect. v2 plan listed
all 472 functions but its 18-category taxonomy and 15-row traps table missed most real
discrepancy patterns. Concrete sampling of 6 function pairs found 60+ discrepancies in
categories v2 didn't even define.

---

## Why v2 Was Still Inadequate

v2 improved inventory (472 functions listed vs v1's ~100) but the VERIFICATION METHODOLOGY
remained superficial:

| Problem | Evidence |
|---------|----------|
| **D1-D18 taxonomy too narrow** | Sampling 6 functions found 15+ discrepancy categories not covered (content priority inversion, GUID construction, type coercion cascade, SQL computation locus, transactional granularity, DOM model, etc.) |
| **Semantic traps table too small** | 15 rows. PHP codebase has 50+ translation-hostile patterns (dynamic SQL concat, DB_TYPE branching, MiniTemplator, DOMDocument, mb_substr, array_merge key collision, etc.) |
| **No cross-function verification** | Verifying each function in isolation misses: caller passes wrong args to callee, function A writes data function B reads with different assumptions, hook sites pass different args than hook specs |
| **No integration pipeline checks** | Feed update pipeline has 12+ steps; error in step 4 (GUID) invalidates step 7 (dedup). Must verify pipelines end-to-end |
| **No complexity triage** | Treating 5-line `label_to_feed_id` same as 200-line `queryFeedHeadlines` wastes time and misses depth |
| **No behavioral contract verification** | Functions promise return types, side effects, error behavior to callers. These contracts aren't checked |
| **Model verification too shallow** | Just "check columns match DDL" — misses computed properties, validators, relationship loading, cascade semantics |

---

## Codebase Census (unchanged from v2)

| Metric | Count |
|--------|-------|
| Python source files (non-test, non-`__pycache__`) | 91 |
| Files with function/class definitions | 66 |
| Total function definitions (`def`) | 472 |
| Total ORM model classes | 37 |
| **Total verification targets** | **509** |

---

## PART 1: Discrepancy Taxonomy (40 Categories)

Organized by DOMAIN, not alphabetically. Every discrepancy found MUST be classified.

### A. SQL & Query Semantics (D01-D10)

| Code | Name | What to check | Real example from sampling |
|------|------|---------------|---------------------------|
| D01 | **SQL join topology** | PHP uses tables A,B,C in FROM (implicit cross-join) → Python uses explicit JOIN but with different table set | `catchup_feed`: PHP inner query joins `ttrss_entries, ttrss_user_entries, ttrss_user_labels2` (3 tables); Python queries only `TtRssUserLabel2` (1 table) |
| D02 | **SQL computation locus** | PHP computes in DB (`NOW() - INTERVAL '1 day'`); Python computes in app (`datetime.now() - timedelta(1)`) — clock skew risk | `catchup_feed`: date cutoff computed in app vs DB |
| D03 | **SQL column mismatch** | SELECT list, WHERE columns, UPDATE targets differ | `queryFeedHeadlines`: PHP selects `favicon_avg_color`; Python doesn't |
| D04 | **SQL subquery nesting** | PHP uses derived-table pattern `(SELECT ... FROM (SELECT ...) AS tmp)`; Python uses flat `scalar_subquery()` | `catchup_feed`: PHP nested subquery wrapper absent in Python |
| D05 | **SQL WHERE condition** | Missing/extra/wrong WHERE clause | `catchup_feed` tag path: PHP filters `ttrss_user_entries.owner_uid`; Python filters `ttrss_tag.owner_uid` (different table) |
| D06 | **SQL ORDER BY / LIMIT / OFFSET** | Pagination or ordering differs | `queryFeedHeadlines`: PHP VFEED_GROUP_BY_FEED prepends `ttrss_feeds.title` to ORDER BY; Python skips |
| D07 | **SQL dialect remnant** | MySQL-specific syntax surviving or PostgreSQL-specific missing | Feed update daemon: `DB_TYPE` branches for INTERVAL syntax |
| D08 | **SQL transaction boundary** | Different commit granularity | `update_rss_feed`: PHP does `BEGIN`/`COMMIT` per article; Python does single `session.commit()` per feed |
| D09 | **SQL validation** | PHP validates filter/regex SQL via test query before using; Python doesn't | `queryFeedHeadlines`: PHP runs `SELECT true ... WHERE $filter_query_part LIMIT 1` to catch bad regex; Python applies directly |
| D10 | **SQL parameter type** | PHP casts `(int)$_REQUEST["id"]` before interpolation; Python passes raw | Various API handlers: PHP `intval()` vs Python `request.form.get()` |

### B. Type System & Coercion (D11-D16)

| Code | Name | What to check | Real example |
|------|------|---------------|--------------|
| D11 | **Systemic type coercion** | PHP function returns typed value (bool/int); Python returns raw string — affects ALL callers | `get_pref`: PHP `Db_Prefs::convert()` returns native bool/int; Python always returns string. EVERY pref consumer is affected |
| D12 | **PHP falsy divergence** | PHP `empty("0")` is true, `0 == false` is true, `"" == 0` is true; Python differs | Pref bool coercion: `(int) get_pref("BOOL_PREF")` in PHP vs manual string comparison in Python |
| D13 | **Null/empty/isset** | PHP `isset($x) && $x !== ""` vs Python `if x` — different semantics for `0`, `"0"`, `[]` | Session fallback: `if (!$owner_uid) $owner_uid = $_SESSION['uid']` — PHP falsy catches 0; Python `if not 0` also catches 0 |
| D14 | **Numeric boundary** | PHP `$feed < LABEL_BASE_INDEX` (strict less) vs Python `nfeed <= LABEL_BASE_INDEX` (less-or-equal) | `catchup_feed` line 438: boundary condition off by one |
| D15 | **intval/int() divergence** | PHP `intval("abc")` → 0; Python `int("abc")` → ValueError | Any `(int)$_REQUEST["param"]` pattern |
| D16 | **Array/dict semantics** | PHP array is ordered map; `array_merge` renumbers numeric keys; `array_keys` returns ordered list | OPML filter import: nested arrays serialized differently |

### C. Data Flow & Content (D17-D22)

| Code | Name | What to check | Real example |
|------|------|---------------|--------------|
| D17 | **Content priority inversion** | PHP extracts content first, summary fallback; Python does opposite | `update_rss_feed`: PHP `get_content() ?: get_description()`; Python `entry.get("summary") or content[0]` — **reversed** |
| D18 | **GUID construction** | PHP prefixes owner_uid, applies SHA1 hash; Python uses raw feedparser ID | `update_rss_feed`: GUID is `SHA1:` + `owner_uid` + `guid` in PHP; raw `entry["id"]` in Python — breaks dedup model |
| D19 | **Field truncation** | PHP `mb_substr($field, 0, 245)`; Python: no truncation — DB column overflow | `update_rss_feed`: guid, comments, author truncated in PHP |
| D20 | **Timestamp validation** | PHP rejects future dates, falls back to `time()`; Python uses raw timestamp | `update_rss_feed`: future-dated articles not corrected |
| D21 | **Encoding normalization** | PHP `mb_convert_encoding` with 3-level fallback; Python feedparser handles encoding but differently | FeedParser constructor: 3-level charset fallback in PHP |
| D22 | **String interpolation** | PHP `"$var-$var2"` vs Python f-string — watch for missing variables or different concat | Template rendering, error messages |

### D. Session, Config & State (D23-D28)

| Code | Name | What to check | Real example |
|------|------|---------------|--------------|
| D23 | **Session state elimination** | PHP reads `$_SESSION["key"]`; Python requires explicit parameter — caller may forget | `make_init_params`: 13 session/config values present in PHP, absent in Python (`bw_limit`, `csrf_token`, `cookie_lifetime`, etc.) |
| D24 | **Session fallback** | PHP `if (!$x) $x = $_SESSION["uid"]`; Python: no fallback, requires caller to pass | `get_pref`, `catchup_feed`: session uid fallback removed |
| D25 | **Config constant mapping** | PHP `SELF_URL_PATH`, `ICONS_URL`, `SESSION_COOKIE_LIFETIME`, `SINGLE_USER_MODE`, `DB_TYPE`, `DAEMON_UPDATE_LOGIN_LIMIT` | `make_init_params`: `icons_url`, `cookie_lifetime` missing |
| D26 | **Profile-aware queries** | PHP joins `$_SESSION["profile"]` into pref queries; Python may not | `get_pref`: PHP profile_qpart is session-dependent |
| D27 | **Global variable** | PHP `global $fetch_last_error`, `$utc_tz`, `$user_tz`; Python module-level or absent | HTTP client error state, timezone globals |
| D28 | **In-memory cache elimination** | PHP caches data (prefs, feed XML, counter cache); Python hits DB every call | `get_pref`: PHP `Db_Prefs` singleton cache; `update_rss_feed`: 30-sec XML file cache |

### E. Return Value & API Contract (D29-D33)

| Code | Name | What to check | Real example |
|------|------|---------------|--------------|
| D29 | **Return shape divergence** | Different keys, extra/missing fields, different types | `make_init_params`: 13 missing keys; `queryFeedHeadlines`: feed_title/site_url/last_error metadata not returned |
| D30 | **Return materialization** | PHP returns cursor/resource (lazy); Python returns materialized list (eager) | `queryFeedHeadlines`: PHP db_query() cursor vs Python `list(session.execute().all())` |
| D31 | **Error envelope** | PHP returns specific error array on failure; Python raises exception or returns None | `get_pref`: PHP `user_error(E_USER_ERROR)` (fatal) vs Python returns None |
| D32 | **HTTP response headers** | PHP `header("Content-Type: ...")` set explicitly; Python response headers may differ | OPML export, RSS feed, image proxy |
| D33 | **JSON response structure** | API error/ok wrappers, seq echoing, field naming | API dispatch: `{"seq": $seq, "status": 0/1, "content": {...}}` |

### F. Feature & Behavior (D34-D40)

| Code | Name | What to check | Real example |
|------|------|---------------|--------------|
| D34 | **Feature absent** | Entire sub-feature not implemented | PubSubHubbub, Sphinx search, favicon refresh, image cache, language detect, bw_limit, highlight_words |
| D35 | **Hook argument mismatch** | PHP `run_hooks(HOOK_X, $a, $b, $c, $d, $e)` passes N args; Python hook passes N-1 | `sanitize`: PHP passes 5 args to `hook_sanitize`; Python passes 4 (omits `article_id`) |
| D36 | **Hook call site missing** | PHP calls `run_hooks(HOOK_X)` at a point; Python omits | Various: cache invalidation hooks, feed update hooks |
| D37 | **Side effect order** | PHP invalidates cache AFTER write; Python does BEFORE (or vice versa) | Counter cache updates relative to article inserts |
| D38 | **Error recovery model** | PHP returns error + continues; Python raises + retries (Celery) | `update_rss_feed`: PHP writes `last_error`, returns; Python raises for Celery retry |
| D39 | **DOM/parsing model** | PHP `DOMDocument` full doc vs Python `lxml.html.fragment_fromstring` in div wrapper | `sanitize`: output wrapped in `<div>` in Python, in `<html><body>` in PHP |
| D40 | **Transactional semantics** | PHP per-row commit allows partial success; Python all-or-nothing | `update_rss_feed`: some articles saved on PHP error; Python loses all on error |

---

## PART 2: PHP→Python Semantic Traps (Comprehensive)

These patterns cause discrepancies — check EVERY function.

### 2A. Type & Comparison Traps

| # | PHP Pattern | Python Gotcha | Frequency |
|---|-------------|---------------|-----------|
| 1 | `empty($x)` | PHP: `empty("0")` → true, `empty([])` → true, `empty(0)` → true. Python: `not "0"` → False, `not []` → True, `not 0` → True. **"0" is the killer.** | ~50 uses |
| 2 | `(int)$x` / `intval($x)` | PHP: `intval("abc")` → 0, `intval("3abc")` → 3. Python: `int("abc")` → ValueError, `int("3abc")` → ValueError. Must use `int(x) if x.isdigit() else 0` or regex. | ~30 uses |
| 3 | `isset($x)` | Checks key exists AND not null. Python `x is not None` doesn't check existence; `"key" in dict and dict["key"] is not None` is equivalent. | ~40 uses |
| 4 | `$x == false` (loose) | PHP: `0 == false` → true, `"" == false` → true, `"0" == false` → true, `null == false` → true. Python: `0 == False` → True, `"" == False` → False. | ~20 uses |
| 5 | `$x === false` (strict) | PHP strict equals has no Python equivalent issue BUT: `strpos()` returning 0 vs false requires `!== false` check; Python `str.find()` returning 0 vs -1 is different | ~15 uses |
| 6 | `$a ?? $b` (null coalescing) | Only null-checks, not falsy. `$x ?? "default"` returns `"0"`, `""`, `0`. Python `x or "default"` returns "default" for all of these. Must use `x if x is not None else "default"`. | ~25 uses |
| 7 | `(bool)$x` / `!!$x` | PHP: `(bool)"0"` → false, `(bool)0` → false, `(bool)""` → false. Python: `bool("0")` → True. | ~10 uses |
| 8 | `array_key_exists($k,$a)` vs `isset($a[$k])` | `array_key_exists` returns true even if value is null; `isset` returns false for null. Python `k in d` is like `array_key_exists`. | ~10 uses |

### 2B. String & Regex Traps

| # | PHP Pattern | Python Gotcha | Frequency |
|---|-------------|---------------|-----------|
| 9 | `mb_substr($s, 0, 245)` | Python `s[:245]` counts characters (correct for UTF-8 str). But PHP `mb_substr` with `mb_internal_encoding("UTF-8")` also counts characters. The trap: if encoding isn't set, PHP counts bytes. Python is always character-based. | ~8 uses |
| 10 | `preg_match($pat, $str, $matches)` | Returns 0/1 (int). Python `re.search()` returns None/Match. Both falsy on no-match, but PHP captures are in `$matches[1]`; Python in `m.group(1)`. Trap: PHP returns 0 on error too (with `preg_last_error()`); Python raises `re.error`. | ~20 uses |
| 11 | `preg_replace($pat, $rep, $str)` | PHP: returns null on error. Python `re.sub()`: raises `re.error`. PHP regex modifiers: `/s` = `re.DOTALL`, `/i` = `re.IGNORECASE`, `/u` = default in Python 3, `/e` = **dangerous, no equivalent**. | ~15 uses |
| 12 | `htmlspecialchars($s, ENT_QUOTES, "UTF-8")` | PHP escapes `& < > " '`. `markupsafe.escape()` escapes `& < > " '` — same set. BUT `htmlspecialchars` default (no `ENT_QUOTES`) only escapes `"` not `'`. Check which mode is used. | ~12 uses |
| 13 | `strip_tags($s)` | PHP strips ALL tags. Python equivalent: `lxml.html.clean.Cleaner` or regex. Behavior on malformed HTML differs. | ~5 uses |
| 14 | `str_replace(array(...), array(...), $s)` | PHP array str_replace applies replacements left-to-right with cascading. Python: no built-in cascade; `re.sub` or loop. | ~8 uses |
| 15 | `sprintf("%d", $x)` | PHP: `sprintf("%d", "abc")` → 0. Python: `"%d" % "abc"` → TypeError. | ~5 uses |
| 16 | `explode(",", $s)` | PHP: `explode(",", "")` → `[""]` (1-element). Python: `"".split(",")` → `[""]` (same). But `explode(",", ",")` → `["", ""]`; `",".split(",")` → `["", ""]` (same). Trap: `explode(",", $s, 2)` limit param works differently from `$s.split(",", 1)` (Python maxsplit). | ~10 uses |

### 2C. Date & Time Traps

| # | PHP Pattern | Python Gotcha | Frequency |
|---|-------------|---------------|-----------|
| 17 | `strtotime($s)` | Parses "2 days ago", "next Monday", "Jan 1, 2025", relative dates, etc. Python `datetime.fromisoformat()` only handles ISO 8601. Need `dateutil.parser.parse()` for equivalent flexibility. | ~8 uses |
| 18 | `date("Y/m/d H:i:s", $ts)` | PHP format chars differ from Python strftime: `Y` = `%Y`, `m` = `%m`, `d` = `%d`, `H` = `%H`, `i` = `%M` (not `%i`!), `s` = `%S`, `G` = `%-H`, `D` = `%a`. | ~10 uses |
| 19 | `new DateTimeZone($tz)` | PHP: throws `Exception` on invalid tz. Python `pytz.timezone()`: raises `UnknownTimeZoneError`. Both need try/catch. But PHP code catches and falls back to UTC; verify Python does too. | ~3 uses |
| 20 | `$ts = time()` | PHP: integer seconds since epoch. Python `time.time()`: float. `int(time.time())` is equivalent but often Python code uses `datetime.now()` instead, which is a different type. | ~15 uses |
| 21 | `mktime()` | PHP: local time to timestamp. Python: `datetime(...).timestamp()`. Trap: timezone context differs if not explicit. | ~2 uses |

### 2D. Database & ORM Traps

| # | PHP Pattern | Python Gotcha | Frequency |
|---|-------------|---------------|-----------|
| 22 | `$this->dbh->affected_rows()` | SQLAlchemy `result.rowcount`. Same concept but: for SELECT, PHP returns -1; SQLAlchemy raises for non-DML. For INSERT with ON CONFLICT DO NOTHING, rowcount may differ. | ~8 uses |
| 23 | `db_escape_string($s)` | SQLAlchemy parameterized queries handle escaping. But watch for f-string interpolation in query text (SQL injection risk if any slip through). | ~30 uses |
| 24 | `$result = db_query($q); while ($line = db_fetch_assoc($result))` | PHP: streaming row-by-row. Python: `session.execute(stmt).all()` loads all. For large result sets (10k+ articles), memory behavior differs. | ~40 uses |
| 25 | `db_num_rows($result)` | PHP: count of result rows. SQLAlchemy: `len(result.all())` but `.all()` materializes. Use `result.rowcount` only for DML. | ~10 uses |
| 26 | `db_query("BEGIN"); ... db_query("COMMIT")` | PHP: explicit transaction control. SQLAlchemy: `session.begin()`/`session.commit()` or context manager. Trap: nested BEGINs in PHP (they work); SQLAlchemy doesn't nest without SAVEPOINTs. | ~5 uses |
| 27 | Dynamic SQL string concat | PHP: `$query .= " AND field = '$var'"`. SQLAlchemy: `stmt = stmt.where(col == var)`. Semantic equivalence depends on whether ALL conditions are translated. | ~60 uses |

### 2E. HTTP, Session & Environment Traps

| # | PHP Pattern | Python Gotcha | Frequency |
|---|-------------|---------------|-----------|
| 28 | `$_REQUEST["key"]` | Merges GET+POST+COOKIE with COOKIE priority. Flask `request.values` merges GET+POST with GET priority. Different merge order + no cookies. | ~50 uses |
| 29 | `$_POST["key"]` / `$_GET["key"]` | Flask: `request.form["key"]` / `request.args["key"]`. Trap: PHP returns null for missing key; Flask raises `KeyError`. Must use `.get()`. | ~30 uses |
| 30 | `$_SESSION["uid"]` reads | Flask-Login: `current_user.id`. Different API, but also: PHP session has custom keys (`bw_limit`, `ref_schema_version`, `clientTzOffset`, etc.) that have no Flask-Login equivalent. | ~40 uses |
| 31 | `header("Content-Type: application/xml")` | Flask: `response.content_type = "application/xml"` or `make_response(..., 200, {"Content-Type": ...})`. | ~5 uses |
| 32 | `die("error")` / `exit()` | Python: `abort(500)` or `return jsonify(error=...), 500`. Trap: PHP `die` stops ALL execution; Python abort only stops the request handler. | ~8 uses |
| 33 | `@file_get_contents($url)` | PHP `@` suppresses errors. Python: must wrap in try/except. If the PHP code uses the error suppression to silently skip, Python must replicate that silence. | ~5 uses |
| 34 | `$_SERVER["REMOTE_ADDR"]` / `$_SERVER["HTTP_USER_AGENT"]` | Flask: `request.remote_addr`, `request.user_agent.string`. | ~3 uses |

### 2F. Architecture & Framework Traps

| # | PHP Pattern | Python Gotcha | Frequency |
|---|-------------|---------------|-----------|
| 35 | PHP singleton `Db::get()` | SQLAlchemy session via Flask-SQLAlchemy. Lifetime differs: PHP singleton lives for request; Flask session is scoped per request but disposed differently. | Global |
| 36 | PHP `$this->dbh` in class methods | SQLAlchemy `session` passed as parameter. Trap: PHP methods access DB implicitly; Python must receive session explicitly. If a new caller forgets to pass session, runtime error. | Global |
| 37 | `PluginHost::getInstance()` | Python: `get_plugin_manager()`. Trap: PHP is truly global singleton; Python may not initialize in all contexts (Celery workers, CLI scripts). | ~20 uses |
| 38 | PHP auto-loading classes | Python explicit imports. Trap: a class referenced in PHP that was never imported in Python gives `NameError` at runtime, not at parse time. | Global |
| 39 | `T_sprintf(...)` | i18n translation function. Python: needs `gettext` or passthrough. If passthrough, the string isn't translated. | ~15 uses |
| 40 | `CACHE_DIR . "/images/" . sha1($url) . ".png"` | Python file caching may use different path structure or not exist at all. | ~5 uses |

---

## PART 3: Integration Pipeline Verification

Individual function verification catches ~60% of bugs. The other ~40% come from
**data flowing through multiple functions with incompatible assumptions**.

### Pipeline 1: Feed Update (CRITICAL — 12 steps)

```
fetch URL → parse XML → iterate entries → build GUID → check existence →
compute content hash → apply filters → insert/update entry → create user_entry →
persist enclosures → update counter cache → purge old articles
```

**Cross-function contracts to verify:**
- `update_feed` builds GUID → `upsert_entry` uses GUID to check existence
  - If GUID construction differs from PHP, ALL dedup breaks
- `update_feed` extracts content → `sanitize` processes content
  - Content priority (summary vs full) affects what gets sanitized
- `apply_filter_actions` scores articles → `upsert_user_entry` stores score
  - If filter action types don't match, scores are wrong
- `persist_article` commits → `ccache_update` reads committed data
  - If transaction boundary is wrong, cache reads uncommitted data
- `update_feed` truncates fields to 245 chars → DB column constraints
  - If Python doesn't truncate, DB rejects insert

**Verification method:** Trace a sample feed entry through ALL 12 steps in both PHP and
Python. At each step boundary, verify the data shape matches.

### Pipeline 2: Article Search (HIGH — 8 steps)

```
parse search query → build qualifiers (d:, note:, star:, pub:, unread:, feed:, cat:) →
construct base query → apply view_mode filter → apply feed/category filter →
apply search filter → apply order/limit → return results
```

**Cross-function contracts:**
- `search_to_sql` returns SQL fragment → `queryFeedHeadlines` embeds it
  - Fragment must be valid SQLAlchemy, not raw SQL string
- Virtual feed IDs (-1=starred, -2=published, -3=fresh, -4=all, 0=archived)
  - Each needs different JOIN/WHERE logic; verify all 5 virtual feed paths
- Label feed IDs (< LABEL_BASE_INDEX) need `feed_to_label_id` conversion
  - Off-by-one in conversion breaks label article display

### Pipeline 3: API Request Lifecycle (HIGH — 6 steps)

```
receive JSON → extract op → dispatch to handler → execute handler →
wrap response {seq, status, content} → return JSON
```

**Cross-function contracts:**
- `dispatch` validates `sid` against session → handler assumes authenticated
  - If validation differs, handlers run unauthenticated
- Handler calls `_ok(result)` / `_err(code, msg)` → client expects exact envelope
  - Verify ALL error codes match PHP `API_E_*` constants
- `_handle_getHeadlines` calls `queryFeedHeadlines` → formats output
  - If queryFeedHeadlines return shape changed, getHeadlines formats wrong fields

### Pipeline 4: Auth Flow (HIGH — 5 steps)

```
receive credentials → authenticate via plugin hooks → create session →
set session variables → redirect to index
```

**Cross-function contracts:**
- `authenticate_user` calls plugin `hook_auth_user` → expects user_id return
  - Hook spec signature must match PHP `HOOK_AUTH_USER` call site
- `initialize_user` creates default prefs → all pref readers assume they exist
  - If any pref is missing, `get_user_pref` returns None vs PHP returning default
- Session variables set on login → read throughout app lifecycle
  - 12+ session keys in PHP; verify all are set equivalently in Python

### Pipeline 5: Counter Cache Update (MEDIUM — 4 steps)

```
article state change (mark read/unread/star) → invalidate cache →
recount feed articles → store new count
```

**Cross-function contracts:**
- `catchup_feed` marks articles read → must call `ccache_update` or `ccache_remove`
  - Verify cache invalidation happens AFTER the UPDATE commits
- `_count_feed_articles` counts with specific WHERE → `getFeedArticles` uses same logic
  - If WHERE clauses diverge, UI shows stale counts
- Virtual feed counters (starred, published, fresh) use different counting logic
  - Each virtual feed ID path must be verified separately

### Pipeline 6: OPML Import/Export Roundtrip (MEDIUM — 6 steps)

```
export: query feeds → build category tree → serialize to XML → include prefs/filters/labels
import: parse XML → create categories → subscribe feeds → import prefs/filters/labels
```

**Cross-function contracts:**
- Export serializes filter rules as JSON in XML attributes → import parses them
  - JSON structure must be identical or import silently loses filter rules
- Category hierarchy (parent→child→feed) must survive roundtrip
  - `opml_import_category` is recursive; verify recursion depth matches PHP
- Label colors serialized as `fg_color`/`bg_color` attributes → import reads them
  - Verify attribute names match exactly

### Pipeline 7: Digest Generation (MEDIUM — 4 steps)

```
select eligible users → query fresh articles → format HTML/text →
send email → mark articles as digested
```

**Cross-function contracts:**
- `send_headlines_digests` checks preferred send time → 2-hour window
  - Time comparison must use same timezone context
- `prepare_headlines_digest` queries articles → uses date/score filters
  - SQL must match PHP exactly or users get wrong digest content
- Email sending uses `ttrssMailer` in PHP → Python `smtplib`
  - Headers, MIME structure, encoding must be compatible

### Pipeline 8: Plugin Lifecycle (LOW — 3 steps)

```
discover plugins → load & register → dispatch hooks at call sites
```

**Cross-function contracts:**
- `init_plugins` loads system plugins → `load_user_plugins` adds user plugins
  - Load order determines hook priority; verify order matches PHP
- `register_plugin` adds to `self._plugins` → `get_hooks` returns registered hooks
  - Hook registration API must accept same arguments
- Hook call sites pass N arguments → hook spec expects N arguments
  - Verify EVERY `run_hooks` call site in PHP maps to correct Python hookspec

---

## PART 4: Complexity-Tiered Triage

Not all functions need equal depth. Classify every function before verifying.

### Tier 1: DEEP AUDIT (read every PHP line, compare line-by-line)

**Criteria:** >50 lines, complex SQL, multiple branches, session/config access, security

**Functions (52 total — do these FIRST):**

| WS | Function | Lines | Why Tier 1 |
|----|----------|-------|-----------|
| 02 | `_handle_getHeadlines` | 128 | Most complex API; virtual feeds, view modes, search, sanitize |
| 02 | `_handle_getArticle` | 102 | Article formatting, enclosures, hooks |
| 02 | `_handle_updateArticle` | 111 | 3 field modes, label toggle, publish toggle |
| 02 | `_handle_getFeeds` | 114 | Category recursion, unread counts, virtual feeds |
| 02 | `_handle_getCategories` | 80 | Nested category counting |
| 02 | `_handle_login` | 89 | Auth, session setup, API-level password decode |
| 02 | `_handle_getFeedTree` | 187 | 4 nested helper functions, full tree construction |
| 02 | `dispatch` | 114 | Request validation, CSRF, session, op routing |
| 03 | `_rpc_archive` | 72 | Archived feed creation with all columns |
| 03 | `_rpc_mass_subscribe` | 78 | JSON parse, category creation, bulk subscribe |
| 03 | `_rpc_sanity_check` | 24 | Schema version, daemon status checks |
| 03 | `dispatch` (backend) | 43 | Method routing + CSRF |
| 04 | `register` | 64 | Validation, email, rate limiting, user creation |
| 04 | `pubsub` | 45 | HMAC verification, hub callback |
| 04 | `rss` | 57 | Access key auth, article query, XML generation |
| 04 | `forgotpass` | 71 | Password reset flow |
| 05 | `edit_feed` | 43 | Feed data load with all metadata |
| 05 | `save_feed` | 31 | Multi-field validation and save |
| 05 | `batch_edit_feeds` | 20 | Selective field update |
| 05 | `test_filter` | 33 | Filter regex evaluation |
| 06 | `update_feed` | 227 | THE most complex function; see Pipeline 1 |
| 06 | `dispatch_feed_updates` | 173 | Daemon scheduling logic |
| 06 | `upsert_entry` | 75 | INSERT ON CONFLICT with all fields |
| 06 | `persist_article` | 136 | Full persist pipeline |
| 06 | `apply_filter_actions` | 73 | Score, label, mark, publish, tag |
| 07 | `format_article` | 122 | Article display with all metadata |
| 07 | `catchup_feed` | 162 | Complex multi-path catchup (see sampling) |
| 08 | `load_filters` | 123 | Filter query with rules + actions |
| 08 | `get_article_filters` | 86 | Multi-rule matching with regex |
| 09 | `queryFeedHeadlines` | 351 | Complex query building (see sampling) |
| 09 | `search_to_sql` | 102 | Search qualifier parsing |
| 10 | `sanitize` | 149 | HTML sanitization (see sampling) |
| 12 | `subscribe_to_feed` | 61 | URL validation, category, duplicate check |
| 14 | `getFeedCounters` | 72 | Feed counter query with complex WHERE |
| 14 | `getFeedArticles` | 117 | Core counting function (virtual feeds, labels) |
| 14 | `getLabelCounters` | 42 | Label counter with LABEL_BASE_INDEX math |
| 15 | `ccache_update` | 94 | Cache write with counting logic |
| 15 | `_count_feed_articles` | 116 | Complex counting (label, virtual, real feeds) |
| 16 | `opml_export_full` | 166 | Full OPML generation |
| 16 | `opml_import_category` | 104 | Recursive import |
| 16 | `opml_import_filter` | 104 | Complex JSON-in-XML filter import |
| 17 | `get_feed_tree` | 159 | Tree construction with 5 helpers |
| 17 | `save_feed_settings` | 50 | Multi-field update with validation |
| 17 | `batch_edit_feeds` | 64 | Selective batch update |
| 17 | `save_feed_order` | 65 | Order persistence with category nesting |
| 17 | `remove_feed` | 86 | Cascading delete (articles, labels, cache, filters) |
| 17 | `rescore_feed_impl` | 50 | Rescore with filter application |
| 18 | `save_rules_and_actions` | 86 | Complex JSON→DB persistence |
| 21 | `PluginHost.__init__` | 14 | Plugin system bootstrap |
| 22 | `prepare_headlines_digest` | 163 | Digest article query + template |
| 22 | `send_headlines_digests` | 141 | User selection, time check, send |
| 24 | `make_init_params` | 49 | Frontend bootstrap (see sampling) |

### Tier 2: STANDARD AUDIT (read both sides, check D-codes, verify SQL)

**Criteria:** 20-50 lines, moderate SQL, some branching

**~150 functions** — the bulk of workstreams WS-05, WS-07, WS-11, WS-12, WS-13, WS-14,
WS-17-20, WS-22-24

### Tier 3: QUICK CHECK (verify return type, SQL table/columns, traceability comment)

**Criteria:** <20 lines, simple logic, helper/utility

**~270 functions** — helpers, type converters, simple getters, wrappers

### Tier 4: MODEL DEEP CHECK (schema-level, 37 models)

See Part 5.

---

## PART 5: Model Verification Depth (37 classes)

Go BEYOND "columns match DDL":

### Per-Model Checklist

```
Schema Correctness:
□ Column names match `ttrss_schema_pgsql.sql` exactly
□ Column types (Integer, String(N), Text, Boolean, DateTime) match DDL
□ Default values match DDL (watch: server_default vs Python default)
□ NOT NULL constraints match DDL
□ Primary key (single vs composite) matches DDL
□ Unique constraints match DDL
□ Check constraints match DDL (if any)

Foreign Keys:
□ FK target table and column correct
□ ON DELETE action (CASCADE, SET NULL, RESTRICT) matches DDL
□ ON UPDATE action matches DDL
□ No orphan FKs (FK in Python with no DDL equivalent)
□ No missing FKs (FK in DDL not in Python)

Indexes:
□ All DDL indexes present in Python (unique, composite, partial)
□ No phantom indexes (Python has index DDL doesn't)
□ Index column order matches DDL for composite indexes

Relationships:
□ Relationship direction correct (parent→child, not reverse)
□ backref/back_populates names make sense
□ Lazy loading strategy appropriate (lazy, eager, subquery, selectin)
□ Cascade behavior on relationship matches FK ON DELETE
□ No circular relationship issues causing import errors

Behavioral:
□ Computed properties (@hybrid_property) match PHP derived columns
□ Model __repr__/__str__ doesn't leak sensitive data
□ Feed.auth_pass getter/setter uses Fernet correctly (ADR-0009)
□ No validators that are stricter/looser than PHP equivalents
□ server_default vs Python-side default: which fires on INSERT?
□ Sequence/autoincrement behavior matches PHP table definitions
```

### Critical Models (deeper audit)

| Model | Why critical | Extra checks |
|-------|-------------|-------------|
| `TtRssFeed` | Core entity; 30+ columns; has Fernet auth_pass | Verify all 30 columns, Fernet round-trip, `favicon_avg_color` handling |
| `TtRssUserEntry` | Most-queried table; has `label_cache` JSON | Verify `label_cache` JSON structure, `int_id` autoincrement, composite FK |
| `TtRssEntry` | Content storage; GUID uniqueness | Verify `guid` length constraint (245 chars), `content_hash` column exists |
| `TtRssFilter2`/`Rule`/`Action` | Complex 3-table filter system | Verify rule→filter FK, action→filter FK, `filter_type` FK, `action_id` FK |
| `TtRssUserPref` | Queried by every page; profile-aware | Verify composite PK `(owner_uid, pref_name, profile)`, profile nullable |
| `TtRssPref` | System defaults; joined by get_pref | Verify `type_id` FK to `ttrss_prefs_types`, `def_value` column |
| `TtRssUser` | Auth, session, admin | Verify `access_level` (0=user, 5=?, 10=admin), `pwd_hash` column, `salt` |
| `TtRssCountersCache` | Counter cache reads/writes | Verify `(owner_uid, feed_id)` is unique, `updated` column |

---

## PART 6: Verification Methodology (Per Function)

### Step 1 — Classify complexity tier (Tier 1/2/3)

### Step 2 — Read PHP source
Open the exact PHP function body at the lines cited in the `Source:` comment.
If no Source comment exists, flag as D34 and find the PHP origin.

### Step 3 — Read Python implementation

### Step 4 — Systematic comparison (depth depends on tier)

**Tier 1 (DEEP) — ALL of these:**
```
INPUT HANDLING:
□ Every parameter: type, default, nullable matches PHP
□ Input validation: (int), isset, !empty, strlen checks present
□ $_REQUEST/$_POST/$_GET → request.form/request.args/request.values correct
□ Session reads: every $_SESSION["key"] has Python equivalent

AUTHENTICATION & AUTHORIZATION:
□ owner_uid / $_SESSION["uid"] enforced on every DB query
□ Admin check (access_level >= 10) present where PHP has it
□ CSRF validation present where PHP has it

EVERY DB QUERY (for each query in the function):
□ Correct table(s) in FROM/JOIN
□ Correct JOIN type (INNER/LEFT/CROSS) and ON clause
□ Correct columns in SELECT list
□ ALL WHERE conditions present (count them!)
□ Correct ORDER BY (columns AND direction)
□ Correct LIMIT / OFFSET
□ Correct GROUP BY / HAVING
□ Correct UPDATE SET targets and values
□ Correct INSERT columns and values
□ Correct DELETE target and WHERE
□ Subquery nesting matches PHP pattern
□ Computation happens in same locus (DB vs app)

EVERY BRANCH (for each if/elseif/else/switch/case):
□ Condition semantics match (watch PHP falsy rules!)
□ Both true-branch and false-branch present
□ Else/default case present
□ Nested condition order matches

EVERY LOOP:
□ Loop variable and iteration target match
□ Break/continue conditions match
□ Empty-collection behavior matches (PHP foreach on empty = no-op)

HOOKS:
□ Every run_hooks() call in PHP has Python equivalent
□ Hook arguments (count and types) match
□ Hook called at same point in execution flow

SIDE EFFECTS (in order):
□ DB writes happen in same order relative to reads
□ Cache invalidation happens AFTER writes commit
□ Counter updates happen after article state changes
□ Error logging happens at same points

RETURN VALUE:
□ Return type matches (dict, list, int, None, etc.)
□ All dict keys present with correct types
□ Error return shape matches (error envelope)
□ HTTP status code matches

ERROR HANDLING:
□ What does PHP return/throw on each failure path?
□ Python replicates same failure behavior
□ @-suppressed errors → try/except in Python

NULL/EMPTY EDGE CASES:
□ What happens when input is null/empty/0/"0"/[]/false?
□ Check each PHP falsy-sensitive comparison
□ Check null coalescing (??) translations

CONFIG/CONSTANT:
□ All PHP constants (SELF_URL_PATH, ICONS_URL, etc.) mapped
□ All PHP defines checked
□ SINGLE_USER_MODE paths handled
```

**Tier 2 (STANDARD):**
```
□ All items above EXCEPT: loop-by-loop, branch-by-branch enumeration
□ Focus on: SQL correctness, return shape, session/config, critical branches
□ Spot-check 2-3 branches for PHP falsy issues
```

**Tier 3 (QUICK):**
```
□ Return type matches
□ SQL table(s) and column(s) correct
□ Traceability comment accurate
□ No obvious PHP falsy / intval trap
```

### Step 5 — Document discrepancies (D01-D40 codes)

### Step 6 — Rewrite Python to match PHP semantics exactly

### Step 7 — Run `pytest` after each function fix

---

## PART 7: Workstream Inventory

**Unchanged from v2.** All 26 workstreams (WS-01 through WS-26) with their complete
function inventories are preserved. The workstream definitions, PHP source mappings,
function tables, and known risk areas from v2 remain valid and are incorporated by
reference.

**Workstream summary (509 targets):**

| WS | Module | Functions | Priority |
|----|--------|-----------|----------|
| 01 | Auth & Session | 12 | P0 |
| 02 | API Dispatch | 29 | P0 |
| 03 | Backend / RPC | 48 | P0 |
| 04 | Public Endpoints | 14 | P0 |
| 05 | Prefs Blueprint Routes | 64 | P1 |
| 06 | Feed Update Engine | 13 | P0 |
| 07 | Article Operations | 12 | P1 |
| 08 | Article Filters | 7 | P1 |
| 09 | Article Search | 5 | P1 |
| 10 | Article Sanitize | 2 (34 refs) | P1 |
| 11 | Labels Core | 10 | P1 |
| 12 | Feed Operations | 10 | P1 |
| 13 | Feed Browser & Categories | 11 | P1 |
| 14 | Feed Counters | 11 | P1 |
| 15 | Counter Cache | 9 | P1 |
| 16 | Feed OPML | 13 | P2 |
| 17 | Prefs CRUD — Feeds | 32 | P2 |
| 18 | Prefs CRUD — Filters | 17 | P2 |
| 19 | Prefs CRUD — Labels/Ops | 15 | P2 |
| 20 | Prefs CRUD — Users | 16 | P2 |
| 21 | Plugin System | 64 defs | P2 |
| 22 | Background Tasks | 12 | P2 |
| 23 | HTTP Client & Crypto | 7 | P2 |
| 24 | UI Init & Utils | 26 | P2 |
| 25 | ORM Models | 37 classes | P2 |
| 26 | App Bootstrap | 15 defs | P3 |

---

## Execution Order

```
Phase A — Tier 1 DEEP AUDIT (52 functions):
  Start with Pipeline 1 (Feed Update) functions: WS-06 update_feed, persist_article,
  upsert_entry, apply_filter_actions, dispatch_feed_updates
  Then Pipeline 2 (Search): WS-09 queryFeedHeadlines, search_to_sql
  Then Pipeline 3 (API): WS-02 dispatch, _handle_getHeadlines, _handle_login
  Then remaining Tier 1 functions by priority

Phase B — Integration Pipeline Checks (8 pipelines):
  Trace data through each pipeline end-to-end after Tier 1 functions are fixed

Phase C — Tier 2 STANDARD AUDIT (~150 functions):
  By workstream priority (P0→P1→P2→P3)

Phase D — Tier 3 QUICK CHECK (~270 functions):
  Batch by workstream, verify in bulk

Phase E — Model DEEP CHECK (37 models):
  Compare each model against ttrss_schema_pgsql.sql

Phase F — Cross-workstream sweep:
  Verify all callers of get_user_pref handle raw string return (D11)
  Verify all session reads have explicit parameter passing (D23/D24)
  Verify all GUID users share same construction logic (D18)
  Verify all counter cache invalidation sites are correct (D37)
  Full regression: pytest must pass
```

---

## Fix Protocol

For each function:

1. **Read PHP source first** — exact lines from Source: comment
2. **Read Python current** — full function
3. **List ALL discrepancies** using D01-D40 taxonomy
4. **Rewrite Python** to match PHP semantics exactly:
   - Same SQL logic (translated to SQLAlchemy)
   - Same branch conditions (watch PHP truthiness rules!)
   - Same return value structure
   - Same error cases
   - Same side effects in same order
5. **Preserve Python idioms** only where semantically equivalent
6. **Update traceability comment** to cite exact PHP lines verified
7. **Run tests** after every function (`pytest` — baseline must pass)

---

## Discrepancy Tracking

Track in `docs/semantic_verification_report.md`:

```markdown
## WS-NN: Module Name

### func_name() [Python file:line / PHP file:lines]  [Tier: 1/2/3]
Status: [ ] Pending  [x] Verified OK  [!] Fixed

Discrepancies found:
- D01: SQL join topology: PHP joins ttrss_entries,ttrss_user_entries,ttrss_user_labels2;
       Python only queries TtRssUserLabel2 (catchup_feed label path)
- D17: Content priority inversion: PHP get_content() first, summary fallback;
       Python summary first, content fallback
- D18: GUID missing owner_uid prefix and SHA1 hash

Fix applied: commit XXXXXXX
```

---

## Success Criteria

A function is **verified** when:
1. All D01-D40 codes checked at appropriate tier depth — none found OR all found ones fixed
2. The Source: comment cites exact PHP lines verified
3. `pytest` passes all baseline tests

A pipeline is **verified** when:
1. Data traced through all steps in both PHP and Python
2. Data shape at each step boundary matches
3. End-to-end output matches for representative test cases

The codebase is **complete** when:
- All 52 Tier 1 functions deep-audited
- All 8 integration pipelines verified
- All ~150 Tier 2 functions standard-audited
- All ~270 Tier 3 functions quick-checked
- All 37 models deep-checked against DDL
- Cross-workstream sweep done (get_pref callers, session reads, GUID, cache)
- Zero unfixed discrepancies
- SME second pass confirms correctness
