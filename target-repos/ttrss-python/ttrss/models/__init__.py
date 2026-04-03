"""
Import all models to register them with Base.metadata.
Imported by ttrss/__init__.py (module level) and alembic/env.py.
AR03: sqlacodegen output is NEVER imported here — all models are hand-written.

Source: ttrss/schema/ttrss_schema_pgsql.sql (schema version 124)

Total active tables in schema: 31 (4 tables listed in specs/02-database.md §Deprecated
were already DROP'd before version 124: ttrss_themes (v83), ttrss_labels, ttrss_filters,
ttrss_scheduled_updates — no CREATE TABLE exists in the base schema).

Phase 1a (10 tables):
  ttrss_users, ttrss_feed_categories, ttrss_feeds (+2 ADR-0015 extensions),
  ttrss_entries, ttrss_user_entries, ttrss_tags, ttrss_enclosures,
  ttrss_labels2, ttrss_user_labels2, ttrss_version.

Phase 1b (21 tables):
  Batch 1: ttrss_archived_feeds, ttrss_counters_cache, ttrss_cat_counters_cache,
           ttrss_entry_comments.
  Batch 2: ttrss_filter_types, ttrss_filter_actions, ttrss_filters2,
           ttrss_filters2_rules, ttrss_filters2_actions.
  Batch 3: ttrss_prefs_types, ttrss_prefs_sections, ttrss_prefs,
           ttrss_settings_profiles, ttrss_user_prefs.
  Batch 4: ttrss_sessions, ttrss_feedbrowser_cache, ttrss_access_keys.
  Batch 5: ttrss_linked_instances, ttrss_linked_feeds, ttrss_plugin_storage,
           ttrss_error_log.

New: module-level import pattern (no PHP equivalent — PHP used autoload.php)
"""
from ttrss.models.access_key import TtRssAccessKey  # noqa: F401
from ttrss.models.archived_feed import TtRssArchivedFeed  # noqa: F401
from ttrss.models.base import Base  # noqa: F401 — re-exported for alembic/env.py
from ttrss.models.category import TtRssFeedCategory  # noqa: F401
from ttrss.models.counters_cache import TtRssCatCountersCache, TtRssCountersCache  # noqa: F401
from ttrss.models.enclosure import TtRssEnclosure  # noqa: F401
from ttrss.models.entry import TtRssEntry  # noqa: F401
from ttrss.models.entry_comment import TtRssEntryComment  # noqa: F401
from ttrss.models.error_log import TtRssErrorLog  # noqa: F401
from ttrss.models.feed import TtRssFeed  # noqa: F401
from ttrss.models.feedbrowser_cache import TtRssFeedbrowserCache  # noqa: F401
from ttrss.models.filter import (  # noqa: F401
    TtRssFilter2,
    TtRssFilter2Action,
    TtRssFilter2Rule,
    TtRssFilterAction,
    TtRssFilterType,
)
from ttrss.models.label import TtRssLabel2, TtRssUserLabel2  # noqa: F401
from ttrss.models.linked import TtRssLinkedFeed, TtRssLinkedInstance  # noqa: F401
from ttrss.models.plugin_storage import TtRssPluginStorage  # noqa: F401
from ttrss.models.pref import (  # noqa: F401
    TtRssPref,
    TtRssPrefsSection,
    TtRssPrefsType,
    TtRssSettingsProfile,
    TtRssUserPref,
)
from ttrss.models.session import TtRssSession  # noqa: F401
from ttrss.models.tag import TtRssTag  # noqa: F401
from ttrss.models.user import TtRssUser  # noqa: F401
from ttrss.models.user_entry import TtRssUserEntry  # noqa: F401
from ttrss.models.version import TtRssVersion  # noqa: F401
