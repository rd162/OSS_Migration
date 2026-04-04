---
name: coverage_gap_plan
description: Full coverage gap resolution plan — 6 workstreams to close all PHP-to-Python translation gaps identified by 2026-04-04 audit
type: project
---

# Coverage Gap Resolution Plan

**Created:** 2026-04-04
**Trigger:** Full coverage audit found 58% function-level coverage across 415 audited functions. 23/73 app PHP files have no traceability in target.

## Workstream Overview

| WS | Name | Files | Functions | Lines | Priority |
|----|------|-------|-----------|-------|----------|
| 1 | Traceability comments for library-replaced files | 16 | — | ~50 comments | Equal |
| 2 | Missing business logic translation | 4 | 17 | ~1,034 | Equal |
| 3 | Pref CRUD operations | 6 | 84 | ~4,500 | Equal |
| 4 | handler/public.php endpoints | 1 | 11 | ~600 | Equal |
| 5 | PluginHost advanced features | 1 | 25 | ~200 | Equal |
| 6 | Partial-coverage functions (add traceability) | ~15 | 35 | ~35 comments | Equal |

---

## WS-1: Traceability Comments for Library-Replaced Files

Add `# Inferred from:` or `# New:` comments to Python files that replace PHP files via ecosystem libraries. No code changes — only comments.

| PHP File | Python Equivalent | Comment Location |
|----------|------------------|-----------------|
| `classes/idb.php` | `extensions.py` (SQLAlchemy) | ADR-0006 ref |
| `classes/db/pgsql.php` | `extensions.py` | ADR-0006 ref |
| `classes/db/mysql.php` | N/A — dropped | `config.py` note |
| `classes/db/mysqli.php` | N/A — dropped | `config.py` note |
| `classes/db/pdo.php` | `extensions.py` | ADR-0006 ref |
| `classes/db/stmt.php` | SQLAlchemy Result | `models/base.py` |
| `classes/feedparser.php` | feedparser lib | `tasks/feed_tasks.py` |
| `classes/feeditem.php` | feedparser lib | `tasks/feed_tasks.py` |
| `classes/feeditem/common.php` | feedparser lib | `tasks/feed_tasks.py` |
| `classes/feeditem/atom.php` | feedparser lib | `tasks/feed_tasks.py` |
| `classes/feeditem/rss.php` | feedparser lib | `tasks/feed_tasks.py` |
| `classes/handler.php` | Flask Blueprint | `blueprints/__init__.py` |
| `classes/ihandler.php` | Flask Blueprint | `blueprints/__init__.py` |
| `classes/iauthmodule.php` | pluggy hookspec | `plugins/hookspecs.py` |
| `include/errorhandler.php` | structlog | `__init__.py` |
| `include/sanity_config.php` | `config.py` | inline |

---

## WS-2: Missing Business Logic Translation

| PHP File | Lines | Target Module | Key Functions |
|----------|-------|---------------|---------------|
| `register.php` | 368 | `ttrss/blueprints/public/views.py` + `ttrss/auth/register.py` | checkUsername, validateRegForm, registration flow |
| `image.php` | 54 | `ttrss/blueprints/public/views.py` (image proxy route) | Cached image proxy with security URL rewriting |
| `include/colors.php` | 351 | `ttrss/utils/colors.py` | 11 color functions for feed icons |
| `include/login_form.php` | 261 | `ttrss/blueprints/public/views.py` + Jinja2 template | Login form with CSRF, mobile detect, i18n |

---

## WS-3: Pref CRUD Operations (84 missing functions)

Implement in `ttrss/blueprints/prefs/` sub-modules + `ttrss/prefs/` ops layer:

| PHP Class | Missing Ops | Target Module |
|-----------|------------|---------------|
| `pref/feeds.php` (32) | editfeed, batchEditSave, savefeedorder, removeicon, uploadicon, categorize, removeCat, addCat, regenOPMLKey, regenFeedKey, renamecat, catsortreset, feedsortreset, editfeeds, editsaveops, resetPubSub, remove, clear, rescore, rescoreAll, batchSubscribe, batchAddFeeds, inactiveFeeds, feedsWithErrors, etc. | `blueprints/prefs/feeds.py` + `feeds/ops.py` |
| `pref/filters.php` (19) | testFilter, editSave, add, remove, newfilter, newrule, newaction, filtersortreset, savefilterorder, getfiltertree, edit, join, printRuleName, printActionName, etc. | `blueprints/prefs/filters.py` + `articles/filters.py` |
| `pref/prefs.php` (17) | changepassword, saveconfig, changeemail, otpenable, otpdisable, setplugins, clearplugindata, customizeCSS, editPrefProfiles, resetconfig, toggleAdvanced, otpqrcode, getHelp | `blueprints/prefs/user_prefs.py` + `prefs/ops.py` |
| `pref/labels.php` (7) | colorset, colorreset, save, remove, add, edit, getlabeltree | `blueprints/prefs/labels.py` + `labels.py` |
| `pref/users.php` (7) | resetUserPassword, resetPass, add, remove, edit, userdetails, before | `blueprints/prefs/users.py` |
| `pref/system.php` (2) | clearLog, before | `blueprints/prefs/system.py` |

---

## WS-4: handler/public.php Endpoints (11 missing)

Implement in `ttrss/blueprints/public/views.py`:

| Method | Purpose | Dependencies |
|--------|---------|-------------|
| login | Login form POST handler | auth/authenticate.py |
| logout | Session destroy | Flask-Login |
| getUnread | Public unread count | feeds/counters.py |
| getProfiles | Profile list | models/pref.py |
| pubsub | PubSubHubbub callback | httpx (ADR-0015) |
| share | Share article to published | articles/ops.py |
| sharepopup | Share popup HTML | Jinja2 template |
| subscribe | Public subscribe handler | feeds/ops.py |
| forgotpass | Password reset | auth/password.py + utils/mail.py |
| dbupdate | Trigger DB schema update | alembic |
| confirmOP | Email confirmation handler | models/user.py |

---

## WS-5: PluginHost Advanced Features (25 missing)

Implement in `ttrss/plugins/manager.py`:

| Category | Functions |
|----------|----------|
| API method registration | add_api_method, get_api_method |
| Command registration | add_command, del_command, run_commands, lookup_command, get_commands |
| Handler registration | add_handler, del_handler, lookup_handler |
| Feed handler | add_feed, get_feeds, get_feed_handler, feed_to_pfeed_id, pfeed_to_feed_id |
| Hook management | del_hook, get_hooks, get_all |
| Data persistence | save_data, clear_data |
| Utility | set_debug, get_debug, get_link |

---

## WS-6: Partial-Coverage Functions (add traceability)

Add `# Source:` comments to ~35 functions that exist in Python but lack traceability:

Key targets: `_debug` → logging, `file_is_locked`, `sanity_check`, `sql_bool_to_bool`, `truncate_string`, `label_to_feed_id`, `feed_to_label_id`, `cleanup_tags`, plus ~27 more across modules.

---

## Execution Order

All workstreams are equal priority. Execution batches by natural dependency:

**Batch A (no deps, can parallelize):** WS-1, WS-6, WS-2 (colors.py, image.py)
**Batch B:** WS-2 (register.py, login_form), WS-4 (handler/public endpoints)
**Batch C:** WS-3 (pref CRUD — largest), WS-5 (plugin advanced)

---

## Execution Status (2026-04-04)

| WS | Status | Changes |
|----|--------|---------|
| 1 | **DONE** | 16 files now have Inferred-from/Eliminated comments (7 target files edited) |
| 2 | **DONE** | colors.py (new, 10 funcs), image proxy route, register.py (new, 4 funcs), login route |
| 3 | **DONE** | 52 new CRUD routes across 6 pref blueprint files (+2,886 lines) |
| 4 | **DONE** | 11 new public endpoints in views.py (+936 lines) |
| 5 | **DONE** | 24 new PluginHost methods in manager.py (+470 lines) |
| 6 | **DONE** | Merged into WS-1 (traceability comments added inline) |

**Result:** 73/73 application PHP files now have traceability in target. 1,266 total traceability comments across 85 Python files. 4,275 lines added, 16 files changed. All files pass syntax check.

---

## Phase 5b — Exact Function Audit (2026-04-05)

File-level traceability was insufficient. A tree-sitter-based exact function audit (`tools/graph_analysis/exact_function_audit.py`) was written and run, verifying each of the 458 in-scope PHP functions individually.

**Audit results (final — commit c42c599):**

| Metric | Count |
|--------|-------|
| In-scope PHP functions (L0-L10) | 458 |
| Exactly traced (name or line-range ref) | 288 |
| Eliminated by spec/ADR | 170 |
| File-level only | **0** |
| Missing | **0** |
| **Coverage** | **100.0%** |

**Workstreams closed:**
- **Category C (13 new implementations):** `labels_contains_caption`, `assign_article_to_label_filters`, `get_plugin_names/get_plugins/get_plugin`, `remove_feed_icon`, `reset_pubsub`, `regen_opml_key`, `regen_feed_key`, `clear_access_keys`, `set_plugins`, `_article_complete_tags`, `_article_assign_to_label`, `_article_remove_from_label`
- **Category A (25 Source comment fixes):** exact function-name Source comments added across 13 Python files
- **Category B (20 Eliminated comments):** `editfeeds`, `batch_edit_cbox`, `newrule`, `newaction`, `customizeCSS`, `toggleAdvanced`, `getHelp`, `get_dbh`, `run_hooks`, `load_all`, session handlers, PHP URL helpers, etc.
- 598 tests pass.
