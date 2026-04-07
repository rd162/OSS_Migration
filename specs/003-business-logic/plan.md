# Plan 003 — Business Logic

**Status:** DONE  
**Completed:** 2026-04-04  
**Spec ref:** specs/003-business-logic/spec.md  
**Method:** Adversarial thinking pipeline — 3 candidates, critique+author round, 3-voter Condorcet. Solution A (Strict Dependency Leaves-Up) won 2-0.

---

## Constitution Check

*Gate: Must pass before implementation begins. Pre-batch model verification is a hard prerequisite.*

| Principle | Requirement | Satisfied |
|-----------|-------------|-----------|
| P1 Library-First | Leaf modules (ccache, labels, utils/feeds) are standalone; counters does not import from ccache (circular import prevention) | ✓ — verified at each batch gate |
| P2 Test-First | Per-batch `pytest --cov-fail-under=80`; no batch committed without passing tests | ✓ — 9 batch gates all passed |
| P3 Source Traceability | Every callable has `# Source:` comment; pre-batch model verification against DDL | ✓ — Rule 10a per batch |
| P5 Behavioral Parity | ID conversion functions are strict inverses; ccache_find has no TTL check; format_article returns dict not HTML | ✓ — 18 exit criteria |
| Law 4 PostgreSQL Only | `grep DB_TYPE = 0`, `grep DATE_SUB = 0` at phase exit | ✓ — exit criterion #16 |
| Law 5 No Server HTML | `print_feed_cat_select`, `print_feed_select` eliminated | ✓ — AR9 enforced |

---

## Technical Context

### Why Solution A Won

Strict dependency leaves-up ordering — leaf modules (ccache, labels, utils/feeds) built first, each batch independently correct at commit time. Solution B used 7 batches with a DAG-first approach; lost because it created temporal coupling between batches that made partial failures harder to diagnose.

### Pre-Batch Gate

Before Batch 0: one-time model verification of all 31 SQLAlchemy models against `ttrss_schema_pgsql.sql`. Flag missing columns, wrong types, phantom defaults. Required because business logic depends on exact column names.

### Graph Level Annotations

Per-batch topological levels from `tools/graph_analysis/output/function_levels.json`:

| Batch | Modules | Graph Levels | DB_TABLE Communities |
|-------|---------|-------------|---------------------|
| 0 | utils/feeds.py, ccache.py, labels.py | L0-L4 | [3] Counters+Prefs, [0] Feed/API |
| 1 | feeds/categories.py | L2-L3 | [0] Feed/API |
| 2 | feeds/ops.py | L1-L7 | [5] Feeds/Users |
| 3 | feeds/counters.py | L2-L6 | [3] Counters+Prefs |
| 4 | articles/ops.py + articles/tags.py | L0-L5 | [4] Articles/Tags |
| 5 | articles/filters.py | L0-L3 | [2] Filters |
| 6 | articles/search.py | L2-L5 | [4] Articles/Tags |
| 7 | tasks/housekeeping.py | L1-L3 | [1] Auth/System |
| 8 | tasks/feed_tasks.py (article persistence) | L0-L10 | [4] Articles/Tags |

---

## Batch Dependency Graph

```
Batch 0: ccache + labels + utils/feeds  (leaf modules, no deps)
    |
    v
Batch 1: feeds/categories  (no Batch 0 deps, parallel-safe)
    |
    v
Batch 2: feeds/ops  (imports: ccache)
    |
    v
Batch 3: feeds/counters  (imports: ccache, labels, utils/feeds)
    |
    v
Batch 4: articles/ops + articles/tags  (imports: ccache, labels, feeds/categories, articles/sanitize)
    |
    v
Batch 5: articles/filters  (imports: feeds/categories, labels)
    |
    v
Batch 6: articles/search  (imports: articles/filters, feeds/categories, utils/feeds)
    |
    v
Batch 7: tasks/housekeeping  (imports: feeds/ops, ccache)
    |
    v
Batch 8: tasks/feed_tasks  (imports: articles/filters, labels, articles/tags, ccache)
```

---

## Batch 0 — Counter Cache + Labels + Feed ID Utilities

**Goal:** Leaf modules with no upstream deps. Foundation for all subsequent batches.

**Key implementation decisions:**

- `ccache_update_all` uses bulk GROUP BY query (not N+1 loop) — eliminates AR3
- `ccache_find` does NOT check TTL — dead code in PHP (R12)
- `_count_feed_articles` inlined in ccache.py (not exposed via counters.py) — avoids circular import (R18)
- `_count_feed_articles` handles all virtual feed types: regular (>=0), starred (-1), published (-2), fresh (-3), all (-4), recently-read (-6), label (<LABEL_BASE_INDEX)
- label_cache JSON format: `[[-1026, "caption", "#fg", "#bg"], ...]` or `{"no-labels": 1}` (R8)
- ID conversion functions are strict inverses: `label_to_feed_id` ↔ `feed_to_label_id`, `pfeed_to_feed_id` ↔ `feed_to_pfeed_id`

**Boundary test values:** -128 (PLUGIN_FEED_BASE_INDEX), -1024 (LABEL_BASE_INDEX), -1025 (first label feed)

---

## Batch 1 — Feed Categories

**Key implementation decisions:**

- Category 0 = uncategorized (PHP `NULL` → Python `0`) throughout all functions
- `getChildCategories(cat_id=0)` returns `[]` matching PHP behavior
- Depth guard: `MAX_CATEGORY_DEPTH=20` on both `getParentCategories` and `getChildCategories`
- Eliminated: `print_feed_cat_select()`, `print_feed_select()` — server-rendered HTML (R13, AR9)

---

## Batch 2 — Feed Operations

**Key implementation decisions:**

- `purge_feed`: PostgreSQL only — MySQL branch (functions.php:266-279) eliminated
- ccache_update called at 2 points in purge_feed: early return AND after deletion (R5 call sites #1, #2)
- `subscribe_to_feed` handles URL normalization and duplicate detection

---

## Batch 3 — Counters

**Key implementation decisions:**

- `getFeedArticles` is the public API for article count; delegates to `ccache._count_feed_articles` for actual counting
- Circular import resolution: counters imports from ccache; ccache does NOT import from counters
- `getCategoryCounters` uses `ccache_find` for cache miss fallback
- PostgreSQL only: eliminate MySQL branch in `getFeedArticles` (functions.php:1438-1441)

---

## Batch 4 — Article Operations + Tag Cache

**Key implementation decisions:**

- `format_article` returns dict (not HTML string) — R13
- All ccache_update call sites in this module wired (R5 call sites #3, #4, #5, #6)
- `catchup_feed`: PostgreSQL only — eliminate 4 DB_TYPE branches (functions.php:1106-1125)
- `catchup_feed` handles 5 WHERE branches: category, feed, virtual, label, tag
- 5 hooks wired: HOOK_RENDER_ARTICLE, HOOK_RENDER_ARTICLE_CDM, HOOK_ARTICLE_BUTTON, HOOK_ARTICLE_LEFT_BUTTON, HOOK_HEADLINE_TOOLBAR_BUTTON

---

## Batch 5 — Article Filters (Shared Infrastructure)

**Key implementation decisions:**

- Extracted as shared module — used by BOTH queryFeedHeadlines (Batch 6) AND feed_tasks.py (Batch 8)
- `filter_to_sql`: PostgreSQL regex `~` only — eliminate MySQL REGEXP (AR2)
- All 8 filter action types implemented: filter, catchup, mark, publish, score, tag, label, stop

---

## Batch 6 — Article Search (queryFeedHeadlines)

**Key implementation decisions:**

- Isolated per R7: ~430 lines, 16 parameters, 6 JOIN strategies — own batch
- Returns 6-tuple: `(result, feed_title, feed_site_url, last_error, last_updated, highlight_words)`
- 6 JOIN strategies: regular feed, category+children, special virtual (-1 to -6), label feeds, plugin feeds, tag feeds
- HOOK_QUERY_HEADLINES fires during query construction
- PostgreSQL only: uses `~` regex, eliminates Sphinx/MySQL branches

---

## Batch 7 — Housekeeping

**Key implementation decisions:**

- `expire_lock_files` eliminated — Celery replaces file locks (ADR-0011)
- `purge_orphans` imported from feeds.ops (not duplicated)
- All sub-functions registered as Celery periodic task
- HOOK_HOUSE_KEEPING fires last

| PHP Sub-Function | Python Mapping |
|-----------------|---------------|
| expire_cached_files | Ported — pathlib glob+unlink for files >7 days |
| expire_lock_files | Eliminated — Celery replaces file locks |
| expire_error_log | Ported — DELETE from ttrss_error_log |
| update_feedbrowser_cache | Ported — DELETE + INSERT into ttrss_feedbrowser_cache |
| purge_orphans | Imported from feeds.ops |
| cleanup_tags | Ported — DELETE old unused tags |
| HOOK_HOUSE_KEEPING | Hook — fires last |

---

## Batch 8 — Feed Task Article Persistence

**Key implementation decisions:**

- GUID construction: fallback chain → `get_id()` → `get_link()` → `make_guid_from_title()` → owner-scoped → SHA1 hashed → truncated to 245 chars
- Content hash: `"SHA1:" + hashlib.sha1(entry_content.encode()).hexdigest()`
- All 8 filter action types applied via `articles.filters` imports
- Tag extraction: parse `<category>`, add manual tags, filter blacklisted, save to ttrss_tags, write tag_cache column
- N-gram dedup: PostgreSQL `similarity()` function at `_NGRAM_TITLE_DUPLICATE_THRESHOLD`
- Enclosures deduplicated by `content_url + post_id`
- ccache_update called after article insert (R5 call site #7)

---

## Graph Gate: All 5 Dimensions Per Batch

After each batch, run `validate_coverage.py` and verify:

1. **Call dimension:** All functions at declared graph level; all callees at lower levels exist
2. **DB_TABLE dimension:** Every table accessed in PHP has model import in Python
3. **Hook dimension:** Hook invocations match hook graph edges
4. **Import dimension:** Python import chain matches call graph cross-module edges
5. **Class dimension:** No new class hierarchies (all Phase 3 modules are function modules)

---

## MySQL Branches Eliminated

| Location | PHP Lines | Branch |
|----------|----------|--------|
| getFeedArticles | functions.php:1438-1441 | DATE_SUB for Fresh interval |
| catchup_feed | functions.php:1106-1125 | 4 mode branches with DATE_SUB |
| purge_feed | functions.php:266-279 | DELETE syntax |
| ccache_find | ccache.php:74-76 | Dead code (TTL, excluded) |
| filter_to_sql | functions2.php:2085-2088 | REGEXP vs ~ |

---

## Status: DONE

All 9 batches committed. 12 test files committed. 18 exit criteria met. Graph gates passed. Hooks wired 2026-04-04.
