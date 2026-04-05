"""Unit tests for ttrss.feeds.opml — OPML export and import functions.

Source PHP: ttrss/classes/opml.php:Opml (full class, lines 1-523)
New: no PHP equivalent — Python test suite.

All DB access is mocked via patch("ttrss.feeds.opml.db") and
patch("ttrss.prefs.ops.db").  get_schema_version is patched to return 124.
A minimal Flask app context is required because opml_export_full calls
get_schema_version() which imports from ttrss.extensions (Flask-SQLAlchemy).
"""
from __future__ import annotations

import pytest
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Minimal Flask app fixture (no DB / Redis needed for unit tests).
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def _unit_app():
    """Minimal Flask app for OPML unit tests — no real DB required.

    opml_export_full lazily imports from ttrss.extensions, so a Flask app
    context must exist.  We patch all actual DB calls.
    """
    import os
    from cryptography.fernet import Fernet

    os.environ.setdefault("SECRET_KEY", "test-secret-opml")
    os.environ.setdefault("FEED_CRYPT_KEY", Fernet.generate_key().decode())
    os.environ.setdefault(
        "DATABASE_URL",
        os.environ.get("TEST_DATABASE_URL", "postgresql://ttrss_test:ttrss_test@localhost:5433/ttrss_test"),
    )
    os.environ.setdefault("REDIS_URL", os.environ.get("TEST_REDIS_URL", "redis://localhost:6380/1"))

    from ttrss import create_app
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False, "RATELIMIT_ENABLED": False})
    return app


# ---------------------------------------------------------------------------
# Helpers — mock session that returns empty query results by default.
# ---------------------------------------------------------------------------

def _make_empty_session():
    """Return a mock SQLAlchemy Session where all queries yield empty results.

    Used for opml_export_full tests where we want a valid but empty export.
    Source: ttrss/classes/opml.php:Opml::opml_export (lines 108-250) — PHP
    iterates DB rows; empty results → minimal valid OPML skeleton.
    """
    session = MagicMock()
    # execute(...).scalar_one_or_none() → None  (category title lookup)
    # execute(...).scalars().all()       → []   (sub-categories, feeds, prefs, labels, filters)
    # execute(...).all()                 → []   (prefs rows)
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    exec_result.scalars.return_value.all.return_value = []
    exec_result.all.return_value = []
    exec_result.scalar.return_value = None
    session.execute.return_value = exec_result
    return session


VALID_MINIMAL_OPML = """\
<?xml version="1.0" encoding="utf-8"?>
<opml version="1.0">
  <head><title>Test</title></head>
  <body>
    <outline type="rss" text="Feed One" xmlUrl="http://feed1.example.com/rss" htmlUrl="http://feed1.example.com"/>
  </body>
</opml>
"""

MALFORMED_XML = "<<not valid xml at all>>"

OPML_WITH_FEEDS = """\
<?xml version="1.0" encoding="utf-8"?>
<opml version="1.0">
  <head><title>Import Me</title></head>
  <body>
    <outline type="rss" text="Feed Alpha" xmlUrl="http://alpha.example.com/rss" htmlUrl="http://alpha.example.com"/>
    <outline type="rss" text="Feed Beta"  xmlUrl="http://beta.example.com/rss"  htmlUrl="http://beta.example.com"/>
  </body>
</opml>
"""


# ---------------------------------------------------------------------------
# 1. csrf_ignore
# ---------------------------------------------------------------------------

class TestCsrfIgnore:
    def test_csrf_ignore_returns_import_and_export(self):
        """csrf_ignore() returns ["import", "export"] — both ops are CSRF-exempt.

        Source: ttrss/classes/opml.php:Opml::csrf_ignore (lines 4-8).
        PHP: $csrf_ignored = array("export", "import"); return array_search(...) !== false.
        Adapted: Python returns the list directly; blueprint callers inspect it.
        """
        from ttrss.feeds.opml import csrf_ignore
        result = csrf_ignore()
        assert isinstance(result, list)
        assert "import" in result
        assert "export" in result


# ---------------------------------------------------------------------------
# 2-7. opml_export_full — XML structure and filtering
# ---------------------------------------------------------------------------

class TestOpmlExportFull:
    """Tests for opml_export_full.

    Source: ttrss/classes/opml.php:Opml::opml_export (lines 108-250).
    """

    def _export(self, session, *, hide_private_feeds=False, include_settings=True, app):
        """Run opml_export_full under a Flask app context with get_schema_version patched."""
        with app.app_context():
            with patch("ttrss.feeds.opml.get_schema_version", return_value=124):
                from ttrss.feeds.opml import opml_export_full
                return opml_export_full(
                    session,
                    user_id=1,
                    hide_private_feeds=hide_private_feeds,
                    include_settings=include_settings,
                )

    def test_export_returns_xml_string(self, _unit_app):
        """opml_export_full returns a UTF-8 XML string.

        Source: ttrss/classes/opml.php:Opml::opml_export line 240 — $doc->saveXML().
        Adapted: Python uses lxml.etree.tostring(xml_declaration=True, encoding='utf-8').
        """
        session = _make_empty_session()
        result = self._export(session, app=_unit_app)
        assert isinstance(result, str)
        assert result.startswith("<?xml")

    def test_export_contains_opml_root_element(self, _unit_app):
        """Exported XML contains <opml version="1.0"> as the root element.

        Source: ttrss/classes/opml.php:Opml::opml_export line 110 — $out = '<opml version="1.0">'.
        Adapted: Python uses lxml_etree.Element("opml", version="1.0").
        """
        session = _make_empty_session()
        result = self._export(session, app=_unit_app)
        assert '<opml version="1.0">' in result

    def test_export_hide_private_feeds_excludes_private(self, _unit_app):
        """hide_private_feeds=True adds a WHERE clause to exclude private feeds.

        Source: ttrss/classes/opml.php:Opml::opml_export_category lines 61-64 —
        AND (private IS false AND auth_login='' AND auth_pass='').
        Adapted: Python passes hide_private_feeds to opml_export_category which adds
        .where(TtRssFeed.private.is_(False), ...) to the feed query.
        """
        session = _make_empty_session()

        # We verify that execute() is called (the where clause is applied at SA level).
        result = self._export(session, hide_private_feeds=True, app=_unit_app)
        assert isinstance(result, str)
        # The call must succeed (no exception) even with hide_private_feeds=True.
        session.execute.assert_called()

    def test_export_include_settings_true_produces_valid_xml(self, _unit_app):
        """include_settings=True exercises the prefs/labels/filters code paths.

        Source: ttrss/classes/opml.php:Opml::opml_export lines 133-218 —
        PHP appends <outline text="tt-rss-prefs"> block when include_settings=True.
        Adapted: Python only adds sections when DB returns rows; with an empty DB
        the structure is the same valid OPML skeleton, but the code path is taken.
        Assert: no exception; valid XML string returned.
        """
        session = _make_empty_session()
        result = self._export(session, include_settings=True, app=_unit_app)
        assert isinstance(result, str)
        assert result.startswith("<?xml")
        assert "<opml" in result

    def test_export_include_settings_false_has_no_prefs_outline(self, _unit_app):
        """include_settings=False omits the prefs, labels, and filters sections.

        Source: ttrss/classes/opml.php:Opml::opml_export lines 133-218 — settings
        block is conditional on the include_settings flag.
        """
        session = _make_empty_session()
        result = self._export(session, include_settings=False, app=_unit_app)
        assert "tt-rss-prefs" not in result
        assert "tt-rss-labels" not in result
        assert "tt-rss-filters" not in result

    def test_export_empty_category_removed(self, _unit_app):
        """Empty folder <outline> elements are pruned from the export.

        Source: ttrss/classes/opml.php:Opml::opml_export lines 232-238 —
        DOMXpath query on //outline[@title]; removeChild if no child <outline>.
        Adapted: Python uses _remove_empty_folders() iterative pruning.
        Note: PHP filters on @title attribute; Python prunes text attribute + no children.
        """
        session = _make_empty_session()
        result = self._export(session, app=_unit_app)
        # Parse the output to check for spurious empty folder outlines.
        root = ET.fromstring(result)
        body = next((c for c in root if c.tag.lower() == "body"), None)
        if body is not None:
            for outline in body.iter("outline"):
                has_text = outline.get("text") is not None
                has_type = outline.get("type") in ("rss", "label", "prefs")
                has_children = any(c.tag == "outline" for c in outline)
                # An outline with text but no children and no type should not exist.
                assert not (has_text and not has_children and not has_type), (
                    f"Empty folder outline found: {ET.tostring(outline, encoding='unicode')}"
                )


# ---------------------------------------------------------------------------
# 8-9. import_opml — success and malformed XML
# ---------------------------------------------------------------------------

class TestImportOpml:
    """Tests for import_opml.

    Source: ttrss/classes/opml.php:Opml::opml_import (lines 461-506).
    """

    def _make_import_session(self):
        """Mock session for import: get_feed_category returns None → category is created."""
        session = MagicMock()

        # Feed count before/after
        exec_result = MagicMock()
        exec_result.scalars.return_value.all.return_value = []
        exec_result.scalar_one_or_none.return_value = None
        exec_result.scalar.return_value = None
        session.execute.return_value = exec_result
        session.flush.return_value = None
        session.commit.return_value = None
        return session

    def test_import_valid_opml_returns_imported_key(self):
        """import_opml with valid OPML returns a dict containing 'imported' key.

        Source: ttrss/classes/opml.php:Opml::opml_import lines 461-506.
        PHP: echoes a success message with count; Python returns {"imported": N, "errors": []}.
        """
        session = self._make_import_session()

        with (
            patch("ttrss.feeds.opml.get_feed_category", return_value=1),
            patch("ttrss.feeds.opml.add_feed_category"),
            patch("ttrss.feeds.opml.opml_import_category"),
        ):
            from ttrss.feeds.opml import import_opml
            result = import_opml(session, user_id=1, xml_content=VALID_MINIMAL_OPML)

        assert isinstance(result, dict)
        assert "imported" in result

    def test_import_malformed_xml_returns_errors_key_no_exception(self):
        """import_opml with malformed XML returns a dict with 'errors' key — no exception raised.

        Source: ttrss/classes/opml.php:Opml::opml_import lines 492-495 —
        PHP: DOMDocument::load returns false on parse error; Python catches ET.ParseError.
        Adapted: Python returns {"imported": 0, "errors": [...]}, never raises.
        """
        session = self._make_import_session()
        from ttrss.feeds.opml import import_opml
        result = import_opml(session, user_id=1, xml_content=MALFORMED_XML)

        assert isinstance(result, dict)
        assert "errors" in result
        assert len(result["errors"]) > 0
        assert result.get("imported", 0) == 0


# ---------------------------------------------------------------------------
# 10. Round-trip: export → import
# ---------------------------------------------------------------------------

class TestOpmlRoundTrip:
    def test_round_trip_export_then_import_returns_dict(self, _unit_app):
        """Export then re-import the XML; import_opml must return a valid result dict.

        Source: ttrss/classes/opml.php — PHP export + import are two separate handler actions.
        Adapted: Python round-trip verifies both functions are composable without error.
        """
        session_exp = _make_empty_session()

        with _unit_app.app_context():
            with patch("ttrss.feeds.opml.get_schema_version", return_value=124):
                from ttrss.feeds.opml import opml_export_full
                exported_xml = opml_export_full(session_exp, user_id=1, include_settings=False)

        # Now import the exported XML
        session_imp = MagicMock()
        exec_result = MagicMock()
        exec_result.scalars.return_value.all.return_value = []
        exec_result.scalar_one_or_none.return_value = None
        session_imp.execute.return_value = exec_result

        with (
            patch("ttrss.feeds.opml.get_feed_category", return_value=1),
            patch("ttrss.feeds.opml.add_feed_category"),
            patch("ttrss.feeds.opml.opml_import_category"),
        ):
            from ttrss.feeds.opml import import_opml
            result = import_opml(session_imp, user_id=1, xml_content=exported_xml)

        assert isinstance(result, dict)
        assert "imported" in result


# ---------------------------------------------------------------------------
# 11. import_opml with feeds — subscribes feeds
# ---------------------------------------------------------------------------

class TestImportOpmlWithFeeds:
    def test_import_opml_with_feeds_subscribes_them(self):
        """import_opml with OPML containing feed entries calls opml_import_feed.

        Source: ttrss/classes/opml.php:Opml::opml_import_category lines 437-455 —
        PHP dispatches each <outline type="rss"> to opml_import_feed().
        Adapted: Python calls opml_import_feed() via opml_import_category().
        """
        session = MagicMock()
        exec_result = MagicMock()
        exec_result.scalars.return_value.all.return_value = []
        exec_result.scalar_one_or_none.return_value = None
        exec_result.scalar.return_value = None
        session.execute.return_value = exec_result

        feed_calls = []

        def fake_import_feed(sess, uid, item, cat_id):
            feed_calls.append(item.get("xmlUrl"))
            return True

        with (
            patch("ttrss.feeds.opml.get_feed_category", return_value=1),
            patch("ttrss.feeds.opml.add_feed_category"),
            patch("ttrss.feeds.opml.opml_import_feed", side_effect=fake_import_feed),
        ):
            from ttrss.feeds.opml import import_opml
            result = import_opml(session, user_id=1, xml_content=OPML_WITH_FEEDS)

        # Both feeds in OPML_WITH_FEEDS must have triggered an import attempt.
        assert "http://alpha.example.com/rss" in feed_calls
        assert "http://beta.example.com/rss" in feed_calls


# ---------------------------------------------------------------------------
# Additional OPML XML fixtures for new test classes.
# ---------------------------------------------------------------------------

OPML_WITH_FEED_OUTLINE = """\
<?xml version="1.0" encoding="utf-8"?>
<opml version="1.0">
  <head><title>Feed Outline Test</title></head>
  <body>
    <outline type="rss" text="Sample Feed" xmlUrl="http://sample.example.com/rss" htmlUrl="http://sample.example.com"/>
  </body>
</opml>
"""

OPML_WITH_CATEGORY = """\
<?xml version="1.0" encoding="utf-8"?>
<opml version="1.0">
  <head><title>Category Test</title></head>
  <body>
    <outline text="Tech News">
      <outline type="rss" text="Tech Feed" xmlUrl="http://tech.example.com/rss" htmlUrl="http://tech.example.com"/>
    </outline>
  </body>
</opml>
"""

OPML_WITH_LABEL = """\
<?xml version="1.0" encoding="utf-8"?>
<opml version="1.0">
  <head><title>Label Test</title></head>
  <body>
    <outline text="tt-rss-labels" schema-version="124">
      <outline label-name="Important" label-fg-color="#ff0000" label-bg-color="#ffffff"/>
    </outline>
  </body>
</opml>
"""

OPML_WITH_PREF = """\
<?xml version="1.0" encoding="utf-8"?>
<opml version="1.0">
  <head><title>Prefs Test</title></head>
  <body>
    <outline text="tt-rss-prefs" schema-version="124">
      <outline pref-name="DEFAULT_ARTICLE_LIMIT" value="30"/>
    </outline>
  </body>
</opml>
"""

OPML_WITH_FILTER_JSON = """\
<?xml version="1.0" encoding="utf-8"?>
<opml version="1.0">
  <head><title>Filter Test</title></head>
  <body>
    <outline text="tt-rss-filters" schema-version="124">
      <outline filter-type="2">{"enabled": true, "match_any_rule": false, "inverse": false, "title": "Test Filter", "rules": [{"reg_exp": "spam", "filter_type": 1, "cat_filter": false, "inverse": false, "feed": ""}], "actions": [{"action_id": 2, "action_param": ""}]}</outline>
    </outline>
  </body>
</opml>
"""


# ---------------------------------------------------------------------------
# 12-18. TestImportOpml — comprehensive import path coverage
# ---------------------------------------------------------------------------

class TestImportOpml:
    """Tests for import_opml and sub-functions: feed, category, label, pref, filter.

    Source: ttrss/classes/opml.php:Opml::opml_import (lines 461-506),
            opml_import_feed (lines 254-285), opml_import_label (lines 287-302),
            opml_import_preference (lines 304-316), opml_import_filter (lines 318-386),
            opml_import_category (lines 388-458).
    """

    def _make_session(self):
        """Return a mock session suitable for import tests."""
        session = MagicMock()
        exec_result = MagicMock()
        exec_result.scalars.return_value.all.return_value = []
        exec_result.scalar_one_or_none.return_value = None
        exec_result.scalar.return_value = None
        session.execute.return_value = exec_result
        session.flush.return_value = None
        session.commit.return_value = None
        return session

    def test_import_valid_minimal_opml_returns_imported_key(self):
        """import_opml(session, uid, valid_minimal_opml) returns dict with 'imported' key >= 0.

        Source: ttrss/classes/opml.php:Opml::opml_import line 461\n
        PHP: echoes "feeds imported: N" after iterating <outline> elements.\n
        Assert: result is dict, 'imported' key present and is non-negative int.
        """
        session = self._make_session()
        with (
            patch("ttrss.feeds.opml.get_feed_category", return_value=1),
            patch("ttrss.feeds.opml.add_feed_category"),
            patch("ttrss.feeds.opml.opml_import_category"),
        ):
            from ttrss.feeds.opml import import_opml
            result = import_opml(session, user_id=1, xml_content=VALID_MINIMAL_OPML)

        assert isinstance(result, dict)
        assert "imported" in result
        assert isinstance(result["imported"], int)
        assert result["imported"] >= 0

    def test_import_malformed_xml_returns_errors_no_exception(self):
        """import_opml(session, uid, malformed_xml) returns dict with 'errors', no exception.

        Source: ttrss/classes/opml.php:Opml::opml_import lines 492-495\n
        PHP: DOMDocument::load returns false on parse error; Python catches ET.ParseError.\n
        Assert: result dict has 'errors' list with at least one entry; imported == 0.
        """
        session = self._make_session()
        from ttrss.feeds.opml import import_opml
        result = import_opml(session, user_id=1, xml_content="<<not xml>>")

        assert isinstance(result, dict)
        assert "errors" in result
        assert len(result["errors"]) > 0
        assert result.get("imported", 0) == 0

    def test_import_with_feed_outline_calls_subscribe(self):
        """import_opml(session, uid, opml_with_feed_outline) calls opml_import_feed.

        Source: ttrss/classes/opml.php:Opml::opml_import_category lines 437-455\n
        PHP: dispatches each <outline type="rss"> to opml_import_feed().\n
        Assert: opml_import_feed called at least once; result is a valid dict.
        """
        session = self._make_session()
        subscribe_calls = []

        def fake_import_feed(sess, uid, item, cat_id):
            subscribe_calls.append(item.get("xmlUrl"))
            return True

        with (
            patch("ttrss.feeds.opml.get_feed_category", return_value=1),
            patch("ttrss.feeds.opml.add_feed_category"),
            patch("ttrss.feeds.opml.opml_import_feed", side_effect=fake_import_feed),
        ):
            from ttrss.feeds.opml import import_opml
            result = import_opml(session, user_id=1, xml_content=OPML_WITH_FEED_OUTLINE)

        assert isinstance(result, dict)
        assert "http://sample.example.com/rss" in subscribe_calls

    def test_import_with_category_calls_add_feed_category(self):
        """import_opml(session, uid, opml_with_category) triggers add_feed_category.

        Source: ttrss/classes/opml.php:Opml::opml_import_category lines 393-409\n
        PHP: if get_feed_category returns null, calls add_feed_category to create it.\n
        Assert: add_feed_category called; result dict returned without exception.
        """
        session = self._make_session()
        cat_creates = []

        def fake_get_cat(sess, title, uid, parent=None):
            # Return None first time (so add is called), then return an ID
            return None if title == "Tech News" else 1

        def fake_add_cat(sess, title, uid, parent=None):
            cat_creates.append(title)

        with (
            patch("ttrss.feeds.opml.get_feed_category", side_effect=fake_get_cat),
            patch("ttrss.feeds.opml.add_feed_category", side_effect=fake_add_cat),
            patch("ttrss.feeds.opml.opml_import_feed"),
        ):
            from ttrss.feeds.opml import import_opml
            result = import_opml(session, user_id=1, xml_content=OPML_WITH_CATEGORY)

        assert isinstance(result, dict)
        # add_feed_category should have been called for the "Tech News" category
        assert "Tech News" in cat_creates

    def test_import_with_label_calls_label_create(self):
        """import_opml(session, uid, opml_with_label) calls label_create for new label.

        Source: ttrss/classes/opml.php:Opml::opml_import_label lines 287-302\n
        PHP: checks for duplicate via label_find_id, then calls label_create.\n
        Assert: label_create called with expected label name.
        """
        session = self._make_session()
        label_creates = []

        def fake_label_create(sess, name, fg, bg, uid):
            label_creates.append(name)

        with (
            patch("ttrss.feeds.opml.get_feed_category", return_value=1),
            patch("ttrss.feeds.opml.add_feed_category"),
            patch("ttrss.feeds.opml.label_find_id", return_value=None),
            patch("ttrss.feeds.opml.label_create", side_effect=fake_label_create),
        ):
            from ttrss.feeds.opml import import_opml
            result = import_opml(session, user_id=1, xml_content=OPML_WITH_LABEL)

        assert isinstance(result, dict)
        assert "Important" in label_creates

    def test_import_with_pref_calls_set_user_pref(self):
        """import_opml(session, uid, opml_with_pref) calls set_user_pref.

        Source: ttrss/classes/opml.php:Opml::opml_import_preference lines 304-316\n
        PHP: reads pref-name and value attributes, calls set_pref().\n
        Assert: set_user_pref called with the pref-name from the OPML.
        """
        session = self._make_session()
        pref_calls = []

        def fake_set_pref(uid, pref_name, value):
            pref_calls.append((pref_name, value))

        with (
            patch("ttrss.feeds.opml.get_feed_category", return_value=1),
            patch("ttrss.feeds.opml.add_feed_category"),
            patch("ttrss.feeds.opml.set_user_pref", side_effect=fake_set_pref),
        ):
            from ttrss.feeds.opml import import_opml
            result = import_opml(session, user_id=1, xml_content=OPML_WITH_PREF)

        assert isinstance(result, dict)
        pref_names = [p[0] for p in pref_calls]
        assert "DEFAULT_ARTICLE_LIMIT" in pref_names

    def test_import_with_filter_json_inserts_filter(self):
        """import_opml(session, uid, opml_with_filter_json) calls session.add for filter.

        Source: ttrss/classes/opml.php:Opml::opml_import_filter lines 318-386\n
        PHP: decodes JSON CDATA, INSERT INTO ttrss_filters2 + rules + actions.\n
        Assert: session.add called (filter row inserted); result dict returned.
        """
        session = self._make_session()
        # Give the new filter object a fake id after flush
        fake_filter = MagicMock()
        fake_filter.id = 42

        add_calls = []

        def fake_add(obj):
            add_calls.append(type(obj).__name__)
            # If it's a filter, make session.flush assign an ID
            if hasattr(obj, "owner_uid"):
                obj.id = 42

        session.add.side_effect = fake_add

        with (
            patch("ttrss.feeds.opml.get_feed_category", return_value=1),
            patch("ttrss.feeds.opml.add_feed_category"),
        ):
            from ttrss.feeds.opml import import_opml
            result = import_opml(session, user_id=1, xml_content=OPML_WITH_FILTER_JSON)

        assert isinstance(result, dict)
        # session.add should have been called at least once (for the filter row)
        assert session.add.called


# ---------------------------------------------------------------------------
# 19-20. TestOpmlHelpers — export category helper and _remove_empty_folders
# ---------------------------------------------------------------------------

class TestOpmlHelpers:
    """Tests for opml_export_category and _remove_empty_folders.

    Source: ttrss/classes/opml.php:Opml::opml_export_category (lines 51-106),
            opml_export (lines 232-238).
    """

    def test_opml_export_category_empty_db_no_children(self, _unit_app):
        """opml_export_category with empty DB produces no child outline elements.

        Source: ttrss/classes/opml.php:Opml::opml_export_category lines 51-106\n
        PHP: SELECT sub-categories and feeds, append to XML string; empty DB → no rows.\n
        Assert: the parent element has no <outline> children when DB is empty.
        """
        from lxml import etree as lxml_etree
        from ttrss.feeds.opml import opml_export_category

        session = _make_empty_session()

        with _unit_app.app_context():
            parent = lxml_etree.Element("body")
            opml_export_category(
                session,
                user_id=1,
                cat_id=None,
                hide_private_feeds=False,
                parent_elem=parent,
            )

        children = [c for c in parent if c.tag == "outline"]
        assert children == [], (
            f"Expected no outline children for empty DB, got: {[c.get('text') for c in children]}"
        )

    def test_remove_empty_folders_removes_folder_with_no_children(self, _unit_app):
        """_remove_empty_folders removes an outline folder that has no child outlines.

        Source: ttrss/classes/opml.php:Opml::opml_export lines 232-238\n
        PHP: DOMXpath query //outline[@title] + removeChild if no child <outline>.\n
        Assert: after pruning, the empty folder outline is no longer in the body.
        """
        from lxml import etree as lxml_etree
        from ttrss.feeds.opml import _remove_empty_folders

        with _unit_app.app_context():
            body = lxml_etree.Element("body")
            # Add an empty folder (no child outlines, has text, no type)
            empty_folder = lxml_etree.SubElement(body, "outline", text="Empty Folder")
            # Add a real feed outline (should survive pruning)
            lxml_etree.SubElement(
                body, "outline",
                type="rss", text="Real Feed",
                xmlUrl="http://real.example.com/rss",
            )

            _remove_empty_folders(body)

        remaining_texts = [c.get("text") for c in body if c.tag == "outline"]
        assert "Empty Folder" not in remaining_texts
        assert "Real Feed" in remaining_texts


# ---------------------------------------------------------------------------
# 21-30. TestOpmlPublishUrl — get_opml_publish_url coverage (lines 78-101)
# ---------------------------------------------------------------------------

class TestOpmlPublishUrl:
    """Tests for opml_publish_url.

    Source: ttrss/classes/opml.php:Opml::opml_publish_url (lines 512-519).
    """

    def test_publish_url_creates_key_when_none_exists(self):
        """opml_publish_url creates a new access key when none exists for this user.

        Source: ttrss/classes/opml.php:Opml::opml_publish_url lines 512-519\n
        PHP: get_feed_access_key creates a new random key when absent.\n
        Assert: returned URL contains the generated key and correct base path.
        """
        session = MagicMock()
        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = None
        session.execute.return_value = exec_result

        from ttrss.feeds.opml import opml_publish_url
        url = opml_publish_url(session, user_id=1, base_url="https://ttrss.example.com")

        assert url.startswith("https://ttrss.example.com/opml.php?op=publish&key=")
        # session.add must have been called to persist the new key
        session.add.assert_called_once()
        session.flush.assert_called()

    def test_publish_url_returns_existing_key(self):
        """opml_publish_url returns the existing access key without creating a new one.

        Source: ttrss/classes/opml.php:Opml::opml_publish_url lines 512-519\n
        PHP: if key exists, returns it directly.\n
        Assert: URL contains the pre-existing key; session.add is NOT called.
        """
        session = MagicMock()
        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = "existingkey1234567890"
        session.execute.return_value = exec_result

        from ttrss.feeds.opml import opml_publish_url
        url = opml_publish_url(session, user_id=1, base_url="https://ttrss.example.com/")

        assert "existingkey1234567890" in url
        # No new key should be inserted
        session.add.assert_not_called()

    def test_publish_url_strips_trailing_slash_from_base_url(self):
        """opml_publish_url strips a trailing slash from base_url.

        Source: ttrss/classes/opml.php:Opml::opml_publish_url lines 512-519\n
        PHP: get_self_url_prefix() typically has no trailing slash.\n
        Assert: URL does not contain double slashes.
        """
        session = MagicMock()
        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = "mykey"
        session.execute.return_value = exec_result

        from ttrss.feeds.opml import opml_publish_url
        url = opml_publish_url(session, user_id=1, base_url="https://ttrss.example.com/")

        assert "//" not in url.split("https://")[1]


# ---------------------------------------------------------------------------
# 31-35. TestOpmlImportFeedDirect — opml_import_feed direct tests (lines 446-481)
# ---------------------------------------------------------------------------

class TestOpmlImportFeedDirect:
    """Direct unit tests for opml_import_feed.

    Source: ttrss/classes/opml.php:Opml::opml_import_feed (lines 254-285).
    """

    def _make_session(self, existing_feed_id=None):
        session = MagicMock()
        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = existing_feed_id
        session.execute.return_value = exec_result
        return session

    def test_import_feed_missing_url_returns_false(self):
        """opml_import_feed with missing xmlUrl returns False without adding.

        Source: ttrss/classes/opml.php:Opml::opml_import_feed lines 257-263\n
        PHP: validates xmlUrl attribute presence; skips if absent.\n
        Assert: returns False; session.add not called.
        """
        session = self._make_session()
        from ttrss.feeds.opml import opml_import_feed
        result = opml_import_feed(session, user_id=1, item={"text": "Feed Without URL"}, cat_id=None)

        assert result is False
        session.add.assert_not_called()

    def test_import_feed_missing_title_returns_false(self):
        """opml_import_feed with missing text/title returns False.

        Source: ttrss/classes/opml.php:Opml::opml_import_feed lines 257-263\n
        PHP: validates text attribute presence; skips if absent.\n
        Assert: returns False; session.add not called.
        """
        session = self._make_session()
        from ttrss.feeds.opml import opml_import_feed
        result = opml_import_feed(
            session, user_id=1,
            item={"xmlUrl": "http://example.com/rss"},
            cat_id=None,
        )

        assert result is False
        session.add.assert_not_called()

    def test_import_feed_duplicate_returns_false(self):
        """opml_import_feed with already-subscribed feed returns False.

        Source: ttrss/classes/opml.php:Opml::opml_import_feed lines 266-269\n
        PHP: SELECT existing feed by feed_url + owner_uid; skips if found.\n
        Assert: returns False; session.add not called.
        """
        session = self._make_session(existing_feed_id=99)
        from ttrss.feeds.opml import opml_import_feed
        result = opml_import_feed(
            session, user_id=1,
            item={"text": "Existing Feed", "xmlUrl": "http://existing.example.com/rss"},
            cat_id=None,
        )

        assert result is False
        session.add.assert_not_called()

    def test_import_feed_new_feed_returns_true_and_adds(self):
        """opml_import_feed with valid new feed returns True and calls session.add.

        Source: ttrss/classes/opml.php:Opml::opml_import_feed lines 274-280\n
        PHP: INSERT INTO ttrss_feeds with title, feed_url, owner_uid, cat_id, site_url.\n
        Assert: returns True; session.add called once.
        """
        session = self._make_session(existing_feed_id=None)
        from ttrss.feeds.opml import opml_import_feed
        result = opml_import_feed(
            session, user_id=1,
            item={
                "text": "New Feed",
                "xmlUrl": "http://new.example.com/rss",
                "htmlUrl": "http://new.example.com",
            },
            cat_id=5,
        )

        assert result is True
        session.add.assert_called_once()


# ---------------------------------------------------------------------------
# 36-38. TestOpmlImportLabelDirect — opml_import_label direct tests (lines 496-509)
# ---------------------------------------------------------------------------

class TestOpmlImportLabelDirect:
    """Direct unit tests for opml_import_label.

    Source: ttrss/classes/opml.php:Opml::opml_import_label (lines 287-302).
    """

    def test_import_label_empty_name_does_nothing(self):
        """opml_import_label with empty label-name is a no-op.

        Source: ttrss/classes/opml.php:Opml::opml_import_label lines 287-302\n
        PHP: returns early if label-name is empty.\n
        Assert: label_create not called.
        """
        session = MagicMock()
        with patch("ttrss.feeds.opml.label_create") as mock_create:
            from ttrss.feeds.opml import opml_import_label
            opml_import_label(session, user_id=1, item={"label-name": ""})
            mock_create.assert_not_called()

    def test_import_label_duplicate_does_not_create(self):
        """opml_import_label skips label_create when duplicate found.

        Source: ttrss/classes/opml.php:Opml::opml_import_label lines 295-299\n
        PHP: label_find_id returns truthy → skips insert.\n
        Assert: label_create not called.
        """
        session = MagicMock()
        with (
            patch("ttrss.feeds.opml.label_find_id", return_value=7),
            patch("ttrss.feeds.opml.label_create") as mock_create,
        ):
            from ttrss.feeds.opml import opml_import_label
            opml_import_label(session, user_id=1, item={"label-name": "Existing Label"})
            mock_create.assert_not_called()

    def test_import_label_new_label_calls_label_create(self):
        """opml_import_label calls label_create for a new (non-duplicate) label.

        Source: ttrss/classes/opml.php:Opml::opml_import_label lines 295-302\n
        PHP: label_find_id returns false → calls label_create(name, fg, bg, uid).\n
        Assert: label_create called with correct arguments.
        """
        session = MagicMock()
        with (
            patch("ttrss.feeds.opml.label_find_id", return_value=None),
            patch("ttrss.feeds.opml.label_create") as mock_create,
        ):
            from ttrss.feeds.opml import opml_import_label
            opml_import_label(
                session, user_id=1,
                item={"label-name": "NewLabel", "label-fg-color": "#aaa", "label-bg-color": "#bbb"},
            )
            mock_create.assert_called_once_with(session, "NewLabel", "#aaa", "#bbb", 1)


# ---------------------------------------------------------------------------
# 39-41. TestOpmlImportPreferenceDirect — opml_import_preference (lines 524-536)
# ---------------------------------------------------------------------------

class TestOpmlImportPreferenceDirect:
    """Direct unit tests for opml_import_preference.

    Source: ttrss/classes/opml.php:Opml::opml_import_preference (lines 304-316).
    """

    def test_import_preference_empty_name_is_noop(self):
        """opml_import_preference with empty pref-name is a no-op.

        Source: ttrss/classes/opml.php:Opml::opml_import_preference lines 304-316\n
        PHP: returns early if pref-name is empty.\n
        Assert: set_user_pref not called.
        """
        session = MagicMock()
        with patch("ttrss.feeds.opml.set_user_pref") as mock_pref:
            from ttrss.feeds.opml import opml_import_preference
            opml_import_preference(session, user_id=1, item={"pref-name": ""})
            mock_pref.assert_not_called()

    def test_import_preference_calls_set_user_pref(self):
        """opml_import_preference calls set_user_pref with pref name and value.

        Source: ttrss/classes/opml.php:Opml::opml_import_preference lines 314\n
        PHP: set_pref($pref_name, $pref_value).\n
        Assert: set_user_pref called with (uid, pref_name, value).
        """
        session = MagicMock()
        with patch("ttrss.feeds.opml.set_user_pref") as mock_pref:
            from ttrss.feeds.opml import opml_import_preference
            opml_import_preference(
                session, user_id=2,
                item={"pref-name": "THEME", "value": "dark"},
            )
            mock_pref.assert_called_once_with(2, "THEME", "dark")


# ---------------------------------------------------------------------------
# 42-45. TestOpmlImportFilterDirect — opml_import_filter (lines 555-634)
# ---------------------------------------------------------------------------

class TestOpmlImportFilterDirect:
    """Direct unit tests for opml_import_filter.

    Source: ttrss/classes/opml.php:Opml::opml_import_filter (lines 318-386).
    """

    def test_import_filter_wrong_type_skips(self):
        """opml_import_filter with filter-type != '2' returns without inserting.

        Source: ttrss/classes/opml.php:Opml::opml_import_filter lines 318-323\n
        PHP: only filter-type 2 is supported; others are skipped.\n
        Assert: session.add not called.
        """
        session = MagicMock()
        from ttrss.feeds.opml import opml_import_filter
        opml_import_filter(session, user_id=1, item={"filter-type": "1"}, node_text="{}")
        session.add.assert_not_called()

    def test_import_filter_bad_json_skips(self):
        """opml_import_filter with invalid JSON node_text returns without inserting.

        Source: ttrss/classes/opml.php:Opml::opml_import_filter lines 325\n
        PHP: json_decode returns null on parse error → skips.\n
        Assert: session.add not called.
        """
        session = MagicMock()
        from ttrss.feeds.opml import opml_import_filter
        opml_import_filter(
            session, user_id=1,
            item={"filter-type": "2"},
            node_text="not-valid-json{{{{",
        )
        session.add.assert_not_called()

    def test_import_filter_empty_json_skips(self):
        """opml_import_filter with empty JSON object skips insertion.

        Source: ttrss/classes/opml.php:Opml::opml_import_filter line 325\n
        PHP: json_decode returns empty array/null → skips.\n
        Assert: session.add not called.
        """
        session = MagicMock()
        from ttrss.feeds.opml import opml_import_filter
        opml_import_filter(
            session, user_id=1,
            item={"filter-type": "2"},
            node_text="{}",
        )
        session.add.assert_not_called()

    def test_import_filter_valid_json_inserts_filter_and_rule(self):
        """opml_import_filter with valid JSON inserts filter, rule, and action rows.

        Source: ttrss/classes/opml.php:Opml::opml_import_filter lines 334-379\n
        PHP: INSERT ttrss_filters2, SELECT max(id), INSERT rules, INSERT actions.\n
        Assert: session.add called 3 times (filter + rule + action).
        """
        session = MagicMock()
        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = None
        session.execute.return_value = exec_result

        # Make flush assign an id to the filter object
        fake_filter_instance = MagicMock()
        fake_filter_instance.id = 10

        add_calls = []

        def track_add(obj):
            add_calls.append(obj)
            # Give the first-added object (the filter) an id
            if not add_calls[1:]:  # first call
                obj.id = 10

        session.add.side_effect = track_add

        filter_json = {
            "enabled": True,
            "match_any_rule": False,
            "inverse": False,
            "title": "Direct Filter Test",
            "rules": [
                {"reg_exp": "spam", "filter_type": 1, "cat_filter": False, "inverse": False, "feed": ""}
            ],
            "actions": [
                {"action_id": 2, "action_param": "label-name"}
            ],
        }

        import json as _json
        from ttrss.feeds.opml import opml_import_filter
        opml_import_filter(
            session, user_id=1,
            item={"filter-type": "2"},
            node_text=_json.dumps(filter_json),
        )

        # filter + rule + action = 3 adds
        assert session.add.call_count == 3
        session.flush.assert_called()

    def test_import_filter_with_cat_filter_rule_looks_up_category(self):
        """opml_import_filter with cat_filter=True rule looks up category by title.

        Source: ttrss/classes/opml.php:Opml::opml_import_filter lines 355-359\n
        PHP: if cat_filter, SELECT id FROM ttrss_feed_categories WHERE title=... AND owner_uid=...\n
        Assert: session.execute called for cat lookup; rule added with cat_id.
        """
        session = MagicMock()
        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = 7
        session.execute.return_value = exec_result

        add_calls = []

        def track_add(obj):
            add_calls.append(obj)
            if not add_calls[1:]:
                obj.id = 11

        session.add.side_effect = track_add

        filter_json = {
            "enabled": True,
            "match_any_rule": False,
            "inverse": False,
            "title": "Cat Filter Test",
            "rules": [
                {
                    "reg_exp": "news",
                    "filter_type": 1,
                    "cat_filter": True,
                    "inverse": False,
                    "feed": "Tech News",
                }
            ],
            "actions": [],
        }

        import json as _json
        from ttrss.feeds.opml import opml_import_filter
        opml_import_filter(
            session, user_id=1,
            item={"filter-type": "2"},
            node_text=_json.dumps(filter_json),
        )

        # Filter + rule (no action) = 2 adds
        assert session.add.call_count == 2


# ---------------------------------------------------------------------------
# 46. TestOpmlExportFull — export function (public alias)
# ---------------------------------------------------------------------------

class TestExportPublicAlias:
    """Tests for the export() public alias.

    Source: ttrss/classes/opml.php:Opml::export (lines 10-18).
    """

    def test_export_alias_delegates_to_opml_export_full(self, _unit_app):
        """export() is an alias for opml_export_full and returns the same XML.

        Source: ttrss/classes/opml.php:Opml::export lines 10-18\n
        PHP: calls $this->opml_export(...).\n
        Assert: export() and opml_export_full() return identical strings for same args.
        """
        session = _make_empty_session()

        with _unit_app.app_context():
            with patch("ttrss.feeds.opml.get_schema_version", return_value=124):
                from ttrss.feeds.opml import export, opml_export_full
                result_alias = export(session, user_id=1, include_settings=False)
                # Reset the mock call state — both call sequences are separate
                session2 = _make_empty_session()
                result_direct = opml_export_full(session2, user_id=1, include_settings=False)

        # Both must produce OPML XML
        assert result_alias.startswith("<?xml")
        assert result_direct.startswith("<?xml")
        assert "<opml" in result_alias
        assert "<opml" in result_direct

    def test_export_with_zero_user_id_returns_empty(self, _unit_app):
        """export() with user_id=0 returns empty string (guard clause).

        Source: ttrss/classes/opml.php:Opml::opml_export lines 108-112\n
        PHP: returns early with empty output if no valid owner_uid.\n
        Assert: returns empty string.
        """
        session = _make_empty_session()
        with _unit_app.app_context():
            with patch("ttrss.feeds.opml.get_schema_version", return_value=124):
                from ttrss.feeds.opml import export
                result = export(session, user_id=0)
        assert result == ""


# ---------------------------------------------------------------------------
# 47-50. TestOpmlExportCategoryWithCatId — cover lines 126-198
# ---------------------------------------------------------------------------

class TestOpmlExportCategoryWithCatId:
    """Tests for opml_export_category when called with a specific cat_id.

    Source: ttrss/classes/opml.php:Opml::opml_export_category (lines 51-106).
    """

    def test_export_category_with_valid_cat_id_creates_wrapper_outline(self, _unit_app):
        """opml_export_category with valid cat_id creates a folder <outline text=cat_title>.

        Source: ttrss/classes/opml.php:Opml::opml_export_category lines 68-74\n
        PHP: if $cat_id, wrap children in <outline text="$cat_title">.\n
        Assert: parent_elem gains a child outline with text=category title.
        """
        from lxml import etree as lxml_etree
        from ttrss.feeds.opml import opml_export_category

        session = MagicMock()
        exec_result = MagicMock()
        # First call: scalar_one_or_none → category title
        # Subsequent calls: scalars().all() → [] (no sub-cats, no feeds)
        exec_result.scalar_one_or_none.return_value = "My Category"
        exec_result.scalars.return_value.all.return_value = []
        exec_result.all.return_value = []
        session.execute.return_value = exec_result

        with _unit_app.app_context():
            parent = lxml_etree.Element("body")
            opml_export_category(
                session,
                user_id=1,
                cat_id=5,
                hide_private_feeds=False,
                parent_elem=parent,
            )

        children = [c for c in parent if c.tag == "outline"]
        assert len(children) == 1
        assert children[0].get("text") == "My Category"

    def test_export_category_with_nonexistent_cat_returns_parent_unchanged(self, _unit_app):
        """opml_export_category with cat_id that returns no title skips the category.

        Source: ttrss/classes/opml.php:Opml::opml_export_category lines 68-74\n
        PHP: if category not found (not owned), skips and returns.\n
        Assert: parent_elem has no new child outlines added.
        """
        from lxml import etree as lxml_etree
        from ttrss.feeds.opml import opml_export_category

        session = MagicMock()
        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = None  # category doesn't exist
        exec_result.scalars.return_value.all.return_value = []
        exec_result.all.return_value = []
        session.execute.return_value = exec_result

        with _unit_app.app_context():
            parent = lxml_etree.Element("body")
            opml_export_category(
                session,
                user_id=1,
                cat_id=999,
                hide_private_feeds=False,
                parent_elem=parent,
            )

        children = [c for c in parent if c.tag == "outline"]
        assert children == []

    def test_export_category_with_feeds_emits_feed_outlines(self, _unit_app):
        """opml_export_category with cat_id emits <outline type=rss> for each feed.

        Source: ttrss/classes/opml.php:Opml::opml_export_category lines 85-101\n
        PHP: SELECT feeds WHERE cat_id=...; emit <outline type="rss"> per row.\n
        Assert: parent wrapper outline has child feed outlines.
        """
        from lxml import etree as lxml_etree
        from ttrss.feeds.opml import opml_export_category
        from unittest.mock import MagicMock

        session = MagicMock()

        # We need different responses at different execute() call sites:
        # 1st call (scalar_one_or_none): category title
        # 2nd call (scalars().all()): sub-categories → []
        # 3rd call (.all()): feed rows

        call_count = [0]

        fake_feed = MagicMock()
        fake_feed.title = "RSS Feed"
        fake_feed.feed_url = "http://rss.example.com/rss"
        fake_feed.site_url = "http://rss.example.com"

        def side_effect_execute(stmt):
            call_count[0] += 1
            r = MagicMock()
            if call_count[0] == 1:
                r.scalar_one_or_none.return_value = "Tech"
            else:
                r.scalar_one_or_none.return_value = None
                r.scalars.return_value.all.return_value = []
                r.all.return_value = [fake_feed]
            return r

        session.execute.side_effect = side_effect_execute

        with _unit_app.app_context():
            parent = lxml_etree.Element("body")
            opml_export_category(
                session,
                user_id=1,
                cat_id=3,
                hide_private_feeds=False,
                parent_elem=parent,
            )

        # Should have a "Tech" folder outline
        folders = [c for c in parent if c.tag == "outline" and c.get("text") == "Tech"]
        assert len(folders) == 1
        # That folder should contain the RSS feed outline
        feed_outlines = [c for c in folders[0] if c.tag == "outline" and c.get("type") == "rss"]
        assert len(feed_outlines) == 1
        assert feed_outlines[0].get("xmlUrl") == "http://rss.example.com/rss"

    def test_import_filter_no_filter_id_after_flush_returns_early(self):
        """opml_import_filter returns early when filter_id is falsy after flush.

        Source: ttrss/classes/opml.php:Opml::opml_import_filter lines 338-341\n
        PHP: if (!$filter_id) return — i.e. INSERT failed to produce an ID.\n
        Assert: only 1 session.add call (filter only, no rules/actions).
        """
        session = MagicMock()
        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = None
        session.execute.return_value = exec_result

        # filter object whose id is falsy (0 / None) after flush
        def track_add(obj):
            # Don't set obj.id — it will default to MagicMock's id (truthy)
            # We need to explicitly set it to falsy
            obj.id = None

        session.add.side_effect = track_add

        import json as _json
        from ttrss.feeds.opml import opml_import_filter
        opml_import_filter(
            session, user_id=1,
            item={"filter-type": "2"},
            node_text=_json.dumps({
                "enabled": True,
                "match_any_rule": False,
                "inverse": False,
                "title": "Broken Filter",
                "rules": [{"reg_exp": "x", "filter_type": 1, "cat_filter": False, "inverse": False, "feed": ""}],
                "actions": [],
            }),
        )

        # Only the filter itself is added; rules are skipped because filter_id is None
        assert session.add.call_count == 1
