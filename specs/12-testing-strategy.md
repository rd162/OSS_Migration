# 12 — Testing Strategy

## Purpose

This document defines the testing strategy for migrating TT-RSS from PHP to Python. Every section is actionable: a developer should know exactly what to test, how to test it, and what constitutes a pass or fail.

---

## Parity Verification Approach

Migration correctness is defined as **behavioral equivalence** between the PHP and Python implementations. Three verification methods enforce this:

1. **Contract testing** — Same JSON input to the same `backend.php` endpoint must produce the same JSON output from the Python replacement.
2. **Golden-file testing** — Capture PHP responses with a known database state, replay the same requests against Python, and diff the results field-by-field.
3. **Database state testing** — The same sequence of API calls must produce identical database state (row counts, column values, FK integrity) in both implementations.

---

## Test Categories

### 1. Unit Tests (per Python module)

Each Python module gets isolated unit tests with no external dependencies (database mocked or in-memory SQLite where schema-compatible).

#### Database Models
- CRUD operations for all 35 tables
- Foreign key cascade behavior (ON DELETE CASCADE, ON DELETE SET NULL)
- Constraint validation (NOT NULL, UNIQUE, CHECK)
- Default value population
- Index existence verification

#### Business Rules (from 11-business-rules.md)

Each business rule gets dedicated tests:

| Rule Domain | Test Cases |
|---|---|
| **Article deduplication** | GUID exact match, content hash match, N-gram similarity threshold (0.0, 0.5, 0.9, 1.0), duplicate across feeds, duplicate within same feed |
| **Filter evaluation** | AND combining, OR combining, all 6 rule types (title, content, author, tag, link, date), all 8 actions (delete, mark read, set starred, publish, set score, add label, remove label, stop), stop action halts chain, inversion flag negates match |
| **Scoring** | Threshold tests at -500 (score_low), 0 (neutral), +500 (score_high), +1000 (score_half_high), filter chain cumulative scoring, score persistence |
| **Purging** | Starred articles protected from purge, unread articles protected from purge, age-based purge (7d, 14d, 30d, 90d), FORCE_ARTICLE_PURGE override, per-feed purge interval |
| **View modes** | SQL generation for: adaptive, marked, published, unread, has_note; each with category scope, feed scope, global scope |
| **Catchup** | Modes: 1day, 1week, 2week, all; scopes: per-feed, per-category, special feeds (-1 starred, -2 published, -3 fresh, -4 all, -6 recently read) |
| **Label ID conversion** | `label_to_feed_id(N)` → `-(N + 11)`, `feed_to_label_id(N)` → `-(N) - 11`, round-trip identity for IDs 1..100 |
| **Counter cache** | Invalidation on article insert/update/delete, 15-minute TTL validity, cascading invalidation (article → feed → category → global), force-refresh path |
| **Session validation** | All 7 checks in order: session exists, not expired, IP matches (if configured), user exists, user not disabled, CSRF token valid, API access level |

#### Feed Parsing
- RSS 2.0: standard, with enclosures, with Dublin Core
- Atom 1.0: standard, with categories, with multiple links
- RDF/RSS 1.0: standard namespace handling
- Invalid XML: recovery, partial parse, error reporting
- Encoding: UTF-8, ISO-8859-1, Windows-1252, declared vs actual mismatch
- Empty feed, feed with zero items, feed with 10,000+ items

#### Search
- SQL generation for PostgreSQL full-text search
- SQL generation for MySQL LIKE fallback
- Sphinx integration (mocked): query construction, result mapping
- Query escaping and injection prevention
- Empty query, single term, multi-term, quoted phrase

#### Crypto
- `encrypt_string` / `decrypt_string` round-trip with known key
- Key derivation determinism
- Empty string, Unicode string, binary-safe
- Wrong key produces decryption failure (not garbage)

#### Config
- All 38 constants from `config.php-dist` have Python equivalents
- Validation rules from `sanity_check.php`: DB connection, schema version match, PHP/Python version check, required extensions, file permissions, data directory writability
- Override precedence: default → config file → environment variable

---

### 2. Integration Tests (endpoint-level)

These tests hit the actual Python web layer with a real (ephemeral) database.

#### backend.php Endpoint Coverage

For **each** of the ~40 `backend.php` handler methods:
- Correct request format and parameters accepted
- Authentication enforced (reject unauthenticated, reject wrong user level)
- Response JSON structure matches contract
- Database state changes verified (row inserted/updated/deleted)
- Counter cache correctly invalidated or updated
- Error responses for invalid input

#### REST API (`api/index.php` replacement)
- All 20+ API methods: login, logout, isLoggedIn, getUnread, getCounters, getFeeds, getCategories, getHeadlines, getArticle, updateArticle, getConfig, updateFeed, getPref, catchupFeed, getLabels, setArticleLabel, shareToPublished, subscribeToFeed, unsubscribeFeed, getFeedTree
- Sequence number (`seq`) pass-through
- Status codes: API_STATUS_OK (0), API_STATUS_ERR (1)
- Session ID management (sid parameter)
- Content-type negotiation

#### Public Endpoints
- RSS feed generation (`public.php?op=rss`)
- Access key validation and rejection
- OPML export (public, authenticated)
- Shared article view

#### OPML
- Import: parse OPML, create feeds and categories, handle duplicates
- Export: generate valid OPML XML, include all feeds with categories
- Round-trip: export → import into fresh DB → export again → diff must be empty

---

### 3. Contract Tests (PHP-Python parity)

#### Golden File Infrastructure

```
tests/
  golden/
    fixtures/          # DB seed SQL files
    requests/          # HTTP request definitions (JSON)
    responses_php/     # Captured PHP responses (JSON)
    responses_python/  # Captured Python responses (JSON)
    diffs/             # Auto-generated diff reports
```

#### Process

1. Seed the PHP database to a known state (from `fixtures/seed.sql`)
2. Execute each request definition against the PHP instance
3. Capture the response body → `responses_php/{endpoint}.json`
4. Seed the Python database to the identical state
5. Execute the same requests against the Python instance
6. Capture the response body → `responses_python/{endpoint}.json`
7. Run field-by-field comparison

#### Non-Deterministic Field Handling

Fields that differ between runs are compared via matchers, not exact equality:

| Field Pattern | Matcher |
|---|---|
| `timestamp`, `updated`, `last_updated` | `IsRecentTimestamp(within_seconds=5)` |
| `session_id`, `sid` | `IsNonEmptyString()` |
| `content_hash` | `IsHexString(length=40)` |
| `random_key`, `access_key` | `IsAlphanumericString(min_length=32)` |
| `version` | `MatchesRegex(r'\d+\.\d+')` |

#### Pass/Fail Criteria

- **Any** structural diff (missing field, extra field, wrong type) = **parity failure** = must fix before release.
- Value diffs on deterministic fields = **parity failure**.
- Value diffs on non-deterministic fields that pass their matcher = **pass**.

---

### 4. Database Migration Tests

- **Schema creation** — `alembic upgrade head` on an empty database produces the exact 35-table schema with all indexes, constraints, and sequences.
- **Migration up/down** — Each Alembic revision can be applied and rolled back without data loss (tested with seed data present).
- **Seed data integrity** — After migration, all seed data is queryable and FK relationships hold.
- **FK cascade behavior** — For every `ON DELETE CASCADE` relationship, deleting the parent removes children. For every `ON DELETE SET NULL`, deleting the parent nullifies the FK column.
- **Schema parity** — The Python-managed schema matches the PHP `schema/ttrss_schema_pgsql.sql` and `schema/ttrss_schema_mysql.sql` (compared via `pg_dump` / `mysqldump` diffing).

---

### 5. Performance Tests

| Metric | Target | How to Measure |
|---|---|---|
| Feed update throughput | >= 10 feeds/sec (single worker) | Benchmark `update_rss_feed()` with 100 real feeds, measure wall clock |
| Headline loading | < 200ms for 60 headlines | Time `getHeadlines` with limit=60 on a 5000-article DB |
| Counter cache hit ratio | > 90% under normal use | Log cache hits/misses over a simulated session of 50 requests |
| API login latency | < 100ms | Benchmark `login` endpoint, 100 iterations |
| Concurrent users | 20 concurrent without errors | k6 or locust load test, 20 virtual users, 5-minute run |

---

## Test Fixtures

### Minimal DB Seed
- 1 admin user (login: `admin`, password: `password`)
- 2 feeds (one RSS 2.0, one Atom 1.0) in 1 category
- 10 articles (5 per feed, mixed read/unread/starred states)
- 1 label applied to 2 articles
- 1 filter (match title containing "test", action: mark read)

### Full DB Seed
- 5 users (1 admin, 4 regular with varying access levels)
- 50 feeds across 10 categories (some nested)
- 5,000 articles with realistic distribution of states
- 10 labels with cross-feed assignments
- 15 filters with varied rule types and actions
- 3 shared articles (published with access keys)

### OPML Fixtures
- `tests/fixtures/opml_simple.xml` — 5 feeds, no categories
- `tests/fixtures/opml_nested.xml` — 20 feeds, 3 levels of nested categories
- `tests/fixtures/opml_google_reader.xml` — Google Reader export format
- `tests/fixtures/opml_invalid.xml` — Malformed XML for error handling tests

### Feed Fixtures
- `tests/fixtures/feeds/rss2_standard.xml`
- `tests/fixtures/feeds/atom1_standard.xml`
- `tests/fixtures/feeds/rdf_standard.xml`
- `tests/fixtures/feeds/encoding_iso8859.xml`
- `tests/fixtures/feeds/empty_feed.xml`
- `tests/fixtures/feeds/large_feed_10k.xml`
- `tests/fixtures/feeds/malformed.xml`

---

## Test Infrastructure

### Framework and Libraries

| Tool | Purpose |
|---|---|
| `pytest` | Test runner and assertion framework |
| `pytest-asyncio` | Async test support (if using FastAPI/Starlette) |
| `pytest-cov` | Coverage measurement and reporting |
| `Factory Boy` | Test data generation (model factories for all 35 tables) |
| `httpx.AsyncClient` | Endpoint testing for async frameworks (FastAPI) |
| `Flask test client` | Endpoint testing if using Flask |
| `responses` or `respx` | HTTP mocking for feed fetching tests |
| `freezegun` | Time-dependent test control (session expiry, purge age) |
| `docker-compose` | Ephemeral PostgreSQL/MySQL for integration tests |

### Docker Compose Test Environment

```yaml
# docker-compose.test.yml
services:
  db-postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ttrss_test
      POSTGRES_USER: ttrss_test
      POSTGRES_PASSWORD: ttrss_test
    tmpfs: /var/lib/postgresql/data  # RAM-backed for speed

  db-mysql:
    image: mysql:8.0
    environment:
      MYSQL_DATABASE: ttrss_test
      MYSQL_USER: ttrss_test
      MYSQL_PASSWORD: ttrss_test
      MYSQL_ROOT_PASSWORD: root
    tmpfs: /var/lib/mysql

  php-golden:
    build: ./source-repos
    depends_on: [db-postgres]
    # Used to capture golden-file responses from PHP
```

### Coverage Target

**Hard constraint (C12 from project charter): 80% line coverage minimum.**

- Enforced in CI via `pytest --cov --cov-fail-under=80`
- Per-module coverage tracked; no module below 70%
- Coverage reports published as CI artifacts

### CI Pipeline Integration

```
test:unit        → runs on every push, < 60 seconds
test:integration → runs on every push, < 5 minutes (ephemeral DB)
test:contract    → runs on PR to main, < 10 minutes (PHP + Python)
test:performance → runs nightly, results tracked over time
test:migration   → runs on any change to alembic/ or models/
```

---

## Parity Testing Workflow

Step-by-step process for verifying PHP-to-Python behavioral equivalence:

```
Step 1: Set up PHP instance with known DB state
        $ docker-compose -f docker-compose.test.yml up php-golden db-postgres
        $ psql -f tests/golden/fixtures/seed.sql

Step 2: Run each endpoint against PHP, capture responses
        $ python tests/golden/capture.py --target=php --output=tests/golden/responses_php/

Step 3: Set up Python instance with same DB state
        $ docker-compose -f docker-compose.test.yml up app-python db-postgres
        $ psql -f tests/golden/fixtures/seed.sql

Step 4: Run same endpoints against Python, capture responses
        $ python tests/golden/capture.py --target=python --output=tests/golden/responses_python/

Step 5: Diff responses field-by-field (ignoring non-deterministic fields)
        $ python tests/golden/compare.py \
            --expected=tests/golden/responses_php/ \
            --actual=tests/golden/responses_python/ \
            --matchers=tests/golden/matchers.json \
            --report=tests/golden/diffs/report.html

Step 6: Any diff = parity failure = must fix before merge
```

---

## Test Matrix — Top 20 Critical Endpoints

Every handler method maps to a row in this matrix. The top 20 most critical endpoints are listed below; the full matrix lives in `tests/TEST_MATRIX.md` (generated from this spec).

| # | Handler | Method | Auth | Key Parameters | Expected Response Shape | DB Side Effects | Golden File |
|---|---|---|---|---|---|---|---|
| 1 | `feeds` | `view` | Yes | `feed_id`, `view_mode`, `limit`, `offset`, `search` | `{headlines: [{id, title, link, updated, ...}], toolbar: {...}}` | Updates `last_viewed` | `feeds_view.json` |
| 2 | `feeds` | `quickAddFeed` | Yes | `feed_url`, `cat_id` | `{status: 0/1, message: "..."}` | Inserts into `ttrss_feeds` | `feeds_quickAddFeed.json` |
| 3 | `feeds` | `catchupAll` | Yes | (none) | `{message: "UPDATE_COUNTERS"}` | Sets `unread=false` on all articles for user | `feeds_catchupAll.json` |
| 4 | `feeds` | `renameCat` | Yes | `id`, `title` | `{value: "new_title"}` | Updates `ttrss_feed_categories.title` | `feeds_renameCat.json` |
| 5 | `feeds` | `removeCat` | Yes | `ids` | `{status: "OK"}` | Deletes category, cascades feeds to uncategorized | `feeds_removeCat.json` |
| 6 | `rpc` | `getAllCounters` | Yes | (none) | `{counters: [{id, counter, ...}]}` | None (read-only, may refresh cache) | `rpc_getAllCounters.json` |
| 7 | `rpc` | `catchupFeed` | Yes | `feed_id`, `is_cat`, `mode` | `{message: "UPDATE_COUNTERS"}` | Sets articles read per mode | `rpc_catchupFeed.json` |
| 8 | `rpc` | `updateFeedBrowser` | Yes | (none) | `{content: "html..."}` | None | `rpc_updateFeedBrowser.json` |
| 9 | `rpc` | `buttonPlugin` | Yes | `plugin`, `method` | Plugin-dependent | Plugin-dependent | `rpc_buttonPlugin.json` |
| 10 | `rpc` | `setpref` | Yes | `key`, `value` | `{status: "OK"}` | Updates `ttrss_user_prefs` | `rpc_setpref.json` |
| 11 | `article` | `view` | Yes | `id` | `{article: {id, title, content, ...}}` | None | `article_view.json` |
| 12 | `article` | `setArticleStar` | Yes | `id`, `starred` (0/1) | `{message: "OK"}` | Updates `ttrss_user_entries.marked` | `article_setArticleStar.json` |
| 13 | `article` | `setArticlePublished` | Yes | `id`, `published` (0/1) | `{message: "OK"}` | Updates `ttrss_user_entries.published` | `article_setArticlePublished.json` |
| 14 | `article` | `setScore` | Yes | `id`, `score` | `{score: N}` | Updates `ttrss_user_entries.score` | `article_setScore.json` |
| 15 | `article` | `setArticleLabel` | Yes | `article_id`, `label_id`, `assign` (0/1) | `{message: "OK"}` | Inserts/deletes `ttrss_user_labels2` | `article_setArticleLabel.json` |
| 16 | `pref-feeds` | `editfeed` | Yes | `id` | `{feed: {id, title, feed_url, ...}}` | None | `pref_feeds_editfeed.json` |
| 17 | `pref-feeds` | `savefeed` | Yes | `id`, `title`, `feed_url`, `cat_id`, ... | `{status: "OK"}` | Updates `ttrss_feeds` | `pref_feeds_savefeed.json` |
| 18 | `pref-filters` | `edit` | Yes | `id` | `{filter: {id, rules: [...], actions: [...]}}` | None | `pref_filters_edit.json` |
| 19 | `pref-filters` | `save` | Yes | `id`, `rules`, `actions`, `enabled` | `{status: "OK"}` | Inserts/updates `ttrss_filters2` + rules + actions | `pref_filters_save.json` |
| 20 | `public` | `rss` | No (key) | `key`, `feed_id`, `is_cat`, `limit` | RSS 2.0 XML | None | `public_rss.xml` |

### Per-Endpoint Test Template

Every endpoint test follows this structure:

```python
class TestFeedsView:
    """Tests for backend.php?op=feeds&method=view"""

    def test_requires_authentication(self, client):
        """Unauthenticated request returns login redirect or 403."""
        resp = client.post("/backend.php", data={"op": "feeds", "method": "view"})
        assert resp.status_code in (401, 403) or "login" in resp.text.lower()

    def test_valid_request(self, client, auth_session, seeded_db):
        """Authenticated request with valid feed_id returns headlines."""
        resp = client.post("/backend.php",
            data={"op": "feeds", "method": "view", "feed": "1"},
            cookies={"sid": auth_session})
        data = resp.json()
        assert "headlines" in data or "content" in data

    def test_matches_golden_file(self, client, auth_session, seeded_db):
        """Response matches captured PHP golden file."""
        resp = client.post("/backend.php",
            data={"op": "feeds", "method": "view", "feed": "1"},
            cookies={"sid": auth_session})
        compare_golden("feeds_view.json", resp.json())

    def test_invalid_feed_id(self, client, auth_session):
        """Non-existent feed_id returns empty or error."""
        resp = client.post("/backend.php",
            data={"op": "feeds", "method": "view", "feed": "99999"},
            cookies={"sid": auth_session})
        assert resp.status_code == 200  # PHP returns 200 with empty content

    def test_view_mode_unread(self, client, auth_session, seeded_db):
        """view_mode=unread filters to unread articles only."""
        resp = client.post("/backend.php",
            data={"op": "feeds", "method": "view", "feed": "1", "view_mode": "unread"},
            cookies={"sid": auth_session})
        # Verify all returned articles have unread=True
```

---

## Running Tests

```bash
# All unit tests
pytest tests/unit/ -v --cov=app --cov-report=html

# All integration tests (requires Docker DB)
docker-compose -f docker-compose.test.yml up -d db-postgres
pytest tests/integration/ -v --cov=app

# Contract/golden-file tests (requires both PHP and Python running)
pytest tests/golden/ -v

# Performance tests
pytest tests/performance/ -v --benchmark-enable

# Full suite with coverage enforcement
pytest --cov=app --cov-fail-under=80 --cov-report=term-missing
```

---

## Appendix: Test File Organization

```
tests/
  conftest.py              # Shared fixtures, DB session, test client
  factories.py             # Factory Boy factories for all models
  golden/
    capture.py             # Script to capture PHP/Python responses
    compare.py             # Field-by-field comparator with matchers
    matchers.json          # Non-deterministic field matcher config
    fixtures/
      seed.sql             # Known DB state for golden tests
    requests/
      *.json               # Request definitions
    responses_php/
      *.json               # Captured PHP responses
    responses_python/
      *.json               # Captured Python responses
  fixtures/
    opml_simple.xml
    opml_nested.xml
    opml_google_reader.xml
    opml_invalid.xml
    feeds/
      rss2_standard.xml
      atom1_standard.xml
      rdf_standard.xml
      encoding_iso8859.xml
      empty_feed.xml
      large_feed_10k.xml
      malformed.xml
  unit/
    test_models.py         # Database model CRUD, constraints
    test_business_rules.py # All rules from 11-business-rules.md
    test_feed_parser.py    # Feed parsing all formats
    test_search.py         # Search SQL generation
    test_crypto.py         # Encrypt/decrypt
    test_config.py         # Config loading, validation
    test_filters.py        # Filter evaluation engine
    test_labels.py         # Label ID conversion
    test_counters.py       # Counter cache logic
    test_sessions.py       # Session validation chain
    test_purge.py          # Article purging logic
  integration/
    test_feeds_endpoints.py
    test_rpc_endpoints.py
    test_article_endpoints.py
    test_pref_feeds.py
    test_pref_filters.py
    test_pref_labels.py
    test_pref_prefs.py
    test_pref_users.py
    test_api.py            # REST API (api/index.php)
    test_public.py         # Public endpoints
    test_opml.py           # OPML import/export
  migration/
    test_alembic.py        # Up/down migrations
    test_schema_parity.py  # Compare against PHP schema SQL
  performance/
    test_feed_update.py
    test_headline_loading.py
    test_counter_cache.py
    test_api_latency.py
```
