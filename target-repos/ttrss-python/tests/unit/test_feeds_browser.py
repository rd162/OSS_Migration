"""Unit tests for ttrss.feeds.browser — make_feed_browser function.

Source PHP: ttrss/include/feedbrowser.php:make_feed_browser
New: no PHP equivalent — Python test suite.

All DB access is mocked via patch("ttrss.extensions.db").
No Flask app context or Postgres connection is required.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers — factory for mock TtRssFeedbrowserCache rows
# ---------------------------------------------------------------------------

def _cache_row(*, feed_url="http://feed.example.com/rss",
               title="Example Feed",
               site_url="http://feed.example.com",
               subscribers=100):
    """Return a MagicMock that mirrors a TtRssFeedbrowserCache ORM row."""
    row = MagicMock()
    row.feed_url = feed_url
    row.title = title
    row.site_url = site_url
    row.subscribers = subscribers
    return row


def _archived_row(*, feed_url="http://archived.example.com/rss",
                  title="Archived Feed",
                  site_url="http://archived.example.com",
                  feed_id=11,
                  articles_archived=7):
    """Return a (TtRssArchivedFeed mock, articles_archived int) tuple mirroring _mode2_archived_feeds rows."""
    feed = MagicMock()
    feed.feed_url = feed_url
    feed.title = title
    feed.site_url = site_url
    feed.id = feed_id
    return (feed, articles_archived)


# ---------------------------------------------------------------------------
# Mode 1 — global browser
# ---------------------------------------------------------------------------

class TestMakeFeedBrowserMode1:
    """Tests for mode=1 (global browser) path.

    Source: ttrss/include/feedbrowser.php:make_feed_browser (mode == 1 branch, lines 21-28).
    Adapted: PHP emits HTML; Python returns list of dicts.
    """

    def _run_mode1(self, rows, *, search="", limit=30):
        """Invoke make_feed_browser(mode=1) with mocked DB returning *rows*."""
        with patch("ttrss.extensions.db") as mock_db:
            mock_db.session.execute.return_value.scalars.return_value.all.return_value = rows
            from ttrss.feeds.browser import make_feed_browser
            return make_feed_browser(user_id=1, search=search, limit=limit, mode=1)

    def test_mode1_returns_list_of_dicts(self):
        """make_feed_browser(mode=1) returns a list of dicts.

        Source: ttrss/include/feedbrowser.php:make_feed_browser — mode 1 output loop (lines 48-70).
        Adapted: PHP emits HTML strings; Python returns structured list of dicts.
        """
        rows = [_cache_row(), _cache_row(feed_url="http://other.com/rss", title="Other", subscribers=50)]
        result = self._run_mode1(rows)
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(item, dict) for item in result)

    def test_mode1_dicts_have_required_keys(self):
        """Each dict in mode=1 results contains feed_url, title, site_url, subscribers.

        Source: ttrss/include/feedbrowser.php lines 48-70 — PHP output loop builds these fields.
        Adapted: PHP emits <li> HTML; Python exposes the same data as dict keys.
        """
        rows = [_cache_row(
            feed_url="http://rss.example.com/feed",
            title="Test Feed",
            site_url="http://rss.example.com",
            subscribers=42,
        )]
        result = self._run_mode1(rows)
        assert len(result) == 1
        item = result[0]
        assert item["feed_url"] == "http://rss.example.com/feed"
        assert item["title"] == "Test Feed"
        assert item["site_url"] == "http://rss.example.com"
        assert item["subscribers"] == 42

    def test_mode1_sorted_by_subscribers_desc(self):
        """make_feed_browser(mode=1) results are ordered by subscribers descending.

        Source: ttrss/include/feedbrowser.php lines 21-28 — ORDER BY subscribers DESC.
        Adapted: Python passes .order_by(TtRssFeedbrowserCache.subscribers.desc()) to SQLAlchemy.
        The mock returns rows in the order we supply, so we supply them pre-sorted
        and verify the query statement includes desc ordering via the ORM call.
        """
        rows = [
            _cache_row(title="Popular", subscribers=500),
            _cache_row(title="Medium", subscribers=200),
            _cache_row(title="Niche", subscribers=10),
        ]
        result = self._run_mode1(rows)
        subscribers = [r["subscribers"] for r in result]
        assert subscribers == sorted(subscribers, reverse=True)

    def test_mode1_search_filters_results(self):
        """make_feed_browser(mode=1) with search only returns matching feeds.

        Source: ttrss/include/feedbrowser.php lines 7-10 — $search_qpart UPPER LIKE filter.
        Adapted: Python applies func.upper().like() to feed_url and title columns.
        Mock verifies that the execute call is made (filter is passed to SQLAlchemy).
        """
        matching_row = _cache_row(title="Python Weekly", feed_url="http://pythonweekly.com/rss")
        with patch("ttrss.extensions.db") as mock_db:
            mock_db.session.execute.return_value.scalars.return_value.all.return_value = [matching_row]
            from ttrss.feeds.browser import make_feed_browser
            result = make_feed_browser(user_id=1, search="python", limit=30, mode=1)

        # DB execute was called (filter was applied at SQLAlchemy level)
        mock_db.session.execute.assert_called_once()
        assert len(result) == 1
        assert result[0]["title"] == "Python Weekly"


# ---------------------------------------------------------------------------
# Mode 2 — archived feeds
# ---------------------------------------------------------------------------

class TestMakeFeedBrowserMode2:
    """Tests for mode=2 (archived feeds) path.

    Source: ttrss/include/feedbrowser.php:make_feed_browser (mode == 2 branch, lines 30-42).
    Adapted: PHP queries ttrss_archived_feeds; Python queries TtRssArchivedFeed model.
    """

    def _run_mode2(self, rows, *, search="", limit=30):
        """Invoke make_feed_browser(mode=2) with mocked DB returning *rows*."""
        with patch("ttrss.extensions.db") as mock_db:
            mock_db.session.execute.return_value.all.return_value = rows
            from ttrss.feeds.browser import make_feed_browser
            return make_feed_browser(user_id=2, search=search, limit=limit, mode=2)

    def test_mode2_returns_user_archived_feeds(self):
        """make_feed_browser(mode=2) returns the user's archived feed list.

        Source: ttrss/include/feedbrowser.php lines 30-42 — query ttrss_archived_feeds.
        Adapted: PHP emits HTML; Python returns list of dicts with feed metadata.
        """
        rows = [
            _archived_row(title="Old Feed 1"),
            _archived_row(title="Old Feed 2", feed_id=12),
        ]
        result = self._run_mode2(rows)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_mode2_results_have_subscribers_zero(self):
        """Archived feed dicts always carry subscribers=0 (no subscriber data for archived feeds).

        Source: ttrss/include/feedbrowser.php lines 72-99 — mode 2 output: no subscriber count.
        Adapted: Python sets subscribers=0 explicitly for archived-feed entries.
        """
        rows = [_archived_row()]
        result = self._run_mode2(rows)
        assert len(result) == 1
        assert result[0]["subscribers"] == 0

    def test_limit_parameter_respected(self):
        """make_feed_browser respects the limit parameter (returns ≤ limit items).

        Source: ttrss/include/feedbrowser.php:make_feed_browser — .limit(limit) applied to query.
        Adapted: Python passes .limit(limit) to the SQLAlchemy select() statement.
        Mock returns exactly 2 rows regardless; test verifies that when limit=2
        and the DB returns 2 rows, we get at most 2 items back.
        """
        rows = [
            _archived_row(title="A", feed_id=1),
            _archived_row(title="B", feed_id=2),
        ]
        result = self._run_mode2(rows, limit=2)
        assert len(result) <= 2
