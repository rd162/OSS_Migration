---
name: semantic_verification_plan
description: COMPREHENSIVE plan for semantic PHP→Python verification — covers ALL 91 Python files, ALL 472 functions, ALL 37 model classes. Every function listed with line numbers. No omissions.
type: project
---

# Semantic Coverage Verification Plan (v2 — Complete)

**Created:** 2026-04-05  
**Revised:** 2026-04-05 (v2 — rewrote from scratch; v1 covered only ~100/472 functions)  
**Trigger:** SME review found all generated Python code incorrect — functional logic,
business rules, and non-functional requirements lost across all modules.  
**Goal:** Every Python function must be 100% semantically equivalent to its PHP source.
No approximations, no "close enough".

---

## Why v1 Was Inadequate

The v1 plan had 15 workstreams naming ~100 specific functions out of 472 total.
**Entire modules were missing:**

| Missing module | Functions | Why critical |
|---------------|-----------|-------------|
| `blueprints/public/views.py` | 14 | Login, register, pubsub, RSS, share — user-facing |
| `labels.py` | 10 | Core label CRUD — used by API, filters, articles |
| `articles/sanitize.py` | 2 (34 Source refs) | HTML sanitization — security-critical |
| `http/client.py` | 5 (35 Source refs) | URL handling — feed fetching depends on it |
| `auth/register.py` | 4 | User registration — data integrity |
| `ui/init_params.py` | 4 | Hotkeys, runtime info — UI bootstrap |
| `utils/colors.py` | 10 | Color math — favicon, label display |
| `utils/misc.py` | 6 | Date/time, email, random bytes |
| `utils/mail.py` | 1 | Email sending — digest feature |
| `utils/feeds.py` | 5 | Label↔feed ID math — used everywhere |
| `crypto/fernet.py` | 2 | Feed credential encryption |
| `plugins/loader.py` | 3 | Plugin init — affects every hook |
| `plugins/storage.py` | 4 | Plugin data persistence |
| `plugins/hookspecs.py` | 24 hook specs | Hook contracts — define all plugin APIs |
| `prefs/ops.py` | 4 | Schema version, user prefs — used globally |
| `prefs/system_crud.py` | 1 | Error log clear |
| All blueprint route files | 63 | Route layer above CRUD — auth, validation, response shapes |
| 22 model files | 37 ORM classes | Schema correctness — foundation of everything |
| `__init__.py`, `celery_app.py`, `errors.py`, `extensions.py` | 13 | App bootstrap — incorrect setup breaks everything |

**Total missing: ~179 functions + 37 model classes.**

Even for files it DID list, the plan named only a subset of functions (e.g., 13 of 29 in
`api/views.py`, 10 of 48 in `backend/views.py`).

---

## Codebase Census

| Metric | Count |
|--------|-------|
| Python source files (non-test, non-`__pycache__`) | 91 |
| Files with function/class definitions | 66 |
| Total function definitions (`def`) | 472 |
| Total ORM model classes | 37 |
| **Total verification targets** | **509** |

---

## Discrepancy Taxonomy

Every discrepancy found must be classified:

| Code | Name | Examples |
|------|------|---------|
| D1 | Missing branch | PHP `if ($user_limit) {...}` entirely absent in Python |
| D2 | Wrong condition | PHP `>= 0` → Python `> 0`; PHP `!empty($x)` → `if x` |
| D3 | SQL mismatch | Missing JOIN, wrong WHERE, wrong column, missing ORDER BY |
| D4 | Missing auth | PHP checks `$_SESSION["uid"]` ownership; Python skips |
| D5 | Wrong return | Different response shape, field names, or field types |
| D6 | Missing hook | PHP `run_hooks(HOOK_*)` omitted in Python |
| D7 | Missing side effect | PHP UPDATEs a column or invalidates cache; Python skips |
| D8 | Wrong config | PHP uses `SELF_URL_PATH`; Python uses wrong constant |
| D9 | Type coercion | PHP `(int)$_REQUEST["id"]`; Python allows non-int through |
| D10 | Missing error path | PHP returns specific error on failure; Python silently continues |
| D11 | Operation order | PHP invalidates cache AFTER write; Python does before |
| D12 | Feature absent | Sub-feature (e.g., PubSubHubbub ping) not implemented |
| D13 | Wrong null/empty | PHP `isset($x) && $x !== ""` vs Python `if x` |
| D14 | Session mismatch | PHP reads `$_SESSION["key"]`; Python reads different key |
| D15 | Missing pagination | PHP LIMIT/OFFSET logic absent or wrong |
| D16 | Schema mismatch | Model column type/default/constraint differs from PHP DDL |
| D17 | Missing relationship | ORM relationship/FK missing or wrong cascade |
| D18 | Hook contract wrong | Hook spec signature differs from PHP `run_hooks` call sites |

---

## PHP→Python Semantic Traps

These patterns consistently cause discrepancies — check EVERY function for them:

| PHP | Python gotcha |
|-----|--------------|
| `empty($x)` | PHP `empty("0")` is **True**, Python `not "0"` is **False** |
| `(int)$x` | `int(x)` raises ValueError on non-numeric; PHP `intval` returns 0 |
| `isset($x)` | Must check key existence, not just truthiness |
| `$arr["key"] ?? default` | `arr.get("key", default)` — correct |
| `strpos($s,$n) !== false` | PHP `strpos` returns `false`; Python `str.find` returns `-1` |
| `$result->fetch_assoc()` | SQLAlchemy `result.fetchall()` → must call, not just reference |
| PHP `"0"` is falsy | Python `"0"` is truthy |
| `preg_match` returns 0/1 | Python `re.search` returns `None`/Match — `if not match` works |
| `htmlspecialchars($s)` | `markupsafe.escape(s)` — different default mode (`ENT_QUOTES`) |
| PHP arrays = ordered maps | Python dicts ordered from 3.7+ — OK, but `array_keys()` ≠ `dict.keys()` in all edge cases |
| `$this->dbh->affected_rows()` | SQLAlchemy `result.rowcount` — same, but check it's used |
| `T_sprintf(...)` | i18n calls — must use equivalent or pass through |
| `header("Content-Type: ...")` | Flask response headers — must set explicitly |
| `$_REQUEST` / `$_POST` / `$_GET` | `request.form` vs `request.args` vs `request.values` — different merge order |
| `die()` / `exit()` | Must `abort()` or `return` with correct status code |

---

## Verification Methodology (Per Function)

### Step 1 — Read PHP source
Open the exact PHP function body at the lines cited in the `Source:` comment.
If no Source comment exists, flag as D12 (feature absent) and find the PHP origin.

### Step 2 — Read Python implementation

### Step 3 — Systematic comparison checklist
```
□ Input validation / type coercion (PHP (int), (bool), isset)
□ Authentication: owner_uid / $_SESSION["uid"] enforced?
□ Authorization: role/admin check present?
□ Every DB query:
    □ Correct table(s)?
    □ Correct columns (SELECT list)?
    □ Correct WHERE conditions (ALL of them)?
    □ Correct JOINs (type, ON clause)?
    □ Correct ORDER BY?
    □ Correct LIMIT / OFFSET?
    □ Correct UPDATE/INSERT targets and values?
□ All conditional branches (if/elseif/else, switch/case)?
□ All loop logic (foreach, while — behavior on empty result)?
□ Hook calls present and at correct execution point?
□ Cache invalidation (ccache_*) present and at correct point?
□ Return value: shape, field names, field types, error envelopes?
□ Error handling: what does PHP return/throw on each failure?
□ NULL/empty handling: PHP empty(), isset(), === NULL equivalents?
□ Config/constant references: correct constant names and values?
□ Side-effect order: writes before or after reads/cache?
□ HTTP headers / content-type set correctly?
□ Session reads/writes match PHP session keys?
```

### Step 4 — Document discrepancies (D1-D18 codes)

### Step 5 — Rewrite Python to match PHP semantics exactly

### Step 6 — Run `pytest` after each function fix (602 baseline tests must pass)

---

## Verification Workstreams — COMPLETE

**Naming convention:** WS-NN: Module Name (priority)
**Every Python file is assigned to exactly one workstream.**
**Every function listed with line number.**

---

### WS-01: Auth & Session (P0 — blocks everything)

**Python files:**
- `auth/authenticate.py` — 4 functions
- `auth/password.py` — 3 functions
- `auth/session.py` — 0 functions (module-level config only)
- `auth/register.py` — 4 functions
- `plugins/auth_internal/__init__.py` — 1 class, 1 method

**PHP sources:**
- `ttrss/classes/api.php` (login/session)
- `ttrss/plugins/auth_internal/init.php`
- `ttrss/include/functions.php` (authenticate_user, validate_session)
- `ttrss/classes/handler/public.php` (register)

**Functions (12 total):**

| # | Function | File | Line | PHP Source |
|---|----------|------|------|-----------|
| 1 | `authenticate_user` | auth/authenticate.py | 26 | functions.php:authenticate_user |
| 2 | `initialize_user` | auth/authenticate.py | 131 | functions.php:initialize_user |
| 3 | `logout_user` | auth/authenticate.py | 171 | functions.php + api.php:logout |
| 4 | `login_sequence` | auth/authenticate.py | 189 | handler/public.php:login |
| 5 | `hash_password` | auth/password.py | 35 | functions.php:make_password |
| 6 | `verify_password` | auth/password.py | 43 | auth_internal/init.php:check_password |
| 7 | `needs_upgrade` | auth/password.py | 97 | functions.php:make_password (SHA1→argon2) |
| 8 | `check_username_available` | auth/register.py | 18 | handler/public.php:register |
| 9 | `cleanup_stale_registrations` | auth/register.py | 28 | handler/public.php:register |
| 10 | `register_user` | auth/register.py | 45 | handler/public.php:register |
| 11 | `registration_slots_feed` | auth/register.py | 127 | handler/public.php:register |
| 12 | `AuthInternal.hook_auth_user` | plugins/auth_internal/__init__.py | 29 | auth_internal/init.php:authenticate |

**Known risk areas:**
- PHP `make_password()` creates SHA1; Python must verify SHA1 AND argon2id (ADR-0008)
- PHP `login_failure_count` + `login_failure_reset_time` — rate limiting
- PHP sets `$_SESSION["ref_schema_version"]` on login
- `API_DISABLED` per-user check
- Base64-decoded password fallback (api.php lines 73-82)
- Registration: PHP checks `REG_MAX_USERS`, validates email format, sends verification

---

### WS-02: API Dispatch (P0 — core API, 29 functions)

**Python files:**
- `blueprints/api/views.py` — 29 functions (1560 lines)

**PHP source:** `ttrss/classes/api.php` (~792 lines)

**Functions (29 total):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `_seq` | 73 | api.php:getSeq |
| 2 | `_ok` | 83 | api.php response wrapper |
| 3 | `_err` | 90 | api.php error wrapper |
| 4 | `_pref_is_true` | 97 | (helper) |
| 5 | `dispatch` | 110 | api.php:index (dispatch switch) |
| 6 | `_handle_login` | 224 | api.php:login |
| 7 | `_handle_getUnread` | 313 | api.php:getUnread |
| 8 | `_handle_getCounters` | 350 | api.php:getCounters |
| 9 | `_handle_getPref` | 363 | api.php:getPref |
| 10 | `_handle_getConfig` | 377 | api.php:getConfig |
| 11 | `_handle_getLabels` | 415 | api.php:getLabels |
| 12 | `_handle_getCategories` | 470 | api.php:getCategories |
| 13 | `_is_virtual_cat_empty` | 550 | api.php helper |
| 14 | `_handle_getFeeds` | 582 | api.php:getFeeds |
| 15 | `_handle_getArticle` | 696 | api.php:getArticle |
| 16 | `_handle_updateArticle` | 798 | api.php:updateArticle |
| 17 | `_handle_catchupFeed` | 909 | api.php:catchupFeed |
| 18 | `_handle_setArticleLabel` | 928 | api.php:setArticleLabel |
| 19 | `_handle_updateFeed` | 970 | api.php:updateFeed |
| 20 | `_handle_getHeadlines` | 1000 | api.php:getHeadlines — MOST COMPLEX |
| 21 | `_handle_subscribeToFeed` | 1128 | api.php:subscribeToFeed |
| 22 | `_handle_unsubscribeFeed` | 1160 | api.php:unsubscribeFeed |
| 23 | `_handle_shareToPublished` | 1253 | api.php:shareToPublished |
| 24 | `_handle_getFeedTree` | 1361 | api.php:getFeedTree |
| 25 | `_make_feed_node` (nested) | 1381 | api.php:getFeedTree helper |
| 26 | `_make_real_feed_node` (nested) | 1396 | api.php:getFeedTree helper |
| 27 | `_cat_node` (nested) | 1411 | api.php:getFeedTree helper |
| 28 | `_build_real_cat` (nested) | 1430 | api.php:getFeedTree helper |
| 29 | `_truthy` | 1548 | PHP boolean coercion helper |

**Highest-risk function:** `_handle_getHeadlines` (L1000) — virtual feed IDs, view_mode,
order_by, search, show_excerpt/content, include_attachments, since_id, include_nested,
sanitize, counter update side effect. Must match api.php line-by-line.

---

### WS-03: Backend / RPC (P0 — UI interaction, 48 functions)

**Python files:**
- `blueprints/backend/views.py` — 48 functions (1412 lines)

**PHP sources:** `ttrss/classes/rpc.php` (~654 lines), `ttrss/classes/backend.php`

**Functions (48 total):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `_param` | 50 | (helper) |
| 2 | `dispatch` | 73 | backend.php:index |
| 3 | `_rpc_mark` | 116 | rpc.php:mark |
| 4 | `_rpc_catchup_feed` | 137 | rpc.php:catchupFeed |
| 5 | `_rpc_delete` | 160 | rpc.php:delete |
| 6 | `_rpc_publ` | 183 | rpc.php:publ |
| 7 | `_rpc_archive` | 204 | rpc.php:archive |
| 8 | `_rpc_unarchive` | 218 | rpc.php:unarchive |
| 9 | `_rpc_remarchive` | 290 | rpc.php:remarchive |
| 10 | `_rpc_mark_selected` | 320 | rpc.php:markSelected |
| 11 | `_rpc_catchup_selected` | 337 | rpc.php:catchupSelected |
| 12 | `_rpc_mark_articles_by_id` | 353 | rpc.php:markArticlesById |
| 13 | `_rpc_publish_articles_by_id` | 368 | rpc.php:publishArticlesById |
| 14 | `_rpc_publish_selected` | 382 | rpc.php:publishSelected |
| 15 | `_rpc_setprofile` | 396 | rpc.php:setProfile |
| 16 | `_rpc_addprofile` | 409 | rpc.php:addProfile |
| 17 | `_rpc_remprofiles` | 442 | rpc.php:remProfiles |
| 18 | `_rpc_saveprofile` | 469 | rpc.php:saveProfile |
| 19 | `_rpc_addfeed` | 514 | rpc.php:addFeed |
| 20 | `_rpc_quick_add_cat` | 539 | rpc.php:quickAddCat |
| 21 | `_rpc_mass_subscribe` | 559 | rpc.php:massSubscribe |
| 22 | `_rpc_update_feed_browser` | 637 | rpc.php:updateFeedBrowser |
| 23 | `_rpc_togglepref` | 678 | rpc.php:togglePref |
| 24 | `_rpc_setpref` | 696 | rpc.php:setPref |
| 25 | `_rpc_sanity_check` | 714 | rpc.php:sanityCheck |
| 26 | `_rpc_complete_labels` | 738 | rpc.php:completeLabels |
| 27 | `_rpc_purge` | 762 | rpc.php:purge |
| 28 | `_rpc_updaterandomfeed` | 789 | rpc.php:updaterandomfeed |
| 29 | `_rpc_getlinktitlebyid` | 807 | rpc.php:getlinktitlebyid |
| 30 | `_rpc_log` | 829 | rpc.php:log |
| 31 | `_rpc_setpanelmode` | 855 | rpc.php:setPanelMode |
| 32 | `_rpc_get_all_counters` | 876 | rpc.php:getAllCounters |
| 33 | `_archive_article` | 915 | article.php:archive/unarchive |
| 34 | `_mark_articles_by_id` | 969 | article.php:_mark_articles |
| 35 | `_publish_articles_by_id` | 1001 | article.php:_publish_articles |
| 36 | `_dlg_import_opml` | 1044 | backend.php:importOpml |
| 37 | `_do_opml_import` | 1067 | backend.php:doOpmlImport |
| 38 | `_dlg_export_opml` | 1111 | backend.php:exportOpml |
| 39 | `_dlg_print_tag_cloud` | 1130 | backend.php:printTagCloud |
| 40 | `_dlg_print_tag_select` | 1167 | backend.php:printTagSelect |
| 41 | `_dlg_generated_feed` | 1186 | backend.php:generatedFeed |
| 42 | `_dlg_new_version` | 1218 | backend.php:newVersionDlg |
| 43 | `_dlg_explain_error` | 1230 | backend.php:explainError |
| 44 | `_backend_loading` | 1263 | backend.php:loading |
| 45 | `_backend_help` | 1272 | backend.php:help |
| 46 | `_article_complete_tags` | 1295 | article.php:completeTags |
| 47 | `_article_assign_to_label` | 1318 | article.php:assignToLabel |
| 48 | `_article_remove_from_label` | 1339 | article.php:removeFromLabel |

---

### WS-04: Public Endpoints (P0 — user-facing, security-critical)

**Python files:**
- `blueprints/public/views.py` — 14 functions

**PHP source:** `ttrss/classes/handler/public.php`

**Functions (14 total):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `index` | 36 | public.php:index |
| 2 | `image_proxy` | 43 | public.php:imgproxy |
| 3 | `register` | 62 | public.php:register |
| 4 | `login` | 126 | public.php:login |
| 5 | `logout` | 164 | public.php:logout |
| 6 | `get_unread` | 172 | public.php:getUnread |
| 7 | `get_profiles` | 201 | public.php:getProfiles |
| 8 | `pubsub` | 225 | public.php:pubsub (PubSubHubbub) |
| 9 | `share` | 270 | public.php:share |
| 10 | `sharepopup` | 290 | public.php:sharepopup |
| 11 | `subscribe` | 321 | public.php:subscribe |
| 12 | `forgotpass` | 342 | public.php:forgotpass |
| 13 | `dbupdate` | 413 | public.php:dbupdate |
| 14 | `rss` | 443 | public.php:rss (published RSS feed) |

**Risk areas:** `register` (user creation, email, rate limiting), `pubsub` (HMAC verification),
`image_proxy` (SSRF prevention), `forgotpass` (password reset flow), `rss` (access key auth).

---

### WS-05: Prefs Blueprint Routes (P1 — 7 files, 64 functions)

**Python files:**
- `blueprints/prefs/feeds.py` — 26 functions (includes `_owner_uid`, `_s` helpers)
- `blueprints/prefs/filters.py` — 10 functions
- `blueprints/prefs/labels.py` — 7 functions
- `blueprints/prefs/system.py` — 3 functions
- `blueprints/prefs/user_prefs.py` — 10 functions
- `blueprints/prefs/users.py` — 7 functions
- `blueprints/prefs/views.py` — 1 function

**PHP sources:** `ttrss/classes/pref/feeds.php`, `ttrss/classes/pref/filters.php`,
`ttrss/classes/pref/labels.php`, `ttrss/classes/pref/prefs.php`, `ttrss/classes/pref/users.php`

**Functions by file:**

**blueprints/prefs/feeds.py (26):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `_owner_uid` | 24 | (helper) |
| 2 | `_s` | 31 | (helper — session) |
| 3 | `edit_feed` | 42 | pref/feeds.php:editFeed |
| 4 | `save_feed` | 85 | pref/feeds.php:editSave |
| 5 | `batch_edit_feeds` | 116 | pref/feeds.php:batchEditSave |
| 6 | `save_feed_order` | 136 | pref/feeds.php:saveFeedOrder |
| 7 | `reset_feed_order` | 150 | pref/feeds.php:resetFeedOrder |
| 8 | `reset_category_order` | 167 | pref/feeds.php:resetCatOrder |
| 9 | `remove_feed` | 184 | pref/feeds.php:remove |
| 10 | `clear_feed` | 200 | pref/feeds.php:clear |
| 11 | `rescore_feed` | 217 | pref/feeds.php:rescore |
| 12 | `rescore_all_feeds` | 229 | pref/feeds.php:rescoreAll |
| 13 | `categorize_feeds` | 248 | pref/feeds.php:categorize |
| 14 | `remove_category` | 268 | pref/feeds.php:removeCat |
| 15 | `rename_category` | 280 | pref/feeds.php:renameCat |
| 16 | `inactive_feeds` | 300 | pref/feeds.php:inactiveFeeds |
| 17 | `feeds_with_errors` | 312 | pref/feeds.php:feedsWithErrors |
| 18 | `batch_subscribe_feeds` | 329 | pref/feeds.php:batchSubscribe |
| 19 | `update_feed_access_key` | 351 | pref/feeds.php:regenFeedKey |
| 20 | `get_feed_tree` | 370 | pref/feeds.php:getFeedTree |
| 21 | `add_category` | 390 | pref/feeds.php:addCat |
| 22 | `remove_feed_icon` | 409 | pref/feeds.php:removeFeedIcon |
| 23 | `reset_pubsub` | 424 | pref/feeds.php:resetPubSub |
| 24 | `regen_opml_key` | 438 | pref/feeds.php:regenOPMLKey |
| 25 | `regen_feed_key` | 450 | pref/feeds.php:regenFeedKey |
| 26 | `clear_access_keys` | 464 | pref/feeds.php:clearKeys |

**blueprints/prefs/filters.py (10):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `_owner_uid` | 20 | (helper) |
| 2 | `filters` | 32 | pref/filters.php:index |
| 3 | `edit_filter` | 76 | pref/filters.php:edit |
| 4 | `add_filter` | 126 | pref/filters.php:add |
| 5 | `save_filter` | 159 | pref/filters.php:editSave |
| 6 | `delete_filter` | 197 | pref/filters.php:remove |
| 7 | `save_filter_order` | 214 | pref/filters.php:saveFilterOrder |
| 8 | `reset_filter_order` | 228 | pref/filters.php:resetFilterOrder |
| 9 | `join_filters` | 245 | pref/filters.php:join |
| 10 | `test_filter` | 267 | pref/filters.php:testFilter |

**blueprints/prefs/labels.py (7):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `_owner_uid` | 23 | (helper) |
| 2 | `labels` | 35 | pref/labels.php:getlabeltree |
| 3 | `add_label` | 75 | pref/labels.php:add |
| 4 | `save_label` | 100 | pref/labels.php:save |
| 5 | `delete_label` | 143 | pref/labels.php:remove |
| 6 | `set_label_color` | 160 | pref/labels.php:colorset |
| 7 | `reset_label_color` | 178 | pref/labels.php:colorreset |

**blueprints/prefs/system.py (3):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `_owner_uid` | 20 | (helper) |
| 2 | `system` | 32 | pref/system.php:index |
| 3 | `clear_log` | 53 | pref/system.php:clearLog |

**blueprints/prefs/user_prefs.py (10):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `_owner_uid` | 24 | (helper) |
| 2 | `user_prefs` | 36 | pref/prefs.php:index |
| 3 | `change_password` | 79 | pref/prefs.php:changepassword |
| 4 | `change_email` | 115 | pref/prefs.php:changeemail |
| 5 | `save_config` | 136 | pref/prefs.php:saveconfig |
| 6 | `reset_config` | 160 | pref/prefs.php:resetconfig |
| 7 | `otp_enable` | 181 | pref/prefs.php:otpenable |
| 8 | `otp_disable` | 194 | pref/prefs.php:otpdisable |
| 9 | `clear_plugin_data` | 212 | pref/prefs.php:clearplugindata |
| 10 | `set_plugins` | 234 | pref/prefs.php:setplugins |

**blueprints/prefs/users.py (7):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `_owner_uid` | 20 | (helper) |
| 2 | `users` | 32 | pref/users.php:index |
| 3 | `user_details` | 69 | pref/users.php:userdetails |
| 4 | `add_user` | 88 | pref/users.php:add |
| 5 | `save_user` | 114 | pref/users.php:save |
| 6 | `delete_user` | 139 | pref/users.php:remove |
| 7 | `reset_user_password` | 160 | pref/users.php:resetPass |

**blueprints/prefs/views.py (1):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `index` | 27 | prefs.php:index |

---

### WS-06: Feed Update Engine (P0 — core daemon)

**Python files:**
- `tasks/feed_tasks.py` — 2 functions
- `articles/persist.py` — 11 functions

**PHP sources:** `ttrss/include/rssfuncs.php` (~1431 lines)

**Functions (13 total):**

| # | Function | File | Line | PHP Source |
|---|----------|------|------|-----------|
| 1 | `dispatch_feed_updates` | tasks/feed_tasks.py | 53 | rssfuncs.php:update_daemon_common |
| 2 | `update_feed` | tasks/feed_tasks.py | 226 | rssfuncs.php:update_rss_feed |
| 3 | `_make_guid_from_title` | articles/persist.py | 58 | rssfuncs.php:make_guid_from_title |
| 4 | `build_entry_guid` | articles/persist.py | 67 | rssfuncs.php (guid logic) |
| 5 | `content_hash` | articles/persist.py | 94 | rssfuncs.php:content_hash |
| 6 | `_is_ngram_duplicate` | articles/persist.py | 107 | rssfuncs.php (dupe check) |
| 7 | `apply_filter_actions` | articles/persist.py | 135 | rssfuncs.php (filter during insert) |
| 8 | `persist_enclosures` | articles/persist.py | 208 | rssfuncs.php (enclosure storage) |
| 9 | `upsert_entry` | articles/persist.py | 247 | rssfuncs.php (article INSERT/UPDATE) |
| 10 | `upsert_user_entry` | articles/persist.py | 322 | rssfuncs.php (user_entry creation) |
| 11 | `persist_article` | articles/persist.py | 370 | rssfuncs.php (full persist pipeline) |
| 12 | `labels_contains_caption` | articles/persist.py | 506 | rssfuncs.php |
| 13 | `assign_article_to_label_filters` | articles/persist.py | 515 | rssfuncs.php |

**Highest risk:** `update_feed` (L226) — HTTP fetch, ETag, feedparser, dedup, filter,
tag extraction, enclosure, PubSubHubbub, error handling, auth credentials.

---

### WS-07: Article Operations (P1)

**Python files:**
- `articles/ops.py` — 9 functions
- `articles/tags.py` — 3 functions

**PHP sources:** `ttrss/classes/article.php`, `ttrss/include/functions.php`, `ttrss/include/functions2.php`

**Functions (12 total):**

| # | Function | File | Line | PHP Source |
|---|----------|------|------|-----------|
| 1 | `_date_cutoff` | articles/ops.py | 54 | functions2.php (date helpers) |
| 2 | `get_article_enclosures` | articles/ops.py | 67 | article.php:get_article_enclosures |
| 3 | `format_article` | articles/ops.py | 102 | article.php:format_article |
| 4 | `format_headline_row` | articles/ops.py | 224 | article.php:format_headline |
| 5 | `catchupArticlesById` | articles/ops.py | 246 | article.php:catchupArticlesById |
| 6 | `catchup_feed` | articles/ops.py | 306 | functions.php:catchup_feed |
| 7 | `_entry_date_where` (nested) | articles/ops.py | 328 | (helper) |
| 8 | `_base_stmt` (nested) | articles/ops.py | 334 | (helper) |
| 9 | `_with_date` (nested) | articles/ops.py | 343 | (helper) |
| 10 | `tag_is_valid` | articles/tags.py | 28 | functions2.php:tag_is_valid |
| 11 | `get_article_tags` | articles/tags.py | 42 | article.php:get_article_tags |
| 12 | `setArticleTags` | articles/tags.py | 94 | article.php:setArticleTags |

---

### WS-08: Article Filters (P1)

**Python files:**
- `articles/filters.py` — 7 functions

**PHP sources:** `ttrss/include/rssfuncs.php:get_article_filters`, `ttrss/include/functions.php`

**Functions (7 total):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `load_filters` | 41 | functions.php:getGlobalCounters (filter loading) |
| 2 | `get_article_filters` | 164 | rssfuncs.php:get_article_filters |
| 3 | `find_article_filter` | 250 | rssfuncs.php:find_article_filter |
| 4 | `find_article_filters` | 263 | rssfuncs.php:find_article_filters |
| 5 | `calculate_article_score` | 278 | rssfuncs.php:calculate_article_score |
| 6 | `filter_to_sql` | 298 | feeds.php (SQL filter) |
| 7 | `false_clause` | 381 | (helper) |

---

### WS-09: Article Search (P1)

**Python files:**
- `articles/search.py` — 5 functions

**PHP sources:** `ttrss/classes/feeds.php` (search section)

**Functions (5 total):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `search_to_sql` | 46 | feeds.php:search_to_sql |
| 2 | `_like` (nested) | 78 | (helper) |
| 3 | `_ilike_both` (nested) | 81 | (helper) |
| 4 | `_maybe_not` (nested) | 84 | (helper) |
| 5 | `queryFeedHeadlines` | 148 | feeds.php:queryFeedHeadlines |

**Risk:** `queryFeedHeadlines` is very complex — virtual feeds, view modes, qualifiers (`d:`, `note:`, `star:`, `pub:`, `unread:`, `feed:N`, `cat:N`).

---

### WS-10: Article Sanitize (P1 — security-critical)

**Python files:**
- `articles/sanitize.py` — 2 functions (34 Source comments — heavily mapped)

**PHP source:** `ttrss/include/functions.php:sanitize`, `ttrss/include/functions2.php`

**Functions (2 total):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `sanitize` | 45 | functions.php:sanitize (core HTML sanitizer) |
| 2 | `strip_harmful_tags` | 194 | functions.php:strip_harmful_tags |

**CRITICAL:** This is the HTML sanitization layer. XSS prevention depends on this matching
PHP exactly. 34 Source refs means complex multi-section logic. Must compare every allowed
tag, attribute, URL scheme, and transformation rule.

---

### WS-11: Labels Core (P1 — used by API, filters, articles)

**Python files:**
- `labels.py` — 10 functions

**PHP sources:** `ttrss/include/functions.php`, `ttrss/include/functions2.php` (label helpers)

**Functions (10 total):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `label_find_id` | 21 | functions.php:label_find_id |
| 2 | `label_find_caption` | 34 | functions.php:label_find_caption |
| 3 | `get_all_labels` | 47 | functions.php:get_all_labels |
| 4 | `get_article_labels` | 61 | functions2.php:get_article_labels |
| 5 | `label_update_cache` | 121 | functions.php:label_update_cache |
| 6 | `label_clear_cache` | 147 | functions.php:label_clear_cache |
| 7 | `label_remove_article` | 160 | functions.php:label_remove_article |
| 8 | `label_add_article` | 177 | functions.php:label_add_article |
| 9 | `label_remove` | 202 | functions.php:label_remove |
| 10 | `label_create` | 240 | functions.php:label_create |

---

### WS-12: Feed Operations (P1)

**Python files:**
- `feeds/ops.py` — 10 functions

**PHP sources:** `ttrss/classes/feeds.php`, `ttrss/include/functions.php`, `ttrss/include/rssfuncs.php`

**Functions (10 total):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `feed_purge_interval` | 44 | feeds.php:feed_purge_interval |
| 2 | `get_feed_update_interval` | 62 | rssfuncs.php:get_feed_update_interval |
| 3 | `purge_feed` | 85 | functions.php:purge_feed |
| 4 | `purge_orphans` | 149 | functions.php:purge_orphans |
| 5 | `feed_has_icon` | 170 | functions2.php:feed_has_icon |
| 6 | `get_favicon_url` | 182 | functions.php:get_favicon_url |
| 7 | `check_feed_favicon` | 211 | rssfuncs.php:check_feed_favicon |
| 8 | `get_feeds_from_html` | 265 | functions.php:get_feeds_from_html |
| 9 | `get_feed_access_key` | 303 | functions.php:get_feed_access_key |
| 10 | `subscribe_to_feed` | 339 | feeds.php:subscribe_to_feed |

---

### WS-13: Feed Browser & Categories (P1)

**Python files:**
- `feeds/browser.py` — 3 functions
- `feeds/categories.py` — 8 functions

**PHP sources:** `ttrss/classes/feeds.php`, `ttrss/include/functions.php`

**Functions (11 total):**

| # | Function | File | Line | PHP Source |
|---|----------|------|------|-----------|
| 1 | `make_feed_browser` | feeds/browser.py | 21 | feeds.php:feedBrowser |
| 2 | `_mode1_global_browser` | feeds/browser.py | 45 | feeds.php (mode 1) |
| 3 | `_mode2_archived_feeds` | feeds/browser.py | 110 | feeds.php (mode 2) |
| 4 | `getCategoryTitle` | feeds/categories.py | 28 | functions.php:getCategoryTitle |
| 5 | `getFeedCatTitle` | feeds/categories.py | 45 | functions.php:getFeedCatTitle |
| 6 | `getFeedTitle` | feeds/categories.py | 64 | functions.php:getFeedTitle |
| 7 | `getArticleFeed` | feeds/categories.py | 102 | functions.php:getArticleFeed |
| 8 | `get_feed_category` | feeds/categories.py | 115 | functions.php (category lookup) |
| 9 | `add_feed_category` | feeds/categories.py | 138 | functions.php:add_feed_category |
| 10 | `getParentCategories` | feeds/categories.py | 167 | functions.php:getParentCategories |
| 11 | `getChildCategories` | feeds/categories.py | 195 | functions.php:getChildCategories |

---

### WS-14: Feed Counters (P1 — visible in UI, complex)

**Python files:**
- `feeds/counters.py` — 11 functions

**PHP sources:** `ttrss/classes/rpc.php:getCounters`, `ttrss/include/functions.php`

**Functions (11 total):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `getGlobalUnread` | 50 | functions.php:getGlobalUnread |
| 2 | `getGlobalCounters` | 64 | functions.php:getGlobalCounters |
| 3 | `getCategoryUnread` | 85 | functions.php:getCategoryUnread |
| 4 | `getCategoryChildrenUnread` | 140 | functions.php:getCategoryChildrenUnread |
| 5 | `getCategoryCounters` | 159 | functions.php:getCategoryCounters |
| 6 | `_feed_unread` | 215 | (helper) |
| 7 | `getVirtCounters` | 224 | functions.php:getVirtCounters |
| 8 | `getLabelCounters` | 250 | functions.php:getLabelCounters |
| 9 | `getFeedCounters` | 292 | functions.php:getFeedCounters |
| 10 | `getAllCounters` | 364 | functions.php:getAllCounters |
| 11 | `getFeedArticles` | 383 | functions.php:getFeedArticles |

**Risk:** Virtual feed IDs, LABEL_BASE_INDEX math, fresh article age, counter cache interaction.

---

### WS-15: Counter Cache (P1)

**Python files:**
- `ccache.py` — 9 functions

**PHP source:** `ttrss/include/ccache.php`

**Functions (9 total):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `_get_pref` | 37 | (helper) |
| 2 | `_pref_bool` | 55 | (helper) |
| 3 | `_pref_int` | 60 | (helper) |
| 4 | `_count_feed_articles` | 73 | ccache.php (counting logic) |
| 5 | `ccache_zero_all` | 189 | ccache.php:ccache_zero_all |
| 6 | `ccache_remove` | 205 | ccache.php:ccache_remove |
| 7 | `ccache_find` | 222 | ccache.php:ccache_find |
| 8 | `ccache_update_all` | 250 | ccache.php:ccache_update_all |
| 9 | `ccache_update` | 344 | ccache.php:ccache_update |

---

### WS-16: Feed OPML (P2)

**Python files:**
- `feeds/opml.py` — 13 functions

**PHP source:** `ttrss/classes/opml.php` (~523 lines)

**Functions (13 total):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `csrf_ignore` | 53 | opml.php (CSRF exempt list) |
| 2 | `opml_publish_url` | 68 | opml.php:opml_publish_url |
| 3 | `opml_export_category` | 109 | opml.php:opml_export_category |
| 4 | `opml_export_full` | 204 | opml.php:opml_export |
| 5 | `_remove_empty_folders` | 370 | opml.php helper |
| 6 | `export` | 402 | opml.php:export (entry point) |
| 7 | `opml_import_feed` | 429 | opml.php:opml_import_feed |
| 8 | `opml_import_label` | 485 | opml.php:opml_import_label |
| 9 | `opml_import_preference` | 513 | opml.php:opml_import_preference |
| 10 | `opml_import_filter` | 540 | opml.php:opml_import_filter |
| 11 | `opml_import_category` | 644 | opml.php:opml_import_category |
| 12 | `_parse_opml_tree` | 735 | opml.php:_parse_opml |
| 13 | `import_opml` | 759 | opml.php:import (entry point) |

---

### WS-17: Prefs CRUD — Feeds (P2 — largest CRUD module, 32 functions)

**Python files:**
- `prefs/feeds_crud.py` — 32 functions (1102 lines)

**PHP source:** `ttrss/classes/pref/feeds.php` (~40 methods)

**Functions (32 total):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `get_feed_for_edit` | 38 | pref/feeds.php:editFeed |
| 2 | `save_feed_settings` | 73 | pref/feeds.php:editSave |
| 3 | `batch_edit_feeds` | 123 | pref/feeds.php:batchEditSave |
| 4 | `save_feed_order` | 187 | pref/feeds.php:saveFeedOrder |
| 5 | `_process_category_order` | 211 | pref/feeds.php (category ordering) |
| 6 | `verify_feed_ownership` | 276 | pref/feeds.php (ownership check) |
| 7 | `reset_favicon_color` | 287 | pref/feeds.php |
| 8 | `remove_feed` | 304 | pref/feeds.php:remove |
| 9 | `clear_feed_articles` | 390 | pref/feeds.php:clear |
| 10 | `rescore_feed_impl` | 432 | pref/feeds.php:rescore |
| 11 | `get_all_feed_ids` | 482 | pref/feeds.php |
| 12 | `categorize_feeds` | 497 | pref/feeds.php:categorize |
| 13 | `remove_category` | 523 | pref/feeds.php:removeCat |
| 14 | `rename_category` | 537 | pref/feeds.php:renameCat |
| 15 | `reset_category_order` | 551 | pref/feeds.php:resetCatOrder |
| 16 | `reset_feed_order` | 564 | pref/feeds.php:resetFeedOrder |
| 17 | `get_inactive_feeds` | 582 | pref/feeds.php:inactiveFeeds |
| 18 | `get_feeds_with_errors` | 631 | pref/feeds.php:feedsWithErrors |
| 19 | `batch_subscribe_feeds` | 658 | pref/feeds.php:batchSubscribe |
| 20 | `update_feed_access_key` | 709 | pref/feeds.php:regenFeedKey |
| 21 | `get_feed_tree` | 747 | pref/feeds.php:getFeedTree |
| 22 | `_get_category_items` | 906 | pref/feeds.php helper |
| 23 | `_feed_to_item` | 959 | pref/feeds.php helper |
| 24 | `_init_cat_node` | 975 | pref/feeds.php helper |
| 25 | `_init_feed_node` | 992 | pref/feeds.php helper |
| 26 | `_calculate_children_count` | 1011 | pref/feeds.php helper |
| 27 | `_checkbox_bool` | 1030 | (helper) |
| 28 | `remove_feed_icon` | 1042 | pref/feeds.php:removeFeedIcon |
| 29 | `reset_pubsub` | 1058 | pref/feeds.php:resetPubSub |
| 30 | `regen_opml_key` | 1075 | pref/feeds.php:regenOPMLKey |
| 31 | `regen_feed_key` | 1084 | pref/feeds.php:regenFeedKey |
| 32 | `clear_access_keys` | 1093 | pref/feeds.php:clearKeys |

---

### WS-18: Prefs CRUD — Filters (P2, 17 functions)

**Python files:**
- `prefs/filters_crud.py` — 17 functions

**PHP source:** `ttrss/classes/pref/filters.php`

**Functions (17 total):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `get_filter_rows` | 32 | pref/filters.php:getFilterList |
| 2 | `get_rule_reg_exps_for_filter` | 44 | pref/filters.php |
| 3 | `get_filter_name` | 55 | pref/filters.php:getFilterName |
| 4 | `create_filter` | 108 | pref/filters.php:add |
| 5 | `update_filter` | 132 | pref/filters.php:editSave |
| 6 | `commit_filter` | 152 | (session commit) |
| 7 | `fetch_filter` | 162 | pref/filters.php:edit |
| 8 | `fetch_filter_rules` | 173 | pref/filters.php (rules query) |
| 9 | `fetch_filter_actions` | 185 | pref/filters.php (actions query) |
| 10 | `delete_filter` | 202 | pref/filters.php:remove |
| 11 | `save_rules_and_actions` | 219 | pref/filters.php:saveRulesAndActions |
| 12 | `save_filter_order` | 305 | pref/filters.php:saveFilterOrder |
| 13 | `reset_filter_order` | 319 | pref/filters.php:resetFilterOrder |
| 14 | `join_filters` | 337 | pref/filters.php:join |
| 15 | `optimize_filter` | 374 | pref/filters.php:optimize |
| 16 | `fetch_filter_type_map` | 419 | pref/filters.php (type lookup) |
| 17 | `fetch_recent_articles_for_test` | 428 | pref/filters.php:testFilter |

---

### WS-19: Prefs CRUD — Labels, Ops, System (P2, 15 functions)

**Python files:**
- `prefs/labels_crud.py` — 10 functions
- `prefs/ops.py` — 4 functions
- `prefs/system_crud.py` — 1 function

**Functions (15 total):**

| # | Function | File | Line | PHP Source |
|---|----------|------|------|-----------|
| 1 | `fetch_labels` | prefs/labels_crud.py | 22 | pref/labels.php:getlabeltree |
| 2 | `create_label` | prefs/labels_crud.py | 39 | pref/labels.php:add |
| 3 | `fetch_label_caption` | prefs/labels_crud.py | 56 | pref/labels.php |
| 4 | `check_caption_taken` | prefs/labels_crud.py | 67 | pref/labels.php |
| 5 | `rename_label` | prefs/labels_crud.py | 79 | pref/labels.php:save |
| 6 | `update_label_colors` | prefs/labels_crud.py | 106 | pref/labels.php:colorset |
| 7 | `commit_label` | prefs/labels_crud.py | 121 | (session commit) |
| 8 | `delete_label` | prefs/labels_crud.py | 131 | pref/labels.php:remove |
| 9 | `set_label_color` | prefs/labels_crud.py | 146 | pref/labels.php:colorset |
| 10 | `reset_label_color` | prefs/labels_crud.py | 188 | pref/labels.php:colorreset |
| 11 | `get_schema_version` | prefs/ops.py | 21 | functions.php:get_schema_version |
| 12 | `get_user_pref` | prefs/ops.py | 42 | functions.php:get_pref |
| 13 | `set_user_pref` | prefs/ops.py | 92 | functions.php:set_pref |
| 14 | `initialize_user_prefs` | prefs/ops.py | 129 | functions.php:initialize_user_prefs |
| 15 | `clear_error_log` | prefs/system_crud.py | 15 | pref/system.php:clearLog |

---

### WS-20: Prefs CRUD — Users & User Prefs (P2, 16 functions)

**Python files:**
- `prefs/user_prefs_crud.py` — 9 functions
- `prefs/users_crud.py` — 7 functions

**Functions (16 total):**

| # | Function | File | Line | PHP Source |
|---|----------|------|------|-----------|
| 1 | `get_user_for_password_change` | user_prefs_crud.py | 22 | pref/prefs.php:changepassword |
| 2 | `save_password_change` | user_prefs_crud.py | 31 | pref/prefs.php:changepassword |
| 3 | `save_email_and_name` | user_prefs_crud.py | 47 | pref/prefs.php:changeemail |
| 4 | `clear_digest_sent_time` | user_prefs_crud.py | 61 | pref/prefs.php |
| 5 | `reset_user_prefs` | user_prefs_crud.py | 74 | pref/prefs.php:resetconfig |
| 6 | `get_user_for_otp` | user_prefs_crud.py | 92 | pref/prefs.php:otpenable |
| 7 | `set_otp_enabled` | user_prefs_crud.py | 100 | pref/prefs.php:otp* |
| 8 | `clear_plugin_data` | user_prefs_crud.py | 112 | pref/prefs.php:clearplugindata |
| 9 | `list_pref_profiles` | user_prefs_crud.py | 130 | pref/prefs.php |
| 10 | `list_users` | users_crud.py | 26 | pref/users.php:index |
| 11 | `find_user_by_login` | users_crud.py | 58 | pref/users.php |
| 12 | `create_user` | users_crud.py | 68 | pref/users.php:add |
| 13 | `get_user_details` | users_crud.py | 100 | pref/users.php:userdetails |
| 14 | `update_user` | users_crud.py | 146 | pref/users.php:save |
| 15 | `delete_user` | users_crud.py | 183 | pref/users.php:remove |
| 16 | `reset_user_password` | users_crud.py | 196 | pref/users.php:resetPass |

---

### WS-21: Plugin System (P2, 65+ definitions)

**Python files:**
- `plugins/manager.py` — 33 functions (PluginHost class + module-level)
- `plugins/loader.py` — 3 functions
- `plugins/storage.py` — 4 functions
- `plugins/hookspecs.py` — 1 class, 24 hook spec methods

**PHP source:** `ttrss/classes/pluginhost.php` (~39 methods)

**Functions — manager.py (33):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `get_plugin_manager` | 34 | (factory) |
| 2 | `reset_plugin_manager` | 49 | (reset) |
| 3 | `init_app` | 59 | (Flask init) |
| 4 | `PluginHost.__init__` | 83 | pluginhost.php:__construct |
| 5 | `PluginHost._is_system` | 97 | pluginhost.php |
| 6 | `PluginHost.add_api_method` | 115 | pluginhost.php:add_api_method |
| 7 | `PluginHost.get_api_method` | 131 | pluginhost.php:get_api_method |
| 8 | `PluginHost.add_command` | 145 | pluginhost.php:add_command |
| 9 | `PluginHost.del_command` | 165 | pluginhost.php:del_command |
| 10 | `PluginHost.lookup_command` | 173 | pluginhost.php:lookup_command |
| 11 | `PluginHost.get_commands` | 181 | pluginhost.php:get_commands |
| 12 | `PluginHost.run_commands` | 189 | pluginhost.php:run_commands |
| 13 | `PluginHost.add_handler` | 216 | pluginhost.php:add_handler |
| 14 | `PluginHost.del_handler` | 233 | pluginhost.php:del_handler |
| 15 | `PluginHost.lookup_handler` | 241 | pluginhost.php:lookup_handler |
| 16 | `PluginHost.add_feed` | 254 | pluginhost.php:add_feed |
| 17 | `PluginHost.get_feeds` | 266 | pluginhost.php:get_feeds |
| 18 | `PluginHost.get_feed_handler` | 278 | pluginhost.php:get_feed_handler |
| 19 | `PluginHost.feed_to_pfeed_id` | 287 | pluginhost.php:feed_to_pfeed_id |
| 20 | `PluginHost.pfeed_to_feed_id` | 298 | pluginhost.php:pfeed_to_feed_id |
| 21 | `PluginHost.del_hook` | 312 | pluginhost.php:del_hook |
| 22 | `PluginHost.get_hooks` | 324 | pluginhost.php:get_hooks |
| 23 | `PluginHost.get_all` | 332 | pluginhost.php:get_all |
| 24 | `PluginHost.save_data` | 345 | pluginhost.php:save_data |
| 25 | `PluginHost.clear_data` | 376 | pluginhost.php:clear_data |
| 26 | `PluginHost.set_debug` | 403 | pluginhost.php:set_debug |
| 27 | `PluginHost.get_debug` | 411 | pluginhost.php:get_debug |
| 28 | `PluginHost.get_link` | 419 | pluginhost.php:get_link |
| 29 | `PluginHost.register_plugin` | 430 | pluginhost.php:register_plugin |
| 30 | `PluginHost.get_plugin_names` | 447 | pluginhost.php:get_plugin_names |
| 31 | `PluginHost.get_plugins` | 455 | pluginhost.php:get_plugins |
| 32 | `PluginHost.get_plugin` | 463 | pluginhost.php:get_plugin |
| 33 | `get_plugin_host` | 475 | (compat alias) |

**Functions — loader.py (3):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `_load_plugin` | 27 | pluginhost.php:load_all |
| 2 | `init_plugins` | 89 | pluginhost.php:load_all (system) |
| 3 | `load_user_plugins` | 113 | pluginhost.php:load_all (user) |

**Functions — storage.py (4):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `get_data` | 25 | pluginhost.php:load_data |
| 2 | `set_data` | 53 | pluginhost.php:save_data |
| 3 | `clear_data` | 81 | pluginhost.php:clear_data |
| 4 | `load_plugin_data` | 94 | pluginhost.php (init data load) |

**Hook specs — hookspecs.py (24 spec methods):**
Verify each hook's **signature** matches PHP `run_hooks` call sites.

| # | Hook | Line | PHP Constant |
|---|------|------|-------------|
| 1 | `hook_article_button` | 56 | HOOK_ARTICLE_BUTTON |
| 2 | `hook_article_filter` | 63 | HOOK_ARTICLE_FILTER |
| 3 | `hook_prefs_tab` | 70 | HOOK_PREFS_TAB |
| 4 | `hook_prefs_tab_section` | 77 | HOOK_PREFS_TAB_SECTION |
| 5 | `hook_prefs_tabs` | 84 | HOOK_PREFS_TABS |
| 6 | `hook_feed_parsed` | 91 | HOOK_FEED_PARSED |
| 7 | `hook_update_task` | 98 | HOOK_UPDATE_TASK |
| 8 | `hook_auth_user` | 110 | HOOK_AUTH_USER |
| 9 | `hook_hotkey_map` | 120 | HOOK_HOTKEY_MAP |
| 10 | `hook_render_article` | 127 | HOOK_RENDER_ARTICLE |
| 11 | `hook_render_article_cdm` | 134 | HOOK_RENDER_ARTICLE_CDM |
| 12 | `hook_feed_fetched` | 141 | HOOK_FEED_FETCHED |
| 13 | `hook_sanitize` | 148 | HOOK_SANITIZE |
| 14 | `hook_render_article_api` | 155 | HOOK_RENDER_ARTICLE_API |
| 15 | `hook_toolbar_button` | 162 | HOOK_TOOLBAR_BUTTON |
| 16 | `hook_action_item` | 169 | HOOK_ACTION_ITEM |
| 17 | `hook_headline_toolbar_button` | 176 | HOOK_HEADLINE_TOOLBAR_BUTTON |
| 18 | `hook_hotkey_info` | 183 | HOOK_HOTKEY_INFO |
| 19 | `hook_article_left_button` | 190 | HOOK_ARTICLE_LEFT_BUTTON |
| 20 | `hook_prefs_edit_feed` | 197 | HOOK_PREFS_EDIT_FEED |
| 21 | `hook_prefs_save_feed` | 204 | HOOK_PREFS_SAVE_FEED |
| 22 | `hook_fetch_feed` | 215 | HOOK_FETCH_FEED |
| 23 | `hook_query_headlines` | 225 | HOOK_QUERY_HEADLINES |
| 24 | `hook_house_keeping` | 247 | HOOK_HOUSE_KEEPING |

---

### WS-22: Background Tasks (P2, 12 functions)

**Python files:**
- `tasks/feed_tasks.py` — 2 functions (already in WS-06 for semantics; verify Celery wrapper here)
- `tasks/housekeeping.py` — 6 functions
- `tasks/digest.py` — 4 functions

**PHP sources:** `ttrss/include/rssfuncs.php`, `ttrss/include/digest.php`

**Functions — housekeeping.py (6):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `expire_cached_files` | 53 | rssfuncs.php:expire_cached_files |
| 2 | `expire_error_log` | 92 | rssfuncs.php:expire_error_log |
| 3 | `update_feedbrowser_cache` | 113 | rssfuncs.php:update_feedbrowser_cache |
| 4 | `cleanup_tags` | 163 | functions2.php:cleanup_tags (2030-2069) |
| 5 | `housekeeping_common` | 203 | rssfuncs.php:housekeeping_common |
| 6 | `run_housekeeping` | 259 | handler/public.php:housekeepingTask |

**Functions — digest.py (4):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `prepare_headlines_digest` | 28 | digest.php:prepare_headlines_digest |
| 2 | `send_headlines_digests` | 191 | digest.php:send_headlines_digests |
| 3 | `_run` (nested) | 214 | (implementation body) |
| 4 | `_catchup_digest_articles` | 332 | digest.php (catchup after send) |

---

### WS-23: HTTP Client & Crypto (P2, 7 functions)

**Python files:**
- `http/client.py` — 5 functions (35 Source comments — heavily mapped)
- `crypto/fernet.py` — 2 functions

**PHP sources:** `ttrss/include/functions.php` (URL helpers), `ttrss/classes/crypt.php`

**Functions (7 total):**

| # | Function | File | Line | PHP Source |
|---|----------|------|------|-----------|
| 1 | `fix_url` | http/client.py | 144 | functions.php:fix_url |
| 2 | `validate_feed_url` | http/client.py | 170 | functions.php:validate_feed_url |
| 3 | `is_html` | http/client.py | 183 | functions.php:is_html |
| 4 | `build_url` | http/client.py | 211 | functions.php:build_url |
| 5 | `rewrite_relative_url` | http/client.py | 224 | functions.php:rewrite_relative_url |
| 6 | `fernet_encrypt` | crypto/fernet.py | 23 | crypt.php:encrypt_string (ADR-0009) |
| 7 | `fernet_decrypt` | crypto/fernet.py | 38 | crypt.php:decrypt_string (ADR-0009) |

---

### WS-24: UI Init & Utils (P2, 26 functions)

**Python files:**
- `ui/init_params.py` — 4 functions
- `utils/colors.py` — 10 functions
- `utils/feeds.py` — 5 functions
- `utils/mail.py` — 1 function
- `utils/misc.py` — 6 functions

**PHP sources:** `ttrss/include/functions.php`, `ttrss/include/functions2.php`, `ttrss/lib/colors.php`

**Functions — ui/init_params.py (4):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `get_hotkeys_info` | 29 | functions.php:get_hotkeys_info |
| 2 | `get_hotkeys_map` | 84 | functions.php:get_hotkeys_map |
| 3 | `make_runtime_info` | 128 | functions.php:make_runtime_info |
| 4 | `make_init_params` | 172 | functions.php:make_init_params |

**Functions — utils/colors.py (10):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `resolve_html_color` | 170 | colors.php:resolve_html_color |
| 2 | `_color_hue_to_rgb` | 181 | colors.php:_color_hue_to_rgb |
| 3 | `color_rgb_to_hsl` | 198 | colors.php:color_rgb_to_hsl |
| 4 | `color_hsl_to_rgb` | 224 | colors.php:color_hsl_to_rgb |
| 5 | `color_unpack` | 237 | colors.php:color_unpack |
| 6 | `color_pack` | 269 | colors.php:color_pack |
| 7 | `rgb_to_hsv` | 289 | colors.php:rgb_to_hsv |
| 8 | `hsv_to_rgb` | 329 | colors.php:hsv_to_rgb |
| 9 | `color_palette` | 363 | colors.php:color_palette |
| 10 | `calculate_avg_color` | 408 | functions2.php:calculate_avg_color |

**Functions — utils/feeds.py (5):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `label_to_feed_id` | 16 | functions.php:label_to_feed_id |
| 2 | `feed_to_label_id` | 23 | functions.php:feed_to_label_id |
| 3 | `pfeed_to_feed_id` | 30 | pluginhost.php:pfeed_to_feed_id |
| 4 | `feed_to_pfeed_id` | 37 | pluginhost.php:feed_to_pfeed_id |
| 5 | `classify_feed_id` | 44 | (helper, virtual feed classification) |

**Functions — utils/mail.py (1):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `send_mail` | 22 | functions.php:send_mail (uses phpmailer) |

**Functions — utils/misc.py (6):**

| # | Function | Line | PHP Source |
|---|----------|------|-----------|
| 1 | `convert_timestamp` | 25 | functions.php:convert_timestamp |
| 2 | `smart_date_time` | 66 | functions2.php:smart_date_time |
| 3 | `make_local_datetime` | 108 | functions.php:make_local_datetime |
| 4 | `get_random_bytes` | 180 | functions.php:get_random_bytes |
| 5 | `save_email_address` | 191 | functions.php:save_email_address |
| 6 | `_pref` | 212 | (helper) |

---

### WS-25: ORM Models — Schema Verification (P2, 37 classes)

**Python files:** 22 files in `models/`

**PHP source:** `ttrss/schema/ttrss_schema_pgsql.sql`, PHP `$this->dbh` usage patterns

**Verification checklist per model:**
- Column names match PHP schema exactly
- Column types (Integer, String(N), Text, Boolean, DateTime) match DDL
- Default values match DDL
- NOT NULL constraints match DDL
- Foreign key references (target table, target column, ON DELETE) match DDL
- Indexes (unique, composite) match DDL
- Relationships (backref, lazy loading, cascade) are correct

**Models (37 total):**

| # | Class | File | Line | DB Table |
|---|-------|------|------|---------|
| 1 | `Base` | models/base.py | 13 | (declarative base) |
| 2 | `TtRssAccessKey` | models/access_key.py | 23 | ttrss_access_keys |
| 3 | `TtRssArchivedFeed` | models/archived_feed.py | 24 | ttrss_archived_feeds |
| 4 | `TtRssFeedCategory` | models/category.py | 22 | ttrss_feed_categories |
| 5 | `TtRssCountersCache` | models/counters_cache.py | 34 | ttrss_counters_cache |
| 6 | `TtRssCatCountersCache` | models/counters_cache.py | 69 | ttrss_cat_counters_cache |
| 7 | `TtRssEnclosure` | models/enclosure.py | 19 | ttrss_enclosures |
| 8 | `TtRssEntry` | models/entry.py | 25 | ttrss_entries |
| 9 | `TtRssEntryComment` | models/entry_comment.py | 25 | ttrss_entry_comments |
| 10 | `TtRssErrorLog` | models/error_log.py | 22 | ttrss_error_log |
| 11 | `TtRssFeed` | models/feed.py | 29 | ttrss_feeds |
| 12 | `TtRssFeedbrowserCache` | models/feedbrowser_cache.py | 20 | ttrss_feedbrowser_cache |
| 13 | `TtRssFilterType` | models/filter.py | 30 | ttrss_filter_types |
| 14 | `TtRssFilterAction` | models/filter.py | 48 | ttrss_filter_actions |
| 15 | `TtRssFilter2` | models/filter.py | 65 | ttrss_filters2 |
| 16 | `TtRssFilter2Rule` | models/filter.py | 95 | ttrss_filters2_rules |
| 17 | `TtRssFilter2Action` | models/filter.py | 131 | ttrss_filters2_actions |
| 18 | `TtRssLabel2` | models/label.py | 25 | ttrss_labels2 |
| 19 | `TtRssUserLabel2` | models/label.py | 43 | ttrss_user_labels2 |
| 20 | `TtRssLinkedInstance` | models/linked.py | 23 | ttrss_linked_instances |
| 21 | `TtRssLinkedFeed` | models/linked.py | 46 | ttrss_linked_feeds |
| 22 | `TtRssPluginStorage` | models/plugin_storage.py | 19 | ttrss_plugin_storage |
| 23 | `TtRssPrefsType` | models/pref.py | 34 | ttrss_prefs_types |
| 24 | `TtRssPrefsSection` | models/pref.py | 50 | ttrss_prefs_sections |
| 25 | `TtRssPref` | models/pref.py | 69 | ttrss_prefs |
| 26 | `TtRssSettingsProfile` | models/pref.py | 101 | ttrss_settings_profiles |
| 27 | `TtRssUserPref` | models/pref.py | 122 | ttrss_user_prefs |
| 28 | `TtRssSession` | models/session.py | 29 | ttrss_sessions |
| 29 | `TtRssTag` | models/tag.py | 20 | ttrss_tags |
| 30 | `TtRssUserEntry` | models/user_entry.py | 28 | ttrss_user_entries |
| 31 | `TtRssUser` | models/user.py | 32 | ttrss_users |
| 32 | `TtRssVersion` | models/version.py | 27 | ttrss_version |
| 33 | `TtRssFeed.auth_pass` (getter) | models/feed.py | 127 | (Fernet decrypt) |
| 34 | `TtRssFeed.auth_pass` (setter) | models/feed.py | 140 | (Fernet encrypt) |

---

### WS-26: App Bootstrap (P3, 13 functions + 2 classes)

**Python files:**
- `__init__.py` — 2 functions
- `celery_app.py` — 4 functions + 1 class
- `config.py` — 1 class
- `extensions.py` — 1 function
- `errors.py` — 6 functions

**These are infrastructure files** — verify they correctly initialize Flask, Celery,
Flask-Login, error handlers, and config consistent with PHP's `config.php` + `init.php`.

**Functions (13 + 2 classes):**

| # | Function | File | Line | PHP Source |
|---|----------|------|------|-----------|
| 1 | `_configure_structlog` | __init__.py | 22 | (New — no PHP equivalent) |
| 2 | `create_app` | __init__.py | 72 | index.php + config.php init |
| 3 | `dispose_db_pool_on_fork` | celery_app.py | 66 | (New — Celery worker) |
| 4 | `close_db_pool_on_shutdown` | celery_app.py | 79 | (New — Celery worker) |
| 5 | `init_app` | celery_app.py | 88 | (New — Celery init) |
| 6 | `ContextTask.__call__` | celery_app.py | 99 | (New — Flask app context) |
| 7 | `Config` class | config.py | 20 | config.php constants |
| 8 | `load_user` | extensions.py | 58 | functions.php session handler |
| 9 | `register_error_handlers` | errors.py | 20 | (error handler registration) |
| 10 | `bad_request` | errors.py | 24 | (400 handler) |
| 11 | `unauthorized` | errors.py | 31 | (401 handler) |
| 12 | `forbidden` | errors.py | 38 | (403 handler) |
| 13 | `not_found` | errors.py | 45 | (404 handler) |
| 14 | `server_error` | errors.py | 52 | (500 handler) |

---

## Execution Order

```
Week 1 — P0 (critical path, blocks everything):
  WS-01  Auth & Session            12 functions
  WS-02  API Dispatch              29 functions
  WS-03  Backend / RPC             48 functions
  WS-04  Public Endpoints          14 functions
  WS-06  Feed Update Engine        13 functions
                                   ─────────────
                          Subtotal: 116 functions

Week 2 — P1 (core features):
  WS-05  Prefs Blueprint Routes    64 functions
  WS-07  Article Operations        12 functions
  WS-08  Article Filters            7 functions
  WS-09  Article Search             5 functions
  WS-10  Article Sanitize           2 functions (34 Source refs!)
  WS-11  Labels Core               10 functions
  WS-12  Feed Operations           10 functions
  WS-13  Feed Browser & Categories 11 functions
  WS-14  Feed Counters             11 functions
  WS-15  Counter Cache              9 functions
                                   ─────────────
                          Subtotal: 141 functions

Week 3 — P2 (full coverage):
  WS-16  Feed OPML                 13 functions
  WS-17  Prefs CRUD — Feeds        32 functions
  WS-18  Prefs CRUD — Filters      17 functions
  WS-19  Prefs CRUD — Labels/Ops   15 functions
  WS-20  Prefs CRUD — Users        16 functions
  WS-21  Plugin System             64 definitions
  WS-22  Background Tasks          12 functions (inc. overlap w/ WS-06)
  WS-23  HTTP Client & Crypto       7 functions
  WS-24  UI Init & Utils           26 functions
  WS-25  ORM Models                37 classes
                                   ─────────────
                          Subtotal: 239 items

Week 4 — P3 (infrastructure + sweep):
  WS-26  App Bootstrap             15 definitions
  Full regression sweep
  SME second pass
                                   ─────────────
                          Subtotal: 15 definitions

GRAND TOTAL: 511 verification targets (472 functions + 37 models + 2 class defs)
```

---

## Fix Protocol

For each function:

1. **Read PHP source first** — exact lines from Source: comment
2. **Read Python current** — full function
3. **List ALL discrepancies** using D1-D18 taxonomy
4. **Rewrite Python** to match PHP semantics exactly:
   - Same SQL logic (translated to SQLAlchemy)
   - Same branch conditions (watch PHP truthiness rules)
   - Same return value structure
   - Same error cases
   - Same side effects in same order
5. **Preserve Python idioms** only where semantically equivalent
6. **Update traceability comment** to cite exact PHP lines verified
7. **Run tests** after every function (`pytest` — 602 baseline must pass)

---

## Discrepancy Tracking

Track in `docs/semantic_verification_report.md`:

```markdown
## WS-NN: Module Name

### func_name() [Python file:line / PHP file:lines]
Status: [ ] Pending  [x] Verified OK  [!] Fixed

Discrepancies found:
- D3: SQL missing `AND owner_uid = :uid` (PHP line 45)
- D1: Missing branch: `if (!$feed_id)` error return (PHP lines 23-25)

Fix applied: commit XXXXXXX
```

---

## Success Criteria

A function is **verified** when:
1. All D1-D18 codes checked — none found OR all found ones fixed
2. The Source: comment cites exact PHP lines verified
3. `pytest` passes all baseline tests

The codebase is **complete** when:
- All 26 workstreams verified (511 targets)
- Zero unfixed discrepancies
- SME second pass confirms correctness
