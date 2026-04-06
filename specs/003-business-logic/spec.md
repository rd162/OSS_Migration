# Spec 003 — Business Logic

**Status:** DONE  
**Completed:** 2026-04-04  
**Phase:** 3 of 6  
**Plan source:** memory/phase3_plan_2026-04-04.md (Solution A, Condorcet 2-0)  
**Constitution ref:** P1 (Library-First), P2 (Test-First), P3 (Source Traceability), P5 (Behavioral Parity)

---

## User Stories

### US-3a — Counter Cache + Label + Feed ID Utilities

> As a developer, I need counter cache management, label operations, and virtual feed ID conversion utilities so that all upstream modules can compute unread counts and manage labels without N+1 queries.

### US-3b — Feed Categories + Feed Operations

> As a developer, I need category hierarchy traversal and feed CRUD operations so that the application can subscribe to feeds, purge old articles, and compute category trees with correct NULL/uncategorized handling.

### US-3c — Counters

> As a developer, I need all counter aggregation functions so that the API can return accurate unread counts for feeds, categories, virtual feeds, labels, and global state.

### US-3d — Article Operations + Tag Cache

> As a developer, I need article formatting, catchup operations, and tag cache management so that articles can be marked read, tagged, and rendered as dicts (not HTML).

### US-3e — Article Filters + Search + Housekeeping

> As a developer, I need filter evaluation, headline queries, and housekeeping tasks so that feed ingestion can apply filters, search can query headlines with 16 parameters, and the system can expire old data.

### US-3f — Feed Task Article Persistence

> As a developer, I need the complete article persistence pipeline so that ingested feed entries are stored with correct GUID construction, content hashing, filter actions, tags, labels, enclosures, and N-gram deduplication.

---

## Functional Requirements

| ID | Requirement | PHP Source | Graph Levels | DB Community |
|----|-------------|-----------|-------------|-------------|
| FR-301 | `ttrss/utils/feeds.py` — LABEL_BASE_INDEX=-1024, PLUGIN_FEED_BASE_INDEX=-128, 4 ID conversion functions, classify_feed_id | functions.php:5-6, functions2.php:2400-2405, pluginhost.php:381-386 | L0-L4 | [3],[0] |
| FR-302 | `ttrss/ccache.py` — 5 counter cache functions (zero_all, remove, find, update, update_all) + inlined _count_feed_articles | include/ccache.php (224 lines) | L0-L4 | [3] |
| FR-303 | `ttrss/labels.py` — 10 label functions | include/labels.php (201 lines) | L0-L4 | [0] |
| FR-304 | `ttrss/feeds/categories.py` — 8 category functions including recursive traversal with depth guard | functions.php:1300-1320, functions2.php:1100-1190 | L2-L3 | [0] |
| FR-305 | `ttrss/feeds/ops.py` — 10 feed operation functions including subscribe, purge, favicons | functions.php:1673-1738, functions.php:400-590, functions2.php:900-960 | L1-L7 | [5] |
| FR-306 | `ttrss/feeds/counters.py` — 12 counter aggregation functions | functions.php:641-1493 | L2-L6 | [3] |
| FR-307 | `ttrss/articles/ops.py` — 10 article operation functions; returns dicts not HTML | functions2.php:1198-1943, functions.php:1094-1237, article.php | L0-L5 | [4] |
| FR-308 | `ttrss/articles/tags.py` — 5 tag cache functions | functions2.php:1055-1098, article.php:222-284 | L0-L5 | [4] |
| FR-309 | `ttrss/articles/filters.py` — 8 filter functions, all 8 filter action types | functions2.php:1491-2160, rssfuncs.php:1272-1399 | L0-L3 | [2] |
| FR-310 | `ttrss/articles/search.py` — search_to_sql + queryFeedHeadlines (16 params, 6 JOIN strategies) | functions2.php:260-830 | L2-L5 | [4] |
| FR-311 | `ttrss/tasks/housekeeping.py` — 5 ported sub-functions, 1 eliminated, HOOK_HOUSE_KEEPING | include/rssfuncs.php:1415-1430 | L1-L3 | [1] |
| FR-312 | `ttrss/tasks/feed_tasks.py` — complete article persistence pipeline (GUID, SHA1, filters, tags, labels, enclosures, N-gram) | include/rssfuncs.php:545-1117 | L0-L10 | [4] |

---

## Hook Invocation Requirements

| Hook | Module | PHP Source | Status |
|------|--------|-----------|--------|
| HOOK_RENDER_ARTICLE | articles/ops.py (format_article, after sanitize) | functions2.php:1250 | DONE |
| HOOK_RENDER_ARTICLE_CDM | articles/ops.py (headline list CDM mode) | feeds.php:517 | DONE |
| HOOK_ARTICLE_BUTTON | articles/ops.py (article footer right) | functions2.php:1360, feeds.php:723 | DONE |
| HOOK_ARTICLE_LEFT_BUTTON | articles/ops.py (article footer left) | functions2.php:1371, feeds.php:686 | DONE |
| HOOK_HEADLINE_TOOLBAR_BUTTON | articles/ops.py (headline toolbar) | feeds.php:138 | DONE |
| HOOK_QUERY_HEADLINES | articles/search.py (queryFeedHeadlines construction) | functions2.php | DONE |
| HOOK_HOUSE_KEEPING | tasks/housekeeping.py (fires last) | rssfuncs.php | DONE |
| HOOK_ARTICLE_FILTER | tasks/feed_tasks.py (per entry, from Phase 2) | rssfuncs.php:687 | DONE |
| HOOK_FEED_PARSED | tasks/feed_tasks.py (from Phase 2) | rssfuncs.php:394 | DONE |

---

## Counter Cache Coherency Requirements (R5)

All 9 `ccache_update` call sites must be wired (7 in Phase 3, 2 deferred to Phase 4):

| # | Call Site | Module | PHP Source |
|---|----------|--------|-----------|
| 1 | purge_feed (early return) | feeds/ops.py | functions.php:226 |
| 2 | purge_feed (after delete) | feeds/ops.py | functions.php:284 |
| 3 | catchup_feed | articles/ops.py | functions.php:1226 |
| 4 | catchupArticlesById (per feed_id) | articles/ops.py | functions2.php:1051 |
| 5 | catchupArticleById | articles/ops.py | article.php:84 |
| 6 | format_article (mark_as_read=True) | articles/ops.py | functions2.php:1222 |
| 7 | After article insert | tasks/feed_tasks.py | rssfuncs.php |
| 8 | Feeds::view (feed >= 0) | Phase 4 (blueprint) | feeds.php:851 |
| 9 | Pref_Feeds::clear_feed_articles | Phase 4 (prefs blueprint) | pref/feeds.php:1696 |

---

## Key Behavioral Parity Rules

| Rule | PHP Behavior | Python Implementation |
|------|-------------|----------------------|
| R6 | Virtual feed ID scheme: LABEL_BASE_INDEX=-1024, PLUGIN_FEED_BASE_INDEX=-128 | Constants in utils/feeds.py; ID functions as inverses |
| R8 | label_cache format: `[[-1026, "caption", "#fg", "#bg"], ...]` or `{"no-labels": 1}` | labels.py writes exact JSON structure |
| R9 | Category hierarchy: cat_id=0 = uncategorized (NULL→0), depth guard MAX_CATEGORY_DEPTH=20 | feeds/categories.py with _depth guard |
| R12 | ccache_find TTL is dead code in PHP — do NOT implement | ccache.py SELECT uses only owner_uid + feed_id |
| R13 | format_article family returns dicts, not HTML | articles/ops.py returns dict |

---

## Anti-Requirements (Eliminated PHP Patterns)

| ID | Pattern Eliminated | PHP Location |
|----|--------------------|-------------|
| AR1 | Raw SQL string concatenation | All modules — SQLAlchemy only |
| AR2 | MySQL compatibility code (DB_TYPE, DATE_SUB, REGEXP) | getFeedArticles, catchup_feed, purge_feed, filter_to_sql |
| AR3 | N+1 query patterns in ccache/counters | ccache_update_all — bulk GROUP BY |
| AR4 | Phantom columns/defaults not in actual schema | Pre-batch model verification required |
| AR5 | Missing ccache_update calls | All 7 Phase 3 call sites wired |
| AR9 | Server-rendered HTML from business logic | print_feed_cat_select, print_feed_select eliminated |

---

## Success Criteria

- **SC-001:** Unread counts are accurate after any read/unread operation, with zero stale cache states observable by users
- **SC-002:** Article persistence is idempotent — re-importing the same feed entry does not create duplicate rows
- **SC-003:** Feed category hierarchies with up to 20 levels resolve without infinite recursion or timeout
- **SC-004:** All 8 filter action types (filter, catchup, mark, publish, score, tag, label, stop) correctly modify article state
- **SC-005:** No server-rendered HTML is returned by any business logic function; all return dicts or lists

## Assumptions

- Counter cache is the source of truth for unread counts; real-time DB queries are not used for display
- Category `id=0` represents "uncategorized" (equivalent to PHP NULL), consistently across all functions
- N-gram deduplication relies on PostgreSQL's built-in `similarity()` function; no external NLP library
- The PHP label cache format `[[-1026, "caption", "#fg", "#bg"], ...]` is fixed and must not be changed

---

> **Heritage note:** This phase was implemented on `main` before the `speckit-specify` branch workflow was established. Spec content is authoritative; it was not generated via `/speckit-specify`.

---

## Exit Gate (18 Criteria)

1. [x] All 9 batch Rule 10a CRITIC/AUTHOR cycles passed (0 findings each)
2. [x] `pytest --cov-fail-under=80` green for every Phase 3 module individually
3. [x] `label_to_feed_id` and `feed_to_label_id` are inverses (round-trip test)
4. [x] `pfeed_to_feed_id` and `feed_to_pfeed_id` are inverses (round-trip test)
5. [x] `LABEL_BASE_INDEX = -1024` and `PLUGIN_FEED_BASE_INDEX = -128` match PHP
6. [x] `ccache_find` does NOT check TTL (dead code exclusion per R12)
7. [x] All 9 ccache_update call sites wired (7 in Phase 3, 2 deferred to Phase 4)
8. [x] `catchup_feed` calls `ccache_update` after every unread state change
9. [x] `label_cache` and `tag_cache` both read/written correctly
10. [x] Category 0 = uncategorized (NULL handling) throughout
11. [x] `getParentCategories` depth-limited to prevent infinite recursion
12. [x] `purge_orphans` imported (not duplicated) in housekeeping
13. [x] All 7 housekeeping sub-functions mapped: 5 ported, 1 eliminated, 1 hook
14. [x] `queryFeedHeadlines` handles all feed ID types
15. [x] All 7 Phase 3 hooks fire at correct points
16. [x] No MySQL branches in any Phase 3 module (grep DB_TYPE = 0, grep DATE_SUB = 0)
17. [x] No circular imports (`python -c` import check for all modules)
18. [x] Article persistence full scope: GUID + SHA1 + content_hash + 8 filters + tags + labels + enclosures + N-gram
