---
id: 004
title: Flask API Blueprint — API Handler Completion
status: done
phase: 4
source: memory/phase4_plan_2026-04-04.md
---

# Spec 004 — Flask API Blueprint: API Handler Completion

## User Stories

| ID | Story |
|----|-------|
| US-001 | As an API consumer, I can call all 17 TT-RSS API operations and receive PHP-identical responses |
| US-002 | As an unauthenticated caller, guard 1 rejects my request with LOGIN_ERROR for non-exempt ops |
| US-003 | As a caller when ENABLE_API_ACCESS is false, guard 2 rejects my request with API_DISABLED (getVersion/getApiLevel not exempt) |
| US-004 | As a caller using getFeeds with include_nested, child categories are included only when cat_id is truthy (cat_id=0 is falsy — PHP parity) |
| US-005 | As a caller using shareToPublished, the entry is created with feed_id=None (not -2) matching PHP source |
| US-006 | As a caller using getFeedTree, the response has CAT:/FEED: prefixes, bare_id, auxcounter=0, virtual feeds in order [-4,-3,-1,-2,0,-6], BFS with cycle detection |

## Functional Requirements

| ID | Requirement | PHP Source |
|----|-------------|------------|
| FR-001 | All 17 ops routed in dispatch() via `if op == "..."` branches — no new routes | api.php:dispatch() |
| FR-002 | Guard 1: not-logged-in check; exempts `{"login", "isloggedin"}` ONLY | api.php:12-31 |
| FR-003 | Guard 2: ENABLE_API_ACCESS check; exempts `{"logout"}` ONLY | api.php:16-31 |
| FR-004 | `getUnread`: getFeedUnread(feed_id, is_cat) or getGlobalUnread() | api.php:102-112 |
| FR-005 | `getCounters`: getAllCounters() | api.php:114-168 |
| FR-006 | `getPref`: get_user_pref(current_user.id, pref_name) | api.php:409-411 |
| FR-007 | `getConfig`: icons_dir/url from config; daemon via Celery inspect ping; num_feeds COUNT | api.php:449-490 |
| FR-008 | `getLabels`: get_all_labels() + get_article_labels only when article_id truthy | api.php:412-447 |
| FR-009 | `getCategories`: virtual cats [-2,-1,0] with getCategoryTitle + getCategoryChildrenUnread | api.php:170-231 |
| FR-010 | `getFeeds`: include_nested guard — `if include_nested and cat_id` (cat_id=0 → falsy) | api.php:504-629 |
| FR-011 | `getArticle`: JOIN ttrss_entries+ttrss_user_entries + enclosures + labels + HOOK_RENDER_ARTICLE_API per article | api.php:310-368 |
| FR-012 | `updateArticle`: FIELD_MAP {0:(marked,last_marked), 1:(published,last_published), 2:(unread,last_read), 3:(note,None)}; ccache_update only when num_updated>0 AND field==2 | api.php:233-308 |
| FR-013 | `catchupFeed`: catchup_feed(session, feed_id, is_cat, owner_uid) | api.php:369-407 |
| FR-014 | `setArticleLabel`: label_find_id or label_find_caption; label_add/remove per article_id | api.php:492-501 |
| FR-015 | `updateFeed`: ownership check + update_feed.delay(feed_id) | api.php (updateFeed) |
| FR-016 | `getHeadlines`: queryFeedHeadlines + HOOK_QUERY_HEADLINES + HOOK_RENDER_ARTICLE_API per row | api.php:631-720 |
| FR-017 | `subscribeToFeed`: subscribe_to_feed(feed_url, category_id, login, password) | api.php |
| FR-018 | `unsubscribeFeed`: ownership check + DELETE cascade | api.php |
| FR-019 | `shareToPublished`: TtRssEntry + TtRssUserEntry inserts with feed_id=None (NOT -2) | article.php:129-134, 155-159 |
| FR-020 | `getFeedTree`: BFS with MAX_CATEGORY_DEPTH=20; visited set for cycle detection; virtual feeds in order [-4,-3,-1,-2,0,-6]; prefixed IDs CAT:{id}/FEED:{id}; bare_id; auxcounter=0; envelope {"identifier":"id","label":"name","items":[...]} | pref/feeds.php:291-292, 123 |

## Implementation Invariants

- SQLAlchemy ORM/Core only (ADR-0006) — no raw SQL strings
- No MySQL/DB_TYPE branches (ADR-0003)
- `get_user_pref(current_user.id, pref_name)` for all pref lookups
- `getFeedTitle(session, i)` per virtual feed ID in getFeeds
- `getCategoryTitle(session, cat_id)` for virtual cats in getCategories
- `get_all_labels` from `ttrss.labels` (NOT `labels_get_all`)
- `get_article_labels` from `ttrss.labels` (NOT `ttrss.articles.ops`)
- N+1 in getFeeds real feeds loop: acknowledged PHP-parity trade-off with Source comment (AR5)
- getFeedTree: BFS with cycle detection via visited set, depth guard MAX_CATEGORY_DEPTH=20

## Acceptance Criteria

- [ ] All 17 new ops routed in dispatch()
- [ ] Guard 1 returns LOGIN_ERROR for unauthenticated calls to non-exempt ops
- [ ] Guard 2 returns API_DISABLED when ENABLE_API_ACCESS=false (except logout)
- [ ] getVersion/getApiLevel blocked when ENABLE_API_ACCESS=false
- [ ] getUnread returns correct count from getFeedUnread / getGlobalUnread
- [ ] getCounters returns all counter types from getAllCounters
- [ ] getPref returns correct pref value for current user
- [ ] getConfig daemon_is_running uses Celery inspect
- [ ] getCategories includes virtual cats with getCategoryTitle titles
- [ ] getFeeds include_nested guard matches PHP (cat_id=0 → no child cats)
- [ ] updateArticle FIELD_MAP correct; ccache_update only on unread changes
- [ ] shareToPublished uses feed_id=None (not -2)
- [ ] getHeadlines fires HOOK_RENDER_ARTICLE_API per row
- [ ] getFeedTree output has CAT:/FEED: prefixes, bare_id, auxcounter=0
- [ ] getFeedTree virtual feeds in order [-4,-3,-1,-2,0,-6]
- [ ] getFeedTree BFS has cycle detection (visited set)
- [ ] pytest --cov-fail-under=80 passes

## Success Criteria

- **SC-001:** All 17 API operations return responses structurally identical to the PHP implementation for the same inputs
- **SC-002:** Unauthenticated requests receive `LOGIN_ERROR` for every protected operation with no exceptions
- **SC-003:** When API access is disabled, all operations except `logout` return `API_DISABLED`
- **SC-004:** Feed tree traversal completes in bounded time regardless of category nesting depth (max 20 levels)
- **SC-005:** `shareToPublished` creates an entry visible in the Published feed without requiring a `feed_id`

## Assumptions

- The TT-RSS API contract is fixed; no extensions or deviations are permitted
- Feed tree uses BFS with a visited-set cycle guard; DFS is not acceptable
- All API responses are JSON-encoded; no HTML or plain-text responses
- `cat_id=0` is falsy in PHP and must be treated as falsy in the `getFeeds include_nested` guard

---

> **Heritage note:** This phase was implemented on `main` before the `speckit-specify` branch workflow was established. Spec content is authoritative; it was not generated via `/speckit-specify`.

## Status

**DONE** — All 17 ops implemented and verified. Phase 4 exit gate (17 criteria) passed.
