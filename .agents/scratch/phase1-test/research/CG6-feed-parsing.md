# Dimension: call-graph · Community: CG-6 — Feed Parsing / Sanitize

## Status
DEGRADED — training knowledge + source corpus reads only; no web search available.
All [TRAINING] claims should be verified against current feedparser, lxml docs before Phase 2.

---

## Members

| File | Level | Est. LOC | Role |
|------|-------|---------|------|
| `classes/feedparser.php` | L2 | ~300 | Top-level feed parser orchestrator |
| `classes/feeditem.php` | L1 | ~80 | Abstract FeedItem base class |
| `classes/feeditem/common.php` | L0 | ~120 | Shared field accessors (author, comments, etc.) |
| `classes/feeditem/atom.php` | L0 | ~150 | Atom 1.0 item implementation |
| `classes/feeditem/rss.php` | L0 | ~150 | RSS 2.0 item implementation |
| `classes/feedenclosure.php` | L0 | ~30 | Media enclosure value object |
| `include/functions2.php` | L2 | ~500 | Contains `sanitize()` — HTML content sanitizer |
| `include/rssfuncs.php` | L3 | ~800 | `update_rss_feed()`, `update_daemon_common()` — feed fetch + storage |

---

## Representative constructs

- `FeedParser::__construct($url)` — initialises SimplePie-like parse pipeline
- `FeedParser::init()` — executes HTTP fetch + parse; detects Atom vs RSS
- `FeedParser::normalize_encoding($data)` — charset normalisation (UTF-8 coercion)
- `FeedParser::format_error($error, $description, $url)` — structured error object
- `FeedParser::get_link()` — channel-level link extraction
- `FeedItem_Atom::get_date()` — ISO 8601 → Unix timestamp
- `FeedItem_Atom::get_categories()` — Atom `<category>` tag list
- `FeedItem_Atom::get_enclosures()` — Atom `<link rel="enclosure">` list
- `FeedItem_RSS::get_link()` — RSS `<link>` with CDATA handling
- `FeedItem_RSS::get_content()` — prefers `<content:encoded>` over `<description>`
- `FeedItem_Common::get_author()` — unifies Atom `<author>` and RSS `<dc:author>`
- `FeedItem::get_title()` — strip_tags normalisation
- `FeedEnclosure` — VO: `content_url`, `content_type`, `title`, `duration`
- `sanitize($str, $strip_images, $site_url, $highlight, $article_id, $owner)` in `include/functions2.php`
- `update_rss_feed($feed_id, $no_cache, $dump, $override_url)` in `include/rssfuncs.php`
- `fetch_file_contents($url, ...)` in `include/functions.php` — HTTP client (cURL + fallback)

---

## Source evidence (from corpus reads)

### FeedParser class
Source: `source-repos/ttrss-php/ttrss/classes/feedparser.php`

- Uses PHP's built-in `xml_parser_create()` / SAX API for feed parsing.
- NOT SimplePie — TT-RSS rolled its own parser to avoid the SimplePie dependency.
- `init()` calls `fetch_file_contents()` for HTTP, then SAX-parses the response.
- Encoding normalisation via `mb_convert_encoding` / `iconv` fallback.
- Feed type detection: checks for `<feed xmlns="...Atom...">` vs `<rss version=...>`.
- Returns a list of `FeedItem` objects (either `FeedItem_Atom` or `FeedItem_RSS`).

### FeedItem hierarchy
Source: `source-repos/ttrss-php/ttrss/classes/feeditem/`

- `FeedItem` is an abstract class with `get_title()`, `get_link()`, `get_id()` stubs.
- `FeedItem_Common` provides author, comments_url, comments_count — shared by both formats.
- `FeedItem_Atom` and `FeedItem_RSS` hold raw XML nodes and implement format-specific accessors.
- `get_enclosures()` returns array of `FeedEnclosure` objects.
- Date parsing: Atom uses ISO 8601 (`2023-01-15T10:00:00Z`);
  RSS uses RFC 2822 (`Mon, 15 Jan 2023 10:00:00 +0000`).
  Both normalised to Unix timestamp via `strtotime()`.

### sanitize() function
Source: `source-repos/ttrss-php/ttrss/include/functions2.php` (~line 1-250 approx)

- Input: raw HTML content from feed item.
- Strips unsafe HTML tags via a whitelist approach.
- Calls `HOOK_SANITIZE` — plugins can modify content before/after sanitization.
- Handles image proxying (`cache_images` pref).
- Converts relative URLs to absolute using `$site_url`.
- Returns sanitized HTML string.
- The whitelist is hardcoded: `a, abbr, acronym, address, area, article, aside, b, big, blockquote, br, caption, center, cite, code, col, colgroup, dd, del, dfn, dir, div, dl, dt, em, font, footer, h1..h6, header, hr, i, img, ins, kbd, li, ol, p, pre, q, s, section, small, span, strike, strong, sub, sup, table, tbody, td, tfoot, th, thead, tr, tt, u, ul, var`.

### update_rss_feed() / rssfuncs.php
Source: `source-repos/ttrss-php/ttrss/include/rssfuncs.php`

- Central function: fetches feed URL, parses with `FeedParser`, stores articles in DB.
- Calls hooks: `HOOK_FETCH_FEED` (before fetch), `HOOK_FEED_FETCHED` (after fetch),
  `HOOK_FEED_PARSED` (after parse), `HOOK_ARTICLE_FILTER` (per article).
- Article deduplication: checks `ttrss_entries.guid` UNIQUE constraint.
- Stores new articles in `ttrss_entries` + per-user rows in `ttrss_user_entries`.
- Applies user filters: calls `find_article_filters()` → filter rules evaluated.
- Updates `ttrss_feeds.last_updated`, `ttrss_feeds.last_error`.
- MySQL vs PostgreSQL SQL branches for date arithmetic.

---

## Research findings [TRAINING]

### PHP feed parsing landscape
- TT-RSS uses a hand-rolled SAX parser (not SimplePie, not Magpie RSS).
- SAX parsing is event-driven, low memory, but complex to map 1:1 to Python.
- Python equivalent: `feedparser` library (Universal Feed Parser, by Mark Pilgrim + team).
  `feedparser` handles Atom 0.3, Atom 1.0, RSS 0.9x, RSS 1.0, RSS 2.0, CDF, and more.
  Source: training knowledge [TRAINING]

### feedparser library (Python target)
- `import feedparser; d = feedparser.parse(url_or_string)`.
- Returns a `FeedParserDict` with `d.feed` (channel) and `d.entries` (items).
- `entry.title`, `entry.link`, `entry.id`, `entry.updated_parsed` (time.struct_time),
  `entry.summary`, `entry.content[0].value`, `entry.enclosures`.
- Sanitization: feedparser has a built-in `_HTMLSanitizer` that strips unsafe tags.
  It is LESS configurable than TT-RSS's `sanitize()` — TT-RSS's whitelist is custom.
- Date parsing: feedparser normalises all dates to UTC `time.struct_time`.
  TT-RSS uses Unix timestamps (ints) throughout. Need: `calendar.timegm(entry.updated_parsed)`.
- Encoding: feedparser auto-detects and normalises to Python str (UTF-8 strings).
  No manual `mb_convert_encoding` needed. [TRAINING]

### lxml for HTML sanitization
- `lxml.html.clean.Cleaner` with `allow_tags` list replaces TT-RSS's custom `sanitize()`.
- `bleach` library (Python) is an alternative with a similar whitelist API.
- Image proxying and URL absolutisation: `lxml.html.rewrite_links()`. [TRAINING]

### HTTP fetching
- TT-RSS: `fetch_file_contents()` uses cURL with extensive option handling
  (timeout, auth, User-Agent, conditional GET via `If-Modified-Since` / ETag).
- Python: `httpx.AsyncClient` with `follow_redirects=True`, `timeout=...`,
  custom headers. Runs inside Celery worker as async task or sync with `httpx.Client`.
  [TRAINING]

---

## Target-side mapping

| PHP construct | Python / Flask equivalent |
|--------------|--------------------------|
| `FeedParser` class | `feedparser.parse(url)` call + `FeedParserDict` |
| `FeedItem_Atom` / `FeedItem_RSS` | `feedparser.FeedParserDict` entry (unified) |
| `FeedItem_Common.get_author()` | `entry.author` or `entry.author_detail.name` |
| `FeedItem.get_date()` (unix int) | `calendar.timegm(entry.updated_parsed)` |
| `FeedEnclosure` | `entry.enclosures[i]` dict (`url`, `type`, `length`) |
| `sanitize($html, ...)` | `lxml.html.clean.Cleaner(allow_tags=[...]).clean_html(html)` |
| `fetch_file_contents($url, ...)` | `httpx.Client.get(url, headers=..., timeout=...)` |
| `update_rss_feed()` | Celery task `fetch_and_store_feed.delay(feed_id)` |
| `HOOK_SANITIZE` invocation | pluggy `hookspec sanitize(content, site_url)` |
| `HOOK_FEED_FETCHED` invocation | pluggy `hookspec feed_fetched(feed_data, feed_id)` |
| `HOOK_FEED_PARSED` invocation | pluggy `hookspec feed_parsed(entries, feed_id)` |
| `HOOK_ARTICLE_FILTER` invocation | pluggy `hookspec article_filter(entry, feed_id)` |

---

## Divergences spotted

### D-CG6-01: feedparser returns time.struct_time; TT-RSS uses Unix int

- **PHP**: `strtotime()` → int. Stored as `timestamp` in PostgreSQL.
- **Python**: `feedparser` returns `time.struct_time` in UTC.
  `calendar.timegm(entry.updated_parsed)` → int. Or store directly as `datetime`.
- **Impact**: Every date comparison and storage call in `update_rss_feed()`.
- **Mitigation**: Convert at feed-item extraction boundary; store as `datetime` in SQLAlchemy.

### D-CG6-02: feedparser sanitize vs TT-RSS sanitize() whitelist mismatch

- **PHP**: Custom whitelist in `sanitize()`, calls `HOOK_SANITIZE`, proxies images.
- **Python/feedparser**: feedparser's sanitizer strips MORE than TT-RSS's whitelist (more conservative).
- **Impact**: Articles that TT-RSS renders correctly may have tags stripped by feedparser.
- **Mitigation**: Disable feedparser sanitization (`feedparser.SANITIZE_HTML = False`);
  apply custom `lxml.clean.Cleaner` with TT-RSS's whitelist.
  Preserve HOOK_SANITIZE invocation via pluggy.

### D-CG6-03: PHP SAX vs feedparser element model

- **PHP**: FeedParser walks raw XML nodes; `FeedItem_RSS.get_content()` checks
  `content:encoded` explicitly before falling back to `description`.
- **Python/feedparser**: feedparser normalises Atom `<content>` and RSS `<content:encoded>`
  into `entry.content[0].value`; `<description>` maps to `entry.summary`.
  The priority logic (`content:encoded` > `description`) is handled internally.
- **Impact**: Content extraction logic simplifies in Python but must verify parity
  for edge cases (malformed feeds, multiple `<content>` elements).

### D-CG6-04: Encoding normalisation

- **PHP**: `normalize_encoding()` in FeedParser uses `mb_convert_encoding` / `iconv`
  to force UTF-8; incorrectly-declared encodings silently coerced.
- **Python**: feedparser normalises to Python str (Unicode).
  `requests`/`httpx` decodes HTTP Content-Type charset; feedparser handles BOM.
- **Impact**: Feeds with ISO-8859-1 or Windows-1252 declaration should be handled.
  Verify with a test corpus of non-UTF-8 feeds.

### D-CG6-05: cURL vs httpx conditional GET (ETag / If-Modified-Since)

- **PHP**: `fetch_file_contents()` sends `If-Modified-Since` header and handles 304.
- **Python/httpx**: Must explicitly send `headers={"If-Modified-Since": ..., "ETag": ...}`.
  Store last `ETag` and `Last-Modified` in `ttrss_feeds` (columns already present as `favicon_last_checked` — need dedicated columns or reuse).
- **Impact**: Bandwidth efficiency; no content change → 304 → skip storage.
  Preserve this behaviour in the Celery fetch task.

### D-CG6-06: GUID deduplication

- **PHP**: `INSERT INTO ttrss_entries ... WHERE guid NOT EXISTS ...` — DB-level UNIQUE.
- **Python/SQLAlchemy**: `INSERT ... ON CONFLICT DO NOTHING` (PostgreSQL) via
  `insert(...).on_conflict_do_nothing(index_elements=['guid'])`.
  Or catch `sqlalchemy.exc.IntegrityError`.
- **Impact**: Standard port; low risk.

---

## Open questions (Phase 2 ADR items)

1. **feedparser vs custom parser**: Should the Python port use `feedparser` entirely,
   or reimplement TT-RSS's custom SAX parsing for exact parity?
   Recommendation: feedparser for production feeds; custom regression suite to detect parity gaps.

2. **HOOK_SANITIZE pass-by-reference semantics**: PHP `sanitize()` passes `$str` to
   `run_hooks(HOOK_SANITIZE, &$str)` — plugins mutate in place.
   Python pluggy equivalent: pass a mutable container (`{"content": html}`) or use
   `firstresult` chain returning a new string per plugin.

3. **Image proxy in sanitize()**: TT-RSS rewrites `<img src>` to a local proxy URL
   when `cache_images` is enabled. The proxy fetches and caches images server-side.
   Python equivalent: preserve `image.php` logic as a Flask route `/image?url=...`.

4. **Sphinx full-text search integration**: `include/rssfuncs.php` calls Sphinx API
   for full-text indexing of articles.
   Decision needed: replace with PostgreSQL `tsvector` full-text search or Elasticsearch.
   (Phase 2 ADR recommended.)

5. **`STRIP_UNSAFE_TAGS` pref**: User-level preference controls sanitization depth.
   Must be wired through to the Python sanitize call with correct `owner_uid` lookup.
