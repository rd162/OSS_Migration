"""OPML import and export for TT-RSS feed subscriptions, categories, labels,
filters, and preferences.

Source: ttrss/classes/opml.php:Opml (full class, lines 1-523)

Design notes
------------
* Export uses ``lxml.etree`` (already a project dependency, ADR-0014) for
  well-formed, pretty-printed XML.
* Import uses stdlib ``xml.etree.ElementTree`` (safe for untrusted input when
  combined with Python's default expat limits; no external network calls).
* PHP used raw string concatenation + DOMDocument for export; Python builds the
  element tree directly then serialises.
* PHP handled HTTP headers and file-upload I/O inside the class; Python exposes
  pure functions — callers (blueprints) handle HTTP concerns.
* SCHEMA_VERSION is read from the live DB via ``prefs.ops.get_schema_version``
  rather than the PHP ``SCHEMA_VERSION`` constant.
* ``opml_export`` / ``opml_import`` are PHP method names preserved as
  ``opml_export_full`` / ``import_opml`` to avoid shadowing the module name.
"""
from __future__ import annotations

import json
import logging
import xml.etree.ElementTree as ET
from typing import Optional

from lxml import etree as lxml_etree
from sqlalchemy import select
from sqlalchemy.orm import Session

from ttrss.feeds.categories import (
    add_feed_category,
    get_feed_category,
    getFeedTitle,
)
from ttrss.labels import label_create, label_find_id
from ttrss.models.access_key import TtRssAccessKey
from ttrss.models.category import TtRssFeedCategory
from ttrss.models.feed import TtRssFeed
from ttrss.models.filter import TtRssFilter2, TtRssFilter2Action, TtRssFilter2Rule
from ttrss.models.label import TtRssLabel2
from ttrss.models.pref import TtRssUserPref
from ttrss.prefs.ops import get_schema_version, set_user_pref

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CSRF exemptions
# ---------------------------------------------------------------------------

# Source: ttrss/classes/opml.php:Opml::csrf_ignore (lines 4-8)
def csrf_ignore() -> list[str]:
    """Return the list of handler names that are exempt from CSRF verification.

    Source: ttrss/classes/opml.php:Opml::csrf_ignore (lines 4-8)
    PHP: $csrf_ignored = array("export", "import"); return array_search(...) !== false
    Python: Blueprint views call this to decide whether to enforce WTF-CSRF.
    """
    return ["import", "export"]


# ---------------------------------------------------------------------------
# Public URL helper
# ---------------------------------------------------------------------------

# Source: ttrss/classes/opml.php:Opml::opml_publish_url (lines 512-519)
def opml_publish_url(session: Session, user_id: int, base_url: str) -> str:
    """Return the public (unauthenticated) OPML URL for *user_id*.

    Source: ttrss/classes/opml.php:Opml::opml_publish_url (lines 512-519)
    PHP: get_self_url_prefix() + "/opml.php?op=publish&key=" + get_feed_access_key(...)
    Adapted: base_url passed explicitly (no PHP get_self_url_prefix() global).
             get_feed_access_key logic inlined using TtRssAccessKey model.
    """
    # Source: ttrss/include/functions2.php:get_feed_access_key (lines 1763-1785)
    # "OPML:Publish" is the feed_id string used by PHP for the publish access key.
    feed_id_str = "OPML:Publish"
    row = session.execute(
        select(TtRssAccessKey.access_key)
        .where(TtRssAccessKey.feed_id == feed_id_str)
        .where(TtRssAccessKey.is_cat.is_(False))
        .where(TtRssAccessKey.owner_uid == user_id)
    ).scalar_one_or_none()

    if row is None:
        import secrets
        key = secrets.token_urlsafe(16)[:24]
        session.add(
            TtRssAccessKey(
                access_key=key,
                feed_id=feed_id_str,
                is_cat=False,
                owner_uid=user_id,
            )
        )
        session.flush()
    else:
        key = row

    return f"{base_url.rstrip('/')}/opml.php?op=publish&key={key}"


# ---------------------------------------------------------------------------
# Export — internal helpers
# ---------------------------------------------------------------------------

# Source: ttrss/classes/opml.php:Opml::opml_export_category (lines 51-106)
def opml_export_category(
    session: Session,
    user_id: int,
    cat_id: Optional[int],
    hide_private_feeds: bool = False,
    parent_elem: Optional[lxml_etree._Element] = None,
) -> lxml_etree._Element:
    """Recursively build OPML ``<outline>`` elements for one category.

    Source: ttrss/classes/opml.php:Opml::opml_export_category (lines 51-106)
    PHP: builds raw XML string recursively; Python builds an lxml element tree.
    Returns the element that was populated (either *parent_elem* or a new
    ``<outline type="folder">`` element created for this category).
    """
    # Determine the wrapper element for this category's children.
    # Source: opml.php lines 68-74 — if $cat_id, wrap in <outline text="$cat_title">
    if cat_id is not None:
        cat_title = session.execute(
            select(TtRssFeedCategory.title)
            .where(TtRssFeedCategory.id == cat_id)
            .where(TtRssFeedCategory.owner_uid == user_id)
        ).scalar_one_or_none()

        if cat_title is None:
            # Category not owned by this user or doesn't exist — skip.
            if parent_elem is not None:
                return parent_elem
            return lxml_etree.Element("outline")

        wrapper = lxml_etree.SubElement(
            parent_elem if parent_elem is not None else lxml_etree.Element("_root"),
            "outline",
            text=cat_title,
        )
    else:
        # Top-level: use parent_elem as the container (the <body> element).
        wrapper = parent_elem  # type: ignore[assignment]

    # Recurse into sub-categories.
    # Source: opml.php lines 76-83 — SELECT ... FROM ttrss_feed_categories WHERE parent_cat = ...
    if cat_id is not None:
        sub_cat_qpart = TtRssFeedCategory.parent_cat == cat_id
    else:
        sub_cat_qpart = TtRssFeedCategory.parent_cat.is_(None)

    sub_cats = session.execute(
        select(TtRssFeedCategory.id)
        .where(sub_cat_qpart)
        .where(TtRssFeedCategory.owner_uid == user_id)
        .order_by(TtRssFeedCategory.order_id, TtRssFeedCategory.title)
    ).scalars().all()

    for sub_cat_id in sub_cats:
        opml_export_category(
            session,
            user_id,
            sub_cat_id,
            hide_private_feeds=hide_private_feeds,
            parent_elem=wrapper,
        )

    # Emit feed <outline> elements for this category.
    # Source: opml.php lines 85-101 — SELECT title,feed_url,site_url FROM ttrss_feeds WHERE ...
    feed_q = (
        select(TtRssFeed.title, TtRssFeed.feed_url, TtRssFeed.site_url)
        .where(TtRssFeed.owner_uid == user_id)
        .order_by(TtRssFeed.order_id, TtRssFeed.title)
    )
    if cat_id is not None:
        feed_q = feed_q.where(TtRssFeed.cat_id == cat_id)
    else:
        feed_q = feed_q.where(TtRssFeed.cat_id.is_(None))

    if hide_private_feeds:
        # Source: opml.php lines 61-64 — AND (private IS false AND auth_login='' AND auth_pass='')
        feed_q = feed_q.where(
            TtRssFeed.private.is_(False),
            TtRssFeed.auth_login == "",
            TtRssFeed._auth_pass == "",
        )

    for feed_row in session.execute(feed_q).all():
        attribs: dict[str, str] = {
            "type": "rss",
            "text": feed_row.title or "",
            "xmlUrl": feed_row.feed_url or "",
        }
        if feed_row.site_url:
            attribs["htmlUrl"] = feed_row.site_url
        lxml_etree.SubElement(wrapper, "outline", **attribs)

    return wrapper


# Source: ttrss/classes/opml.php:Opml::opml_export (lines 108-250)
def opml_export_full(
    session: Session,
    user_id: int,
    hide_private_feeds: bool = False,
    include_settings: bool = True,
) -> str:
    """Build and return a complete OPML 2.0 document as a UTF-8 XML string.

    Source: ttrss/classes/opml.php:Opml::opml_export (lines 108-250)
    PHP: builds string, loads via DOMDocument for pretty-printing, removes
         empty categories. Python builds via lxml from the start.
    Adapted: PHP sends HTTP headers inside this function; Python is pure
             (callers set Content-Type/Content-Disposition headers).
    """
    if not user_id:
        return ""

    schema_ver = get_schema_version()

    root = lxml_etree.Element("opml", version="1.0")
    head = lxml_etree.SubElement(root, "head")

    # Source: opml.php lines 121-125 — <dateCreated> + <title>
    from datetime import datetime, timezone
    lxml_etree.SubElement(head, "dateCreated").text = (
        datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    )
    lxml_etree.SubElement(head, "title").text = "Tiny Tiny RSS Feed Export"

    body = lxml_etree.SubElement(root, "body")

    # Export feed/category hierarchy starting from top-level (cat_id=None).
    # Source: opml.php line 127 — $out .= $this->opml_export_category($owner_uid, false, ...)
    opml_export_category(
        session,
        user_id,
        cat_id=None,
        hide_private_feeds=hide_private_feeds,
        parent_elem=body,
    )

    if include_settings:
        # --- Preferences ---
        # Source: opml.php lines 133-143 — <outline text="tt-rss-prefs" ...> per-pref <outline>
        prefs_outline = lxml_etree.SubElement(
            body,
            "outline",
            text="tt-rss-prefs",
            **{"schema-version": str(schema_ver)},
        )
        pref_rows = session.execute(
            select(TtRssUserPref.pref_name, TtRssUserPref.value)
            .where(TtRssUserPref.owner_uid == user_id)
            .where(TtRssUserPref.profile.is_(None))
            .order_by(TtRssUserPref.pref_name)
        ).all()
        for pref_row in pref_rows:
            lxml_etree.SubElement(
                prefs_outline,
                "outline",
                **{"pref-name": pref_row.pref_name, "value": pref_row.value or ""},
            )

        # --- Labels ---
        # Source: opml.php lines 145-158 — <outline text="tt-rss-labels" ...> per-label <outline>
        labels_outline = lxml_etree.SubElement(
            body,
            "outline",
            text="tt-rss-labels",
            **{"schema-version": str(schema_ver)},
        )
        label_rows = session.execute(
            select(TtRssLabel2.caption, TtRssLabel2.fg_color, TtRssLabel2.bg_color)
            .where(TtRssLabel2.owner_uid == user_id)
        ).all()
        for lrow in label_rows:
            lxml_etree.SubElement(
                labels_outline,
                "outline",
                **{
                    "label-name": lrow.caption or "",
                    "label-fg-color": lrow.fg_color or "",
                    "label-bg-color": lrow.bg_color or "",
                },
            )

        # --- Filters ---
        # Source: opml.php lines 160-218 — <outline text="tt-rss-filters" ...>
        #         each filter serialised as JSON in a CDATA <outline filter-type="2">
        filters_outline = lxml_etree.SubElement(
            body,
            "outline",
            text="tt-rss-filters",
            **{"schema-version": str(schema_ver)},
        )
        filter_rows = session.execute(
            select(TtRssFilter2)
            .where(TtRssFilter2.owner_uid == user_id)
            .order_by(TtRssFilter2.id)
        ).scalars().all()

        for flt in filter_rows:
            # Source: opml.php lines 167-169 — sql_bool_to_bool conversions
            flt_dict: dict = {
                "enabled": flt.enabled,
                "match_any_rule": flt.match_any_rule,
                "inverse": flt.inverse,
                "title": flt.title,
                "rules": [],
                "actions": [],
            }

            # Source: opml.php lines 175-199 — build rules list
            rule_rows = session.execute(
                select(TtRssFilter2Rule)
                .where(TtRssFilter2Rule.filter_id == flt.id)
            ).scalars().all()
            for rule in rule_rows:
                # Source: opml.php lines 184-191 — resolve feed/cat title by ID
                feed_title = ""
                if rule.cat_filter and rule.cat_id is not None:
                    feed_title = getFeedTitle(session, rule.cat_id, cat=True)
                elif not rule.cat_filter and rule.feed_id is not None:
                    feed_title = getFeedTitle(session, rule.feed_id, cat=False)

                flt_dict["rules"].append({
                    "reg_exp": rule.reg_exp,
                    "filter_type": rule.filter_type,
                    "cat_filter": rule.cat_filter,
                    "inverse": rule.inverse,
                    "feed": feed_title,
                })

            # Source: opml.php lines 201-208 — build actions list
            action_rows = session.execute(
                select(TtRssFilter2Action)
                .where(TtRssFilter2Action.filter_id == flt.id)
            ).scalars().all()
            for action in action_rows:
                flt_dict["actions"].append({
                    "action_id": action.action_id,
                    "action_param": action.action_param,
                })

            # Source: opml.php lines 210-215 — <outline filter-type="2"><![CDATA[json]]></outline>
            filter_node = lxml_etree.SubElement(
                filters_outline,
                "outline",
                **{"filter-type": "2"},
            )
            filter_node.text = json.dumps(flt_dict)

    # Source: opml.php lines 225-248 — DOMDocument::loadXML, formatOutput, remove empty categories
    # In Python we remove <outline> folder elements that have no children of their own.
    _remove_empty_folders(body)

    # Serialise with pretty printing.
    # Source: opml.php line 240 — $doc->saveXML()
    return lxml_etree.tostring(
        root,
        xml_declaration=True,
        encoding="utf-8",
        pretty_print=True,
    ).decode("utf-8")


def _remove_empty_folders(body: lxml_etree._Element) -> None:
    """Remove ``<outline>`` folder nodes that contain no child outline elements.

    Source: ttrss/classes/opml.php:Opml::opml_export (lines 232-238)
    PHP: DOMXpath query on //outline[@title] + removeChild if no child <outline>.
    Python: iterative pruning; repeated until stable (handles deeply nested empty trees).
    Note: PHP filters on ``@title`` attribute (not ``@text``); that appears to be a
    legacy attribute — the export writes ``text`` not ``title``.  We prune outlines
    that have a ``text`` attribute but no child ``<outline>`` children, matching the
    intent of the PHP code.
    """
    changed = True
    while changed:
        changed = False
        # Walk a copy of the list since we mutate during iteration.
        for elem in list(body.iter("outline")):
            if elem is body:
                continue
            has_text = elem.get("text") is not None
            has_children = any(child.tag == "outline" for child in elem)
            if has_text and not has_children and elem.get("type") not in ("rss", "label", "prefs"):
                parent = elem.getparent()
                if parent is not None:
                    parent.remove(elem)
                    changed = True


# ---------------------------------------------------------------------------
# Public export entry point
# ---------------------------------------------------------------------------

# Source: ttrss/classes/opml.php:Opml::export (lines 10-18)
def export(
    session: Session,
    user_id: int,
    hide_private_feeds: bool = False,
    include_settings: bool = True,
) -> str:
    """Export all feeds/categories/labels/filters/prefs for *user_id* as OPML XML.

    Source: ttrss/classes/opml.php:Opml::export (lines 10-18)
    Adapted: PHP reads ``$_REQUEST`` and sends HTTP headers; Python is a pure
             function — caller (blueprint) handles HTTP concerns.

    Returns the OPML document as a UTF-8 XML string.
    """
    return opml_export_full(
        session,
        user_id,
        hide_private_feeds=hide_private_feeds,
        include_settings=include_settings,
    )


# ---------------------------------------------------------------------------
# Import — internal helpers
# ---------------------------------------------------------------------------

# Source: ttrss/classes/opml.php:Opml::opml_import_feed (lines 254-285)
def opml_import_feed(
    session: Session,
    user_id: int,
    item: dict,
    cat_id: Optional[int],
) -> bool:
    """Import a single RSS feed entry parsed from OPML.

    Source: ttrss/classes/opml.php:Opml::opml_import_feed (lines 254-285)
    PHP: uses $node->attributes; Python receives a pre-parsed *item* dict from
         ``opml_import_category``.

    *item* must contain at minimum ``xmlUrl`` and one of ``text``/``title``.
    Returns True if the feed was newly inserted, False if it was a duplicate
    or had missing required fields.
    """
    # Source: opml.php lines 257-263 — extract and validate attributes
    feed_title = (item.get("text") or item.get("title") or "")[:250].strip()
    feed_url = (item.get("xmlUrl") or item.get("xmlURL") or "").strip()
    site_url = (item.get("htmlUrl") or "")[:250].strip()

    if not (feed_url and feed_title):
        logger.debug(
            "opml_import_feed: skipping entry with missing url=%r title=%r",
            feed_url,
            feed_title,
        )
        return False

    # Source: opml.php lines 266-269 — check for existing subscription
    existing = session.execute(
        select(TtRssFeed.id)
        .where(TtRssFeed.feed_url == feed_url)
        .where(TtRssFeed.owner_uid == user_id)
    ).scalar_one_or_none()

    if existing is not None:
        logger.info("opml_import_feed: duplicate feed %r for uid=%d", feed_title, user_id)
        return False

    # Source: opml.php lines 274-280 — INSERT INTO ttrss_feeds
    new_feed = TtRssFeed(
        title=feed_title,
        feed_url=feed_url,
        owner_uid=user_id,
        cat_id=cat_id,
        site_url=site_url,
        order_id=0,
        update_method=0,
    )
    session.add(new_feed)
    logger.info("opml_import_feed: adding feed %r for uid=%d", feed_title, user_id)
    return True


# Source: ttrss/classes/opml.php:Opml::opml_import_label (lines 287-302)
def opml_import_label(
    session: Session,
    user_id: int,
    item: dict,
) -> None:
    """Import a label entry from parsed OPML.

    Source: ttrss/classes/opml.php:Opml::opml_import_label (lines 287-302)
    PHP: reads label-name, label-fg-color, label-bg-color attributes from DOMNode.
    Python: receives pre-parsed *item* dict.
    """
    label_name = (item.get("label-name") or "").strip()
    if not label_name:
        return

    fg_color = (item.get("label-fg-color") or "").strip()
    bg_color = (item.get("label-bg-color") or "").strip()

    # Source: opml.php lines 295-299 — check duplicate, then label_create
    if label_find_id(session, label_name, user_id):
        logger.info("opml_import_label: duplicate label %r for uid=%d", label_name, user_id)
        return

    label_create(session, label_name, fg_color, bg_color, user_id)
    logger.info("opml_import_label: added label %r for uid=%d", label_name, user_id)


# Source: ttrss/classes/opml.php:Opml::opml_import_preference (lines 304-316)
def opml_import_preference(
    session: Session,
    user_id: int,
    item: dict,
) -> None:
    """Import a user preference key/value from parsed OPML.

    Source: ttrss/classes/opml.php:Opml::opml_import_preference (lines 304-316)
    PHP: reads pref-name and value attributes, calls set_pref().
    Python: calls set_user_pref with explicit owner_uid.
    """
    pref_name = (item.get("pref-name") or "").strip()
    if not pref_name:
        return

    pref_value = (item.get("value") or "")
    logger.info(
        "opml_import_preference: setting %r=%r for uid=%d",
        pref_name,
        pref_value,
        user_id,
    )
    # Source: opml.php line 314 — set_pref($pref_name, $pref_value)
    set_user_pref(user_id, pref_name, pref_value)


# Source: ttrss/classes/opml.php:Opml::opml_import_filter (lines 318-386)
def opml_import_filter(
    session: Session,
    user_id: int,
    item: dict,
    node_text: str,
) -> None:
    """Import a filter from parsed OPML.

    Source: ttrss/classes/opml.php:Opml::opml_import_filter (lines 318-386)
    PHP: reads filter-type attribute and JSON from CDATA node text.
    Python: *item* carries the element attributes; *node_text* is the element's
            text content (the JSON payload).

    Only filter-type "2" is supported (matches PHP).
    """
    filter_type_attr = (item.get("filter-type") or "").strip()
    if filter_type_attr != "2":
        logger.debug(
            "opml_import_filter: unsupported filter-type %r — skipping", filter_type_attr
        )
        return

    # Source: opml.php line 325 — $filter = json_decode($node->nodeValue, true)
    try:
        flt = json.loads(node_text or "")
    except (json.JSONDecodeError, ValueError):
        logger.warning("opml_import_filter: failed to parse filter JSON for uid=%d", user_id)
        return

    if not flt:
        return

    # Source: opml.php lines 327-330 — extract top-level fields
    match_any_rule: bool = bool(flt.get("match_any_rule", False))
    enabled: bool = bool(flt.get("enabled", True))
    inverse: bool = bool(flt.get("inverse", False))
    title: str = str(flt.get("title", ""))[:250]

    # Source: opml.php line 334 — INSERT INTO ttrss_filters2
    new_filter = TtRssFilter2(
        owner_uid=user_id,
        match_any_rule=match_any_rule,
        enabled=enabled,
        inverse=inverse,
        title=title,
    )
    session.add(new_filter)
    session.flush()  # Needed to obtain new_filter.id (mirrors PHP's SELECT MAX(id))

    filter_id = new_filter.id
    if not filter_id:
        logger.warning("opml_import_filter: failed to obtain filter_id for uid=%d", user_id)
        return

    logger.info("opml_import_filter: adding filter %r for uid=%d", title, user_id)

    # Source: opml.php lines 345-370 — insert rules
    for rule in flt.get("rules", []):
        feed_id: Optional[int] = None
        cat_id: Optional[int] = None
        cat_filter: bool = bool(rule.get("cat_filter", False))
        feed_title_str: str = str(rule.get("feed", ""))

        if feed_title_str:
            if not cat_filter:
                # Source: opml.php lines 350-353 — look up feed by title
                feed_id = session.execute(
                    select(TtRssFeed.id)
                    .where(TtRssFeed.title == feed_title_str)
                    .where(TtRssFeed.owner_uid == user_id)
                ).scalar_one_or_none()
            else:
                # Source: opml.php lines 355-359 — look up category by title
                cat_id = session.execute(
                    select(TtRssFeedCategory.id)
                    .where(TtRssFeedCategory.title == feed_title_str)
                    .where(TtRssFeedCategory.owner_uid == user_id)
                ).scalar_one_or_none()

        # Source: opml.php lines 363-370 — INSERT INTO ttrss_filters2_rules
        session.add(
            TtRssFilter2Rule(
                filter_id=filter_id,
                reg_exp=str(rule.get("reg_exp", ""))[:250],
                filter_type=int(rule.get("filter_type", 1)),
                cat_filter=cat_filter,
                inverse=bool(rule.get("inverse", False)),
                feed_id=feed_id,
                cat_id=cat_id,
            )
        )

    # Source: opml.php lines 372-379 — insert actions
    for action in flt.get("actions", []):
        session.add(
            TtRssFilter2Action(
                filter_id=filter_id,
                action_id=int(action.get("action_id", 1)),
                action_param=str(action.get("action_param", ""))[:250],
            )
        )


# Source: ttrss/classes/opml.php:Opml::opml_import_category (lines 388-458)
def opml_import_category(
    session: Session,
    user_id: int,
    item: Optional[dict],
    parent_cat_id: Optional[int],
    node_children: Optional[list] = None,
    _cat_title_override: Optional[str] = None,
) -> None:
    """Recursively import a category node and all its children from parsed OPML.

    Source: ttrss/classes/opml.php:Opml::opml_import_category (lines 388-458)
    PHP: takes a DOMDocument + DOMNode (or None for top-level) and recurses.
    Python: takes a pre-parsed attribute dict *item* (or None for top-level)
            and a list of child dicts *node_children*.

    *node_children* is a list of tuples ``(attrib_dict, text_content, child_list)``
    representing the direct ``<outline>`` children of this node.
    """
    # Source: opml.php lines 391 — $default_cat_id = get_feed_category('Imported feeds', false)
    default_cat_id = get_feed_category(session, "Imported feeds", user_id)

    # Resolve category title and ID for this level.
    # Source: opml.php lines 393-409
    cat_title: str = ""
    cat_id: Optional[int] = None

    if item is not None:
        cat_title = (
            _cat_title_override
            or (item.get("text") or item.get("title") or "")[:250].strip()
        )

        # Source: opml.php lines 399 — skip special tt-rss meta-categories from getting a DB row
        if cat_title not in ("tt-rss-filters", "tt-rss-labels", "tt-rss-prefs"):
            cat_id = get_feed_category(session, cat_title, user_id, parent_cat_id)
            if cat_id is None:
                add_feed_category(session, cat_title, user_id, parent_cat_id)
                session.flush()
                cat_id = get_feed_category(session, cat_title, user_id, parent_cat_id)
        else:
            cat_id = 0  # sentinel: route items to special importers

    # Source: opml.php line 421 — log current category
    logger.debug(
        "opml_import_category: processing %r cat_id=%s parent=%s uid=%d",
        cat_title or "Uncategorized",
        cat_id,
        parent_cat_id,
        user_id,
    )

    if node_children is None:
        return

    for child_attribs, child_text, grandchildren in node_children:
        # Source: opml.php lines 423-424 — check tagName == "outline" and hasAttributes
        node_cat_title = (child_attribs.get("text") or child_attribs.get("title") or "").strip()
        node_feed_url = (child_attribs.get("xmlUrl") or child_attribs.get("xmlURL") or "").strip()

        if node_cat_title and not node_feed_url:
            # This child is a sub-category — recurse.
            # Source: opml.php line 434 — $this->opml_import_category(...)
            opml_import_category(
                session,
                user_id,
                item=child_attribs,
                parent_cat_id=cat_id if cat_id else None,
                node_children=grandchildren,
            )
        else:
            # This child is a feed or a special item.
            # Source: opml.php lines 437-455 — dispatch on $cat_title
            if not cat_id:
                dst_cat_id = default_cat_id
            else:
                dst_cat_id = cat_id

            if cat_title == "tt-rss-prefs":
                opml_import_preference(session, user_id, child_attribs)
            elif cat_title == "tt-rss-labels":
                opml_import_label(session, user_id, child_attribs)
            elif cat_title == "tt-rss-filters":
                opml_import_filter(session, user_id, child_attribs, child_text or "")
            else:
                opml_import_feed(session, user_id, child_attribs, dst_cat_id)


# ---------------------------------------------------------------------------
# XML parsing helper
# ---------------------------------------------------------------------------

def _parse_opml_tree(
    root: ET.Element,
) -> list[tuple[dict, Optional[str], list]]:
    """Recursively convert an ElementTree <body> element into a nested list.

    Returns a list of ``(attrib_dict, text, children)`` tuples where
    *children* is itself a list of the same structure.

    New: no PHP equivalent — Python replaces DOMDocument + DOMXPath traversal
    with stdlib ElementTree.
    """
    result: list[tuple[dict, Optional[str], list]] = []
    for child in root:
        if child.tag.lower() == "outline":
            children = _parse_opml_tree(child)
            result.append((dict(child.attrib), child.text, children))
    return result


# ---------------------------------------------------------------------------
# Public import entry point
# ---------------------------------------------------------------------------

# Source: ttrss/classes/opml.php:Opml::opml_import (lines 461-506)
def import_opml(
    session: Session,
    user_id: int,
    xml_content: str,
) -> dict:
    """Import feeds from an OPML XML string for *user_id*.

    Source: ttrss/classes/opml.php:Opml::import (lines 20-506)
    Source: ttrss/classes/opml.php:Opml::opml_import (lines 461-506)
    PHP: reads file upload from $_FILES, calls opml_import_category(doc, false, ...).
    Adapted: accepts pre-read XML string (caller handles file/upload I/O);
             returns structured result dict instead of printing HTML.

    Returns ``{"imported": N, "errors": [...]}``.
    """
    if not user_id:
        return {"imported": 0, "errors": ["No user_id provided."]}

    # Source: opml.php lines 492-495 — DOMDocument::load + parse
    try:
        # Use defusedxml-safe stdlib ET (Python's expat enforces entity limits).
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        logger.warning("import_opml: XML parse error for uid=%d: %s", user_id, exc)
        return {"imported": 0, "errors": [f"XML parse error: {exc}"]}

    # Locate <body> element (case-insensitive for robustness).
    body_elem: Optional[ET.Element] = None
    for child in root:
        if child.tag.lower() == "body":
            body_elem = child
            break

    if body_elem is None:
        # Try root itself (some minimal OPML omits the outer <opml> wrapper).
        body_elem = root

    # Source: opml.php lines 501-504 — call opml_import_category(doc, false, owner_uid, false)
    # Ensure the "Imported feeds" catch-all category exists.
    # Source: opml.php line 36 — add_feed_category("Imported feeds")
    if get_feed_category(session, "Imported feeds", user_id) is None:
        add_feed_category(session, "Imported feeds", user_id)
        session.flush()

    top_level_children = _parse_opml_tree(body_elem)

    errors: list[str] = []
    imported = 0

    # Count feeds before and after to derive "imported" count.
    before_count = session.execute(
        select(TtRssFeed.id).where(TtRssFeed.owner_uid == user_id)
    ).scalars().all()

    try:
        opml_import_category(
            session,
            user_id,
            item=None,          # top-level: no wrapper category
            parent_cat_id=None,
            node_children=top_level_children,
        )
        session.flush()
    except Exception as exc:
        logger.exception("import_opml: error during category import for uid=%d", user_id)
        errors.append(str(exc))

    after_count = session.execute(
        select(TtRssFeed.id).where(TtRssFeed.owner_uid == user_id)
    ).scalars().all()

    imported = len(after_count) - len(before_count)

    return {"imported": imported, "errors": errors}
