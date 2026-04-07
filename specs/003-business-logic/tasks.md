# Tasks 003 — Business Logic

**Status:** ALL DONE  
**Completed:** 2026-04-04  
**Spec ref:** specs/003-business-logic/spec.md  
**Plan ref:** specs/003-business-logic/plan.md

---

## Pre-Batch Gate — Model Verification

- [x] Verify all 31 SQLAlchemy models against `ttrss_schema_pgsql.sql` — flag missing columns, wrong types, phantom defaults  
  _Required: business logic depends on exact column names_

---

## Batch 0 — Counter Cache + Labels + Feed ID Utilities (L0-L4) **[US-3a]**

> **Story:** As a developer, I need counter cache management, label operations, and virtual feed ID conversion utilities so that all upstream modules can compute unread counts and manage labels without N+1 queries.

- [x] Implement `ttrss/utils/feeds.py` — LABEL_BASE_INDEX=-1024, PLUGIN_FEED_BASE_INDEX=-128, 6 functions  
  _Source: include/functions.php:5-6, include/functions2.php:2400-2405, classes/pluginhost.php:381-386_
- [x] Implement `ttrss/ccache.py` — ccache_zero_all, ccache_remove, ccache_find, ccache_update, ccache_update_all  
  _Source: ttrss/include/ccache.php (224 lines)_
- [x] Implement `_count_feed_articles` inlined in ccache.py — all 7 virtual feed type branches  
  _Source: include/functions.php:1401-1493 — inlined to avoid circular import (R18)_
- [x] Verify ccache_update_all uses bulk GROUP BY query (not N+1 loop)  
  _AR3 elimination_
- [x] Verify ccache_find does NOT check TTL (dead code per R12)  
  _Source: ccache.php:74-76 — TTL branch eliminated_
- [x] Implement `ttrss/labels.py` — all 10 label functions  
  _Source: ttrss/include/labels.php (201 lines)_
- [x] Verify label_cache JSON format: `[[-1026, "caption", "#fg", "#bg"], ...]` or `{"no-labels": 1}`  
  _Behavioral parity R8_
- [x] Write unit tests for all ID conversion functions (boundary values at -128, -1024, -1025)  
  _AGENTS.md test traceability rule_
- [x] Write test: ccache_find does NOT filter by time  
  _R12 dead code exclusion_
- [x] Write test: _count_feed_articles for each virtual feed type  
  _Behavioral parity_
- [x] Write test: label_cache JSON format matches PHP  
  _Behavioral parity R8_
- [x] Run `pytest --cov=ttrss.ccache --cov=ttrss.labels --cov=ttrss.utils.feeds --cov-fail-under=80`  
  _QG-1 gate_
- [x] Rule 10a adversarial self-refine — 0 traceability violations  
  _AGENTS.md Rule 10a_

**Gate:** [x] ID conversion inverses | [x] no TTL | [x] bulk GROUP BY | [x] pytest green

---

## Batch 1 — Feed Categories (L2-L3) **[US-3b]**

> **Story (partial):** As a developer, I need category hierarchy traversal and feed CRUD operations so that the application can subscribe to feeds and compute category trees with correct NULL/uncategorized handling.

- [x] Implement `ttrss/feeds/categories.py` — 8 category functions  
  _Source: include/functions.php:1300-1320, include/functions2.php:1100-1190_
- [x] Verify category 0 = uncategorized (NULL handling) throughout  
  _Behavioral parity R9_
- [x] Verify getChildCategories(cat_id=0) returns [] matching PHP  
  _Source: include/functions2.php:1171-1190_
- [x] Verify depth guard MAX_CATEGORY_DEPTH=20 on getParentCategories and getChildCategories  
  _R9 — prevents infinite recursion_
- [x] Eliminate print_feed_cat_select() and print_feed_select() — server-rendered HTML  
  _R13, AR9_
- [x] Write test: uncategorized (cat_id=0 → empty children)  
  _Behavioral parity_
- [x] Write test: depth guard (>20 levels returns [])  
  _R9_
- [x] Run `pytest --cov=ttrss.feeds.categories --cov-fail-under=80`  
  _QG-1 gate_
- [x] Rule 10a adversarial self-refine — 0 traceability violations  
  _AGENTS.md Rule 10a_

**Gate:** [x] NULL/0 handling | [x] depth guard | [x] HTML eliminated | [x] pytest green

---

## Batch 2 — Feed Operations (L1-L7) **[US-3b]**

> **Story (complete):** Feed subscribe, purge, favicon, and CRUD operations.

- [x] Implement `ttrss/feeds/ops.py` — 10 feed operation functions  
  _Source: include/functions.php:1673-1738, 400-590; include/functions2.php:900-960_
- [x] Eliminate MySQL branch in purge_feed (functions.php:266-279)  
  _AR2, ADR-0003_
- [x] Wire ccache_update at purge_feed early return (R5 call site #1)  
  _Source: include/functions.php:226_
- [x] Wire ccache_update at purge_feed after deletion (R5 call site #2)  
  _Source: include/functions.php:284_
- [x] Write test: purge with various intervals  
  _Behavioral parity_
- [x] Run `pytest --cov=ttrss.feeds.ops --cov-fail-under=80`  
  _QG-1 gate_
- [x] Rule 10a adversarial self-refine — 0 traceability violations  
  _AGENTS.md Rule 10a_

**Gate:** [x] MySQL branch gone | [x] 2 ccache_update sites | [x] pytest green

---

## Batch 3 — Counters (L2-L6) **[US-3c]**

> **Story:** As a developer, I need all counter aggregation functions so that the API can return accurate unread counts for feeds, categories, virtual feeds, labels, and global state.

- [x] Implement `ttrss/feeds/counters.py` — 12 counter aggregation functions  
  _Source: include/functions.php:641-1493_
- [x] Verify getFeedArticles delegates counting to `ccache._count_feed_articles`  
  _Circular import resolution — counters imports from ccache; ccache does NOT import from counters_
- [x] Eliminate MySQL branch in getFeedArticles (functions.php:1438-1441)  
  _AR2, ADR-0003_
- [x] Verify getCategoryCounters uses ccache_find for cache miss fallback  
  _Source: include/functions.php:1101-1140_
- [x] Write test: each counter type (global, feed, category, virtual, label)  
  _Behavioral parity_
- [x] Run `pytest --cov=ttrss.feeds.counters --cov-fail-under=80`  
  _QG-1 gate_
- [x] Verify no circular import: `python -c "from ttrss.feeds import counters; from ttrss import ccache"`  
  _Exit criterion #17_
- [x] Rule 10a adversarial self-refine — 0 traceability violations  
  _AGENTS.md Rule 10a_

**Gate:** [x] no circular import | [x] MySQL branch gone | [x] pytest green

---

## Batch 4 — Article Operations + Tag Cache (L0-L5) **[US-3d]**

> **Story:** As a developer, I need article formatting, catchup operations, and tag cache management so that articles can be marked read, tagged, and rendered as dicts (not HTML).

- [x] Implement `ttrss/articles/tags.py` — 5 tag cache functions  
  _Source: include/functions2.php:1055-1098, classes/article.php:222-284_
- [x] Implement `ttrss/articles/ops.py` — 10 article operation functions  
  _Source: include/functions2.php:1198-1943, include/functions.php:1094-1237, classes/article.php_
- [x] Verify format_article returns dict (not HTML string)  
  _R13_
- [x] Wire HOOK_RENDER_ARTICLE after sanitize in format_article  
  _Source: include/functions2.php:1250_
- [x] Wire HOOK_RENDER_ARTICLE_CDM in headline list CDM mode  
  _Source: ttrss/classes/feeds.php:517_
- [x] Wire HOOK_ARTICLE_BUTTON (article footer right)  
  _Source: include/functions2.php:1360, ttrss/classes/feeds.php:723_
- [x] Wire HOOK_ARTICLE_LEFT_BUTTON (article footer left)  
  _Source: include/functions2.php:1371, ttrss/classes/feeds.php:686_
- [x] Wire HOOK_HEADLINE_TOOLBAR_BUTTON (headline toolbar)  
  _Source: ttrss/classes/feeds.php:138_
- [x] Wire ccache_update: format_article with mark_as_read=True (R5 call site #6)  
  _Source: include/functions2.php:1222_
- [x] Wire ccache_update: catchup_feed after every unread state change (R5 call site #3)  
  _Source: include/functions.php:1226_
- [x] Wire ccache_update: catchupArticlesById per distinct feed_id (R5 call site #4)  
  _Source: include/functions2.php:1051_
- [x] Wire ccache_update: catchupArticleById always (R5 call site #5)  
  _Source: classes/article.php:84_
- [x] Eliminate 4 MySQL DB_TYPE branches from catchup_feed (functions.php:1106-1125)  
  _AR2, ADR-0003_
- [x] Verify catchup_feed handles 5 WHERE branches: category, feed, virtual, label, tag  
  _Behavioral parity_
- [x] Write test: tag_cache read/write cycle  
  _Behavioral parity R8_
- [x] Write test: mark-as-read triggers ccache_update  
  _R5_
- [x] Write test: all 5 catchup_feed WHERE branches  
  _Behavioral parity_
- [x] Write test: format_article returns dict (not HTML string)  
  _R13_
- [x] Run `pytest --cov=ttrss.articles.ops --cov=ttrss.articles.tags --cov-fail-under=80`  
  _QG-1 gate_
- [x] Rule 10a adversarial self-refine — 0 traceability violations  
  _AGENTS.md Rule 10a_

**Gate:** [x] dict return | [x] 5 hooks wired | [x] 4 ccache sites | [x] pytest green

---

## Batch 5 — Article Filters (L0-L3) **[US-3e]**

> **Story (partial):** As a developer, I need filter evaluation and shared filter infrastructure so that feed ingestion can apply all 8 filter action types.

- [x] Implement `ttrss/articles/filters.py` — 8 filter functions  
  _Source: include/functions2.php:1491-2160, include/rssfuncs.php:1272-1399_
- [x] Implement all 8 filter action types: filter, catchup, mark, publish, score, tag, label, stop  
  _Source: include/rssfuncs.php filter action enum_
- [x] Use PostgreSQL `~` regex in filter_to_sql (eliminate MySQL REGEXP)  
  _AR2, ADR-0003_
- [x] Write test: each of 8 filter action types  
  _Behavioral parity_
- [x] Write test: filter rule matching for all 6 rule types (title, content, both, link, author, tag)  
  _Behavioral parity_
- [x] Run `pytest --cov=ttrss.articles.filters --cov-fail-under=80`  
  _QG-1 gate_
- [x] Rule 10a adversarial self-refine — 0 traceability violations  
  _AGENTS.md Rule 10a_

**Gate:** [x] 8 filter actions | [x] PostgreSQL regex | [x] pytest green

---

## Batch 6 — Article Search (L2-L5) **[US-3e]**

> **Story (partial):** Headline query with 16 parameters and 6 JOIN strategies.

- [x] Implement `ttrss/articles/search.py` — search_to_sql + queryFeedHeadlines  
  _Source: include/functions2.php:260-830_
- [x] Verify queryFeedHeadlines returns 6-tuple: (result, feed_title, feed_site_url, last_error, last_updated, highlight_words)  
  _Behavioral parity — matches PHP return_
- [x] Implement all 6 JOIN strategies  
  _Source: include/functions2.php — regular, category+children, virtual, label, plugin, tag_
- [x] Wire HOOK_QUERY_HEADLINES during query construction  
  _Source: include/functions2.php — hook graph edge_
- [x] Use PostgreSQL `~` regex; eliminate Sphinx/MySQL branches  
  _AR2, ADR-0003_
- [x] Write test: each of 6 JOIN strategy paths  
  _Behavioral parity R7_
- [x] Write test: search modes, view modes, offset/limit, since_id  
  _Behavioral parity_
- [x] Run `pytest --cov=ttrss.articles.search --cov-fail-under=80`  
  _QG-1 gate_
- [x] Rule 10a adversarial self-refine — 0 traceability violations  
  _AGENTS.md Rule 10a_

**Gate:** [x] 6 JOIN strategies | [x] HOOK_QUERY_HEADLINES | [x] pytest green

---

## Batch 7 — Housekeeping (L1-L3) **[US-3e]**

> **Story (partial):** Celery periodic housekeeping — expire old data, update caches.

- [x] Implement `ttrss/tasks/housekeeping.py` — 5 sub-functions ported, 1 eliminated  
  _Source: include/rssfuncs.php:1415-1430_
- [x] expire_cached_files: pathlib glob+unlink for files >7 days in CACHE_DIR  
  _Source: include/rssfuncs.php:expire_cached_files_
- [x] expire_error_log: DELETE from ttrss_error_log WHERE created_at < NOW() - INTERVAL '7 days'  
  _Source: include/rssfuncs.php:expire_error_log_
- [x] update_feedbrowser_cache: DELETE + INSERT into ttrss_feedbrowser_cache  
  _Source: include/rssfuncs.php:update_feedbrowser_cache_
- [x] cleanup_tags(days=14, limit=50000): DELETE old unused tags  
  _Source: include/rssfuncs.php:cleanup_tags_
- [x] Eliminate expire_lock_files — Celery replaces file locks (ADR-0011)  
  _AR elimination_
- [x] Import purge_orphans from feeds.ops (not duplicate it)  
  _Exit criterion #12_
- [x] Wire HOOK_HOUSE_KEEPING as last call in housekeeping task  
  _Source: include/rssfuncs.php — hook graph edge_
- [x] Register housekeeping as Celery periodic task  
  _ADR-0011_
- [x] Write test: each sub-function independently  
  _AGENTS.md test traceability rule_
- [x] Write test: expire_lock_files is NOT present  
  _Elimination verification_
- [x] Run `pytest --cov=ttrss.tasks.housekeeping --cov-fail-under=80`  
  _QG-1 gate_
- [x] Rule 10a adversarial self-refine — 0 traceability violations  
  _AGENTS.md Rule 10a_

**Gate:** [x] 5 ported | [x] lock files eliminated | [x] purge_orphans imported | [x] pytest green

---

## Batch 8 — Feed Task Article Persistence (L0-L10) **[US-3f]**

> **Story:** As a developer, I need the complete article persistence pipeline so that ingested feed entries are stored with correct GUID construction, content hashing, filter actions, tags, labels, enclosures, and N-gram deduplication.

- [x] Implement full GUID construction: get_id() → get_link() → make_guid_from_title() → owner-scoped → SHA1 → truncate 245  
  _Source: include/rssfuncs.php:550-560, 621_
- [x] Implement content_hash: `"SHA1:" + hashlib.sha1(entry_content.encode()).hexdigest()`  
  _Source: include/rssfuncs.php:707_
- [x] Implement ttrss_entries INSERT/UPDATE (new GUID → INSERT; existing → UPDATE date_updated)  
  _Source: include/rssfuncs.php:720-750, 956-962_
- [x] Implement ttrss_user_entries INSERT with filter-determined fields (unread, marked, published, score)  
  _Source: include/rssfuncs.php:887-894_
- [x] Apply all 8 filter action types via articles.filters imports  
  _Source: include/rssfuncs.php:812-828, 845-863_
- [x] Implement tag extraction: parse <category>, add manual tags, filter blacklisted, save ttrss_tags, write tag_cache  
  _Source: include/rssfuncs.php:634-648, 1062-1097_
- [x] Implement label auto-assignment (AUTO_ASSIGN_LABELS pref)  
  _Source: include/rssfuncs.php:1102-1113_
- [x] Implement enclosure INSERT deduplicated by content_url + post_id  
  _Source: include/rssfuncs.php:982-1020_
- [x] Implement N-gram dedup using PostgreSQL similarity() at _NGRAM_TITLE_DUPLICATE_THRESHOLD  
  _Source: include/rssfuncs.php:867-882_
- [x] Implement content update detection (compare content_hash, title, num_comments, plugin_data)  
  _Source: include/rssfuncs.php:923-970_
- [x] Wire ccache_update after article insert (R5 call site #7)  
  _Source: include/rssfuncs.php (post-loop)_
- [x] Write test: GUID fallback chain  
  _Behavioral parity_
- [x] Write test: each of 8 filter action outcomes  
  _Behavioral parity_
- [x] Write test: tag_cache write  
  _Behavioral parity_
- [x] Write test: enclosure dedup  
  _Behavioral parity_
- [x] Run `pytest --cov=ttrss.tasks.feed_tasks --cov-fail-under=80`  
  _QG-1 gate_
- [x] Verify grep DB_TYPE = 0, grep DATE_SUB = 0 across all Phase 3 modules  
  _Exit criterion #16_
- [x] Verify no circular imports for all Phase 3 modules  
  _Exit criterion #17_
- [x] Rule 10a adversarial self-refine — 0 traceability violations  
  _AGENTS.md Rule 10a_

**Gate:** [x] 10 persistence steps | [x] 8 filter actions | [x] ccache call site #7 | [x] pytest green

---

## Summary

| Batch | Description | Tasks | Completed | Gate |
|-------|-------------|-------|-----------|------|
| Pre | Model verification | 1 | 1 | PASSED |
| 0 | Counter cache + Labels + Feed IDs | 13 | 13 | PASSED 2026-04-04 |
| 1 | Feed categories | 9 | 9 | PASSED 2026-04-04 |
| 2 | Feed operations | 7 | 7 | PASSED 2026-04-04 |
| 3 | Counters | 8 | 8 | PASSED 2026-04-04 |
| 4 | Article ops + tag cache | 20 | 20 | PASSED 2026-04-04 |
| 5 | Article filters | 7 | 7 | PASSED 2026-04-04 |
| 6 | Article search | 9 | 9 | PASSED 2026-04-04 |
| 7 | Housekeeping | 12 | 12 | PASSED 2026-04-04 |
| 8 | Feed task persistence | 18 | 18 | PASSED 2026-04-04 |
| **Total** | | **104** | **104** | **ALL DONE** |
