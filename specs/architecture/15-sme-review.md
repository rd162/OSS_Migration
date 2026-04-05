# Architecture Spec 15 — SME Review: Source PHP App Functional Inventory

**Status**: stable (reference)
**Date**: 2026-04-06
**Source**: SME demo video (ttrss_demo.mp4, 22 min, 90 scene cadres) + test scenario spreadsheet (ttrss.xlsx)

This spec captures the functional inventory observed during the SME walkthrough of the live
PHP TT-RSS application. It serves as the authoritative reference for completeness checking
against the Python migration.

---

## 1. Feed Management

### 1.1 Subscribe to Feed
- User opens Actions ▾ → "Subscribe to feed" (or clicks + in toolbar)
- Pastes feed URL (or website URL — auto-discovery attempted)
- Clicks "Subscribe"; feed appears in "Uncategorized" folder after polling interval
- Test: omgubuntu.co.uk (RSS icon URL) and xkcd.com both demonstrated
- **Python**: fully implemented (API `subscribeToFeed` + subscribe modal)

### 1.2 Organize Feeds into Categories
- Actions ▾ → Preferences → Feeds tab → Categories dropdown → "Add category"
- Dialog: enter title (e.g. "Tech", "News"), click OK
- Category folder appears in sidebar
- **Assign feed**: drag-drop feed into category folder (PHP Dojo Tree)
- Python compromise: category dropdown selector in Settings modal (ADR-0018)
- **Python**: category creation + assignment via modal (Phase 6 implementation)

### 1.3 Edit Feed
- Select feed → Actions ▾ → "Edit this feed" (or right-click context menu)
- Editable fields: title, update interval, category, display options
- Save button applies changes
- **Python**: backend `/prefs/feeds/<id>` GET/POST — Settings modal feed edit

### 1.4 Remove Feed
- Right-click feed → "Edit feed" → "Unsubscribe" button → confirm dialog
- Feed removed with all its articles
- **Python**: fully implemented (`unsubscribeFeed` API + Settings modal Remove button)

### 1.5 Star Articles
- Click ★ icon on article in reading pane
- Article appears in "Starred articles" virtual feed (-1)
- **Python**: fully implemented (`updateArticle` field=0)

### 1.6 Mark Read / Unread
- Moving through articles auto-marks them read
- Force mark: select articles → filter dropdown → "Unread"
- View mode filter shows unread/all/starred/published
- **Python**: fully implemented (view modes + `updateArticle` field=2)

---

## 2. Automatic Feed Updates

### 2.1 Background Update Process
- TTRSS uses a background daemon/cron that polls feeds at regular intervals
- Default interval: 30 minutes (configurable globally and per-feed)
- **Python**: Celery beat task (ADR-0011) — default interval configurable via env

### 2.2 Per-User Default Update Interval
- User can change default update interval (demo: 30 min → 15 min)
- Via Preferences → Feeds tab → user preference
- Setting persists per-user
- **Python**: `rpc/setpref` with key=`DEFAULT_UPDATE_INTERVAL`; Settings modal Account tab

### 2.3 Force Feed Update
- Hover over feed shows last update timestamp
- Clicking feed title triggers immediate update request
- **Python**: `updateFeed` API (triggers Celery task); Actions ▾ → "Refresh feed" button

---

## 3. Filtering & Tags

### 3.1 Manual Article Tags
- Click (+) button on article → text input for comma-separated tags
- Tags saved; click tag name to filter articles in current feed
- Actions ▾ → "Select by tag" for cross-feed tag filtering
- **Python**: `articles/tags.py::setArticleTags` — exposed via Settings modal article tag editor

### 3.2 Auto-Filters
- Preferences → Filters → "Create filter…"
- Filter components:
  - **Rule**: match against title | body | link | author | tag | title+body
  - **Regexp**: pattern to match
  - **Feed scope**: any feed, specific feed, or category
  - **Action**: add tag | mark read | delete | publish | set score | label
- Example: match "Google" in title → add tag "Tech"
- Filters apply during feed ingestion AND live article view
- **Python**: `/prefs/filters` POST/GET — Settings modal Filters tab (simplified: 1 rule + 1 action)

### 3.3 Filter Ordering
- Filters processed in order; "stop" action short-circuits remaining filters
- **Python**: filter order preserved in DB; order API `/prefs/filters/order`

---

## 4. Multi-User

### 4.1 User Creation (Admin Only)
- Preferences → Users tab → "Create user"
- Fields: username, password
- Each user gets isolated feed list, preferences, and filters
- **Python**: backend `/prefs/users` POST — admin-only; Settings modal Users tab (Phase 6)

### 4.2 Per-User Isolation
- Feeds, categories, tags, filters, labels are scoped per user
- **Python**: all DB queries filter by `owner_uid`; fully implemented

---

## 5. OPML Import/Export

### 5.1 Export
- Preferences → Feeds → "Export OPML"
- Downloads `.opml` file with all current feed subscriptions and categories
- **Python**: `dlg/pubopmlurl` returns key-authenticated URL → download; Settings modal OPML tab

### 5.2 Import
- Preferences → Feeds → "Import OPML"
- File picker → upload `.opml` file
- Feeds added instantly with their categories
- **Python**: `dlg/importopml` with file upload; Settings modal OPML tab

---

## 6. Deployment

### 6.1 Technology Stack (PHP original)
- PHP backend, PostgreSQL or MySQL database
- Docker deployment: `git clone` + `docker compose up`
- Admin account provisioned at first login
- **Python**: Flask + PostgreSQL only; Docker multi-stage (Phase 6 B3/B4)

---

## 7. Test Coverage Matrix (from ttrss.xlsx)

| # | Category | Core Module | E2E Coverage |
|---|----------|-------------|-------------|
| 1 | Feed Management (subscribe, categorize, OPML) | Feed Management | + |
| 2 | Aggregation & Display (polling, read/unread, starring) | Article Handling | needs tests |
| 3 | Navigation & UI (keyboard, mobile) | Misc | + |
| 4 | Filtering (regex, ordering, complex rules) | Article Handling | + |
| 5 | Generated Feeds (Atom/JSON, key regen) | Feed Management | + |
| 6 | Plugins & Themes | Misc | — (explicitly out of scope) |
| 7 | API Integration (JSON API) | Misc | + |
| 8 | Multi-user Settings (accounts, prefs, isolation) | User Settings | + |
| 9 | Content Processing (full-text, dedup, podcasts) | Article Handling | + |
| 10 | Search & Labeling (SQL virtual feeds) | Article Handling | + |
| 11 | Security (HTTPS, authenticated feeds) | Misc | + |
| 12 | Preferences | — | needs tests |
| 13 | Localization (i18n) | — | ADR-0013 proposed only |

### Gaps

- **Aggregation & Display** (category 2): missing E2E coverage for read/unread toggling in headlines
- **Preferences** (category 12): settings modal now implemented; E2E tests needed
- **Localization** (category 13): ADR-0013 is proposed, not implemented — out of Phase 6 scope
- **Plugins & Themes** (category 6): backend plugin system implemented; UI hooks deferred (ADR-0017)

---

## 8. User Management Test Cases (from ttrss.xlsx Sheet 3)

Detailed test coverage required for:
1. User creation (unique username, validation, empty dashboard)
2. Roles/permissions (admin vs regular user access control)
3. Authentication (login/logout, session expiry, disabled accounts, brute-force throttling)
4. Per-user isolation (feeds, categories, settings don't bleed across users)
5. Password management (reset, change, weak password rejection)
6. Deletion/deactivation (data cleanup, cascade behavior)
7. API tokens (generate, revoke, scope)
8. Security (XSS/CSRF protection, SQLi prevention, bcrypt hash storage)

**Python status**: backend fully implemented for all 8 categories;
integration tests cover auth, isolation, and security invariants.
