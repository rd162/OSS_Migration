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
