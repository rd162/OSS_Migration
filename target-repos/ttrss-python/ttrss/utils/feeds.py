"""Virtual feed ID scheme constants and feed classification utilities.

Source: ttrss/include/functions.php (constants, lines 5-6)
        ttrss/include/functions2.php (label_to_feed_id/feed_to_label_id, lines 2400-2406)
        ttrss/classes/pluginhost.php (pfeed_to_feed_id/feed_to_pfeed_id, lines 381-387)
"""
from __future__ import annotations

# Source: ttrss/include/functions.php:5
LABEL_BASE_INDEX: int = -1024

# Source: ttrss/include/functions.php:6
PLUGIN_FEED_BASE_INDEX: int = -128


def label_to_feed_id(label_id: int) -> int:
    """Convert label database ID to virtual feed ID.
    # Source: ttrss/include/functions2.php:label_to_feed_id (lines 2400-2401)
    """
    return LABEL_BASE_INDEX - 1 - abs(label_id)


def feed_to_label_id(feed_id: int) -> int:
    """Convert virtual label feed ID back to label database ID.
    # Source: ttrss/include/functions2.php:feed_to_label_id (lines 2404-2405)
    """
    return LABEL_BASE_INDEX - 1 + abs(feed_id)


def pfeed_to_feed_id(pfeed_id: int) -> int:
    """Convert plugin feed ID to virtual feed ID.
    Source: ttrss/classes/pluginhost.php:381-382
    """
    return PLUGIN_FEED_BASE_INDEX - 1 - abs(pfeed_id)


def feed_to_pfeed_id(feed_id: int) -> int:
    """Convert virtual plugin feed ID back to plugin feed ID.
    Source: ttrss/classes/pluginhost.php:385-386
    """
    return PLUGIN_FEED_BASE_INDEX - 1 + abs(feed_id)


def classify_feed_id(feed_id: int | str) -> str:
    """Return routing category for a feed_id.

    Source: inferred from ttrss/classes/feeds.php virtual feed routing (line 221)

    Returns one of:
    - "tag"     : string feed_id  (tag name)
    - "regular" : feed_id >= 0   (0 = uncategorized placeholder)
    - "label"   : feed_id < LABEL_BASE_INDEX  (i.e. <= -1025)
    - "plugin"  : LABEL_BASE_INDEX <= feed_id <= PLUGIN_FEED_BASE_INDEX  (-128 to -1024)
    - "special" : -127 <= feed_id <= -1  (virtual feeds -1 through -6)
    """
    if isinstance(feed_id, str):
        return "tag"
    feed_id = int(feed_id)
    if feed_id >= 0:
        return "regular"
    if feed_id < LABEL_BASE_INDEX:
        return "label"
    if feed_id <= PLUGIN_FEED_BASE_INDEX:
        return "plugin"
    return "special"
