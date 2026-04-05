---
name: integration-test-plan
description: Plan for comprehensive integration tests covering all API ops, models, auth flows, and security
type: project
---

# Integration Test Plan

**Goal:** Full integration test coverage — all API endpoints, model transactions, auth flows,
and security invariants — using real Postgres + Redis (docker-compose.test.yml).

**Why:** Unit tests mock DB and API calls. Integration tests catch FK violations, session
management bugs, cascade delete issues, and auth guard failures that mocks miss.

## Batches

### I1 — Shared conftest (DONE when conftest.py written)
File: `tests/integration/conftest.py`
- `seed_prefs` (session-scoped, autouse) — seeds TtRssPrefsType(1), TtRssPrefsSection(1), TtRssPref(ENABLE_API_ACCESS=true)
- `api_user` (function-scoped) — creates TtRssUser + ENABLE_API_ACCESS user_pref, yields, deletes
- `logged_in_client` (function-scoped) — logs in api_user via POST /api/, yields client with session
- `test_feed` (function-scoped) — creates TtRssFeed for api_user
- `test_entry_pair` (function-scoped) — creates TtRssEntry + TtRssUserEntry for test_feed

### I2 — API meta ops
File: `tests/integration/test_api_meta.py` (~8 tests)
- getVersion → "1.12.0-python"
- getApiLevel → level=8
- isLoggedIn unauthenticated → status=0
- isLoggedIn authenticated → status=1
- logout → session cleared
- NOT_LOGGED_IN guard on getFeeds
- seq echo
- UNKNOWN_METHOD echo

### I3 — API counters & prefs
File: `tests/integration/test_api_counters.py` (~12 tests)
- getUnread global (empty DB)
- getUnread by feed
- getUnread by category
- getCounters (empty)
- getPref known pref (ENABLE_API_ACCESS)
- getPref unknown pref
- getConfig
- getLabels empty
- getLabels after label insert
- API_DISABLED enforcement

### I4 — API feed operations
File: `tests/integration/test_api_feeds.py` (~15 tests)
- getFeeds empty → []
- getFeeds after subscribe
- getCategories empty
- subscribeToFeed new URL
- subscribeToFeed duplicate (idempotent)
- unsubscribeFeed existing
- unsubscribeFeed missing feed
- getFeedTree empty
- getFeedTree with feeds + categories
- updateFeed (change title)

### I5 — API article operations
File: `tests/integration/test_api_articles.py` (~18 tests)
- getHeadlines empty
- getHeadlines with entry (default feed)
- getHeadlines with is_cat
- getArticle by id
- getArticle missing → error
- updateArticle mark read (field=2)
- updateArticle mark starred (field=0)
- updateArticle mark published (field=1)
- updateArticle set note (field=4)
- catchupFeed all articles
- setArticleLabel add
- setArticleLabel remove
- shareToPublished

### I6 — Model-level transactions
File: `tests/integration/test_models.py` (~20 tests)
- TtRssUser CRUD
- TtRssFeed FK owner_uid cascade
- TtRssEntry GUID uniqueness constraint
- TtRssUserEntry state transitions (marked/published/unread/note)
- TtRssFeedCategory self-referential FK
- TtRssLabel2 CRUD
- User cascade delete → feed + entry deleted
- Feed cascade delete → user_entry deleted
- TtRssUserPref isolation between users
- TtRssPluginStorage CRUD

### I7 — Auth flow end-to-end
File: `tests/integration/test_auth_flow.py` (~10 tests)
- Full login/logout/login cycle
- Session persistence across requests
- Wrong password → LOGIN_ERROR
- API_DISABLED for user without pref
- SHA1 password upgrade to argon2id on login
- Base64 password fallback

### I8 — Security invariants
File: `tests/integration/test_security.py` (~10 tests)
- pwd_hash never in any API response
- session does not contain pwd_hash
- NOT_LOGGED_IN on all guarded ops
- seq always echoed correctly
- API errors don't expose tracebacks
- Different users cannot read each other's articles

## Totals

| File | Tests |
|------|-------|
| conftest.py | fixtures only |
| test_api_login.py | 7 (existing, updated) |
| test_api_meta.py | 8 |
| test_api_counters.py | 12 |
| test_api_feeds.py | 15 |
| test_api_articles.py | 18 |
| test_models.py | 20 |
| test_auth_flow.py | 10 |
| test_security.py | 10 |
| **Total** | **~100** |

## Status

- [x] Plan written
- [x] I1 conftest.py — seed_prefs, api_user, logged_in_client, test_feed, test_entry_pair
- [x] I2 test_api_meta.py — 8 tests
- [x] I3 test_api_counters.py — 12 tests
- [x] I4 test_api_feeds.py — 15 tests
- [x] I5 test_api_articles.py — 18 tests
- [x] I6 test_models.py — 20 tests
- [x] I7 test_auth_flow.py — 10 tests
- [x] I8 test_security.py — 10 tests (incl. 19-op parametrize)
- [x] Update test_api_login.py — seed_prefs dependency added

**Total collected: 115 tests** (pytest --collect-only confirms)
