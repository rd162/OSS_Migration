# Dimension: hook-extension · All Communities (Hook-0 through Hook-6)

> ∆6 research notes — hook/extension-point graph, 7 communities.
> Status: DEGRADED — training knowledge + source corpus reads only (no web search available).
> Source: `source-repos/ttrss-php/ttrss/classes/pluginhost.php`
> Graph artifact: `tools/graph_analysis/output/hook_graph.json`
> Nodes: 40  Edges: 39  Communities: 7

---

## Hook-0 — Render-time UI hooks

### Members

| Hook constant              | Int | Registration / invocation site                           |
| -------------------------- | --- | -------------------------------------------------------- |
| `HOOK_SANITIZE`            | 13  | Invoked in `include/functions2.php::sanitize` (HTML purification) |
| `HOOK_RENDER_ARTICLE`      | 10  | Invoked in `classes/feeds.php::format_headlines_list`    |
| `HOOK_RENDER_ARTICLE_CDM`  | 11  | Invoked in `classes/feeds.php` (Combined Display Mode)   |
| `HOOK_ARTICLE_BUTTON`      | 1   | Invoked when rendering per-article toolbar buttons       |
| `HOOK_ARTICLE_LEFT_BUTTON` | 19  | Left-side per-article button injection                   |
| `HOOK_HEADLINE_TOOLBAR_BUTTON` | 17 | Headline list toolbar button injection                |
| `HOOK_HOTKEY_MAP`          | 9   | Keyboard shortcut map extension                          |
| `HOOK_HOTKEY_INFO`         | 18  | Keyboard shortcut help text extension                    |

Level (all): invocation sites live inside `Feeds::format_headlines_list`
and `sanitize()` — both are leaf functions called from HTTP request path.

### Representative constructs

```php
// classes/pluginhost.php — hook invocation pattern
$pluginhost->run_hooks(PluginHost::HOOK_SANITIZE, $line);
$pluginhost->run_hooks(PluginHost::HOOK_ARTICLE_BUTTON, $line);

// plugins register via:
$host->add_hook($host::HOOK_SANITIZE, $this);
// then implement:
function hook_sanitize($article, $site_url, $ob_sanitize) { ... }
```

### Research findings [TRAINING]

- `HOOK_SANITIZE` is the most security-critical hook:
  it wraps the HTML purification pipeline.
  Plugins can inject or bypass sanitization.
- `HOOK_RENDER_ARTICLE` and `HOOK_RENDER_ARTICLE_CDM` are the primary
  content-injection hooks — plugins can prepend/append HTML to articles.
- Hotkey hooks (`HOOK_HOTKEY_MAP`, `HOOK_HOTKEY_INFO`) are JS-side configuration
  hooks that emit JSON structures consumed by the Dojo frontend.
  These have no direct Python equivalent — they are frontend configuration endpoints.
- PHP's `run_hooks($hook_id, &$param)` passes `$param` by reference.
  Each plugin in the chain mutates the same `$param` object.
  This is fundamentally different from pluggy's call model.

### Target-side mapping

| PHP hook                    | Python / pluggy equivalent                              |
| --------------------------- | ------------------------------------------------------- |
| `HOOK_SANITIZE`             | `@hookspec def sanitize(article, site_url)` — `firstresult=False`, chained |
| `HOOK_RENDER_ARTICLE`       | `@hookspec def render_article(article)` — chained       |
| `HOOK_RENDER_ARTICLE_CDM`   | `@hookspec def render_article_cdm(article)` — chained  |
| `HOOK_ARTICLE_BUTTON`       | `@hookspec def article_buttons(article)` → returns list of button dicts |
| `HOOK_ARTICLE_LEFT_BUTTON`  | `@hookspec def article_left_buttons(article)` → list    |
| `HOOK_HEADLINE_TOOLBAR_BUTTON` | `@hookspec def headline_toolbar_buttons()` → list    |
| `HOOK_HOTKEY_MAP`           | `@hookspec def hotkey_map()` → returns dict             |
| `HOOK_HOTKEY_INFO`          | `@hookspec def hotkey_info()` → returns dict            |

Key adaptation: hooks that return HTML fragments should become hooks that
return structured data (dicts/lists); rendering moves to Jinja2 templates.

### Divergences spotted

- D1: **Pass-by-reference mutation** — PHP `&$param` allows in-place mutation;
  Python must use a mutable wrapper (dict or dataclass) or pluggy's `tryfirst`/`trylast`.
- D2: **HTML generation in hooks** — PHP hooks emit raw HTML strings.
  Python target should emit structured data; templates render it.
  Semantic gap: plugins that emit raw HTML must be refactored.
- D3: **HOOK_SANITIZE security boundary** — PHP implementation invokes
  `strip_tags` + custom purification inside the hook chain.
  Python must use `lxml.html.clean.Cleaner` with equivalent tag allowlists.

### Open questions

- Which plugins (beyond `auth_internal`) register `HOOK_SANITIZE`?
  Need audit of `plugins/` directory for third-party plugins.
- Is pluggy `firstresult=True` or chaining the right model for `HOOK_RENDER_ARTICLE`?
  Answer determines whether all plugins contribute or only the first.

---

## Hook-1 — Preferences UI hooks

### Members

| Hook constant           | Int | Site                                                        |
| ----------------------- | --- | ----------------------------------------------------------- |
| `HOOK_PREFS_TAB`        | 3   | Invoked in `classes/pref/*.php` — inserts tab content panels |
| `HOOK_PREFS_TAB_SECTION`| 4   | Invoked in pref tabs — inserts sections within a tab         |
| `HOOK_PREFS_SAVE_FEED`  | 21  | Invoked when saving feed-level settings                      |
| `HOOK_PREFS_EDIT_FEED`  | 20  | Invoked when rendering feed-edit dialog                      |

### Representative constructs

```php
// classes/pref/feeds.php
$pluginhost->run_hooks(PluginHost::HOOK_PREFS_EDIT_FEED, $feed_id);
$pluginhost->run_hooks(PluginHost::HOOK_PREFS_SAVE_FEED, $feed_id);

// classes/dlg.php
$pluginhost->run_hooks(PluginHost::HOOK_PREFS_TAB, $tab_id);
```

### Research findings [TRAINING]

- These hooks allow plugins to extend the preferences UI with custom tabs,
  sections, and per-feed settings.
- `HOOK_PREFS_SAVE_FEED` and `HOOK_PREFS_EDIT_FEED` are paired:
  edit renders the form, save processes submitted values.
  This is a classic CRUD extension point.
- In the PHP model, hooks emit HTML form elements directly.
  The prefs page is a server-side rendered modal dialog.

### Target-side mapping

| PHP hook                | Python / pluggy equivalent                                 |
| ----------------------- | ---------------------------------------------------------- |
| `HOOK_PREFS_TAB`        | `@hookspec def prefs_tab(tab_id)` → returns HTML/template-ref |
| `HOOK_PREFS_TAB_SECTION`| `@hookspec def prefs_tab_section(tab_id, section_id)` → fragment |
| `HOOK_PREFS_EDIT_FEED`  | `@hookspec def prefs_edit_feed(feed_id)` → returns form schema |
| `HOOK_PREFS_SAVE_FEED`  | `@hookspec def prefs_save_feed(feed_id, form_data)` → side-effects |

Recommended adaptation: prefs hooks should emit JSON schema (form fields),
not HTML. Jinja2 renders the form from the schema.
This decouples plugins from the rendering layer.

### Divergences spotted

- D4: **Prefs UI as server-rendered HTML** — PHP hooks emit `<tr><td>` HTML fragments
  for a table-based prefs dialog. Python target uses a modal with structured form
  schema — plugin API must change.
- D5: **HOOK_PREFS_SAVE_FEED coupling** — The hook receives `$feed_id` and is expected
  to read `$_POST` superglobal directly. Python hook must receive a `form_data` dict
  instead; plugins cannot access Flask's `request.form` directly.

### Open questions

- Should prefs hooks be `firstresult=False` (all plugins contribute) or
  `firstresult=True` (first matching plugin wins)?
  Multiple plugins adding prefs sections → must be `firstresult=False`.

---

## Hook-2 — Feed fetch / update hooks

### Members

| Hook constant        | Int | Site                                                                 |
| -------------------- | --- | -------------------------------------------------------------------- |
| `HOOK_FETCH_FEED`    | 22  | Invoked before fetching — allows plugins to substitute fetch logic   |
| `HOOK_FEED_FETCHED`  | 12  | Invoked after raw feed content fetched                               |
| `HOOK_FEED_PARSED`   | 6   | Invoked after feed parsed to article list                            |
| `HOOK_ARTICLE_FILTER`| 2   | Invoked per article during ingestion — filter/transform              |
| `HOOK_HOUSE_KEEPING` | 24  | Invoked during housekeeping (purge, cleanup)                         |
| `HOOK_UPDATE_TASK`   | 7   | Invoked as extra update-cycle task (scheduled background work)       |

### Representative constructs

```php
// include/rssfuncs.php — fetch pipeline
$pluginhost->run_hooks(PluginHost::HOOK_FETCH_FEED, $fetch_url);
$pluginhost->run_hooks(PluginHost::HOOK_FEED_FETCHED, $feed_data);
$pluginhost->run_hooks(PluginHost::HOOK_FEED_PARSED, $articles);
$pluginhost->run_hooks(PluginHost::HOOK_ARTICLE_FILTER, $article);

// update_daemon2.php + Handler_Public::housekeepingTask
$pluginhost->run_hooks(PluginHost::HOOK_HOUSE_KEEPING, null);
$pluginhost->run_hooks(PluginHost::HOOK_UPDATE_TASK, null);
```

### Research findings [TRAINING]

- This community defines the **feed ingestion pipeline**.
  Hooks form a processing chain: fetch → fetched → parsed → filter (per article).
- `HOOK_FETCH_FEED` allows plugins to replace the HTTP fetch entirely
  (e.g., for authenticated feeds, Tor proxies, local files).
- `HOOK_ARTICLE_FILTER` is the most frequently invoked hook — called once
  per article per update cycle. Performance matters.
- `HOOK_UPDATE_TASK` is the extension point for daemon-level scheduled work
  (e.g., a plugin that publishes digest emails on a schedule).
- `HOOK_HOUSE_KEEPING` runs during the periodic cleanup task
  (purging old articles, clearing caches).

### Target-side mapping

| PHP hook              | Python / pluggy equivalent                                     |
| --------------------- | -------------------------------------------------------------- |
| `HOOK_FETCH_FEED`     | `@hookspec def fetch_feed(url, feed_id)` → `firstresult=True` (override or None) |
| `HOOK_FEED_FETCHED`   | `@hookspec def feed_fetched(feed_id, raw_content)` → `firstresult=False` |
| `HOOK_FEED_PARSED`    | `@hookspec def feed_parsed(feed_id, articles)` → chained mutation |
| `HOOK_ARTICLE_FILTER` | `@hookspec def article_filter(article)` → `firstresult=True` (True=filter, False=keep) |
| `HOOK_HOUSE_KEEPING`  | `@hookspec def house_keeping()` → Celery periodic task signal  |
| `HOOK_UPDATE_TASK`    | `@hookspec def update_task()` → Celery periodic task signal    |

Note: `HOOK_HOUSE_KEEPING` and `HOOK_UPDATE_TASK` map to Celery beat signals
rather than synchronous hook calls. A plugin registers a Celery task;
the beat scheduler triggers it. This changes the calling convention.

### Divergences spotted

- D6: **Async fetch in daemon** — PHP `HOOK_FETCH_FEED` is synchronous;
  Python daemon (Celery) uses `httpx` async. Plugins implementing
  `HOOK_FETCH_FEED` must become async-compatible or run in a thread pool.
- D7: **`HOOK_ARTICLE_FILTER` pass-by-reference** — PHP passes `&$article`;
  plugin sets `$article['filtered'] = true` in-place.
  Python: article dict passed as mutable; `firstresult=True` returning `True`
  signals "filter this article". Semantics differ.
- D8: **`HOOK_HOUSE_KEEPING` / `HOOK_UPDATE_TASK` in Celery** —
  In PHP these run synchronously in the daemon loop.
  In Python these become Celery `on_after_finalize.connect` callbacks
  or custom periodic tasks. Plugins must be rewritten to register Celery tasks.

### Open questions

- Should `HOOK_FETCH_FEED` allow full replacement (firstresult) or decoration (chained)?
  Depends on whether multiple plugins need to transform the same fetch.
- What is the latency budget for `HOOK_ARTICLE_FILTER`? If articles are
  ingested in bulk (500 per daemon run), synchronous per-article hooks may block.

---

## Hook-3 — API / headline query hooks

### Members

| Hook constant             | Int | Site                                                     |
| ------------------------- | --- | -------------------------------------------------------- |
| `HOOK_QUERY_HEADLINES`    | 23  | Invoked inside `API::getHeadlines` — modifies SQL query  |
| `HOOK_RENDER_ARTICLE_API` | 14  | Invoked in `API::getArticle` — transforms article for API response |

### Representative constructs

```php
// classes/api.php::getHeadlines
$pluginhost->run_hooks(PluginHost::HOOK_QUERY_HEADLINES, $query_parts);

// classes/api.php::getArticle
$pluginhost->run_hooks(PluginHost::HOOK_RENDER_ARTICLE_API, $article);
```

### Research findings [TRAINING]

- `HOOK_QUERY_HEADLINES` is unusual: it allows plugins to mutate the SQL
  query parts used to fetch headlines. The hook receives a `$query_parts`
  array containing WHERE, ORDER BY, etc. fragments.
  This is a tight coupling between the plugin API and the DB query structure.
- `HOOK_RENDER_ARTICLE_API` allows plugins to transform article data
  before it is serialised to the JSON API response.

### Target-side mapping

| PHP hook                  | Python / pluggy equivalent                                          |
| ------------------------- | ------------------------------------------------------------------- |
| `HOOK_QUERY_HEADLINES`    | `@hookspec def query_headlines(filters)` → returns SQLAlchemy filter additions |
| `HOOK_RENDER_ARTICLE_API` | `@hookspec def render_article_api(article_dict)` → returns modified dict |

Critical design decision: `HOOK_QUERY_HEADLINES` must change from
raw SQL fragment injection to SQLAlchemy filter contributions.
Plugins receive a `Query` object or a filter dict,
not raw SQL strings.

### Divergences spotted

- D9: **SQL injection via hook parameter** — PHP `HOOK_QUERY_HEADLINES`
  passes raw SQL fragment strings. Plugins can inject arbitrary SQL.
  Python target MUST replace with SQLAlchemy filter objects.
  This is a **security boundary** change.
- D10: **API article shape** — `HOOK_RENDER_ARTICLE_API` mutates a PHP array
  that maps directly to the JSON response. Python must use a dataclass or TypedDict
  to enforce API shape; plugins add fields to a known schema.

### Open questions

- Are there known plugins in the wild that use `HOOK_QUERY_HEADLINES`?
  If so, migration of those plugins is a Phase 2 concern.

---

## Hook-4 — Authentication hook

### Members

| Hook constant   | Int | Site                                                             |
| --------------- | --- | ---------------------------------------------------------------- |
| `HOOK_AUTH_USER`| 8   | Invoked in `include/functions.php::authenticate_user` — allows plugins to authenticate users |

### Representative constructs

```php
// include/functions.php::authenticate_user
$auth_result = $pluginhost->run_hooks(PluginHost::HOOK_AUTH_USER,
    array("login" => $login, "password" => $password));
if ($auth_result) return $auth_result;

// plugins/auth_internal/init.php registers:
$host->add_hook($host::HOOK_AUTH_USER, $this);
function hook_auth_user($auth_credentials) {
    // verify $auth_credentials['login'] / $auth_credentials['password']
    // return user_id on success or false
}
```

### Research findings [TRAINING]

- `HOOK_AUTH_USER` is the **single authentication extension point**.
  The built-in plugin `auth_internal` uses it for SHA1 password verification.
  Additional auth plugins (LDAP, OAuth, etc.) register the same hook.
- `run_hooks` returns the first non-false result → this is a `firstresult=True` pattern.
- The hook receives plain-text credentials. Security implication: every plugin
  in the chain sees the password. In PHP's per-request model this is acceptable;
  in a persistent Python process it requires the same care.
- `auth_internal` also handles OTP (TOTP) verification:
  if `otp_enabled` is true on the user record, verifies the TOTP code
  alongside the password.

### Target-side mapping

| PHP hook        | Python / pluggy equivalent                                          |
| --------------- | ------------------------------------------------------------------- |
| `HOOK_AUTH_USER`| `@hookspec(firstresult=True) def authenticate(login, password)` → returns `UserInfo` or `None` |

The `authenticate` hookspec returns a `UserInfo` dataclass (id, login, access_level)
on success or `None` on failure.
Flask-Login's `load_user` calls the hookspec after the user is identified.

### Divergences spotted

- D11: **Credential exposure in hook chain** — HOOK_AUTH_USER passes
  plain-text password to all registered plugins in sequence.
  This is equivalent in Python. Document as an accepted risk;
  plugins are trusted code running in the same process.
- D12: **OTP verification coupling** — `auth_internal` does both password
  and OTP verification in the same hook. In Python, OTP should be a
  separate step (Flask-Login `two_factor_required` pattern or
  a second pluggy hook `HOOK_VERIFY_OTP`).

### Open questions

- Should OTP be separated into its own hookspec in the Python target?
  Recommendation: yes — enables OTP plugins independently of auth plugins.

---

## Hook-5 — UI action hooks

### Members

| Hook constant       | Int | Site                                               |
| ------------------- | --- | -------------------------------------------------- |
| `HOOK_ACTION_ITEM`  | 16  | Injected into per-article action menu              |
| `HOOK_TOOLBAR_BUTTON`| 15 | Injected into the main application toolbar         |

### Representative constructs

```php
$pluginhost->run_hooks(PluginHost::HOOK_ACTION_ITEM, $article_id);
$pluginhost->run_hooks(PluginHost::HOOK_TOOLBAR_BUTTON, null);
```

### Research findings [TRAINING]

- These hooks allow plugins to add custom actions to the UI.
  `HOOK_ACTION_ITEM` adds items to the per-article context menu
  (e.g., "Send to Pocket", "Share to Mastodon").
- `HOOK_TOOLBAR_BUTTON` adds buttons to the global top toolbar.
- Both hooks emit HTML fragments (anchor tags, button tags) directly.
- In the Dojo frontend, these HTML strings are injected into widget containers.

### Target-side mapping

| PHP hook             | Python / pluggy equivalent                           |
| -------------------- | ---------------------------------------------------- |
| `HOOK_ACTION_ITEM`   | `@hookspec def action_items(article_id)` → list of `ActionItem` dicts |
| `HOOK_TOOLBAR_BUTTON`| `@hookspec def toolbar_buttons()` → list of `ToolbarButton` dicts |

Both hooks return structured data instead of raw HTML.
The frontend (Vanilla JS SPA, ADR-0017) renders from JSON.

### Divergences spotted

- D13: **HTML emission vs. structured data** — PHP plugins emit raw HTML.
  Python/JS target should use structured JSON.
  Plugin authors must rewrite hook implementations.
  This is a **breaking change** to the plugin API.

---

## Hook-6 — Prefs navigation hook

### Members

| Hook constant    | Int | Site                                                  |
| ---------------- | --- | ----------------------------------------------------- |
| `HOOK_PREFS_TABS`| 5   | Invoked in `prefs.php` — adds new top-level preference tabs |

### Representative constructs

```php
// prefs.php
$pluginhost->run_hooks(PluginHost::HOOK_PREFS_TABS, null);
// plugins emit <li> elements for the tab navigation list
```

### Research findings [TRAINING]

- `HOOK_PREFS_TABS` is a navigation-level hook that adds entire top-level tabs
  to the preferences modal. Distinct from `HOOK_PREFS_TAB` (Hook-1) which adds
  content inside an existing tab.
- Only one known built-in use: plugins that want a completely custom prefs section.

### Target-side mapping

| PHP hook         | Python / pluggy equivalent                              |
| ---------------- | ------------------------------------------------------- |
| `HOOK_PREFS_TABS`| `@hookspec def prefs_tabs()` → list of `PrefsTab` dicts |

A `PrefsTab` dict: `{id, label, icon, content_url}`.
The frontend fetches the tab content via a dedicated route.

### Divergences spotted

- D14: **Tab content as rendered HTML vs. route** — PHP hooks emit `<li>` HTML for
  the tab nav and PHP for the tab body inline.
  Python target: tab content should be a separate Flask route endpoint.
  Plugins register a Blueprint with their prefs content route.

---

## Cross-community summary

### pluggy hookspec design principles (for Phase 2)

```python
# Recommended pluggy hookspec pattern for TT-RSS Python target

import pluggy

hookspec = pluggy.HookspecMarker("ttrss")
hookimpl = pluggy.HookimplMarker("ttrss")

class TtRssSpec:
    # firstresult=True: first non-None return wins (auth, fetch-override)
    @hookspec(firstresult=True)
    def authenticate(self, login: str, password: str): ...

    @hookspec(firstresult=True)
    def fetch_feed(self, url: str, feed_id: int): ...

    # firstresult=False: all plugins contribute (render, filter)
    @hookspec
    def sanitize(self, article: dict, site_url: str): ...

    @hookspec
    def render_article(self, article: dict): ...

    @hookspec
    def article_filter(self, article: dict) -> bool: ...

    @hookspec
    def prefs_tabs(self) -> list: ...

    @hookspec
    def action_items(self, article_id: int) -> list: ...
```

### Key architectural divergences (all Hook communities)

| ID  | PHP pattern                                  | Python consequence                                         |
| --- | -------------------------------------------- | ---------------------------------------------------------- |
| D1  | `&$param` pass-by-reference                  | Use mutable dict/dataclass; pluggy chaining                |
| D2  | Hooks emit raw HTML strings                  | Hooks emit structured data; Jinja2/JS renders              |
| D6  | Synchronous fetch in daemon                  | Async httpx in Celery; plugins must be async-compatible    |
| D7  | `HOOK_ARTICLE_FILTER` in-place mutation      | `firstresult=True` returning bool; dict passed mutable     |
| D8  | `HOOK_UPDATE_TASK` in daemon loop            | Celery periodic task registration                          |
| D9  | SQL injection via `HOOK_QUERY_HEADLINES`     | SQLAlchemy filter objects only — security boundary fix     |
| D11 | Plain-text password in hook chain            | Same risk in Python; accepted (trusted plugins only)       |
| D12 | OTP coupled to HOOK_AUTH_USER                | Separate `HOOK_VERIFY_OTP` hookspec recommended            |
| D13 | HTML fragments from UI hooks                 | Structured JSON; breaking plugin API change                |
| D14 | Tab content inline HTML                      | Separate Blueprint route per plugin tab                    |

### Migration order recommendation

```text
Phase 2 (Foundation):
  1. Define pluggy HookspecMarker + all 24 hookspecs
  2. Implement auth_internal plugin (HOOK_AUTH_USER) → verifies argon2id
  3. Implement feed-fetch pipeline hooks (HOOK_FETCH_FEED … HOOK_ARTICLE_FILTER)

Phase 3 (Business logic):
  4. Implement prefs hooks (HOOK_PREFS_TAB, HOOK_PREFS_TABS, HOOK_PREFS_EDIT_FEED)
  5. Implement render hooks (HOOK_RENDER_ARTICLE, HOOK_SANITIZE)

Phase 4 (API + UI):
  6. Implement API hooks (HOOK_QUERY_HEADLINES, HOOK_RENDER_ARTICLE_API)
  7. Implement UI hooks (HOOK_ACTION_ITEM, HOOK_TOOLBAR_BUTTON)

Phase 5 (Background):
  8. Convert HOOK_UPDATE_TASK, HOOK_HOUSE_KEEPING to Celery periodic signals
```

---

*Source: `classes/pluginhost.php` (L1–L120), `plugins/auth_internal/init.php`,
`include/functions.php:authenticate_user`, `include/rssfuncs.php`,
`tools/graph_analysis/output/hook_graph.json`.*
*Status: DEGRADED (training knowledge + source reads; no web search).*
