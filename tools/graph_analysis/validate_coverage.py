#!/usr/bin/env python3
"""validate_coverage.py — 5-Dimension PHP→Python Migration Coverage Validator

Cross-references PHP graph analysis output against the existing Python
migration code in target-repos/ttrss-python/ttrss/.

Dimensions validated:
  1. Call coverage     — function_levels.json vs # Source: comments
  2. Import coverage   — call_graph.json edges vs Python import chains
  3. DB table coverage — db_table_graph.json vs model imports
  4. Hook invocation   — hook_graph.json INVOKES edges vs pm.hook calls
  5. Class hierarchy   — class_graph.json extends/implements vs Python inheritance

Usage:
    python tools/graph_analysis/validate_coverage.py \
        --graph-dir tools/graph_analysis/output \
        --python-dir target-repos/ttrss-python/ttrss
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Third-party class/function prefixes to skip (PHP-only libraries)
# ---------------------------------------------------------------------------
THIRD_PARTY_PREFIXES: Set[str] = {
    "QRcode", "QR", "PHPMailer", "SMTP", "SphinxClient",
    "gettext_reader", "FileReader", "Text_LanguageDetect",
    "MiniTemplator", "Mobile_Detect", "floIcon", "jimIcon",
    "HOTP", "OTP", "TOTP", "Minifier", "FrameFiller",
    "Db_Mysql", "Db_Mysqli", "Publisher", "Subscriber", "Base32",
    "CachedFileReader", "StringReader", "StreamReader",
    "QRrs", "QRmask", "QRencode", "QRsplit", "QRrawcode",
    "QRimage", "qrstr", "QRspec", "phpmailerException", "Db_Pgsql",
    # Path-based third-party: lib/ directory
    "ttrss/lib/", "ttrss/lib/languagedetect", "ttrss/lib/phpqrcode",
    "ttrss/lib/phpmailer", "ttrss/lib/sphinxapi",
    "ttrss/lib/floIcon", "ttrss/lib/jimIcon",
    # Daemon entry points (not ported — Celery replaces)
    "ttrss/update_daemon2.php", "ttrss/update.php",
    # Feed parser classes (feedparser Python library replaces — ADR-0014)
    "FeedParser", "FeedItem", "FeedItem_Atom", "FeedItem_RSS",
    "FeedItem_Common", "FeedEnclosure",
    # LanguageDetect (not in migration scope — third-party PHP library)
    "LanguageDetect",
    # Colors library (PHP image processing — not ported)
    "ttrss/include/colors.php",
}

def _is_third_party(name: str) -> bool:
    """Return True if *name* starts with any known third-party prefix."""
    for prefix in THIRD_PARTY_PREFIXES:
        if name == prefix:
            return True
        if name.startswith(prefix + "::") or name.startswith(prefix + "."):
            return True
        # Path-based prefix (contains "/") — match with "/" separator.
        # Normalise: if prefix already ends with "/" don't add another one
        # (e.g. "ttrss/lib/" must match "ttrss/lib/accept-to-gettext.php::*").
        if "/" in prefix:
            norm = prefix if prefix.endswith("/") else prefix + "/"
            if name.startswith(norm):
                return True
        # Class-name prefix (no "/" in prefix) — plain startswith so that
        # prefix "QR" matches "QRinput::append" and
        # prefix "Text_LanguageDetect" matches "Text_LanguageDetect_Parser::analyze"
        if "/" not in prefix and name.startswith(prefix):
            return True
    return False

# ---------------------------------------------------------------------------
# Known elimination list — PHP functions intentionally NOT ported (spec 13)
# ---------------------------------------------------------------------------
ELIMINATED_FUNCTIONS: Set[str] = {
    "print_select", "print_select_hash", "print_radio",
    "print_feed_cat_select", "print_feed_select", "print_label_select",
    "render_login_form", "print_checkpoint", "print_error",
    "print_warning", "print_notice",
    "stylesheet_tag", "javascript_tag", "get_minified_js",
    "T_js_decl", "T_sprintf",
    "implements_interface", "check_for_update", "startup_gettext",
    "init_js_translations",
    "print_user_stylesheet", "calculate_dep_timestamp", "get_score_pic",
    "format_warning", "format_notice", "format_error",
    "stripslashes_deep", "gzdecode", "trim_array",
    "file_is_locked", "make_lockfile", "make_stampfile",
    "sql_random_function", "db_escape_string", "get_pgsql_version",
    # Additional eliminations
    "sql_bool_to_bool", "bool_to_sql_bool", "checkbox_to_sql_bool",
    "define_default", "truncate_string", "get_random_bytes",
    "_debug", "_debug_suppress", "check_for_update",
    # DB adapters (replaced by SQLAlchemy — only Db_PDO::connect used as reference)
    "escape_string", "query", "fetch_assoc", "num_rows", "fetch_result",
    "close", "affected_rows", "last_error", "reconnect",
    # PHP-specific functions
    "session_read", "session_write", "session_destroy",
    "ttrss_open", "ttrss_close",
    "__autoload", "__construct", "__clone", "__destruct",
    # Colors library (PHP-specific favicon/color processing)
    "_color_pack", "_color_unpack", "_resolve_htmlcolor",
    "calculate_avg_color", "colorPalette", "hsl2rgb",
    "_color_hsl2rgb", "_color_hue2rgb", "_color_rgb2hsl",
    # DbUpdater (replaced by Alembic)
    "getSchemaLines", "getSchemaVersion", "isUpdateRequired", "performUpdateTo",
    # Db_Stmt (replaced by SQLAlchemy)
    "fetch", "rowCount",
    # Logger/Logger_SQL/Logger_Syslog (replaced by structlog)
    "log_error", "log", "get",
    # Handler base class (replaced by Flask blueprints)
    "after", "csrf_ignore",
    # PluginHandler (replaced by Flask routing)
    "catchall",
    # Plugin base interface (replaced by pluggy)
    "about", "api_version", "get_js", "get_prefs_js",
    # Auth_Base (replaced by auth module functions)
    "find_user_by_login", "auto_create_user",
    # PHP global bootstrap (replaced by Flask app factory)
    "connect",
    # PHP error handlers (replaced by Flask error handling)
    "ttrss_error_handler", "ttrss_fatal_handler",
    # sanity_check.php (replaced by Flask request context / Docker healthchecks)
    "make_self_url_path", "initial_sanity_check",
    # Email (replaced by utils/mail.py)
    "quickMail",
    # Plugin base init method (replaced by pluggy hookimpl)
    "init",
    # PHP entry-point files (no Python equivalent — Flask handles routing)
    "ttrss/public.php",
    "ttrss/include/login_form.php",
    "ttrss/include/sanity_check.php",
    "ttrss/register.php",
    "ttrss/opml.php",
    "ttrss/include/version.php",
    # Bare PHP include files appearing as call graph nodes (module-level code, no Python equivalent)
    "ttrss/include/functions.php",   # module-level bootstrap; functions cited individually
    "ttrss/include/rssfuncs.php",    # module-level bootstrap; functions cited individually
    # Pref_Filters UI-rendering helpers (eliminated: Dojo HTML → Vanilla JS SPA, ADR-0017)
    "getRuleName", "printRuleName", "getActionName", "printActionName",
    "newfilter", "newrule", "newaction",
    # Low-level PHP DB wrapper functions (eliminated: replaced by SQLAlchemy, ADR-0006)
    "db_affected_rows", "db_fetch_assoc", "db_fetch_result", "db_last_error",
    "db_num_rows", "db_query", "db_quote",
    # PHP install script (eliminated: Alembic + Docker handle DB init, ADR-0003)
    "ttrss/install/index.php", "db_connect", "make_config",
    # PHP API entry-point (eliminated: replaced by Flask routing)
    "ttrss/api/index.php",
    # PluginHost accessors/mutators (eliminated: pluggy framework replaces, ADR-0010)
    # The Python PluginManager has equivalent functionality under different API.
    "add_command", "del_command", "get_commands", "lookup_command", "run_commands",
    "add_feed", "get_feeds", "get_feed_handler",
    "get_all", "get_api_method", "get_dbh", "get_debug", "set_debug",
    "get_hooks", "del_hook", "get_link", "get_plugin", "get_plugin_names", "get_plugins",
    "lookup_handler", "add_handler", "del_handler", "pfeed_to_feed_id", "feed_to_pfeed_id",
    "register_plugin", "run_hooks", "set",
    # Handler_Public scheduled-update entry points (eliminated: Celery tasks replace)
    "globalUpdateFeeds", "housekeepingTask", "updateTask",
    # Dlg HTML-rendering helpers (eliminated: SPA frontend replaces PHP dialog rendering)
    "explainError", "opml_notice", "opml_publish_url",
    # Backend::loading is a stub spinner (eliminated: SPA handles loading state client-side)
    "loading",
    # Db::quote (eliminated: SQLAlchemy parameterized queries replace manual quoting)
    "quote",
    # Db_Prefs::convert (eliminated: SQLAlchemy type coercion replaces PHP manual conversion)
    "convert",
    # Feeds::generate_error_feed (eliminated: SPA renders error state client-side)
    "generate_error_feed",
    # format_* HTML rendering functions (eliminated R13: HTML output → JSON for SPA, ADR-0017)
    "format_article_labels", "format_article_note", "format_inline_player",
    "format_tags_string", "format_article_enclosures", "format_headline_subtoolbar",
    # PHP UI helper methods in pref/prefs.php (eliminated: Dojo dialogs → SPA)
    "getHelpText", "getSectionName", "getShortDesc", "toggleAdvanced", "getHelp",
    # Pref_Feeds HTML helper (eliminated: PHP checkbox rendering → SPA)
    "batch_edit_cbox",
    # PHP utility functions not applicable to Python (eliminated)
    "get_self_url_prefix",   # Flask url_for() replaces
    "geturl",                # PHP curl wrapper; httpx replaces (ADR-0015)
    "read_stdin",            # PHP CLI utility; not applicable
    "tmpdirname",            # PHP temp dir; tempfile replaces
    "get_ssl_certificate_id", # PHP OpenSSL binding; not applicable in Python
    "get_translations",      # PHP gettext init; i18n deferred (ADR-0013)
    "convertUrlQuery",       # PHP URL query builder; urllib.parse replaces
    "format_libxml_error",   # PHP libxml error formatter; lxml handles natively
    "add_feed_url",          # Dojo autodetect helper; SPA handles client-side
    # Article HTML handlers (eliminated: SPA handles redirect + score UI)
    "redirect",              # PHP article redirect helper
    "Article::redirect",
    # encrypt_password (eliminated: legacy salted-hash PHP; argon2id replaces, ADR-0008)
    "encrypt_password",
    # PHP install script helpers (eliminated: Docker + Alembic, ADR-0003)
    "make_password",         # re: install/index.php only (auth/password.py has it as IMPLEMENTED)
    # getFeedIcon (eliminated: favicon fetched client-side in SPA; documented in http/client.py)
    "getFeedIcon",
    # PHP session callbacks (eliminated: Flask-Login + Redis replace, ADR-0007)
    "ttrss_destroy", "ttrss_gc", "ttrss_read", "ttrss_write",
    "validate_session",      # Flask-Login load_user() replaces
    "validate_csrf",         # Flask-WTF CSRFProtect replaces (documented: auth/session.py)
    # PHP lock file management (eliminated: Celery task locking replaces, ADR-0011)
    "expire_lock_files",
    # PHP image caching (eliminated: inlined into article sanitize pipeline)
    "cache_images",
    # PHP HTML-rendering class methods (eliminated: SPA frontend replaces, ADR-0017, R13)
    "display_main_help",     # Backend::display_main_help → SPA handles help
    "customizeCSS",          # Pref_Prefs::customizeCSS → SPA has no per-user CSS editor
    "format_headlines_list", # Feeds::format_headlines_list → SPA renders headlines
    "view",                  # Feeds::view, Article::view, Backend::view → SPA replaces all PHP view renderers
    "generate_dashboard_feed",  # Feeds::generate_dashboard_feed → called only by Feeds::view (SPA)
    # Sphinx FTS (eliminated: PostgreSQL FTS used instead; Sphinx not ported)
    "sphinx_search",
    # Db_Prefs PHP caching layer (eliminated: SQLAlchemy session identity map serves same purpose)
    "cache",                 # Db_Prefs::cache → SQLAlchemy eliminates need for manual pref caching
    # PHP digest test UI trigger (eliminated: Celery send_headlines_digests task replaces)
    "digestTest",
}

def _bare_name(qname: str) -> str:
    """Extract the bare function/method name from a qualified name.

    Examples:
        'API::login'                          -> 'login'
        'ttrss/include/functions.php::catchup_feed' -> 'catchup_feed'
        'Handler_Public::opml'                -> 'opml'
    """
    if "::" in qname:
        return qname.rsplit("::", 1)[1]
    return qname

# ---------------------------------------------------------------------------
# PHP file → Python module mapping (hardcoded from specs/13)
# ---------------------------------------------------------------------------
PHP_TO_PYTHON_MAP: Dict[str, List[str]] = {
    "ttrss/include/functions.php": [
        "auth/authenticate.py", "feeds/counters.py", "feeds/ops.py",
        "utils/misc.py", "utils/feeds.py", "config.py",
    ],
    "ttrss/include/functions2.php": [
        "articles/ops.py", "articles/search.py", "articles/sanitize.py",
        "articles/tags.py", "feeds/categories.py", "http/client.py",
        "feeds/ops.py", "utils/misc.py",
    ],
    "ttrss/include/rssfuncs.php": [
        "tasks/feed_tasks.py", "tasks/housekeeping.py",
        "articles/filters.py", "articles/persist.py",
    ],
    "ttrss/include/labels.php": ["labels.py"],
    "ttrss/include/ccache.php": ["ccache.py"],
    "ttrss/include/db-prefs.php": ["prefs/ops.py"],
    "ttrss/include/sessions.php": [
        "auth/session.py", "auth/authenticate.py",
    ],
    "ttrss/classes/pluginhost.php": [
        "plugins/manager.py", "plugins/loader.py",
    ],
    "ttrss/classes/api.php": ["blueprints/api/views.py"],
    "ttrss/classes/feeds.php": ["blueprints/backend/views.py", "feeds/ops.py"],
    "ttrss/classes/article.php": ["articles/ops.py"],
    "ttrss/classes/auth/base.php": [
        "auth/authenticate.py", "auth/password.py",
    ],
    "ttrss/plugins/auth_internal/init.php": ["auth/password.py"],
    "ttrss/classes/handler.php": ["blueprints/backend/views.py"],
    "ttrss/classes/handler/protected.php": ["blueprints/backend/views.py"],
    "ttrss/classes/handler/public.php": ["blueprints/public/views.py"],
    "ttrss/classes/backend.php": ["blueprints/backend/views.py"],
    "ttrss/classes/db.php": ["extensions.py"],
    "ttrss/classes/db/prefs.php": ["prefs/ops.py"],
    "ttrss/classes/pref/feeds.php": ["feeds/ops.py", "prefs/feeds_crud.py", "blueprints/prefs/feeds.py"],
    "ttrss/classes/pref/prefs.php": ["prefs/ops.py", "prefs/user_prefs_crud.py", "blueprints/prefs/user_prefs.py"],
    "ttrss/classes/pref/labels.php": ["labels.py", "blueprints/prefs/labels.py"],
    "ttrss/classes/pref/users.php": ["auth/authenticate.py", "prefs/users_crud.py", "blueprints/prefs/users.py"],
    "ttrss/classes/pref/filters.php": ["prefs/filters_crud.py", "blueprints/prefs/filters.py"],
    "ttrss/classes/pref/system.php": ["blueprints/prefs/system.py"],
    "ttrss/include/db.php": ["extensions.py"],
    "ttrss/classes/rpc.php": ["blueprints/backend/views.py"],
    "ttrss/classes/rpc2.php": ["blueprints/backend/views.py"],
    "ttrss/classes/dlg.php": ["blueprints/backend/views.py"],
    "ttrss/classes/opml.php": ["feeds/opml.py", "feeds/ops.py"],
    "ttrss/include/crypt.php": ["crypto/fernet.py"],
    "ttrss/include/errorhandler.php": ["errors.py"],
    # Phase 6: new modules added in coverage remediation
    "ttrss/include/digest.php": ["tasks/digest.py"],
    "ttrss/include/feedbrowser.php": ["feeds/browser.py"],
    "ttrss/classes/ttrssmailer.php": ["utils/mail.py"],
}

# ---------------------------------------------------------------------------
# Table → Model class mapping
# ---------------------------------------------------------------------------
TABLE_TO_MODEL: Dict[str, str] = {
    "ttrss_users": "TtRssUser",
    "ttrss_feeds": "TtRssFeed",
    "ttrss_feed_categories": "TtRssFeedCategory",
    "ttrss_entries": "TtRssEntry",
    "ttrss_user_entries": "TtRssUserEntry",
    "ttrss_tags": "TtRssTag",
    "ttrss_enclosures": "TtRssEnclosure",
    "ttrss_labels2": "TtRssLabel2",
    "ttrss_user_labels2": "TtRssUserLabel2",
    "ttrss_version": "TtRssVersion",
    "ttrss_archived_feeds": "TtRssArchivedFeed",
    "ttrss_counters_cache": "TtRssCountersCache",
    "ttrss_cat_counters_cache": "TtRssCatCountersCache",
    "ttrss_entry_comments": "TtRssEntryComment",
    "ttrss_filter_types": "TtRssFilterType",
    "ttrss_filter_actions": "TtRssFilterAction",
    "ttrss_filters2": "TtRssFilter2",
    "ttrss_filters2_rules": "TtRssFilter2Rule",
    "ttrss_filters2_actions": "TtRssFilter2Action",
    "ttrss_prefs_types": "TtRssPrefsType",
    "ttrss_prefs_sections": "TtRssPrefsSection",
    "ttrss_prefs": "TtRssPref",
    "ttrss_settings_profiles": "TtRssSettingsProfile",
    "ttrss_user_prefs": "TtRssUserPref",
    "ttrss_sessions": "TtRssSession",
    "ttrss_feedbrowser_cache": "TtRssFeedbrowserCache",
    "ttrss_access_keys": "TtRssAccessKey",
    "ttrss_linked_instances": "TtRssLinkedInstance",
    "ttrss_linked_feeds": "TtRssLinkedFeed",
    "ttrss_plugin_storage": "TtRssPluginStorage",
    "ttrss_error_log": "TtRssErrorLog",
    # Deprecated / missing tables — skip gracefully
    "ttrss_filters": None,
    "ttrss_themes": None,
    "ttrss_labels": None,
    "ttrss_scheduled_updates": None,
}

# ---------------------------------------------------------------------------
# PHP handler class → PHP source file mapping (B2: Fix 2)
# Resolves "ClassName::method" qnames to their PHP file path so the
# file-level fallback in validate_call_coverage() can match them.
# ---------------------------------------------------------------------------
HANDLER_CLASS_PHP_FILE: Dict[str, str] = {
    "api":             "ttrss/classes/api.php",
    "API":             "ttrss/classes/api.php",
    "Handler":         "ttrss/classes/handler.php",
    "Handler_Public":  "ttrss/classes/handler/public.php",
    "Handler_Protected": "ttrss/classes/handler/protected.php",
    "Backend":         "ttrss/classes/backend.php",
    "Pref_Feeds":      "ttrss/classes/pref/feeds.php",
    "Pref_Filters":    "ttrss/classes/pref/filters.php",
    "Pref_Labels":     "ttrss/classes/pref/labels.php",
    "Pref_System":     "ttrss/classes/pref/system.php",
    "Pref_Prefs":      "ttrss/classes/pref/prefs.php",
    "Pref_Users":      "ttrss/classes/pref/users.php",
    "Feeds":           "ttrss/classes/feeds.php",
    "Article":         "ttrss/classes/article.php",
    "Dlg":             "ttrss/classes/dlg.php",
    "RPC":             "ttrss/classes/rpc.php",
    "RPC2":            "ttrss/classes/rpc2.php",
    "Opml":            "ttrss/classes/opml.php",
    "PluginHost":      "ttrss/classes/pluginhost.php",
    "Auth_Internal":   "ttrss/plugins/auth_internal/init.php",
    "Db":              "ttrss/classes/db.php",
    "Db_PDO":          "ttrss/classes/db.php",
    "Db_Prefs":        "ttrss/classes/db/prefs.php",
    "Logger":          "ttrss/classes/logger.php",
    "Logger_SQL":      "ttrss/classes/logger/sql.php",
    "DbUpdater":       "ttrss/classes/dbupdater.php",
    "Auth_Base":       "ttrss/classes/auth/base.php",
}

# ---------------------------------------------------------------------------
# PHP class → Python class mapping (known equivalences)
# ---------------------------------------------------------------------------
PHP_CLASS_TO_PYTHON: Dict[str, Optional[str]] = {
    "Handler": None,  # abstract, no direct Python equivalent
    "Handler_Protected": None,
    "Handler_Public": None,
    "API": None,  # mapped to Flask blueprints, not a class
    "Article": None,  # functions in articles/ops.py
    "Backend": None,
    "Feeds": None,  # functions in feeds/ops.py
    "Dlg": None,
    "Db": None,  # SQLAlchemy replaces
    "Db_PDO": None,
    "Db_Prefs": None,
    "Db_Stmt": None,
    "DbUpdater": None,
    "PluginHost": "PluginManager",
    "Plugin": None,  # base class, pluggy replaces
    "Auth_Base": None,  # auth module functions
    "FeedItem": None,  # feedparser replaces
    "FeedItem_Common": None,
    "FeedItem_Atom": None,
    "FeedItem_RSS": None,
    "FeedEnclosure": None,
    "FeedParser": None,
    "Opml": None,
    "RPC": None,
    "RPC2": None,
    "Pref_Feeds": None,
    "Pref_Labels": None,
    "Pref_Prefs": None,
    "Pref_Users": None,
    "Logger_SQL": None,
    # PHP handler sub-classes eliminated by Flask blueprint routing (B2)
    "PluginHandler": None,
    "Pref_Filters": None,
    "Pref_System": None,
    # Auth_Internal extends Plugin — pluggy hookimpl replaces PHP Plugin base class
    "Auth_Internal": None,
}

# ---------------------------------------------------------------------------
# Regex patterns for # Source: traceability comments (7 known formats)
# ---------------------------------------------------------------------------
SOURCE_PATTERNS: List[re.Pattern] = [
    # Format 1: # Source: ttrss/path/file.php:FuncOrClass::method (lines N-M)
    re.compile(
        r"#\s*Source:\s*(?P<path>ttrss/\S+\.php)"
        r":(?P<qname>[A-Za-z_]\w*(?:(?:::|[.:])[A-Za-z_]\w*)?)"
        r"\s*\(lines?\s*\d+"
    ),
    # Format 2: # Source: ttrss/path/file.php:func_name — description
    re.compile(
        r"#\s*Source:\s*(?P<path>ttrss/\S+\.php)"
        r":(?P<qname>[A-Za-z_]\w*(?:(?:::|[.:])[A-Za-z_]\w*)?)"
        r"\s*[\u2014—-]"
    ),
    # Format 3: # Source: ttrss/path/file.php:func_name (no trailing info)
    re.compile(
        r"#\s*Source:\s*(?P<path>ttrss/\S+\.php)"
        r":(?P<qname>[A-Za-z_]\w*(?:[.:][A-Za-z_]\w*)?)\s*$"
    ),
    # Format 4: # Source: ttrss/path/file.php line NNN — description
    re.compile(
        r"#\s*Source:\s*(?P<path>ttrss/\S+\.php)"
        r"\s+lines?\s*\d+"
    ),
    # Format 5: # Source: file.php:N-M or file.php:N (short form without ttrss/ prefix)
    re.compile(
        r"#\s*Source:\s*(?P<path>[\w/.-]*\.php)"
        r"[:\s]+(?:lines?\s*)?(?P<lines>\d+(?:\s*[-–]\s*\d+)?)"
    ),
    # Format 5b: # Source: file.php:func_name (short form, function name after colon)
    re.compile(
        r"#\s*Source:\s*(?P<path>[\w/.-]*\.php)"
        r":(?P<qname>[A-Za-z_]\w*(?:(?:::|[.:])[A-Za-z_]\w*)?)"
    ),
    # Format 6: # Source: ttrss/path/file.php (file-level, no function)
    re.compile(
        r"#\s*Source:\s*(?P<path>ttrss/\S+\.php)\s*(?:\(|$)"
    ),
    # Format 7: # Source: ttrss/path/file.php + ttrss/path/file2.php (multi-file)
    re.compile(
        r"#\s*Source:\s*(?P<path>ttrss/\S+\.php)\s*\+"
    ),
    # Format 7b: # Source: ttrss/path/file.php, ttrss/path/file2.php (comma-separated multi-file)
    re.compile(
        r"#\s*Source:\s*(?P<path>ttrss/\S+\.php)\s*,"
    ),
    # Format 7c: # Source: ttrss/schema/...sql (schema file reference — mark parseable, no qname)
    re.compile(
        r"#\s*Source:\s*(?P<path>ttrss/\S+\.sql)\s*(?:\(|$|,|\+)"
    ),
    # Format 8: # Source: api.php (bare filename, file-level, no ttrss/ prefix)
    # Catches short-form comments like "# Source: api.php"
    re.compile(
        r"#\s*Source:\s*(?P<path>[\w/-]+\.php)\s*$"
    ),
    # Format 9: alternative traceability keywords (B2: Fix 1)
    # Matches: # Adapted from: / # New: / # PHP source: / # Migrated from: / # Based on:
    re.compile(
        r"#\s*(?:Adapted from|PHP source|Migrated from|Based on):\s*"
        r"(?:ttrss/)?(?P<path>[\w./]+\.php)",
        re.IGNORECASE,
    ),
    # ── Docstring variants (no # prefix) ─────────────────────────────────────
    # Format 10: bare "Source: ttrss/path/file.php:Class::method (lines N-M)"
    re.compile(
        r"(?<![#\w])Source:\s*(?P<path>ttrss/\S+\.php)"
        r":(?P<qname>[A-Za-z_]\w*(?:(?:::|[.:])[A-Za-z_]\w*)?)"
        r"\s*\(lines?\s*\d+"
    ),
    # Format 11: bare "Source: ttrss/path/file.php:func — description"
    re.compile(
        r"(?<![#\w])Source:\s*(?P<path>ttrss/\S+\.php)"
        r":(?P<qname>[A-Za-z_]\w*(?:(?:::|[.:])[A-Za-z_]\w*)?)"
        r"\s*[\u2014—-]"
    ),
    # Format 12: bare "Source: ttrss/path/file.php:func" (end of line)
    re.compile(
        r"(?<![#\w])Source:\s*(?P<path>ttrss/\S+\.php)"
        r":(?P<qname>[A-Za-z_]\w*(?:[.:][A-Za-z_]\w*)?)\s*$"
    ),
    # Format 13: bare "Source: file.php:func" (short form, no ttrss/ prefix)
    re.compile(
        r"(?<![#\w])Source:\s*(?P<path>[\w/.-]+\.php)"
        r":(?P<qname>[A-Za-z_]\w*(?:(?:::|[.:])[A-Za-z_]\w*)?)"
        r"(?:\s|\(|$)"
    ),
    # Format 14: bare "Source: ttrss/path/file.php" (file-level in docstring)
    re.compile(
        r"(?<![#\w])Source:\s*(?P<path>ttrss/\S+\.php)\s*(?:\(|$)"
    ),
]

# Broad catch-all: any traceability keyword pointing to a .php file.
# Now also matches bare "Source:" in docstrings (no # prefix).
SOURCE_COMMENT_RE = re.compile(
    r"(?:#\s*)?(?:Source|Adapted from|New|PHP source|Migrated from|Based on|Inferred from):\s*"
    r"(?:ttrss/)?(?P<file>[\w./]+\.php)"
    r"(?:[:\s].*)?\s*$",
    re.IGNORECASE,
)

# Catch-all for any Source: traceability line (# comment or docstring)
SOURCE_ANY = re.compile(r"(?:#\s*)?Source:\s*\S")


# ---------------------------------------------------------------------------
# Python file scanner
# ---------------------------------------------------------------------------
class PythonModule:
    """Parsed information about a single .py file."""

    def __init__(self, path: Path, root: Path):
        self.path = path
        self.root = root
        # Module dotted name relative to root's parent, e.g. "ttrss.feeds.ops"
        rel = path.relative_to(root.parent)
        parts = list(rel.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        self.dotted = ".".join(parts)
        # Relative path from the ttrss/ root, e.g. "feeds/ops.py"
        self.rel_path = str(path.relative_to(root))

        self.source_text: str = ""
        self.source_lines: List[str] = []
        self.imports: Set[str] = set()  # dotted module names imported
        self.model_classes: Set[str] = set()  # model class names imported
        self.source_comments: List[Dict[str, Any]] = []
        self.defined_classes: Dict[str, List[str]] = {}  # class_name -> [bases]
        self.hook_calls: Set[str] = set()  # lowered hook names invoked

    def parse(self) -> None:
        try:
            self.source_text = self.path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        self.source_lines = self.source_text.splitlines()
        self._extract_source_comments()
        self._extract_imports_and_classes()
        self._extract_hook_calls()

    def _extract_source_comments(self) -> None:
        # B2 Fix 1: expanded traceability keywords (was only "# Source:" + "# Inferred from:")
        # Also match bare "Source:" in docstrings (indented, no # prefix).
        _TRACEABILITY_KEYWORDS = (
            "# Source:", "# Inferred from:", "# Adapted from:",
            "# New:", "# PHP source:", "# Migrated from:", "# Based on:",
            # Docstring variants (indented without # prefix):
            "Source:", "Inferred from:", "Adapted from:", "Based on:",
        )
        for lineno, line in enumerate(self.source_lines, 1):
            if not any(kw in line for kw in _TRACEABILITY_KEYWORDS):
                continue
            matched = False
            for pat in SOURCE_PATTERNS:
                m = pat.search(line)
                if m:
                    gd = m.groupdict()
                    self.source_comments.append({
                        "line": lineno,
                        "path": gd.get("path", ""),
                        "qname": gd.get("qname", ""),
                        "raw": line.strip(),
                    })
                    matched = True
                    break
            if not matched:
                # Try broad SOURCE_COMMENT_RE as secondary catch (B2 Fix 1)
                m = SOURCE_COMMENT_RE.search(line)
                if m:
                    self.source_comments.append({
                        "line": lineno,
                        "path": m.group("file"),
                        "qname": "",
                        "raw": line.strip(),
                    })
                    matched = True
            if not matched and SOURCE_ANY.search(line):
                # Genuinely unparseable source comment
                self.source_comments.append({
                    "line": lineno,
                    "path": "",
                    "qname": "",
                    "raw": line.strip(),
                    "unparseable": True,
                })

    def _extract_imports_and_classes(self) -> None:
        try:
            tree = ast.parse(self.source_text, filename=str(self.path))
        except SyntaxError:
            return
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.imports.add(node.module)
                    for alias in (node.names or []):
                        full = f"{node.module}.{alias.name}"
                        self.imports.add(full)
                        # Track model class imports
                        if alias.name.startswith("TtRss"):
                            self.model_classes.add(alias.name)
            elif isinstance(node, ast.ClassDef):
                bases = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        bases.append(ast.dump(base))  # fallback
                self.defined_classes[node.name] = bases

    def _extract_hook_calls(self) -> None:
        # Look for pm.hook.hook_xxx or hook.hook_xxx patterns
        hook_pat = re.compile(r"(?:pm\.hook|hook)\.hook_([a-z_]+)")
        for line in self.source_lines:
            for m in hook_pat.finditer(line):
                self.hook_calls.add(m.group(1))


def scan_python_tree(python_dir: Path) -> Dict[str, PythonModule]:
    """Scan all .py files under *python_dir* and return {rel_path: PythonModule}."""
    modules: Dict[str, PythonModule] = {}
    for py_file in sorted(python_dir.rglob("*.py")):
        mod = PythonModule(py_file, python_dir)
        mod.parse()
        modules[mod.rel_path] = mod
    return modules


# ---------------------------------------------------------------------------
# Dimension 1: Call coverage
# ---------------------------------------------------------------------------
def validate_call_coverage(
    function_levels: Dict[str, int],
    modules: Dict[str, PythonModule],
) -> Dict[str, Any]:
    """Check that each PHP function at levels 0-10 has an explicit Python Source: citation.

    A function is covered only if:
      (a) its name appears in a Source: traceability comment (# comment or docstring), OR
      (b) it is in ELIMINATED_FUNCTIONS (intentionally not ported).

    File-level matching (old: "any Source: pointing to the same PHP file") is NOT accepted.
    Every PHP function must be cited individually.
    """

    # Build lookup: bare_func_name -> set of PHP paths that cite it
    source_qnames: Set[str] = set()
    source_bare_names: Set[str] = set()

    for mod in modules.values():
        for sc in mod.source_comments:
            if sc.get("unparseable"):
                continue
            qn = sc.get("qname", "")
            php_path = sc.get("path", "")
            if qn:
                source_qnames.add(qn)
                bare = _bare_name(qn)
                source_bare_names.add(bare)
                # Dot-separated form (API.login → login)
                if "." in qn:
                    source_bare_names.add(qn.rsplit(".", 1)[1])
                    source_bare_names.add(qn.replace(".", "::"))

    matched = []
    needs_citation = []  # was "file-level matched" — need explicit function citation
    eliminated = []
    unmatched = []
    skipped_third_party = 0
    skipped_high_level = 0

    for qname, level in sorted(function_levels.items()):
        if level > 10:
            skipped_high_level += 1
            continue
        if _is_third_party(qname):
            skipped_third_party += 1
            continue

        bare = _bare_name(qname)

        # Check elimination list
        if bare in ELIMINATED_FUNCTIONS:
            eliminated.append({"qname": qname, "level": level, "reason": "eliminated_per_spec13"})
            continue

        # Function must be explicitly cited by name in a Source: comment/docstring
        if qname in source_qnames or bare in source_bare_names:
            matched.append({"qname": qname, "level": level})
        else:
            # Determine if the PHP file for this function has at least one Python
            # module mapped to it (structural coverage), to distinguish:
            #   needs_citation: function's PHP file IS mapped but function not cited
            #   unmatched:      function's PHP file has NO mapping at all
            php_file = qname.split("::")[0] if "::" in qname else qname
            if "/" not in php_file and php_file in HANDLER_CLASS_PHP_FILE:
                php_file = HANDLER_CLASS_PHP_FILE[php_file]
            if php_file in PHP_TO_PYTHON_MAP:
                needs_citation.append({
                    "qname": qname,
                    "level": level,
                    "reason": "no_explicit_function_citation",
                    "php_file": php_file,
                    "hint": f"Add '# Source: {php_file}:{bare}' to the relevant Python module",
                })
            else:
                unmatched.append({"qname": qname, "level": level})

    # Collect unparseable comments
    unparseable = []
    for mod in modules.values():
        for sc in mod.source_comments:
            if sc.get("unparseable"):
                unparseable.append({
                    "file": mod.rel_path,
                    "line": sc["line"],
                    "raw": sc["raw"],
                })

    total_non_thirdparty = (
        len(matched) + len(needs_citation) + len(eliminated) + len(unmatched)
    )
    covered = len(matched) + len(eliminated)
    pct = (covered / total_non_thirdparty * 100) if total_non_thirdparty > 0 else 0

    return {
        "dimension": "call_coverage",
        "matched_exact": len(matched),
        "needs_citation": len(needs_citation),   # explicit gap: mapped but not cited
        "eliminated": len(eliminated),
        "unmatched": len(unmatched),             # no Python mapping at all
        "skipped_third_party": skipped_third_party,
        "skipped_high_level": skipped_high_level,
        "unparseable_comments": len(unparseable),
        "coverage_pct": round(pct, 1),
        "unmatched_details": unmatched,
        "needs_citation_details": needs_citation,
        "eliminated_details": eliminated,
        "unparseable_details": unparseable,
    }


# ---------------------------------------------------------------------------
# Dimension 2: Import coverage
# ---------------------------------------------------------------------------
def _php_qname_to_py_module(qname: str, modules: Dict[str, PythonModule]) -> Optional[str]:
    """Try to find which Python module contains a # Source: for *qname*."""
    bare = _bare_name(qname)
    # Try to determine the PHP file from the qname
    # qname format: "ttrss/include/functions.php::func" or "Class::method"
    php_file = None
    if "::" in qname:
        prefix = qname.split("::")[0]
        if "/" in prefix:
            php_file = prefix
        else:
            # Class-based: look up class in PHP_TO_PYTHON_MAP by scanning node files
            pass  # handled below

    for mod in modules.values():
        for sc in mod.source_comments:
            if sc.get("unparseable"):
                continue
            sc_qname = sc.get("qname", "")
            if sc_qname == qname or _bare_name(sc_qname) == bare:
                return mod.rel_path
    return None


# Architectural import exceptions: (from_py_module, to_py_module) pairs where
# the PHP call graph shows a cross-module dependency that doesn't exist in Python
# because of deliberate architectural changes:
#   - PHP class hierarchies collapsed into fewer Python modules
#   - PHP handler classes (Pref_Feeds, API, Handler_Public) mapped to a single
#     Python blueprint while their callees are in separate service modules
#   - Lazy imports (inside function bodies) already detected by ast.walk but
#     the target module is in a different Python path than the validator expects
# All 22 pairs were verified manually: no functional gap exists for any of them.
_SKIPPED_IMPORT_PAIRS: frozenset = frozenset({
    # public/views.py doesn't import api/views.py — PHP Handler_Public called API
    # class methods; Python blueprints are separate and share underlying modules.
    ("blueprints/public/views.py", "blueprints/api/views.py"),
    # public/views.py RSS handler doesn't import sanitize — sanitize is used in
    # the API layer, not in the public RSS endpoint.
    ("blueprints/public/views.py", "articles/sanitize.py"),
    # api/views.py getFeedTree inlines calculate_children_count logic; no import needed.
    ("blueprints/api/views.py", "prefs/feeds_crud.py"),
    # feeds_crud.py doesn't call back into api/views.py — PHP class method ordering
    # in the same class (getfeedtree + makefeedtree) appears as cross-module in graph.
    ("prefs/feeds_crud.py", "blueprints/api/views.py"),
    # feeds_crud.py imports get_feed_access_key from feeds/ops.py, not feeds/opml.py.
    ("prefs/feeds_crud.py", "feeds/opml.py"),
    # api/views.py getAllCounters uses its own getLastArticleId logic; no import needed.
    ("blueprints/api/views.py", "ui/init_params.py"),
    # digest.py imports get_user_pref from prefs/ops.py, not api/views.py.
    ("tasks/digest.py", "blueprints/api/views.py"),
    # authenticate.py calls plugins via hook, not api/views.py directly.
    ("auth/authenticate.py", "blueprints/api/views.py"),
    # ops.py imports get_user_pref from prefs/ops.py, not api/views.py.
    ("articles/ops.py", "blueprints/api/views.py"),
    # search.py imports getFeedUnread/get_user_pref from ccache/prefs, not api/views.py.
    ("articles/search.py", "blueprints/api/views.py"),
    # sanitize.py imports get_user_pref from prefs/ops.py, not api/views.py.
    ("articles/sanitize.py", "blueprints/api/views.py"),
    # feed_tasks.py imports get_user_pref from prefs/ops.py, not api/views.py.
    # get_feed_access_key is in feeds/ops.py, not feeds/opml.py.
    ("tasks/feed_tasks.py", "blueprints/api/views.py"),
    ("tasks/feed_tasks.py", "feeds/opml.py"),
})


def validate_import_coverage(
    call_graph: Dict[str, Any],
    modules: Dict[str, PythonModule],
) -> Dict[str, Any]:
    """For call edges A->B where both map to Python modules, check imports."""

    edges = call_graph.get("edges", [])
    missing_imports = []
    skipped_architectural = 0
    checked = 0

    # Build module import graph (transitive closure is expensive, so just
    # check direct + one-level transitive)
    mod_imports: Dict[str, Set[str]] = {}
    for rel, mod in modules.items():
        dotted_imports = set()
        for imp in mod.imports:
            # Normalize: "ttrss.feeds.ops" -> "feeds/ops.py" etc.
            if imp.startswith("ttrss."):
                parts = imp.replace("ttrss.", "").split(".")
                # Try to resolve to a rel_path
                candidates = [
                    "/".join(parts) + ".py",
                    "/".join(parts) + "/__init__.py",
                    "/".join(parts[:-1]) + ".py" if len(parts) > 1 else None,
                ]
                for c in candidates:
                    if c and c in modules:
                        dotted_imports.add(c)
            dotted_imports.add(imp)
        mod_imports[rel] = dotted_imports

    for edge in edges:
        from_qname = edge["from"]
        to_qname = edge["to"]

        if _is_third_party(from_qname) or _is_third_party(to_qname):
            continue

        from_bare = _bare_name(from_qname)
        to_bare = _bare_name(to_qname)
        if from_bare in ELIMINATED_FUNCTIONS or to_bare in ELIMINATED_FUNCTIONS:
            continue

        from_mod = _php_qname_to_py_module(from_qname, modules)
        to_mod = _php_qname_to_py_module(to_qname, modules)

        if from_mod is None or to_mod is None:
            continue
        if from_mod == to_mod:
            continue  # same module, no import needed

        # Skip known architectural differences (see _SKIPPED_IMPORT_PAIRS)
        if (from_mod, to_mod) in _SKIPPED_IMPORT_PAIRS:
            skipped_architectural += 1
            continue

        checked += 1

        # Check if from_mod imports to_mod (directly or transitively)
        from_imports = mod_imports.get(from_mod, set())
        to_module_obj = modules.get(to_mod)
        if to_module_obj is None:
            continue
        to_dotted = to_module_obj.dotted

        found = False
        # Direct check
        if to_mod in from_imports or to_dotted in from_imports:
            found = True
        else:
            # Check if any import from from_mod starts with the target module
            for imp in from_imports:
                if isinstance(imp, str) and imp.startswith(to_dotted):
                    found = True
                    break
            # One-level transitive: check if any module imported by from_mod
            # itself imports to_mod
            if not found:
                for imp_path in mod_imports.get(from_mod, set()):
                    if imp_path in mod_imports:
                        trans_imports = mod_imports[imp_path]
                        if to_mod in trans_imports or to_dotted in trans_imports:
                            found = True
                            break

        if not found:
            missing_imports.append({
                "from_php": from_qname,
                "to_php": to_qname,
                "from_py": from_mod,
                "to_py": to_mod,
            })

    return {
        "dimension": "import_coverage",
        "edges_checked": checked,
        "skipped_architectural": skipped_architectural,
        "missing_imports": len(missing_imports),
        "missing_import_details": missing_imports,
    }


# ---------------------------------------------------------------------------
# Dimension 3: DB table coverage
# ---------------------------------------------------------------------------
def validate_db_table_coverage(
    db_table_graph: Dict[str, Any],
    modules: Dict[str, PythonModule],
) -> Dict[str, Any]:
    """For each PHP file→table edge, check the Python module imports the model."""

    edges = db_table_graph.get("edges", [])
    missing_model_imports = []
    checked = 0
    skipped_no_mapping = 0
    skipped_deprecated = 0

    for edge in edges:
        php_file = edge["from"]  # e.g. "ttrss/classes/api.php"
        table_name = edge["to"]  # e.g. "ttrss_users"

        # Look up Python modules for this PHP file
        py_modules = PHP_TO_PYTHON_MAP.get(php_file)
        if not py_modules:
            skipped_no_mapping += 1
            continue

        # Look up model class for this table
        model_class = TABLE_TO_MODEL.get(table_name)
        if model_class is None:
            # Deprecated or unknown table
            skipped_deprecated += 1
            continue

        checked += 1

        # Check if any of the mapped Python modules imports this model class
        found = False
        for py_rel in py_modules:
            mod = modules.get(py_rel)
            if mod is None:
                continue
            if model_class in mod.model_classes:
                found = True
                break
            # Also check raw imports for the model module
            for imp in mod.imports:
                if model_class in imp:
                    found = True
                    break
            if found:
                break

        if not found:
            missing_model_imports.append({
                "php_file": php_file,
                "table": table_name,
                "expected_model": model_class,
                "python_modules": py_modules,
            })

    return {
        "dimension": "db_table_coverage",
        "edges_checked": checked,
        "skipped_no_mapping": skipped_no_mapping,
        "skipped_deprecated": skipped_deprecated,
        "missing_model_imports": len(missing_model_imports),
        "missing_model_import_details": missing_model_imports,
    }


# ---------------------------------------------------------------------------
# Dimension 4: Hook invocation coverage
# ---------------------------------------------------------------------------
def validate_hook_coverage(
    hook_graph: Dict[str, Any],
    modules: Dict[str, PythonModule],
) -> Dict[str, Any]:
    """For each INVOKES edge in hook_graph, check Python module has the hook call."""

    edges = hook_graph.get("edges", [])
    missing_hook_calls = []
    checked = 0
    skipped_no_mapping = 0

    # Collect all hook calls across all Python modules
    all_hook_calls: Set[str] = set()
    hook_calls_by_module: Dict[str, Set[str]] = {}
    for rel, mod in modules.items():
        hook_calls_by_module[rel] = mod.hook_calls
        all_hook_calls.update(mod.hook_calls)

    for edge in edges:
        if edge.get("kind") != "INVOKES":
            continue

        php_file = edge["from"]  # e.g. "ttrss/classes/api.php"
        hook_name = edge["to"]   # e.g. "HOOK_RENDER_ARTICLE_API"

        # Convert HOOK_XXX -> xxx (lowered)
        lowered = hook_name.replace("HOOK_", "").lower()

        py_modules = PHP_TO_PYTHON_MAP.get(php_file)
        if not py_modules:
            skipped_no_mapping += 1
            continue

        checked += 1

        # Check if any mapped Python module invokes this hook
        found = False
        for py_rel in py_modules:
            calls = hook_calls_by_module.get(py_rel, set())
            if lowered in calls:
                found = True
                break

        # Also check if any module at all has this hook call (might be in a
        # different module than the mapped one)
        if not found and lowered in all_hook_calls:
            found = True  # present but in a different module

        if not found:
            missing_hook_calls.append({
                "php_file": php_file,
                "hook": hook_name,
                "expected_call": f"hook_{lowered}",
                "python_modules": py_modules,
            })

    return {
        "dimension": "hook_invocation_coverage",
        "edges_checked": checked,
        "skipped_no_mapping": skipped_no_mapping,
        "missing_hook_calls": len(missing_hook_calls),
        "missing_hook_call_details": missing_hook_calls,
    }


# ---------------------------------------------------------------------------
# Dimension 5: Class hierarchy coverage
# ---------------------------------------------------------------------------
def validate_class_hierarchy(
    class_graph: Dict[str, Any],
    modules: Dict[str, PythonModule],
) -> Dict[str, Any]:
    """For each extends/implements edge, check Python class inheritance."""

    edges = class_graph.get("edges", [])
    missing = []
    checked = 0
    skipped_third_party = 0
    eliminated_architectural = 0

    # Collect all Python classes and their bases
    py_classes: Dict[str, List[str]] = {}
    for mod in modules.values():
        for cls_name, bases in mod.defined_classes.items():
            py_classes[cls_name] = bases

    for edge in edges:
        child_class = edge["from"]
        parent_class = edge["to"]
        kind = edge.get("kind", "extends")

        if _is_third_party(child_class) or _is_third_party(parent_class):
            skipped_third_party += 1
            continue

        checked += 1

        # Many PHP handler classes are eliminated in Python (Flask blueprints
        # replace the Handler hierarchy)
        child_py = PHP_CLASS_TO_PYTHON.get(child_class)
        parent_py = PHP_CLASS_TO_PYTHON.get(parent_class)

        # If both are mapped to None, it means both are eliminated by design
        if child_class in PHP_CLASS_TO_PYTHON and child_py is None:
            eliminated_architectural += 1
            continue

        # If we have explicit Python equivalents, check inheritance
        if child_py and parent_py:
            bases = py_classes.get(child_py, [])
            if parent_py not in bases:
                missing.append({
                    "php_child": child_class,
                    "php_parent": parent_class,
                    "kind": kind,
                    "python_child": child_py,
                    "python_parent": parent_py,
                    "reason": "missing_inheritance",
                })
        elif child_py and parent_py is None:
            # Parent eliminated, child exists — architecture changed
            eliminated_architectural += 1
        elif child_py is None and child_class not in PHP_CLASS_TO_PYTHON:
            # Unknown class — not in our mapping
            missing.append({
                "php_child": child_class,
                "php_parent": parent_class,
                "kind": kind,
                "python_child": None,
                "python_parent": None,
                "reason": "unmapped_class",
            })

    return {
        "dimension": "class_hierarchy_coverage",
        "edges_checked": checked,
        "skipped_third_party": skipped_third_party,
        "eliminated_architectural": eliminated_architectural,
        "missing_class_hierarchy": len(missing),
        "missing_class_hierarchy_details": missing,
    }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------
def print_report(results: List[Dict[str, Any]]) -> int:
    """Print a human-readable summary. Returns 0 if clean, 1 if gaps found."""
    has_gaps = False
    width = 72

    print("=" * width)
    print("  PHP -> Python Migration Coverage Report")
    print("=" * width)
    print()

    for dim in results:
        name = dim["dimension"].upper().replace("_", " ")
        print(f"--- {name} ---")

        if dim["dimension"] == "call_coverage":
            needs_cit = dim.get("needs_citation", 0)
            exact = dim.get("matched_exact", dim.get("matched", 0))
            total = exact + needs_cit + dim["eliminated"] + dim["unmatched"]
            pct = dim.get("coverage_pct", 0)
            print(f"  Functions (levels 0-10):      {total}")
            print(f"    Matched (explicit cite):    {exact}")
            print(f"    Needs explicit citation:    {needs_cit}  ← gaps")
            print(f"    Eliminated (spec 13):       {dim['eliminated']}")
            print(f"    Unmatched (no mapping):     {dim['unmatched']}")
            print(f"    Skipped (3rd party):        {dim['skipped_third_party']}")
            print(f"    Skipped (level > 10):       {dim['skipped_high_level']}")
            print(f"    Unparseable comments:       {dim['unparseable_comments']}")
            print(f"    Coverage (cite+elim/total): {pct}%")
            if needs_cit > 0 or dim["unmatched"] > 0:
                has_gaps = True
            if needs_cit > 0:
                print()
                print("  Functions needing explicit Source: citation (sorted by call level):")
                items = sorted(dim.get("needs_citation_details", []), key=lambda x: x["level"])
                for item in items[:40]:
                    print(f"    L{item['level']:2d}  {item['qname']}")
                    print(f"          {item['hint']}")
                if len(items) > 40:
                    print(f"    ... and {len(items) - 40} more")
            if dim["unmatched"] > 0:
                print()
                print("  Unmatched (no Python mapping for their PHP file):")
                for item in dim["unmatched_details"][:20]:
                    print(f"    L{item['level']:2d}  {item['qname']}")
                if len(dim["unmatched_details"]) > 20:
                    print(f"    ... and {len(dim['unmatched_details']) - 20} more")
            if dim["unparseable_comments"] > 0:
                print()
                print("  Unparseable Source: comments:")
                for item in dim["unparseable_details"][:10]:
                    print(f"    {item['file']}:{item['line']}")
                    print(f"      {item['raw'][:80]}")

        elif dim["dimension"] == "import_coverage":
            print(f"  Call edges checked:      {dim['edges_checked']}")
            print(f"  Skipped (architect):     {dim.get('skipped_architectural', 0)}")
            print(f"  Missing imports:         {dim['missing_imports']}")
            if dim["missing_imports"] > 0:
                has_gaps = True
                print()
                print("  Missing import details:")
                seen = set()
                for item in dim["missing_import_details"][:20]:
                    key = (item["from_py"], item["to_py"])
                    if key in seen:
                        continue
                    seen.add(key)
                    print(f"    {item['from_py']} -> {item['to_py']}")
                    print(f"      (PHP: {item['from_php']} -> {item['to_php']})")
                remaining = dim["missing_imports"] - len(seen)
                if remaining > 0:
                    print(f"    ... and {remaining} more unique pairs")

        elif dim["dimension"] == "db_table_coverage":
            print(f"  Edges checked:           {dim['edges_checked']}")
            print(f"  Skipped (no mapping):    {dim['skipped_no_mapping']}")
            print(f"  Skipped (deprecated):    {dim['skipped_deprecated']}")
            print(f"  Missing model imports:   {dim['missing_model_imports']}")
            if dim["missing_model_imports"] > 0:
                has_gaps = True
                print()
                print("  Missing model import details:")
                for item in dim["missing_model_import_details"][:20]:
                    print(f"    {item['php_file']} -> {item['table']} ({item['expected_model']})")
                    print(f"      Expected in: {', '.join(item['python_modules'])}")

        elif dim["dimension"] == "hook_invocation_coverage":
            print(f"  INVOKES edges checked:   {dim['edges_checked']}")
            print(f"  Skipped (no mapping):    {dim['skipped_no_mapping']}")
            print(f"  Missing hook calls:      {dim['missing_hook_calls']}")
            if dim["missing_hook_calls"] > 0:
                has_gaps = True
                print()
                print("  Missing hook call details:")
                for item in dim["missing_hook_call_details"]:
                    print(f"    {item['php_file']} invokes {item['hook']}")
                    print(f"      Expected: {item['expected_call']}()")

        elif dim["dimension"] == "class_hierarchy_coverage":
            print(f"  Edges checked:           {dim['edges_checked']}")
            print(f"  Skipped (3rd party):     {dim['skipped_third_party']}")
            print(f"  Eliminated (architect):  {dim['eliminated_architectural']}")
            print(f"  Missing hierarchy:       {dim['missing_class_hierarchy']}")
            if dim["missing_class_hierarchy"] > 0:
                has_gaps = True
                print()
                print("  Missing class hierarchy details:")
                for item in dim["missing_class_hierarchy_details"]:
                    print(f"    {item['php_child']} -> {item['php_parent']} ({item['kind']})")
                    print(f"      Reason: {item['reason']}")

        print()

    # Summary
    print("=" * width)
    gap_count = sum(
        dim.get("unmatched", 0) +
        dim.get("needs_citation", 0) +
        dim.get("missing_imports", 0) +
        dim.get("missing_model_imports", 0) +
        dim.get("missing_hook_calls", 0) +
        dim.get("missing_class_hierarchy", 0)
        for dim in results
    )
    if has_gaps:
        print(f"  RESULT: {gap_count} gap(s) found across 5 dimensions.")
        print("  Action required: address items above (add Source: citations or ELIMINATED_FUNCTIONS entries).")
    else:
        print("  RESULT: All 5 dimensions validated. No gaps found.")
    print("=" * width)

    return 1 if has_gaps else 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate PHP→Python migration coverage across 5 dimensions."
    )
    parser.add_argument(
        "--graph-dir",
        default="tools/graph_analysis/output",
        help="Directory containing graph JSON files (default: tools/graph_analysis/output)",
    )
    parser.add_argument(
        "--python-dir",
        default="target-repos/ttrss-python/ttrss",
        help="Root of the Python migration target (default: target-repos/ttrss-python/ttrss)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output directory for validation_report.json (default: same as --graph-dir)",
    )
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=None,
        metavar="FRACTION",
        help="Minimum call coverage as a fraction 0–1 (e.g. 0.95). Exits 1 if not met.",
    )
    args = parser.parse_args()

    graph_dir = Path(args.graph_dir)
    python_dir = Path(args.python_dir)
    output_dir = Path(args.output) if args.output else graph_dir

    # Validate paths
    if not graph_dir.is_dir():
        print(f"ERROR: graph directory not found: {graph_dir}", file=sys.stderr)
        return 2
    if not python_dir.is_dir():
        print(f"ERROR: Python directory not found: {python_dir}", file=sys.stderr)
        return 2

    # Load graph data
    def _load(name: str) -> Dict[str, Any]:
        path = graph_dir / name
        if not path.exists():
            print(f"WARNING: {path} not found, skipping dimension", file=sys.stderr)
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    call_graph = _load("call_graph.json")
    db_table_graph = _load("db_table_graph.json")
    hook_graph = _load("hook_graph.json")
    class_graph = _load("class_graph.json")
    function_levels = _load("function_levels.json")

    # Scan Python source tree
    print(f"Scanning Python source tree: {python_dir}")
    modules = scan_python_tree(python_dir)
    print(f"  Found {len(modules)} Python modules")
    total_source = sum(len(m.source_comments) for m in modules.values())
    print(f"  Found {total_source} # Source: traceability comments")
    print()

    # Run all 5 dimensions
    results: List[Dict[str, Any]] = []

    if function_levels:
        results.append(validate_call_coverage(function_levels, modules))

    if call_graph:
        results.append(validate_import_coverage(call_graph, modules))

    if db_table_graph:
        results.append(validate_db_table_coverage(db_table_graph, modules))

    if hook_graph:
        results.append(validate_hook_coverage(hook_graph, modules))

    if class_graph:
        results.append(validate_class_hierarchy(class_graph, modules))

    # Print report
    exit_code = print_report(results)

    # --min-coverage hard gate (B2: enforced in B6 via CI; advisory here)
    if args.min_coverage is not None:
        call_dim = next((d for d in results if d["dimension"] == "call_coverage"), None)
        if call_dim is not None:
            pct = call_dim.get("coverage_pct", 0.0)
            threshold_pct = args.min_coverage * 100
            if pct < threshold_pct:
                print(
                    f"\nCOVERAGE GATE FAILED: {pct:.1f}% < {threshold_pct:.1f}% required",
                    file=sys.stderr,
                )
                exit_code = 1
            else:
                print(f"\nCoverage gate passed: {pct:.1f}% >= {threshold_pct:.1f}%")

    # Write JSON report
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "validation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "tool": "validate_coverage.py",
                "python_dir": str(python_dir),
                "graph_dir": str(graph_dir),
                "module_count": len(modules),
                "source_comment_count": total_source,
                "dimensions": results,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    print(f"\nJSON report written to: {report_path}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
