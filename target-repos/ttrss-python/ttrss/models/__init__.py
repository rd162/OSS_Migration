"""
Import all 10 models to register them with Base.metadata.
Imported by ttrss/__init__.py (module level) and alembic/env.py.
AR03: sqlacodegen output is NEVER imported here — all models are hand-written.

Source: ttrss/schema/ttrss_schema_pgsql.sql (all 10 tables modeled below)
  ttrss_users (13 columns), ttrss_feed_categories (6), ttrss_feeds (34),
  ttrss_entries (15), ttrss_user_entries (16), ttrss_tags (4),
  ttrss_enclosures (6), ttrss_labels2 (5), ttrss_user_labels2 (2),
  ttrss_version (1).

New: module-level import pattern (no PHP equivalent — PHP used autoload.php)

Remaining 25 tables (Phase 1b+): ttrss_archived_feeds, ttrss_counters_cache,
  ttrss_cat_counters_cache, ttrss_entry_comments, ttrss_filter_types,
  ttrss_filter_actions, ttrss_filters2, ttrss_filters2_rules, ttrss_filters2_actions,
  ttrss_settings_profiles, ttrss_prefs_types, ttrss_prefs_sections, ttrss_prefs,
  ttrss_user_prefs, ttrss_sessions, ttrss_feedbrowser_cache, ttrss_access_keys,
  ttrss_linked_instances, ttrss_linked_feeds, ttrss_plugin_storage, ttrss_error_log,
  ttrss_themes, ttrss_scheduled_updates, ttrss_labels (deprecated), ttrss_filters (deprecated).
"""
from ttrss.models.base import Base  # noqa: F401 — re-exported for alembic/env.py
from ttrss.models.category import TtRssFeedCategory  # noqa: F401
from ttrss.models.enclosure import TtRssEnclosure  # noqa: F401
from ttrss.models.entry import TtRssEntry  # noqa: F401
from ttrss.models.feed import TtRssFeed  # noqa: F401
from ttrss.models.label import TtRssLabel2, TtRssUserLabel2  # noqa: F401
from ttrss.models.tag import TtRssTag  # noqa: F401
from ttrss.models.user import TtRssUser  # noqa: F401
from ttrss.models.user_entry import TtRssUserEntry  # noqa: F401
from ttrss.models.version import TtRssVersion  # noqa: F401
