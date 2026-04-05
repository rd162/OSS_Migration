---
name: SME Review — TTRSS Demo (2026-04-06)
description: SME review artifacts ingested 2026-04-06: demo video transcription, test scenario spreadsheet, 90 scene cadres
type: project
---

# SME Review Knowledge (2026-04-06)

Ingested three files from SME walkthrough of the original PHP TTRSS app:

## Source Fragments

- `__FRAGMENTS__/ttrss_demo/markdown/ttrss_demo_whisper.vtt` — Whisper-tiny VTT of 22-min demo video (90 scene cadres in `images/`)
- `__FRAGMENTS__/ttrss/markdown/ttrss_markitdown.md` — Test scenarios spreadsheet (3 sheets, 7 PDF pages)
- `/Users/rd/Downloads/ttrss_demo_transcription.txt` — Manual transcription of same video (more accurate than Whisper)

## Demo Walkthrough Coverage (7 sections)

1. **Feed Management** — subscribe by URL (Actions → Subscribe to feed), organize into categories via drag-drop, edit feed title, remove feed (right-click → Edit → Unsubscribe), star articles, mark read/unread
2. **Auto Feed Updates** — background cron/daemon; default 30-min interval; configurable (demo: changed to 15 min via Preferences → System config → Save configuration); force-update by clicking feed title; hover shows last update time
3. **Filtering & Tags** — tag articles via `(+)` button (comma-separated); filter by tag name or Actions → Select by tag; create auto-filters (Preferences → Filters → Create filter) with rules + actions (auto-tag, auto-mark-read, auto-delete)
4. **Multi-User** — Preferences → Users tab → create new user; each user has isolated feeds/prefs/filters
5. **OPML Import/Export** — Preferences → Feeds → Export OPML (save .opml); Import OPML (choose file, upload); feeds added instantly
6. **Deployment** — PHP + PostgreSQL/MySQL; Docker via `git clone` + `docker compose up`; demo shows live install from scratch (~8 min)

## Test Scenario Spreadsheet (ttrss.xlsx) — 13 Categories

| # | Category | Core Module | Coverage |
|---|----------|------------|---------|
| 1 | Feed Management (subscribe, categorize, OPML) | Feed Management | + |
| 2 | Aggregation & Display (polling, read/unread, starring) | Article Handling | **MISSING** |
| 3 | Navigation & UI (keyboard, mobile) | Misc | + |
| 4 | Filtering (regex, ordering, complex rules) | Article Handling | + |
| 5 | Generated Feeds (Atom/JSON export, key regen) | Feed Management | + |
| 6 | Plugins & Themes | Misc | **-** (explicitly not covered) |
| 7 | API Integration (JSON API) | Misc | + |
| 8 | Multi-user Settings (accounts, prefs, isolation) | User Settings | + |
| 9 | Content Processing (full-text, dedup, podcasts) | Article Handling | + |
| 10 | Search & Labeling (SQL virtual feeds) | Article Handling | + |
| 11 | Security (HTTPS, authenticated feeds) | Misc | + |
| 12 | Preferences | — | **no test cases** |
| 13 | Localization | — | **no test cases** |

**User Management** (Sheet 3) — 8 detailed test areas: creation, roles/permissions, auth (incl. brute-force throttling), per-user isolation, password management, deletion/deactivation, API tokens, security (XSS/CSRF/SQLi input sanitization).

## Key Gaps vs Current Implementation

**Why:** These gaps from the SME review matrix identify areas needing attention in Phase 6 or follow-on work.
**How to apply:** When planning test coverage or deployment validation, prioritize these uncovered areas.

- **Aggregation & Display** — no `+` in coverage matrix; auto-polling, read/unread toggling, starring/publishing
- **Plugins & Themes** — explicitly `-`; pluggy system is implemented but SME didn't cover it
- **Preferences** — listed as category but no test cases written
- **Localization/i18n** — ADR-0013 is only "proposed"; no test cases
- **Generated Feeds** — Atom/JSON public feeds with key regeneration; access key invalidation
- **Podcast enclosures** — feed enclosure inline playback
- **Brute-force protection** — login throttling after multiple failures (SME User Management sheet)
- **Feed credential encryption** (Fernet per ADR-0009) — authenticated feed fetching with Basic/Digest auth
