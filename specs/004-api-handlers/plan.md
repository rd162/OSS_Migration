---
id: 004
title: Phase 4 Implementation Plan — Flask API Blueprint Completion
status: done
selection: Condorcet 2-0 (Solution B beats A and C on R15 getFeedTree specificity)
date: 2026-04-04
---

# Plan 004 — Flask API Blueprint Completion

## Constitution Check

| Constraint | Satisfied |
|------------|-----------|
| ADR-0006: ORM/Core only, no raw SQL | Yes — all queries use SQLAlchemy |
| ADR-0003: No DB_TYPE branches | Yes — PostgreSQL only |
| ADR-0009: Encrypted feed credentials | N/A — read path only |
| Source traceability on every callable | Yes — `# Source: ttrss/classes/api.php` on all |

## Technical Context

- Target file: `ttrss/blueprints/api/views.py`
- All ops extend `dispatch()` via `if op == "..."` branches — no new routes
- 17 remaining ops covered in 5 dependency-topology batches

## Batch Structure

### Batch 1 — Auth gate + counter-only ops (6 ops)

Auth guard (Source: ttrss/classes/api.php:12-31):
- Guard 1 (line 16): not-logged-in check; exempts `{"login", "isloggedin"}` ONLY
- Guard 2 (line 21): ENABLE_API_ACCESS pref check; exempts `{"logout"}` ONLY
- getVersion and getApiLevel are NOT exempt from Guard 2
- Implementation: inline guards at top of dispatch() before op routing

Ops: `getUnread`, `getCounters`, `getPref`, `getConfig`, `getLabels`

### Batch 2 — Query ops with category/feed deps (3 ops)

Ops: `getCategories`, `getFeeds`, `getArticle`

Key constraint: getFeeds include_nested requires `if include_nested and cat_id` — cat_id=0 is falsy.
N+1 in real feeds loop accepted as PHP-parity trade-off; documented with Source comment.

### Batch 3 — Write ops (4 ops)

Ops: `updateArticle`, `catchupFeed`, `setArticleLabel`, `updateFeed`

FIELD_MAP = {0:(marked,last_marked), 1:(published,last_published), 2:(unread,last_read), 3:(note,None)}.
ccache_update only when num_updated>0 AND field==2 (unread), per distinct feed_id.

### Batch 4 — Complex chained ops (4 ops)

Ops: `getHeadlines`, `subscribeToFeed`, `unsubscribeFeed`, `shareToPublished`

shareToPublished: `TtRssUserEntry(feed_id=None, ...)` — NOT -2 (R16).

### Batch 5 — getFeedTree (1 op, standalone)

Output structure (Source: pref/feeds.php:291-292, 123):
- Prefixed IDs: `CAT:{id}` and `FEED:{id}`
- `bare_id` (int), `auxcounter=0`
- Virtual feeds in exact order: `[-4,-3,-1,-2,0,-6]`
- Envelope: `{"identifier":"id","label":"name","items":[...]}`
- BFS with `MAX_CATEGORY_DEPTH=20` + visited set for cycle detection

## Per-Batch Gates

1. Source traceability comment on every callable
2. `pytest --cov=ttrss --cov-fail-under=80`
3. Rule 10a adversarial self-refine (CRITIC/AUTHOR, max 3 rounds, stop on CONVERGE/DEFENSE)

## Outcome

Phase 4 complete. All 17 ops routed. All 17 exit-gate criteria passed.
