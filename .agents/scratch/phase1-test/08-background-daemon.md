# 08 — Background Daemon

**Dimension**: `background-daemon`
**Derivation**: Cross-cutting — `update_daemon2.php` (call-graph GRP-02),
hook-graph C2 (feed pipeline hooks), db_table C0 (feeds/entries), include C2 (rssfuncs.php)
**Phase**: Phase 1
**Status**: extracted ✓ · communities detected ✓ · research DEGRADED

---

## Purpose

Captures the background feed-update daemon: PCNTL fork model, feed update pipeline,
scheduling mechanism, hook dispatch points, and the Celery migration path.

---

## PHP architecture summary

### Daemon (update_daemon2.php)

- PCNTL fork-based master/worker: master spawns up to `MAX_JOBS` (default 2) child processes
- Each child handles one feed batch; exits when done
- `reap_children()` harvests via `pcntl_waitpid()` with `WNOHANG`
- Lock files in `LOCK_DIRECTORY` prevent duplicate runs
- `MAX_CHILD_RUNTIME` (1800s default): `posix_kill()` kills hung children
- `SPAWN_INTERVAL` = `DAEMON_SLEEP_INTERVAL`: master loop sleep cadence
- `SIMPLE_UPDATE_MODE`: HTTP-triggered update fallback (no daemon required)
- Source: `source-repos/ttrss-php/ttrss/update_daemon2.php:1–80`

### Feed update pipeline (rssfuncs.php)

```
update_rss_feed($feed_id):
  1. run_hooks(HOOK_FETCH_FEED, url)       — plugin override of HTTP fetch
  2. fetch_url($url, login, pass)          — curl w/ ETag/Last-Modified
  3. run_hooks(HOOK_FEED_FETCHED, content) — post-fetch processing
  4. FeedParser::parse($content)           — RSS/Atom DOM parse
  5. run_hooks(HOOK_FEED_PARSED, items)    — post-parse processing
  6. For each new article:
     a. Dedup by GUID → insert ttrss_entries + ttrss_user_entries
     b. run_hooks(HOOK_ARTICLE_FILTER, article)
     c. Evaluate ttrss_filters2 rules
     d. ccache_update(feed_id, owner_uid)
  7. UPDATE ttrss_feeds SET last_updated=NOW(), last_error=... WHERE id=$feed_id
```

Source: `source-repos/ttrss-php/ttrss/include/rssfuncs.php:~190`

### Scheduling

- `update.php` — CLI single-pass (cron or debug)
- `update_daemon2.php` — long-running daemon (production recommended)
- `SIMPLE_UPDATE_MODE` — web-triggered via `Handler_Public::globalUpdateFeeds()` (line 421)
- Feed interval: `ttrss_feeds.update_interval` column (0 = global default)
- Global interval: `UPDATE_INTERVAL` config constant (default 3600s)
- No job-queue — scheduling via `ttrss_feeds.last_updated` column

### Error handling

- `ttrss_feeds.last_error` — last error message per feed
- No retry backoff — failed feeds retried on next daemon cycle
- Errors logged to `ttrss_error_log`

---

## Communities (cross-dimension)

| Dim | Community | Members | Significance |
|---|---|---|---|
| call-graph | C7 (54 nodes) | Backend::digestTest, Feeds::format_headline_subtoolbar | Feed rendering |
| hook-graph | C2 (9 nodes) | HOOK_FEED_FETCHED, HOOK_FETCH_FEED, HOOK_FEED_PARSED, HOOK_ARTICLE_FILTER, HOOK_HOUSE_KEEPING, HOOK_UPDATE_TASK | Full feed pipeline |
| db_table | C0 (13 nodes) | ttrss_feeds, ttrss_entries, ttrss_archived_feeds | Primary update targets |
| include | C2 (11 nodes) | rssfuncs.php, api.php, crypt.php | Feed processing cluster |

Research note: `research/GRP-02-feed-engine.md`

---

## Migration path to Celery

| PHP construct | Python/Celery equivalent | Notes |
|---|---|---|
| `update_daemon2.php` master loop | Celery beat scheduler | Task dispatch replaces fork |
| `pcntl_fork()` worker | Celery worker process | Pre-fork → task queue |
| `update_rss_feed($feed_id)` | `update_feed.delay(feed_id)` | Async, retryable |
| `fetch_url()` curl | `httpx.AsyncClient.get()` | Async in worker context |
| `FeedParser::parse()` | `feedparser.parse(url_or_content)` | Better malformed feed handling |
| Lock files in `lock/` | Redis-based distributed lock | Celery task deduplication |
| `ttrss_feeds.last_updated` | `Feed.last_updated` column | 1:1 mapping |
| `ttrss_feeds.last_error` | `Feed.last_error` column | 1:1 mapping |
| `HOOK_UPDATE_TASK` | Celery beat periodic task | Decouple from HTTP path |
| `HOOK_HOUSE_KEEPING` | Celery beat periodic task | Move from HTTP-trigger anti-pattern |
| `SIMPLE_UPDATE_MODE` | Celery eager mode / sync call | Config-driven |
| `mcrypt` cred decryption | Fernet decryption | ADR-0009 (crypt.php migration) |

---

## Key divergences

**D-BD-01 — PCNTL fork → Celery** (severity: HIGH):
PHP daemon uses OS-level `pcntl_fork()`. Python multiprocessing equivalent is
Celery task queue. Retry semantics, error logging, and max-runtime enforcement all change.
Frequency: every feed update cycle.

**D-BD-02 — ETag/Last-Modified conditional GET** (severity: MEDIUM):
`fetch_url()` checks response headers to avoid re-downloading unchanged feeds.
Python `httpx` must replicate conditional GET logic explicitly.
Omission causes unnecessary re-parsing of unchanged feeds.
Source: `source-repos/ttrss-php/ttrss/include/rssfuncs.php`

**D-BD-03 — mcrypt feed credential decryption** (severity: CRITICAL):
Daemon decrypts `ttrss_feeds.auth_pass` via `decrypt_string()` in `include/crypt.php`
before making authenticated HTTP requests. Python must use Fernet decryption.
One-time migration of existing encrypted credentials required before Python daemon goes live.
Source: `source-repos/ttrss-php/ttrss/include/crypt.php`

**D-BD-04 — SIMPLE_UPDATE_MODE HTTP anti-pattern** (severity: MEDIUM):
Background tasks triggered from `Handler_Public` as HTTP side-effect.
Python: use Celery beat or `apply_async()` from Flask route (non-blocking).
Source: `source-repos/ttrss-php/ttrss/classes/handler/public.php:415–421`

**D-BD-05 — DOMDocument vs feedparser tolerance** (severity: LOW, positive):
PHP `FeedParser` uses strict DOMDocument; Python `feedparser` handles malformed XML.
Python may successfully parse feeds PHP rejected. Positive divergence; test parity needed.

---

## Source cross-references

| Construct | Source | Lines |
|---|---|---|
| Daemon master loop | `source-repos/ttrss-php/ttrss/update_daemon2.php` | 1–150 |
| `reap_children()` | `source-repos/ttrss-php/ttrss/update_daemon2.php` | 42 |
| `update_rss_feed()` | `source-repos/ttrss-php/ttrss/include/rssfuncs.php` | ~190 |
| `fetch_url()` | `source-repos/ttrss-php/ttrss/include/rssfuncs.php` | ~50 |
| HOOK_FEED_FETCHED invocation | `source-repos/ttrss-php/ttrss/include/rssfuncs.php` | (grep HOOK_FEED_FETCHED) |
| HOOK_HOUSE_KEEPING | `source-repos/ttrss-php/ttrss/classes/handler/public.php` | 415 |
| HOOK_UPDATE_TASK | `source-repos/ttrss-php/ttrss/classes/handler/public.php` | 421 |
| `FeedParser::parse()` | `source-repos/ttrss-php/ttrss/classes/feedparser.php` | full |
| Feed credential decryption | `source-repos/ttrss-php/ttrss/include/crypt.php` | full |
| `MAX_JOBS`, `MAX_CHILD_RUNTIME` | `source-repos/ttrss-php/ttrss/update_daemon2.php` | define() lines |
