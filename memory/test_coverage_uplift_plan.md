---
name: test_coverage_uplift_plan
description: Active plan to lift unit test coverage from 51% to >80% in all 32 below-threshold Python files — 5 batches, ~250 tests, every test traced to PHP source
type: project
---

# Test Coverage Uplift Plan

**Goal:** All Python files ≥ 80% line coverage.  
**Baseline:** 51% overall; 32 files below threshold.  
**Approach:** Every test traces to a PHP source function for behavioral specification.  
**Rule:** Test the _behavior_ PHP defined — not the Python implementation detail.

---

## Coverage Baseline (files < 80%)

| File | Current | Stmts | Priority |
|------|---------|-------|----------|
| `auth/session.py` | 0% | 2 | P3 |
| `feeds/browser.py` | 0% | 46 | P2 |
| `auth/register.py` | 0% | 48 | P2 |
| `auth/authenticate.py` | 0% | 66 | P2 |
| `utils/misc.py` | 0% | 79 | P1 |
| `utils/colors.py` | 0% | 139 | P1 |
| `feeds/opml.py` | 0% | 250 | P2 |
| `articles/sanitize.py` | 6% | 101 | P1 |
| `blueprints/backend/views.py` | 10% | 529 | P2 |
| `prefs/feeds_crud.py` | 11% | 346 | P2 |
| `blueprints/public/views.py` | 11% | 286 | P2 |
| `utils/mail.py` | 12% | 52 | P1 |
| `prefs/filters_crud.py` | 14% | 145 | P2 |
| `tasks/digest.py` | 21% | 142 | P2 |
| `blueprints/prefs/user_prefs.py` | 25% | 147 | P2 |
| `prefs/users_crud.py` | 30% | 75 | P2 |
| `plugins/manager.py` | 30% | 149 | P2 |
| `http/client.py` | 30% | 83 | P1 |
| `prefs/labels_crud.py` | 31% | 46 | P2 |
| `prefs/user_prefs_crud.py` | 32% | 47 | P2 |
| `errors.py` | 32% | 27 | P3 |
| `blueprints/prefs/filters.py` | 33% | 121 | P2 |
| `blueprints/prefs/labels.py` | 36% | 76 | P2 |
| `prefs/ops.py` | 37% | 42 | P2 |
| `blueprints/prefs/users.py` | 37% | 88 | P2 |
| `plugins/loader.py` | 43% | 62 | P3 |
| `blueprints/prefs/feeds.py` | 45% | 208 | P2 |
| `plugins/auth_internal/__init__.py` | 48% | 55 | P3 |
| `celery_app.py` | 50% | 20 | P3 |
| `plugins/storage.py` | 67% | 34 | P3 |
| `__init__.py` | 67% | 49 | P3 |
| `prefs/system_crud.py` | 71% | 7 | P3 |

---

## Batch 1 — Pure Functions (no DB, no HTTP)

**Files:** `utils/colors.py`, `utils/misc.py`, `utils/mail.py`, `http/client.py`, `articles/sanitize.py`  
**Target file:** `tests/unit/test_utils_colors.py`, `test_utils_misc.py`, `test_utils_mail.py`, `test_http_client.py`, `test_articles_sanitize_full.py`

---

### B1-1: `utils/colors.py`
**PHP source:** `ttrss/include/colors.php`

| Test | PHP behavior traced | Assert |
|------|---------------------|--------|
| `resolve_html_color("red")` → `"#ff0000"` | `colors.php:$html_colors["red"]` | exact hex string |
| `resolve_html_color("RED")` → `"#ff0000"` | case-insensitive lookup | lowercase match |
| `resolve_html_color("#abc123")` → `"#abc123"` | unknown names returned as-is | passthrough |
| `color_unpack("#ff0000")` → `(255,0,0)` | `colors.php:color_unpack` RGB split | correct triplet |
| `color_unpack("#f00")` → `(255,0,0)` | 3-char shorthand: each char doubled | expansion |
| `color_unpack("#ff0000", normalize=True)` → `(1.0,0,0)` | divide by 255 | float range |
| `color_pack((255,0,0))` → `"#ff0000"` | `colors.php:color_pack` | hex format |
| `color_pack((0,0,0))` → `"#000000"` | black edge case | zero padding |
| `color_rgb_to_hsl((1.0,0.0,0.0))` → `(0.0, 1.0, 0.5)` | `colors.php:color_rgb_to_hsl` | red=hue 0 |
| `color_hsl_to_rgb((0.0,1.0,0.5))` → `(1.0,0.0,0.0)` | inverse of above | round-trip |
| `rgb_to_hsv((255,0,0))` → `(0.0,1.0,1.0)` | `colors.php:rgb2hsl` (actually HSV) | red hue 0 |
| `hsv_to_rgb((0.0,1.0,1.0))` → `(255,0,0)` | `colors.php:hsl2rgb` (actually HSV→RGB) | inverse |
| `rgb_to_hsv((0,0,0))` value=0 edge | black: S=0,V=0 | correct degenerate |
| `color_palette` on missing file → `[]` | graceful failure | no exception |
| `calculate_avg_color` on missing file → `None` | graceful failure | None |

**Fixtures:** No mocks needed. Provide minimal 1×1 PNG bytes for image tests (create with `struct.pack`).

---

### B1-2: `utils/misc.py`
**PHP source:** `ttrss/include/functions.php:convert_timestamp`, `make_local_datetime`, `smart_date_time`

| Test | PHP behavior traced | Assert |
|------|---------------------|--------|
| `truncate_string("hello world", 5)` → `"hello…"` | `functions.php:truncate_string mb_substr+suffix` | truncated + ellipsis |
| `truncate_string("hi", 10)` → `"hi"` | no truncation when short | unchanged |
| `truncate_string("", 10)` → `""` | empty input | empty |
| `make_local_datetime(ts, owner_uid=N)` returns string | `functions.php:make_local_datetime` | non-empty string |
| UTC→user TZ conversion (mock USER_TIMEZONE="Europe/London") | TZ applied to display | correct offset |
| Invalid TZ → falls back to UTC | `functions.php` TZ fallback | no exception |
| `make_local_datetime(None)` → `""` | NULL timestamp in PHP → empty string | empty |
| `_pref(owner_uid, "X", "default")` fallback when no context | helper returns default | default value |

**Fixtures:** Mock `get_user_pref` to return timezone string. Flask app context for session-dependent paths.

---

### B1-3: `utils/mail.py`
**PHP source:** `ttrss/classes/ttrssmailer.php:quickMail`

| Test | PHP behavior traced | Assert |
|------|---------------------|--------|
| `send_mail(to, "", subject, body)` with mock SMTP → True | `ttrssMailer::quickMail` returns bool | True |
| SMTP connection error → returns False, no exception | PHP returns false on error | False, no raise |
| `is_html=True` → MIME multipart/alternative with text fallback | PHP ContentType=text/html | two parts |
| `is_html=False` → plain text only | PHP plain text path | single part |
| `SMTP_LOGIN` set → `conn.login()` called | PHP `SMTPAuth=true` | login called |
| `SMTP_LOGIN` empty → no login | PHP `SMTPAuth=false` | login not called |
| From header: `"Name <email>"` when SMTP_FROM_NAME set | PHP From header format | correct header |
| From header: `"email"` when no name | PHP omits name | bare address |
| `to_name` set → `"Name <email>"` in To | PHP quickMail to_name | correct To |

**Fixtures:** `unittest.mock.patch("smtplib.SMTP")` or `smtplib.SMTP_SSL`. Set `SMTP_SERVER`, `SMTP_FROM_ADDRESS` env vars.

---

### B1-4: `http/client.py`
**PHP source:** `ttrss/include/functions.php:fetch_file_contents`, `functions2.php:fix_url`, `validate_feed_url`, `rewrite_relative_url`

| Test | PHP behavior traced | Assert |
|------|---------------------|--------|
| `fix_url("example.com")` → `"http://example.com/"` | `functions2.php:fix_url` adds http:// | correct |
| `fix_url("feed://x.com")` → `"http://x.com/"` | feed: → http: | converted |
| `fix_url("https://x.com/path")` → unchanged | has scheme + path, no trailing slash added | unchanged |
| `fix_url("https://x.com")` → `"https://x.com/"` | trailing slash added to bare domain | slash added |
| `fix_url("http:///")` → `""` | degenerate case returns empty | empty string |
| `validate_feed_url("http://x.com")` → True | `functions2.php:validate_feed_url` http ok | True |
| `validate_feed_url("https://x.com")` → True | https ok | True |
| `validate_feed_url("feed://x.com")` → True | feed ok | True |
| `validate_feed_url("ftp://x.com")` → False | ftp rejected | False |
| `validate_feed_url("javascript:x")` → False | js rejected | False |
| `validate_feed_url("example.com")` → False | no scheme → False | False |
| `rewrite_relative_url("http://x.com/", "img.png")` → `"http://x.com/img.png"` | `functions2.php:rewrite_relative_url` relative | resolved |
| `rewrite_relative_url("http://x.com/a/b", "../img.png")` → `"http://x.com/img.png"` | parent traversal | correct |
| `rewrite_relative_url("http://x.com/", "http://other.com/x")` → unchanged | absolute passthrough | unchanged |
| `rewrite_relative_url("http://x.com/", "//cdn.com/x")` → unchanged | protocol-relative passthrough | unchanged |
| `get_feeds_from_html("http://x.com/", html_with_rss_link)` → `{url: title}` | `functions2.php:get_feeds_from_html` | correct dict |
| `get_feeds_from_html(…, html_no_feeds)` → `{}` | no link tags → empty | empty dict |

**Fixtures:** None for pure functions. For `fetch_file_contents`, mock `httpx.AsyncClient`.

---

### B1-5: `articles/sanitize.py`
**PHP source:** `ttrss/include/functions2.php:sanitize` (lines 831–965), `strip_harmful_tags` (lines 967–997)

| Test | PHP behavior traced | Assert |
|------|---------------------|--------|
| `sanitize("")` → `""` | `functions2.php:834` early return on empty | empty string |
| `sanitize("<p>hello</p>")` → contains `<p>hello</p>` | allowed element preserved | p preserved |
| `sanitize("<script>x</script>")` → no `<script>` | `strip_harmful_tags` removes disallowed | stripped |
| `sanitize('<a href="/rel">x</a>', site_url="http://x.com")` → absolute href | `functions2.php:855` rewrite href | absolute URL |
| `sanitize('<img src="/img.png">', site_url="http://x.com")` → absolute src | `functions2.php:861` rewrite img src | absolute URL |
| All `<a>` get `target="_blank"` | `functions2.php:892` adds target | attribute present |
| All `<a>` get `rel="noreferrer"` | `functions2.php:857` adds rel | attribute present |
| `<iframe>` removed when `has_sandbox=False` | `functions2.php:915` hasSandbox gate | no iframe |
| `<iframe>` kept when `has_sandbox=True` | iframe in allowed_elements | iframe present |
| `<iframe>` gets `sandbox="allow-scripts"` | `functions2.php:897` | sandbox attr |
| `id`, `style`, `class` attrs stripped | `functions2.php:917` disallowed_attributes | attrs removed |
| `onclick`, `onload` attrs stripped | `functions2.php:981` on* pattern | attrs removed |
| `href` attr preserved on `<a>` | not in disallowed set | href kept |
| `force_remove_images=True` replaces `<img>` with link | `functions2.php:877` | img → a link |
| `highlight_words=["foo"]` wraps match in span | `functions2.php:933` | span.highlight |
| `highlight_words` case-insensitive | `/foo/i` in PHP | FOO also wrapped |
| Malformed HTML → returns original content | `functions2.php:834` parse failure path | no exception |
| HOOK_SANITIZE plugin returning None → doc unchanged | `functions2.php:921-927` | content unchanged |
| HOOK_SANITIZE plugin returning `[doc,elems,attrs]` → all updated | `functions2.php:922-924` | doc updated |

**Fixtures:** Mock `get_plugin_manager()` with pluggy PM that has no implementations (default) or mock implementations.

---

## Batch 2 — DB-Mocked CRUD and Service Layers

**Files:** `prefs/ops.py`, `prefs/feeds_crud.py`, `prefs/filters_crud.py`, `prefs/labels_crud.py`, `prefs/user_prefs_crud.py`, `prefs/users_crud.py`, `tasks/digest.py`, `auth/register.py`, `auth/authenticate.py`, `feeds/browser.py`, `feeds/opml.py`  
**Pattern:** `MagicMock` session with `.execute().scalar*()`, `.query().filter*().first()`, `.add()`, `.commit()`.

---

### B2-1: `prefs/ops.py`
**PHP source:** `ttrss/include/db-prefs.php:Db_Prefs::read`, `set`, `initialize_user_prefs`

| Test | PHP behavior | Assert |
|------|-------------|--------|
| `get_user_pref(1, "X")` with user row → returns user value | user override takes precedence | user value |
| `get_user_pref(1, "X")` no user row, system row exists → def_value | `db-prefs.php:get_pref` fallback | def_value |
| `get_user_pref(1, "X")` no rows → None + debug log | `user_error` in PHP | None |
| `get_user_pref(1, "X", profile=5)` → filters profile=5 | `db-prefs.php:$profile_qpart` | profile filter |
| `get_user_pref(1, "X", profile=None)` → filters profile IS NULL | NULL profile path | null filter |
| `set_user_pref(1, "X", "v")` → merge + commit called | `db-prefs.php:set_pref INSERT/UPDATE` | merge called |
| `get_schema_version()` with row → returns int | `functions.php:get_schema_version` | int value |
| `get_schema_version()` no row → 0 | empty ttrss_version table | 0 |
| `initialize_user_prefs(1)` → merge called per system pref | `db-prefs.php:initialize_user_prefs` | N merges |

---

### B2-2: `prefs/feeds_crud.py`
**PHP source:** `ttrss/classes/pref/feeds.php`

| Test | PHP behavior | Assert |
|------|-------------|--------|
| `save_feed_settings(s, fid, data, uid)` → feed updated | `pref/feeds.php:editsaveops` UPDATE | execute called |
| `save_feed_settings(s, fid, {"auth_pass":"x"}, uid)` → `auth_pass_encrypted=True` | crypt.php encrypt + flag | flag set |
| `batch_edit_feeds(s, uid, fids, data)` → all feeds updated | `pref/feeds.php:editsaveops(true)` batch | UPDATE per fid |
| `batch_subscribe_feeds(s, uid, "http://a.com\nhttp://b.com\n", None, "", "")` → 2 results | `pref/feeds.php:batchAddFeeds` | 2 subscriptions |
| `batch_subscribe_feeds(s, uid, "not-a-url\n", …)` → invalid_url status | `validate_feed_url` gate | invalid_url |
| `batch_subscribe_feeds(s, uid, "http://a.com\n", …)` existing feed → already_subscribed | duplicate check | already_subscribed |
| `save_feed_order(s, uid, order_json)` → `order_id + cat_id` updated | `pref/feeds.php:savefeedorder` | execute called |
| `get_inactive_feeds(s, uid)` → list of dicts | `pref/feeds.php:inactiveFeeds` | list |
| `rescore_feed_impl(s, fid, uid)` → score UPDATEs executed | `pref/feeds.php:rescore` | UPDATE per score |
| `rescore_feed_impl` fetches actual article tags (not []) | `pref/feeds.php:1116 get_article_tags` | tags passed |
| `clear_feed_articles(s, fid, uid, icons_dir)` → user_entries deleted | `pref/feeds.php:clear` | DELETE called |
| `remove_feed(s, fid, uid, icons_dir)` → ccache_remove called | `pref/feeds.php:remove ccache_remove` | ccache called |
| `update_feed_access_key(s, uid, fid, is_cat)` existing → key updated | `pref/feeds.php:update_feed_access_key` | new key returned |

---

### B2-3: `prefs/filters_crud.py`
**PHP source:** `ttrss/classes/pref/filters.php`

| Test | PHP behavior | Assert |
|------|-------------|--------|
| `get_filter_rows(uid)` → ordered list | `pref/filters.php:getfiltertree` | query called |
| `create_filter(uid, data)` → INSERT + commit | `pref/filters.php:add` | add called |
| `update_filter(fid, uid, data)` → UPDATE + commit | `pref/filters.php:editSave` | execute called |
| `fetch_filter(fid, uid)` exists → returns row | `pref/filters.php:edit` SELECT | row returned |
| `fetch_filter(fid, uid)` wrong owner → None | owner_uid filter | None |
| `fetch_filter_rules(fid)` → list of rule rows | `pref/filters.php:edit line 282` | list |
| `delete_filter(fid, uid)` → DELETE + commit | `pref/filters.php:remove` | delete called |
| `save_rules_and_actions(fid, rules, actions)` → DELETE old + INSERT new | `pref/filters.php:saveRulesAndActions` | savepoint used |
| `save_rules_and_actions` with invalid regex → skipped | `pref/filters.php:@preg_match` | invalid not inserted |
| `join_filters(uid, base_id, merge_ids)` → rules moved to base | `pref/filters.php:join` | UPDATE filter_id |
| `join_filters` with non-owned base_id → no-op | ownership check | no UPDATE |
| `optimize_filter(fid)` → duplicate rules removed | `pref/filters.php:optimizeFilter` | deduplication |

---

### B2-4: `prefs/labels_crud.py`
**PHP source:** `ttrss/classes/pref/labels.php`

| Test | PHP behavior | Assert |
|------|-------------|--------|
| `is_caption_taken(uid, caption)` → True if exists | `pref/labels.php:save duplicate check` | True |
| `is_caption_taken(uid, caption)` → False if not | unique | False |
| `rename_label(lid, uid, new_caption)` → UPDATE title | `pref/labels.php:save UPDATE caption` | execute called |
| `set_label_color(lid, uid, fg, bg)` → UPDATE colors | `pref/labels.php:colorset` | execute called |
| `reset_label_color(lid, uid)` → UPDATE to "" | `pref/labels.php:colorreset` | empty colors set |
| `delete_label(lid, uid)` → DELETE + commit | `pref/labels.php:remove` | delete called |

---

### B2-5: `prefs/user_prefs_crud.py`
**PHP source:** `ttrss/classes/pref/prefs.php`

| Test | PHP behavior | Assert |
|------|-------------|--------|
| `get_user_details(uid)` existing → dict with email, login, etc. | `pref/prefs.php:userdetails` | dict keys |
| `get_user_details(999)` not found → None | not found | None |
| `update_profile(uid, email, full_name)` → execute + commit | `pref/prefs.php:saveprofile` | execute called |
| `clear_digest_sent_time(uid)` → UPDATE last_digest_sent=NULL | `pref/prefs.php:saveconfig line 109` | NULL update |
| `reset_user_prefs(uid)` → DELETE + initialize_user_prefs | `pref/prefs.php:resetconfig` | delete called |
| `reset_user_prefs` uses flush before init | savepoint fix | flush called |
| `set_otp_enabled(uid, True)` → UPDATE otp_enabled=True + commit | `pref/prefs.php:otpenable` | True set |

---

### B2-6: `prefs/users_crud.py`
**PHP source:** `ttrss/classes/pref/users.php`

| Test | PHP behavior | Assert |
|------|-------------|--------|
| `find_user_by_login("admin")` → user row | `pref/users.php:add line 215` duplicate check | row returned |
| `find_user_by_login("nobody")` → None | not found | None |
| `create_user("newuser")` → INSERT + initialize_prefs | `pref/users.php:add INSERT` | add called |
| `create_user` returns dict with login + tmp_password | temp password generation | keys present |
| `update_user(uid, login, 0, email)` → UPDATE + commit | `pref/users.php:editSave` | execute called |
| `update_user` caps access_level at 10 | security cap | ≤ 10 |
| `update_user` resets otp_enabled on every update | `pref/users.php:191 otp_enabled=false` | otp_enabled False |
| `delete_user(uid)` → DELETE tags + feeds + user | `pref/users.php:remove` cascade | 3 deletes |
| `reset_user_password(uid)` → new hash + salt="" | `pref/users.php:resetUserPassword` | hash updated |
| `reset_user_password(999)` → None | not found | None |

---

### B2-7: `tasks/digest.py`
**PHP source:** `ttrss/include/digest.php:prepare_headlines_digest`, `send_headlines_digests`

| Test | PHP behavior | Assert |
|------|-------------|--------|
| `prepare_headlines_digest(uid)` no rows → None | `digest.php:65-67` no headlines | None |
| `prepare_headlines_digest(uid)` with rows → dict | `digest.php:132-182` build output | dict keys |
| Result `article_count` matches row count | `digest.php:$headlines_count` | correct count |
| Result `affected_ids` is list of ref_ids | `digest.php:$affected_ids` | correct ids |
| HTML contains feed name in `<h3>` | `digest.php:addBlock('feed')` | feed title present |
| HTML excerpt truncated at 300 chars + `"..."` | `digest.php:161 truncate_string(...,300)` | truncated |
| HTML tags stripped from excerpt | `digest.php:162 strip_tags` | no HTML tags |
| `ENABLE_FEED_CATS=true` → `"Cat / Feed"` in title | `digest.php:171` ENABLE_FEED_CATS | cat prefix |
| `ENABLE_FEED_CATS=false` → no prefix | not set | no prefix |
| User timezone applied to date/time display | `digest.php:93-97 convert_timestamp` | local time |
| `send_headlines_digests()` skips user with `DIGEST_ENABLE=false` | `digest.php:29` pref gate | send not called |
| `send_headlines_digests()` respects 2h time window | `digest.php:33-34` preferred_ts check | timing check |
| `send_headlines_digests()` calls catchup if `DIGEST_CATCHUP=true` | `digest.php:61` catchup | catchup called |
| `send_headlines_digests()` updates `last_digest_sent` | `digest.php:69-71` UPDATE | update called |

**Fixtures:** Mock `db.session` with rows. Mock `get_user_pref`. Mock `send_mail`.

---

### B2-8: `auth/register.py`
**PHP source:** `ttrss/register.php`, `ttrss/include/functions.php:register_user`

| Test | PHP behavior | Assert |
|------|-------------|--------|
| `check_username_available(s, "new")` → True | `register.php:74` username check | True |
| `check_username_available(s, "admin")` → False (exists) | duplicate | False |
| `cleanup_stale_registrations(s)` → deletes old unactivated | `register.php:60-68 stale cleanup` | DELETE called |
| `register_user(s, "user", "e@x.com", 0, True)` → success | `register.php:247-314` full flow | success dict |
| `register_user` with `reg_max_users=1` full → max_users_reached | `register.php` user count check | error key |
| `register_user` with `enable_registration=False` → disabled | `register.php:99` | error key |
| `register_user` duplicate login → error | `register.php` duplicate check | error key |
| New user has `access_level=0` | PHP registers with access_level=0 | 0 |
| `registration_slots_feed(…)` returns XML string | `register.php:24-57` Atom feed | valid XML |

---

### B2-9: `auth/authenticate.py`
**PHP source:** `ttrss/include/functions.php:authenticate_user`

| Test | PHP behavior | Assert |
|------|-------------|--------|
| `authenticate_user("admin", "pass")` correct → user object | `functions.php:authenticate_user` | user returned |
| `authenticate_user("admin", "wrong")` → None | password mismatch | None |
| `authenticate_user("nobody", "pass")` → None | user not found | None |
| `authenticate_user` in SINGLE_USER_MODE → returns user 1 without password check | `functions.php:750` single user | user id=1 |
| Plugin hook `HOOK_AUTH_USER` called before DB check | `functions.php:711-718` plugin first | hook fired |
| Plugin returns user_id → short-circuits DB check | `functions.php:715-716 break` | DB not queried |

---

### B2-10: `feeds/browser.py`
**PHP source:** `ttrss/include/feedbrowser.php`

| Test | PHP behavior | Assert |
|------|-------------|--------|
| `make_feed_browser(s, uid, limit, search, mode=1)` → list | `feedbrowser.php:make_feed_browser mode=1` | list of dicts |
| mode=1 result has keys: feed_url, title, site_url, subscribers | PHP response format | all keys |
| mode=1 sorted by subscribers desc | `feedbrowser.php ORDER BY subscribers DESC` | descending |
| mode=1 search="python" → only matching feeds | LIKE search | filtered |
| mode=2 → archived feeds for user | `feedbrowser.php mode=2` | user's archives |
| mode=2 result has subscriber=0 | archived feeds have no subscribers | 0 |
| Limit=5 returns ≤ 5 items | LIMIT clause | ≤ 5 |

---

### B2-11: `feeds/opml.py`
**PHP source:** `ttrss/classes/opml.php`

| Test | PHP behavior | Assert |
|------|-------------|--------|
| `csrf_ignore()` → `["import", "export"]` | `opml.php:csrf_ignore` | exact list |
| `opml_export_full(s, uid)` → valid UTF-8 XML string | `opml.php:opml_export` | starts `<?xml` |
| Export contains `<opml version="1.0">` | OPML version | version attr |
| Export with no feeds → `<body/>` or empty body | empty state | no crash |
| `hide_private_feeds=True` excludes private feeds | `opml.php:opml_export $hide_private_feeds` | private excluded |
| `include_settings=True` includes `<outline text="tt-rss-prefs">` | `opml.php:133-143` prefs section | prefs outline |
| `include_settings=False` no prefs section | PHP `$include_settings` gate | no prefs |
| Empty category removed by `_remove_empty_folders` | `opml.php:232-238 DOMXpath` | empty cat gone |
| `import_opml(s, uid, xml)` valid OPML → dict with "imported" key | `opml.php:opml_import` | dict |
| `import_opml(s, uid, malformed_xml)` → dict with errors | bad XML handling | errors key |
| Round-trip: export then import → same feed count | export↔import parity | consistent |

---

## Batch 3 — HTTP Blueprint Handlers

**Files:** `blueprints/prefs/feeds.py`, `blueprints/prefs/filters.py`, `blueprints/prefs/labels.py`, `blueprints/prefs/user_prefs.py`, `blueprints/prefs/users.py`, `blueprints/public/views.py`, `blueprints/backend/views.py`  
**Pattern:** Use `app.test_client()` + mock CRUD layer. One test per route: status code + response shape.

---

### B3-1: `blueprints/prefs/feeds.py`
**PHP source:** `ttrss/classes/pref/feeds.php`

| Route | Test | Status | Assert |
|-------|------|--------|--------|
| `GET /feeds/<id>` | valid feed | 200 | JSON with feed data + plugin fields |
| `GET /feeds/<id>` | wrong owner | 404 | error key |
| `POST /feeds/<id>` | valid save | 200 | `{"status":"ok"}` |
| `POST /feeds/<id>` | not found | 404 | error key |
| `POST /feeds/batch_edit` | valid batch | 200 | `{"status":"ok"}` |
| `POST /feeds/order` | valid JSON | 200 | ok |
| `DELETE /feeds/<id>` | valid delete | 200 | ok |
| `DELETE /feeds/<id>` | self-delete guard | 400 | error |
| `POST /feeds/rescore/<id>` | valid | 200 | ok |
| `GET /feeds/keys/opml/regen` | valid | 200 | `{"key": ...}` |
| Hook `HOOK_PREFS_EDIT_FEED` fires on GET | `pref/feeds.php:748` | mock asserted |
| Hook `HOOK_PREFS_SAVE_FEED` fires on POST | `pref/feeds.php:981` | mock asserted |

---

### B3-2: `blueprints/prefs/filters.py`
**PHP source:** `ttrss/classes/pref/filters.php`

| Route | Test | Status | Assert |
|-------|------|--------|--------|
| `GET /filters` | list | 200 | `{"filters":[...]}` |
| `GET /filters/<id>` | valid | 200 | filter + rules + actions |
| `GET /filters/<id>` | wrong owner | 404 | error |
| `POST /filters` | create | 201 | `{"id":...}` |
| `POST /filters/<id>` | update | 200 | ok |
| `DELETE /filters/<id>` | delete | 200 | ok |
| `POST /filters/test` | with recent articles | 200 | `{"matches":[...]}` |
| `POST /filters/join` | merge | 200 | ok |
| `POST /filters/order` | reorder | 200 | ok |

---

### B3-3: `blueprints/prefs/labels.py`
**PHP source:** `ttrss/classes/pref/labels.php`

| Route | Test | Status | Assert |
|-------|------|--------|--------|
| `GET /labels` | list | 200 | `{"labels":[...]}` |
| `POST /labels` | create new | 201 | `{"id":...}` |
| `POST /labels` | duplicate caption | 409 | error |
| `POST /labels` | empty caption | 400 | error |
| `POST /labels/<id>` | rename | 200 | ok |
| `DELETE /labels/<id>` | delete | 200 | ok |
| `POST /labels/<id>/color` | set color | 200 | ok |
| `POST /labels/<id>/color/reset` | reset | 200 | ok |

---

### B3-4: `blueprints/prefs/user_prefs.py`
**PHP source:** `ttrss/classes/pref/prefs.php`

| Route | Test | Status | Assert |
|-------|------|--------|--------|
| `POST /user/password` | correct old pass | 200 | ok |
| `POST /user/password` | wrong old pass | 403 | error |
| `POST /user/password` | mismatch confirm | 400 | error |
| `POST /user/config` | save pref | 200 | ok |
| `POST /user/config` | DIGEST_PREFERRED_TIME changed → clears | 200 | clear called |
| `POST /user/config` | DIGEST_PREFERRED_TIME same → not cleared | 200 | clear NOT called |
| `POST /user/config/reset` | reset prefs | 200 | ok |
| `POST /user/otp/enable` | correct pass + OTP | 200 | ok |
| `POST /user/otp/enable` | wrong pass | 403 | error |
| `POST /user/otp/disable` | correct pass | 200 | ok |
| `POST /user/otp/disable` | wrong pass | 403 | error |

---

### B3-5: `blueprints/prefs/users.py` (admin only)
**PHP source:** `ttrss/classes/pref/users.php`

| Route | Test | Status | Assert |
|-------|------|--------|--------|
| `GET /users` | as admin | 200 | `{"users":[...]}` |
| `GET /users` | as non-admin | 403 | insufficient_access_level |
| `POST /users` | create | 201 | ok |
| `POST /users` | duplicate login | 409 | error |
| `POST /users/<id>` | update | 200 | ok |
| `POST /users/<id>` | access_level=99 capped at 10 | 200 | level ≤ 10 |
| `DELETE /users/<id>` | delete other | 200 | ok |
| `DELETE /users/<id>` | self-delete | 400 | cannot_delete_self |
| `POST /users/<id>/reset_password` | valid | 200 | `{"tmp_password":...}` |

---

### B3-6: `blueprints/public/views.py` (key routes)
**PHP source:** `ttrss/classes/handler/public.php`

| Route | Test | Status | Assert |
|-------|------|--------|--------|
| `GET /` | health check | 200 | `{"status":"ok"}` |
| `POST /login` | correct creds | 302 | redirect |
| `POST /login` | wrong creds | 401 | error |
| `GET /logout` | authenticated | 302 | redirect |
| `GET /getUnread?login=x` | valid user | 200 | integer string |
| `GET /getUnread?login=nobody` | not found | 200 | `"-1;User not found"` |
| `POST /register` | valid new user | 200 | ok + email sent |
| `POST /register` | captcha wrong | 400 | captcha_failed |
| `POST /register` | reg disabled | 403 | registration_disabled |
| `POST /forgotpass` `method=do` | valid user | 200 | instructions sent + email |
| `GET /forgotpass?hash=x&login=y` | valid token | 200 | password reset + email |
| `GET /forgotpass?hash=x&login=y` | expired token | 400 | error |
| `GET /opml?key=x` | valid key | 200 | XML content-type |
| `GET /opml?key=x` | invalid key | 403 | error |

---

### B3-7: `blueprints/backend/views.py` (sample — highest-impact routes)
**PHP source:** `ttrss/classes/rpc.php`, `ttrss/classes/article.php`

Focus on the 10 most frequently used dispatch targets:

| Handler | Test | Assert |
|---------|------|--------|
| `catchupFeed` is_cat=false | 200 | `{"status":"OK"}` |
| `markSelected` mode=0 | 200 | OK |
| `markSelected` mode=2 (toggle) | 200 | OK |
| `catchupSelected` | 200 | OK |
| `getAllCounters` | 200 | counters list |
| `getHeadlines` (simple) | 200 | headlines array |
| `sanitizeCheck` | 200 | init-params present |
| `updateFeedBrowser` mode=1 | 200 | content list |
| `updateFeedBrowser` mode=2 | 200 | archived list |
| `togglepref` with bool pref | 200 | `{"param":..,"value":..}` |

---

## Batch 4 — Plugin System

**Files:** `plugins/manager.py`, `plugins/loader.py`, `plugins/auth_internal/__init__.py`, `plugins/storage.py`

---

### B4-1: `plugins/manager.py`
**PHP source:** `ttrss/classes/pluginhost.php`

| Test | PHP behavior | Assert |
|------|-------------|--------|
| `get_plugin_manager()` → PluginManager | `pluginhost.php:getInstance` singleton | not None |
| `get_plugin_manager()` twice → same instance | singleton | identical |
| `reset_plugin_manager()` → next call returns new instance | test isolation | new instance |
| `PluginHost()` → empty dicts for handlers/commands/etc. | `pluginhost.php:__construct` | all empty |
| `PluginHost.add_handler("test", sender)` → stored | `pluginhost.php:add_handler` | lookup works |
| `PluginHost.lookup_handler("test")` → sender | `pluginhost.php:lookup_handler` | sender returned |
| `PluginHost.add_command("cmd", "desc", sender)` | `pluginhost.php:add_command` | stored |
| `PluginHost.add_api_method("m", sender)` | `pluginhost.php:add_api_method` | stored |
| `PluginHost.get_plugins()` → dict | `pluginhost.php:get_plugins` | dict type |
| `PluginHost.get_plugin("name")` None → None | `pluginhost.php:get_plugin` | None |

---

### B4-2: `plugins/loader.py`
**PHP source:** `ttrss/classes/pluginhost.php:init_plugins`, `load_user_plugins`

| Test | PHP behavior | Assert |
|------|-------------|--------|
| `_load_plugin("auth_internal", KIND_SYSTEM, None)` → registers | `pluginhost.php:loadPlugin` | plugin in registry |
| `_load_plugin("nonexistent", KIND_ALL, None)` → returns False | missing plugin | False |
| KIND filter: `_load_plugin("auth_internal", KIND_USER, None)` → False (is SYSTEM) | kind mismatch | False |
| `load_user_plugins(uid)` with `_ENABLED_PLUGINS=""` → no user plugins | empty pref | no user plugins added |

---

### B4-3: `plugins/auth_internal/__init__.py`
**PHP source:** `ttrss/plugins/auth_internal/init.php`

| Test | PHP behavior | Assert |
|------|-------------|--------|
| `hook_auth_user("admin", correct_pass)` → user.id | `auth_internal/init.php:authenticate` | integer > 0 |
| `hook_auth_user("admin", wrong_pass)` → None | wrong password | None |
| `hook_auth_user("nobody", "pass")` → None | user not found | None |
| `hook_auth_user("", "pass")` → None | empty login gate | None |
| argon2 hash upgrade on successful login | `auth_internal/init.php:91-101` | pwd_hash updated |
| `otp_enabled=True` with no OTP code → None | `auth_internal/init.php:42-70` OTP required | None |
| `otp_enabled=True` with correct TOTP → user.id | OTP verified | integer |
| `otp_enabled=True` with wrong TOTP → None | OTP mismatch | None |

**Fixtures:** Flask app context. Mock `db.session`. Create mock `TtRssUser` with argon2 hash.

---

### B4-4: `plugins/storage.py`
**PHP source:** `ttrss/classes/pluginhost.php:get`, `set`, `clear`

| Test | PHP behavior | Assert |
|------|-------------|--------|
| `save_plugin_data(s, uid, "plugin", data)` → UPSERT | `pluginhost.php:set` | merge called |
| `load_plugin_data(s, uid, "plugin")` → dict | `pluginhost.php:get` | dict or {} |
| `load_plugin_data` missing → empty dict | not found | {} |
| `clear_plugin_data(s, uid, "plugin")` → DELETE | `pluginhost.php:clear` | delete called |

---

## Batch 5 — App Infrastructure

**Files:** `__init__.py`, `celery_app.py`, `errors.py`, `auth/session.py`, `prefs/system_crud.py`

---

### B5-1: `errors.py`
| Test | Assert |
|------|--------|
| `GET /nonexistent` → 404 JSON | `{"error":"not_found"}` or similar |
| Force 500 via route that raises → 500 JSON | no stack trace in body |
| 405 Method Not Allowed → 405 JSON | JSON error |

### B5-2: `__init__.py` (create_app)
| Test | Assert |
|------|--------|
| `create_app(test_config)` returns Flask app | app.testing = True |
| `create_app` without SECRET_KEY raises RuntimeError | startup validation |
| `create_app` with empty FEED_CRYPT_KEY → `FERNET=None` | graceful |
| All blueprints registered | url_map has /api/, /prefs/, etc. |

### B5-3: `celery_app.py`
| Test | Assert |
|------|--------|
| `celery_app` is a Celery instance | isinstance check |
| `update_feed` task registered | in `celery_app.tasks` |
| Beat schedule key `dispatch_feed_updates` exists | schedule dict |

### B5-4: `auth/session.py`
| Test | Assert |
|------|--------|
| `user_loader(uid)` with valid uid → user | user returned |
| `user_loader(uid)` missing → None | None |

### B5-5: `prefs/system_crud.py`
| Test | Assert |
|------|--------|
| `get_system_pref("SCHEMA_VERSION")` → value | query called |
| `get_system_pref("MISSING")` → None | None |

---

## Implementation Notes

### Fixture conventions
```python
# All DB tests follow this pattern:
session = MagicMock()
session.execute.return_value.scalar_one_or_none.return_value = mock_row
session.execute.return_value.scalars.return_value.all.return_value = [mock_row]
```

### Flask context for blueprint tests
```python
# Use existing app fixture from conftest.py
def test_route(app, client):
    with patch("ttrss.blueprints.prefs.feeds.feeds_crud") as mock_crud:
        mock_crud.get_feed_for_edit.return_value = {"id": 1, "title": "Test"}
        resp = client.get("/feeds/1")
        assert resp.status_code == 200
```

### PHP source consultation rule
Every test docstring must include:
```python
"""
Source: ttrss/include/functions2.php:sanitize line 834
PHP: if (!$res) return ''
Assert: sanitize("") returns ""
"""
```

---

## Estimated test count by batch

| Batch | Files | New tests | Target coverage |
|-------|-------|-----------|-----------------|
| B1 Pure functions | 5 | ~65 | >90% each |
| B2 CRUD + services | 11 | ~85 | >80% each |
| B3 Blueprints | 7 | ~60 | >80% each |
| B4 Plugins | 4 | ~25 | >80% each |
| B5 Infrastructure | 5 | ~15 | >80% each |
| **Total** | **32** | **~250** | **>80% all** |
