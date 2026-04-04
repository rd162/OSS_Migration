"""
Pluggy hook specifications — 24 hooks matching PHP PluginHost constants (specs/05-plugin-system.md).

Source: ttrss/classes/pluginhost.php (lines 18-41 — HOOK_* integer constants 1-24)
        ttrss/classes/pluginhost.php (lines 43-45 — KIND_ALL/SYSTEM/USER constants)
        ttrss/classes/pluginhost.php:run_hooks/get_hooks (invocation patterns)
        ttrss/include/functions.php:authenticate_user (HOOK_AUTH_USER firstresult, lines 711-718)
        ttrss/include/rssfuncs.php (HOOK_FETCH_FEED pipeline at lines 270-272,
                                    HOOK_FEED_FETCHED at line 367,
                                    HOOK_FEED_PARSED at line 394,
                                    HOOK_ARTICLE_FILTER at line 687)

Hook semantics:
  - firstresult=True: HOOK_AUTH_USER ONLY (PHP iterates + breaks on first truthy user_id)
  - All 23 other hooks: collecting (pipeline or fire-and-forget; caller decides on return value)

R15 note: HOOK_FETCH_FEED is deliberately collecting (not firstresult).
  PHP source (rssfuncs.php:270-272):
      foreach ($pluginhost->get_hooks(HOOK_FETCH_FEED) as $plugin) {
          $feed_data = $plugin->hook_fetch_feed($feed_data, ...);  // pipeline, no break
      }
  Marking it firstresult would silently discard all but the first plugin's transformation.

Plugin kinds (R16):
  KIND_ALL = 1   — load both system and user plugins
  KIND_SYSTEM = 2 — can register handlers, commands, API methods, virtual feeds
  KIND_USER = 3   — hooks only (no handler/command/API registration)
"""
import pluggy

# Namespace marker for this project — prevents collision with pytest's own pluggy markers.
# Source: ttrss/classes/pluginhost.php:add_hook (hook registration method)
hookspec = pluggy.HookspecMarker("ttrss")

# hookimpl exported for use by plugin authors implementing hooks.
# Source: ttrss/classes/pluginhost.php (plugin registration via add_hook)
hookimpl = pluggy.HookimplMarker("ttrss")
# Inferred from: ttrss/classes/iauthmodule.php (IAuthModule interface — replaced by hookspec hook_auth_user, ADR-0010)

# Source: ttrss/classes/pluginhost.php (lines 43-45 — KIND constants)
KIND_ALL = 1
KIND_SYSTEM = 2
KIND_USER = 3


class TtRssHookSpec:
    """
    All 24 TT-RSS hook specifications.
    Source: ttrss/classes/pluginhost.php (HOOK_* constants, lines 18-41)
    """

    # --- HOOK_ARTICLE_BUTTON = 1 ---
    # Source: ttrss/classes/pluginhost.php:HOOK_ARTICLE_BUTTON (const 1)
    # Trigger: ttrss/classes/feeds.php (get_hooks loop, collects button HTML fragments)
    @hookspec
    def hook_article_button(self, line):
        """Add custom buttons to article toolbar. Returns HTML string."""

    # --- HOOK_ARTICLE_FILTER = 2 ---
    # Source: ttrss/classes/pluginhost.php:HOOK_ARTICLE_FILTER (const 2)
    # Trigger: ttrss/include/rssfuncs.php line 687 (pipeline: article dict passed through each plugin)
    @hookspec
    def hook_article_filter(self, article):
        """Filter or modify article dict during feed parsing. Returns modified article."""

    # --- HOOK_PREFS_TAB = 3 ---
    # Source: ttrss/classes/pluginhost.php:HOOK_PREFS_TAB (const 3)
    # Trigger: ttrss/classes/pref/*.php (run_hooks — fire-and-forget, no return value used)
    @hookspec
    def hook_prefs_tab(self):
        """Add preference tab content to settings UI."""

    # --- HOOK_PREFS_TAB_SECTION = 4 ---
    # Source: ttrss/classes/pluginhost.php:HOOK_PREFS_TAB_SECTION (const 4)
    # Trigger: ttrss/classes/pref/*.php (run_hooks — fire-and-forget)
    @hookspec
    def hook_prefs_tab_section(self):
        """Add sections within preference tabs."""

    # --- HOOK_PREFS_TABS = 5 ---
    # Source: ttrss/classes/pluginhost.php:HOOK_PREFS_TABS (const 5)
    # Trigger: ttrss/prefs.php line 139 (run_hooks — fire-and-forget)
    @hookspec
    def hook_prefs_tabs(self, args):
        """Called when all preference tabs have been rendered."""

    # --- HOOK_FEED_PARSED = 6 ---
    # Source: ttrss/classes/pluginhost.php:HOOK_FEED_PARSED (const 6)
    # Trigger: ttrss/include/rssfuncs.php line 394 (run_hooks — fire-and-forget)
    @hookspec
    def hook_feed_parsed(self, rss):
        """Called after feed XML is parsed into a FeedParser/SimplePie-compatible object."""

    # --- HOOK_UPDATE_TASK = 7 ---
    # Source: ttrss/classes/pluginhost.php:HOOK_UPDATE_TASK (const 7)
    # Trigger: ttrss/update.php lines 161, 190 (run_hooks — fire-and-forget)
    @hookspec
    def hook_update_task(self):
        """Background update task hook. Called during daemon update cycle."""

    # --- HOOK_AUTH_USER = 8  *** firstresult=True *** ---
    # Source: ttrss/classes/pluginhost.php:HOOK_AUTH_USER (const 8)
    # Trigger: ttrss/include/functions.php:authenticate_user (lines 711-718)
    #   foreach (...HOOK_AUTH_USER...) {
    #       $user_id = (int) $plugin->authenticate($login, $password);
    #       if ($user_id) { break; }   <-- ONLY hook with explicit break-on-truthy
    #   }
    # R15: This is the SOLE hook mapped to firstresult=True.
    @hookspec(firstresult=True)
    def hook_auth_user(self, login, password):
        """
        Authenticate user. Returns user_id (int > 0) on success, 0/None on failure.
        First plugin to return a truthy user_id wins (mirrors PHP break-on-truthy).
        """

    # --- HOOK_HOTKEY_MAP = 9 ---
    # Source: ttrss/classes/pluginhost.php:HOOK_HOTKEY_MAP (const 9)
    # Trigger: ttrss/include/functions2.php line 186 (pipeline: hotkeys dict)
    @hookspec
    def hook_hotkey_map(self, hotkeys):
        """Modify keyboard shortcut mapping dict. Returns modified dict."""

    # --- HOOK_RENDER_ARTICLE = 10 ---
    # Source: ttrss/classes/pluginhost.php:HOOK_RENDER_ARTICLE (const 10)
    # Trigger: ttrss/classes/feeds.php (pipeline: article dict passed through plugins)
    @hookspec
    def hook_render_article(self, article):
        """Modify article for normal view rendering. Returns modified article."""

    # --- HOOK_RENDER_ARTICLE_CDM = 11 ---
    # Source: ttrss/classes/pluginhost.php:HOOK_RENDER_ARTICLE_CDM (const 11)
    # Trigger: ttrss/classes/feeds.php line 517 (pipeline)
    @hookspec
    def hook_render_article_cdm(self, article):
        """Modify article for combined display mode rendering. Returns modified article."""

    # --- HOOK_FEED_FETCHED = 12 ---
    # Source: ttrss/classes/pluginhost.php:HOOK_FEED_FETCHED (const 12)
    # Trigger: ttrss/include/rssfuncs.php line 367 (pipeline: feed_data passed through plugins)
    @hookspec
    def hook_feed_fetched(self, feed_data, fetch_url, owner_uid, feed):
        """Called after HTTP fetch, before XML parsing. Returns modified feed_data."""

    # --- HOOK_SANITIZE = 13 ---
    # Source: ttrss/classes/pluginhost.php:HOOK_SANITIZE (const 13)
    # Trigger: ttrss/include/functions2.php:sanitize (pipeline)
    @hookspec
    def hook_sanitize(self, doc, site_url, allowed_elements, disallowed_attributes):
        """HTML content sanitization hook. Returns modified doc."""

    # --- HOOK_RENDER_ARTICLE_API = 14 ---
    # Source: ttrss/classes/pluginhost.php:HOOK_RENDER_ARTICLE_API (const 14)
    # Trigger: ttrss/classes/api.php lines 354, 712 (pipeline)
    @hookspec
    def hook_render_article_api(self, headline_row):
        """Modify article dict for API responses. Returns modified headline_row."""

    # --- HOOK_TOOLBAR_BUTTON = 15 ---
    # Source: ttrss/classes/pluginhost.php:HOOK_TOOLBAR_BUTTON (const 15)
    # Trigger: ttrss/index.php line 213 (collecting HTML fragments)
    @hookspec
    def hook_toolbar_button(self):
        """Add button HTML to main toolbar. Returns HTML string."""

    # --- HOOK_ACTION_ITEM = 16 ---
    # Source: ttrss/classes/pluginhost.php:HOOK_ACTION_ITEM (const 16)
    # Trigger: ttrss/index.php line 252 (collecting HTML fragments)
    @hookspec
    def hook_action_item(self):
        """Add item HTML to action menu. Returns HTML string."""

    # --- HOOK_HEADLINE_TOOLBAR_BUTTON = 17 ---
    # Source: ttrss/classes/pluginhost.php:HOOK_HEADLINE_TOOLBAR_BUTTON (const 17)
    # Trigger: ttrss/classes/feeds.php line 138 (collecting HTML fragments)
    @hookspec
    def hook_headline_toolbar_button(self):
        """Add button HTML to headline toolbar. Returns HTML string."""

    # --- HOOK_HOTKEY_INFO = 18 ---
    # Source: ttrss/classes/pluginhost.php:HOOK_HOTKEY_INFO (const 18)
    # Trigger: ttrss/include/functions2.php line 110 (pipeline: hotkeys help dict)
    @hookspec
    def hook_hotkey_info(self, hotkeys):
        """Modify keyboard shortcut help text dict. Returns modified dict."""

    # --- HOOK_ARTICLE_LEFT_BUTTON = 19 ---
    # Source: ttrss/classes/pluginhost.php:HOOK_ARTICLE_LEFT_BUTTON (const 19)
    # Trigger: ttrss/classes/feeds.php line 686 (collecting HTML fragments)
    @hookspec
    def hook_article_left_button(self, line):
        """Add button HTML to article left side. Returns HTML string."""

    # --- HOOK_PREFS_EDIT_FEED = 20 ---
    # Source: ttrss/classes/pluginhost.php:HOOK_PREFS_EDIT_FEED (const 20)
    # Trigger: ttrss/classes/pref/feeds.php line 748 (run_hooks — fire-and-forget)
    @hookspec
    def hook_prefs_edit_feed(self, feed_id):
        """Called when feed edit dialog is rendered."""

    # --- HOOK_PREFS_SAVE_FEED = 21 ---
    # Source: ttrss/classes/pluginhost.php:HOOK_PREFS_SAVE_FEED (const 21)
    # Trigger: ttrss/classes/pref/feeds.php line 981 (run_hooks — fire-and-forget)
    @hookspec
    def hook_prefs_save_feed(self, feed_id):
        """Called when feed preferences are saved."""

    # --- HOOK_FETCH_FEED = 22 ---
    # Source: ttrss/classes/pluginhost.php:HOOK_FETCH_FEED (const 22)
    # Trigger: ttrss/include/rssfuncs.php lines 270-272 (pipeline — NOT firstresult)
    #   foreach ($pluginhost->get_hooks(HOOK_FETCH_FEED) as $plugin) {
    #       $feed_data = $plugin->hook_fetch_feed($feed_data, ...);  // no break
    #   }
    # Each plugin transforms feed_data and passes it on. See R15 note in module docstring.
    @hookspec
    def hook_fetch_feed(self, feed_data, fetch_url, owner_uid, feed):
        """
        Custom feed fetching (pipeline). Each plugin receives and may transform feed_data.
        Returns modified feed_data.
        """

    # --- HOOK_QUERY_HEADLINES = 23 ---
    # Source: ttrss/classes/pluginhost.php:HOOK_QUERY_HEADLINES (const 23)
    # Trigger: multiple locations (pipeline: modifies SQL query parameters)
    @hookspec
    def hook_query_headlines(
        self,
        qfh_ret,
        feed,
        limit,
        view_mode,
        cat_view,
        search,
        search_mode,
        override_order,
        offset,
        owner_uid,
        filter_results,
        since_id,
        include_children,
    ):
        """Modify headline SQL query parameters. Returns modified qfh_ret."""

    # --- HOOK_HOUSE_KEEPING = 24 ---
    # Source: ttrss/classes/pluginhost.php:HOOK_HOUSE_KEEPING (const 24)
    # Trigger: ttrss/classes/handler/public.php line 415 (run_hooks — fire-and-forget)
    @hookspec
    def hook_house_keeping(self, args):
        """Called during periodic maintenance/housekeeping tasks."""
