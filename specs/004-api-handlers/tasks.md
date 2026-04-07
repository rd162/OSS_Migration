---
id: 004
title: Phase 4 Tasks — Flask API Blueprint Completion
status: done
---

# Tasks 004 — Flask API Blueprint Completion

All tasks DONE. Phase 4 exit gate (17 criteria) passed.

## Batch 1 — Auth gate + counter-only ops **[US-001, US-002, US-003]**

- [x] Implement two-guard auth decorator at top of dispatch()
  - Guard 1 (not-logged-in): exempts `{"login", "isloggedin"}` only
  - Guard 2 (ENABLE_API_ACCESS): exempts `{"logout"}` only
  - getVersion/getApiLevel NOT exempt from Guard 2
- [x] `getUnread` — getFeedUnread(feed_id, is_cat) or getGlobalUnread() `# Source: api.php:102-112`
- [x] `getCounters` — getAllCounters() `# Source: api.php:114-168`
- [x] `getPref` — get_user_pref(current_user.id, pref_name) `# Source: api.php:409-411`
- [x] `getConfig` — icons_dir/url from config; daemon via Celery inspect ping; num_feeds COUNT `# Source: api.php:449-490`
- [x] `getLabels` — get_all_labels() + get_article_labels only when article_id truthy `# Source: api.php:412-447`
- [x] Batch 1 gate: pytest --cov-fail-under=80 passes

## Batch 2 — Query ops with category/feed deps **[US-001, US-004]**

- [x] `getCategories` — virtual cats [-2,-1,0] + getCategoryTitle + getCategoryChildrenUnread `# Source: api.php:170-231`
- [x] `getFeeds` — include_nested guard: `if include_nested and cat_id`; getFeedTitle per virtual feed; N+1 accepted with Source comment `# Source: api.php:504-629`
- [x] `getArticle` — JOIN ttrss_entries+ttrss_user_entries + enclosures + labels + HOOK_RENDER_ARTICLE_API per article `# Source: api.php:310-368`
- [x] Batch 2 gate passed

## Batch 3 — Write ops **[US-001]**

- [x] `updateArticle` — FIELD_MAP {0-3}; ccache_update only on unread (field==2) + num_updated>0 per distinct feed_id `# Source: api.php:233-308`
- [x] `catchupFeed` — catchup_feed(session, feed_id, is_cat, owner_uid) `# Source: api.php:369-407`
- [x] `setArticleLabel` — label_find_id or label_find_caption; add/remove per article_id `# Source: api.php:492-501`
- [x] `updateFeed` — ownership check + update_feed.delay(feed_id)
- [x] Batch 3 gate passed

## Batch 4 — Complex chained ops **[US-001, US-005]**

- [x] `getHeadlines` — queryFeedHeadlines + HOOK_QUERY_HEADLINES + HOOK_RENDER_ARTICLE_API per row `# Source: api.php:631-720`
- [x] `subscribeToFeed` — subscribe_to_feed(feed_url, category_id, login, password)
- [x] `unsubscribeFeed` — ownership check + DELETE cascade
- [x] `shareToPublished` — TtRssUserEntry(feed_id=None) NOT -2 `# Source: article.php:129-134, 155-159`
- [x] Batch 4 gate passed

## Batch 5 — getFeedTree **[US-006]**

- [x] `getFeedTree` — BFS with MAX_CATEGORY_DEPTH=20 + visited set; CAT:/FEED: prefixes; bare_id; auxcounter=0; virtual feeds [-4,-3,-1,-2,0,-6]; envelope {"identifier":"id","label":"name","items":[...]} `# Source: pref/feeds.php:291-292, 123`
- [x] Batch 5 gate passed

## Phase 4 Exit Gate (17 criteria) — ALL PASSED

- [x] All 17 new ops routed in dispatch()
- [x] Guard 1 returns LOGIN_ERROR for unauthenticated calls to non-exempt ops
- [x] Guard 2 returns API_DISABLED (except logout)
- [x] getVersion/getApiLevel blocked when ENABLE_API_ACCESS=false
- [x] getUnread correct count
- [x] getCounters all counter types
- [x] getPref correct pref value for current user
- [x] getConfig daemon_is_running uses Celery inspect
- [x] getCategories includes virtual cats with getCategoryTitle titles
- [x] getFeeds include_nested guard matches PHP (cat_id=0 → no child cats)
- [x] updateArticle FIELD_MAP correct; ccache_update only on unread changes
- [x] shareToPublished uses feed_id=None (not -2)
- [x] getHeadlines fires HOOK_RENDER_ARTICLE_API per row
- [x] getFeedTree output has CAT:/FEED: prefixes, bare_id, auxcounter=0
- [x] getFeedTree virtual feeds in order [-4,-3,-1,-2,0,-6]
- [x] getFeedTree BFS has cycle detection (visited set)
- [x] pytest --cov-fail-under=80 passes
