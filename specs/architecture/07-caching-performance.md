# 07 — Caching & Performance Spec

## Caching Layers Overview

```
┌─────────────────────────────────────────────┐
│ HTTP Layer                                   │
│ If-Modified-Since / 304 / Last-Modified      │
│ Gzip output (ob_gzhandler)                   │
│ X-Sendfile (Nginx optimization)              │
├─────────────────────────────────────────────┤
│ Application Layer                            │
│ Preference cache (Db_Prefs singleton)        │
│ Tag cache (per-article text field)           │
│ Label cache (per-article JSON field)         │
├─────────────────────────────────────────────┤
│ Database Layer                               │
│ Counter cache (ttrss_counters_cache)         │
│ Category counter cache                       │
│ Feed browser cache (ttrss_feedbrowser_cache) │
├─────────────────────────────────────────────┤
│ File System Layer                            │
│ SimplePie feed cache (CACHE_DIR/simplepie/)  │
│ Image cache (CACHE_DIR/images/)              │
│ Export/upload cache (CACHE_DIR/export|upload) │
└─────────────────────────────────────────────┘
```

## Database Counter Cache

**Files**: `ttrss/include/ccache.php`

### Tables
- `ttrss_counters_cache` — per-feed unread counts (feed_id, owner_uid, value, updated)
- `ttrss_cat_counters_cache` — per-category unread counts

### Functions
| Function | Purpose |
|----------|---------|
| `ccache_find($feed_id, $owner_uid, $is_cat)` | Look up cached count |
| `ccache_update($feed_id, $owner_uid, $is_cat)` | Recalculate and store |
| `ccache_remove($feed_id, $owner_uid, $is_cat)` | Delete cache entry |
| `ccache_zero_all($owner_uid)` | Reset all to zero |

### Cache Validity
- 15-minute TTL (entries older than 15 min trigger recalculation)
- Invalidated on: article read/unread, feed update, mark all read
- Cascading: feed update → category update → parent category update

## Article Tag & Label Caches

### Tag Cache
- **Field**: `ttrss_user_entries.tag_cache` (text, comma-separated)
- **Logic**: Check cache first → fall back to DB query → update cache on miss
- **Invalidation**: On tag add/remove (`setArticleTags()`)

### Label Cache
- **Field**: `ttrss_user_entries.label_cache` (text, JSON-encoded)
- **Logic**: JSON decode from cache → fall back to DB query
- **Invalidation**: `label_update_cache()` on label add/remove, `label_clear_cache()` on change
- **Format**: `[[label_id, caption, fg_color, bg_color], ...]`

## File-Based Caching

### SimplePie Feed Cache

> **Note:** The cache directory is named 'simplepie' for historical reasons. The actual feed parsing uses a custom FeedParser class (see spec 01). SimplePie was removed from the codebase but the cache directory name was retained.

- **Directory**: `CACHE_DIR/simplepie/`
- **Filename**: `sha1($fetch_url).xml`
- **Short TTL**: 30 seconds (avoid duplicate fetches during same request cycle)
- **Long retention**: 7 days (cleanup by `expire_cached_files()`)
- **Logic**: If file exists and < 30s old, use cached XML; else fetch from network

### Image Cache
- **Directory**: `CACHE_DIR/images/`
- **Filename**: `sha1($src).png`
- **Retention**: 7 days
- **Triggered by**: `cache_images` flag per feed
- **Served by**: `image.php` with Last-Modified headers and X-Sendfile

### Cache Expiration
```php
// rssfuncs.php — expire_cached_files()
// Runs during daemon housekeeping
foreach (["simplepie", "images", "export", "upload"] as $dir) {
    // Remove files older than 7 days (86400*7 seconds)
}
```

## HTTP Caching

### Conditional Requests (Feed Fetching)
- Sends `If-Modified-Since` header when fetching remote feeds
- Stores `last_article_timestamp` and sends on subsequent fetches
- Handles `304 Not Modified` response (skip parsing)
- Uses CURL with `CURLOPT_HTTPHEADER` for conditional requests

### Response Caching (Public Feeds)
```php
// handler/public.php — syndicated feed generation
if (isset($_SERVER['HTTP_IF_MODIFIED_SINCE'])
    && strtotime($_SERVER['HTTP_IF_MODIFIED_SINCE']) >= $ts) {
    header('HTTP/1.0 304 Not Modified');
    return;
}
header("Last-Modified: " . gmdate("D, d M Y H:i:s", $ts) . " GMT");
```

### Gzip Compression
```php
// Enabled in backend.php and public.php
if (ENABLE_GZIP_OUTPUT && function_exists("ob_gzhandler")) {
    ob_start("ob_gzhandler");
}
```

## Locking & Concurrency

### File Lock System
- **Directory**: `LOCK_DIRECTORY/`
- **Mechanism**: `flock()` with `LOCK_EX | LOCK_NB` (non-blocking exclusive)
- **Functions**: `file_is_locked()`, `make_lockfile()`, `make_stampfile()`
- **Lock files**: PID written to file for process identification

### Feed Update Locking (Double-Update Prevention)
```
1. Query feeds needing update (WHERE last_update_started < 10 min ago OR NULL)
2. Set last_update_started = NOW() before downloading
3. Other processes see updated timestamp → skip feed
4. 10-minute timeout for stale locks
```

### Daemon Lock
- `update_daemon.lock` — prevents multiple daemon instances
- `update_daemon-{pid}.lock` — per-worker process locks
- `expire_lock_files()` — cleans stale locks older than 2 days

## Background Processing (Daemon)

### Architecture
```
update_daemon2.php (master)
├── Acquires update_daemon.lock
├── Main loop (every DAEMON_SLEEP_INTERVAL=120s):
│   ├── Query feeds needing update
│   ├── Spawn workers (MAX_JOBS=2)
│   │   ├── Worker 1: update_rss_feed($feed_id)
│   │   └── Worker 2: update_rss_feed($feed_id)
│   ├── Monitor child timeouts (MAX_CHILD_RUNTIME=1800s)
│   ├── Run HOOK_UPDATE_TASK hooks
│   └── Housekeeping (expire files, locks)
└── Signal handling: SIGCHLD for child reap
```

### Update Scheduling

| Interval | Description |
|----------|-------------|
| 0 | Use user default (from preferences) |
| -1 | Disabled |
| 15 | Every 15 minutes |
| 30 | Every 30 minutes |
| 60 | Hourly |
| 240 | Every 4 hours |
| 720 | Every 12 hours |
| 1440 | Daily |
| 10080 | Weekly |

### User Activity Filter
- Only update feeds for users who logged in within last 30 days (`DAEMON_UPDATE_LOGIN_LIMIT`)
- Reduces unnecessary feed fetching for inactive accounts

### Feed Update Batch Size
- `DAEMON_FEED_LIMIT` = 500 (max feeds per update cycle)

## Preference Caching

### Db_Prefs Singleton
- **File**: `ttrss/classes/db/prefs.php`
- In-memory cache of user preferences
- Type conversion (bool, integer, string)
- Profile support (multiple preference sets per user)

### Daemon Cache Bypass
```php
// rssfuncs.php — daemon context
define('PREFS_NO_CACHE', true);  // Disable pref caching to avoid stale data
```

## Timeout Configuration

| Constant | Default | Purpose |
|----------|---------|---------|
| `FEED_FETCH_TIMEOUT` | 45s | Feed download timeout |
| `FEED_FETCH_NO_CACHE_TIMEOUT` | 15s | First-time fetch timeout |
| `FILE_FETCH_TIMEOUT` | 45s | General file fetch timeout |
| `FILE_FETCH_CONNECT_TIMEOUT` | 15s | TCP connection timeout |
| `DAEMON_SLEEP_INTERVAL` | 120s | Daemon loop sleep |
| `MAX_CHILD_RUNTIME` | 1800s | Worker process timeout |

## Python Migration Notes

- **Counter cache**: Consider Redis or PostgreSQL materialized views
- **File cache**: Python `diskcache` library or Redis
- **Feed fetching**: `aiohttp` for async concurrent fetching (much faster than sequential PHP)
- **Background workers**: Celery with Redis/RabbitMQ, or Python `asyncio` tasks
- **Locking**: Redis distributed locks (if multi-process), or `fcntl.flock()` for single-node
- **HTTP caching**: `requests-cache` library or `httpx` with caching middleware
- **Image proxy**: Serve via Nginx directly (X-Accel-Redirect) or Python streaming response
- **Gzip**: Handled by WSGI middleware or Nginx `gzip on`
