# Dimension: call-graph + class-hierarchy + include-graph + hook-graph · Community: GRP-02 — Feed engine + parsing + update daemon

⚠ RESEARCH MODE: DEGRADED — web search unavailable; training-knowledge-only.
All findings from source corpus reads + training knowledge. No T1 URL citations.

---

## Members

### Primary files
- `include/rssfuncs.php` (level 1, ~1431 LOC) — feed fetch + update orchestration
- `classes/feeds.php` (level 1, ~1163 LOC) — headline rendering + feed-view handler
- `classes/feedparser.php` (level 0, ~530 LOC) — RSS/Atom parser
- `classes/feeditem.php` (level 0, ~50 LOC) — feed-item base class
- `classes/feeditem/common.php` (level 0) — FeedItem_Common abstract
- `classes/feeditem/atom.php` (level 0) — FeedItem_Atom parser
- `classes/feeditem/rss.php` (level 0) — FeedItem_RSS parser
- `classes/feedenclosure.php` (level 0, ~20 LOC) — enclosure value object
- `update_daemon2.php` (entry point, ~300 LOC) — fork-based daemon entry
- `update.php` (entry point, ~80 LOC) — CLI single-pass updater

### Call communities merged into GRP-02
- call C7 (54 nodes): Backend::digestTest, Feeds::format_headline_subtoolbar,
  Handler_Public::generate_syndicated_feed, Handler_Public::forgotpass,
  Pref_Users::resetUserPassword, Feeds::view, Feeds::catchupFeed, ...

### Class communities
- class C2 (4 nodes): FeedItem_Atom, FeedItem_Common, FeedItem, FeedItem_RSS

### Hook communities
- hook C2 (9 nodes): HOOK_FEED_FETCHED, HOOK_FETCH_FEED, HOOK_FEED_PARSED,
  HOOK_ARTICLE_FILTER, HOOK_HOUSE_KEEPING, HOOK_UPDATE_TASK,
  classes/handler/public.php, include/rssfuncs.php, update.php

---

## Representative constructs

- `update_rss_feed($feed_id, $ignore_daemon=false)` — top-level per-feed update
  (`source-repos/ttrss-php/ttrss/include/rssfuncs.php` ~line 190)
- `fetch_url($url, $login, $pass, ...)` — HTTP fetch with auth + caching
  (`source-repos/ttrss-php/ttrss/include/rssfuncs.php` ~line 50)
- `FeedParser::parse()` — entry point: detects RSS vs Atom, returns item list
  (`source-repos/ttrss-php/ttrss/classes/feedparser.php`)
- `FeedItem_Common::get_title()`, `::get_guid()`, `::get_content()` — item accessors
  (`source-repos/ttrss-php/ttrss/classes/feeditem/common.php`)
- `Feeds::view()` — headline list AJAX handler, applies filters + hook
  (`source-repos/ttrss-php/ttrss/classes/feeds.php:1`)
- `reap_children()` — PCNTL child-process harvester in daemon
  (`source-repos/ttrss-php/ttrss/update_daemon2.php:42`)
- `check_ctimes()` — max-child-runtime enforcer
  (`source-repos/ttrss-php/ttrss/update_daemon2.php:~80`)
- `PluginHost->run_hooks(HOOK_FEED_FETCHED, ...)` — post-fetch plugin chain
  (`source-repos/ttrss-php/ttrss/include/rssfuncs.php`)
- `PluginHost->run_hooks(HOOK_FEED_PARSED, ...)` — post-parse plugin chain
  (`source-repos/ttrss-php/ttrss/include/rssfuncs.php`)
- `PluginHost->run_hooks(HOOK_ARTICLE_FILTER, ...)` — per-article filter chain
  (`source-repos/ttrss-php/ttrss/include/rssfuncs.php`)
- `PluginHost->run_hooks(HOOK_FETCH_FEED, ...)` — pre-fetch override chain
  (`source-repos/ttrss-php/ttrss/include/rssfuncs.php`)
- `PluginHost->run_hooks(HOOK_UPDATE_TASK, ...)` — periodic housekeeping task
  (`source-repos/ttrss-php/ttrss/update.php`)
- `PluginHost->run_hooks(HOOK_HOUSE_KEEPING, ...)` — housekeeping from public handler
  (`source-repos/ttrss-php/ttrss/classes/handler/public.php:415`)

---

## Research findings (training-knowledge-only — DEGRADED)

### Daemon architecture
- `update_daemon2.php` is a PCNTL fork-based master/worker process:
  master loop spawns up to `MAX_JOBS` (default 2) child processes,
  each child handles one feed batch, exits when done.
- `pcntl_fork()` is a hard dependency — PHP must be compiled with PCNTL.
  This is a Unix-only pattern; not portable to Windows.
- Lock files under `LOCK_DIRECTORY` prevent concurrent runs and zombie children.
- `MAX_CHILD_RUNTIME` (default 1800s) enforces kill on hung children via
  `posix_kill()`.
- `SPAWN_INTERVAL` / `DAEMON_SLEEP_INTERVAL` controls master polling cadence.
- `SIMPLE_UPDATE_MODE` is a fallback: update triggered in-process on each
  web request instead of via daemon — for restricted hosting environments.
- Schema: daemon progress tracked via `ttrss_feeds.last_updated`,
  `ttrss_feeds.last_error` columns, not a separate job table.

### Feed parsing
- `FeedParser` uses PHP's `DOMDocument` / `SimpleXML` to parse RSS 2.0, Atom 1.0,
  and RDF/RSS 1.0. It does NOT use a dedicated parsing library.
- Item deduplication uses `guid` (RSS) or `id` (Atom); falls back to URL if absent.
- Content sanitization via `HOOK_SANITIZE` or internal `sanitize()` function
  in `include/functions2.php` — strips dangerous HTML, resolves relative URLs.
- Enclosures (podcast attachments) stored in `ttrss_enclosures` table.
- Language detection via `lib/languagedetect/` — applied per article.
- PubSubHubbub subscriber (`lib/pubsubhubbub/`) — push feed support alongside polling.

### Feed fetch
- HTTP fetch via PHP's `curl_exec()` wrapped in `fetch_url()`.
- Supports Basic Auth for password-protected feeds; credentials encrypted
  via `include/crypt.php` (mcrypt AES-128 — deprecated in PHP 7.2+, removed 7.3).
- ETag + Last-Modified headers used for conditional GET (304 handling).
- `fetch_file_contents()` shared utility for arbitrary URL fetches.
- Feed icon (favicon) fetched separately, stored in `ICONS_DIR`.
- `floIcon` and `jimIcon` libraries in `lib/` for favicon discovery.

### Known PHP → Python divergences (training knowledge)

1. **PCNTL fork-based daemon** — no Python equivalent of `pcntl_fork()` at
   library level. Python target must use `multiprocessing`, `asyncio`, or
   Celery task queue. Celery is the conventional choice (ADR-0011).

2. **DOMDocument / SimpleXML parsing** — Python's `feedparser` library
   (PyPI) handles RSS/Atom with better error tolerance. `lxml` for
   sanitization. Semantics largely equivalent; edge cases differ.

3. **mcrypt encryption for feed credentials** — `mcrypt` is removed from
   PHP 7.2+; Python target should use `cryptography` library with
   AES-GCM or Fernet. Key migration required.

4. **PHP `sleep()` in master loop** — Python daemon loop would use
   `time.sleep()` or asyncio event loop. Semantically identical.

5. **File locking** (`flock()`) — Python `fcntl.flock()` is equivalent
   on Unix. Cross-platform concern if target ever runs on Windows.

6. **`$_SERVER['argv']` CLI invocation** — Python uses `sys.argv` / `argparse`.
   Semantically identical.

7. **Direct SQL in rssfuncs.php** — `update_rss_feed()` builds raw SQL strings.
   Python target must use parameterised SQLAlchemy queries throughout.

---

## Target-side mapping

| PHP construct | Python/Celery equivalent | Notes |
|---|---|---|
| `update_daemon2.php` master loop | Celery beat scheduler | Task dispatch replaces fork |
| `pcntl_fork()` worker | Celery worker process | Pre-fork model → task queue model |
| `update_rss_feed($feed_id)` | `update_feed.delay(feed_id)` Celery task | Async, retryable |
| `FeedParser::parse()` | `feedparser.parse(url)` | Better error tolerance in Python |
| `fetch_url()` curl | `httpx.AsyncClient.get()` | Async in Celery worker context |
| `sanitize()` HTML clean | `bleach.clean()` + `lxml` | Equivalent allowlist-based sanitize |
| HOOK_FEED_FETCHED | pluggy `feed_fetched` hookspec | Same semantics |
| HOOK_FEED_PARSED | pluggy `feed_parsed` hookspec | Same semantics |
| HOOK_ARTICLE_FILTER | pluggy `article_filter` hookspec | Same semantics |
| HOOK_FETCH_FEED | pluggy `fetch_feed` hookspec | Pre-fetch override |
| HOOK_UPDATE_TASK | pluggy `update_task` hookspec | Periodic task hook |
| HOOK_HOUSE_KEEPING | pluggy `house_keeping` hookspec | Scheduled housekeeping |
| Lock files in `lock/` | Celery task deduplication | Distributed lock via Redis |
| `ttrss_feeds.last_updated` | `Feed.last_updated` column | 1:1 mapping |
| `ttrss_feeds.last_error` | `Feed.last_error` column | 1:1 mapping |
| PubSubHubbub subscriber | `lib/pubsubhubbub/` → Flask webhook route | Push vs poll |
| mcrypt AES-128 cred encrypt | Fernet / AES-GCM | Key migration needed |

---

## Divergences spotted

1. **PCNTL → Celery architectural change**: Fork-based daemon is the deepest
   architectural divergence in this codebase. Retry semantics, error logging,
   and max-runtime enforcement all change. Frequency: every feed update cycle.
   Severity: HIGH — ADR required (ADR-0011 covers this).

2. **mcrypt removal**: `include/crypt.php` uses `mcrypt_encrypt()` with
   `MCRYPT_RIJNDAEL_128` (removed PHP 7.2). Python must use modern crypto.
   Existing encrypted credentials in DB need migration path.
   Frequency: every feed with stored password. Severity: HIGH security.

3. **DOMDocument tolerance vs feedparser**: PHP's DOMDocument is strict;
   many real-world feeds are malformed XML. `feedparser` (Python) is
   explicitly designed for malformed feeds. Behavioural difference:
   Python may successfully parse feeds PHP rejected. LOW risk (positive divergence).

4. **SIMPLE_UPDATE_MODE**: browser-triggered updates. Python equivalent
   would be a background thread or Celery eager mode. Must be preserved
   as a config option. Frequency: niche use case. Severity: LOW.

5. **ETag / Last-Modified caching**: `fetch_url()` checks response headers
   to avoid re-downloading unchanged feeds. Python httpx must replicate
   this conditional-GET logic explicitly. Frequency: every update cycle.
   Severity: MEDIUM (performance regression risk if omitted).

6. **Language detection**: `lib/languagedetect/` is a PHP port of
   `Text_LanguageDetect` (PEAR). Python equivalent: `langdetect` or
   `lingua`. API differs; result format differs. Frequency: every new
   article. Severity: LOW (optional feature).

---

## Open questions

1. Should Celery beat replace the daemon 1:1 (one task per feed) or
   batch feeds into groups? (Affects DB load pattern.)
2. What is the target retry policy for failed feed fetches?
   (PHP daemon has no explicit retry — just tries again next cycle.)
3. PubSubHubbub webhook endpoint: Flask route needs to be registered;
   where does it live in the Blueprint structure?
4. How do we handle the key-migration path for mcrypt-encrypted feed
   credentials already stored in the database?
5. `HOOK_HOUSE_KEEPING` is called from `Handler_Public` on web requests —
   a background-task side effect triggered by HTTP. Should this become
   a Celery beat periodic task instead?
