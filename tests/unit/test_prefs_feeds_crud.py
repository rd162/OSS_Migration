"""
Unit tests for ttrss/prefs/feeds_crud.py.

Source PHP: ttrss/classes/pref/feeds.php (Pref_Feeds handler, 1925 lines)

All tests mock the SQLAlchemy Session passed as the first argument to each
function (per AR-2 design: session is injected, not imported from db).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _session() -> MagicMock:
    """Return a fresh MagicMock Session."""
    session = MagicMock()
    # Provide a sensible default for scalar_one_or_none
    session.execute.return_value.scalar_one_or_none.return_value = None
    session.execute.return_value.scalars.return_value.all.return_value = []
    return session


# ---------------------------------------------------------------------------
# save_feed_settings
# ---------------------------------------------------------------------------


class TestSaveFeedSettings:
    """Source: ttrss/classes/pref/feeds.php:editSave (line 912) /
               editsaveops(false) (line 916)
    """

    def test_save_feed_settings_title_commits(self):
        """
        When feed is found, save_feed_settings applies 'title' from data and commits.

        Source: ttrss/classes/pref/feeds.php:918 — feed_title = trim($_POST["title"])
        Source: ttrss/classes/pref/feeds.php:editSave (line 912)
        """
        session = _session()
        mock_feed = MagicMock()
        session.execute.return_value.scalar_one_or_none.return_value = mock_feed

        from ttrss.prefs.feeds_crud import save_feed_settings
        result = save_feed_settings(session, feed_id=10, owner_uid=1, data={"title": "My Feed"})

        assert result is True
        assert mock_feed.title == "My Feed"
        session.commit.assert_called_once()

    def test_save_feed_settings_auth_pass_set_via_property(self):
        """
        When data contains 'auth_pass', it is assigned to feed.auth_pass (encrypted
        via the ORM property setter).

        Source: ttrss/classes/pref/feeds.php:editsaveops — auth_pass field handling
        Adapted: PHP stores raw or hashed password; Python uses a Fernet property
                 setter on TtRssFeed.auth_pass.
        """
        session = _session()
        mock_feed = MagicMock()
        session.execute.return_value.scalar_one_or_none.return_value = mock_feed

        from ttrss.prefs.feeds_crud import save_feed_settings
        result = save_feed_settings(
            session, feed_id=10, owner_uid=1,
            data={"auth_pass": "s3cr3t"},
        )

        assert result is True
        # The property setter must have been called with the stripped value
        assert mock_feed.auth_pass == "s3cr3t"
        session.commit.assert_called_once()

    def test_save_feed_settings_feed_not_found_returns_false(self):
        """
        When the feed does not exist or is not owned, return False without committing.

        Source: ttrss/classes/pref/feeds.php:editSave — ownership check before update
        """
        session = _session()
        session.execute.return_value.scalar_one_or_none.return_value = None

        from ttrss.prefs.feeds_crud import save_feed_settings
        result = save_feed_settings(session, feed_id=99, owner_uid=1, data={"title": "X"})

        assert result is False
        session.commit.assert_not_called()


# ---------------------------------------------------------------------------
# batch_edit_feeds
# ---------------------------------------------------------------------------


class TestBatchEditFeeds:
    """Source: ttrss/classes/pref/feeds.php:batchEditSave (line 908) /
               editsaveops(true) (line 984)
    """

    def test_batch_edit_feeds_executes_update_and_commits(self):
        """
        batch_edit_feeds should execute an UPDATE for the given feed IDs and commit.

        Source: ttrss/classes/pref/feeds.php:984-1064 — iterate posted keys
                and update matching feeds in bulk.
        """
        session = _session()

        from ttrss.prefs.feeds_crud import batch_edit_feeds
        batch_edit_feeds(session, feed_ids=[1, 2], owner_uid=7, data={"title": "Renamed"})

        session.execute.assert_called()
        session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# batch_subscribe_feeds
# ---------------------------------------------------------------------------


class TestBatchSubscribeFeeds:
    """Source: ttrss/classes/pref/feeds.php:batchSubscribe (lines 1767-1860)"""

    def test_valid_url_subscribes(self):
        """
        A valid, not-yet-subscribed URL results in status='subscribed'.

        Source: ttrss/classes/pref/feeds.php:1820 — validate_feed_url() check,
                then INSERT INTO ttrss_feeds if not already present.
        """
        session = _session()
        # No existing feed
        session.execute.return_value.scalar_one_or_none.return_value = None

        with patch("ttrss.prefs.feeds_crud.validate_feed_url", return_value=True):
            from ttrss.prefs.feeds_crud import batch_subscribe_feeds
            results = batch_subscribe_feeds(
                session, owner_uid=1,
                feeds_text="http://example.com/feed\n",
                cat_id=None, login="", password="",
            )

        assert len(results) == 1
        assert results[0]["status"] == "subscribed"
        session.add.assert_called_once()
        session.commit.assert_called_once()

    def test_invalid_url_returns_invalid_url_status(self):
        """
        A URL that fails validate_feed_url results in status='invalid_url'.

        Source: ttrss/classes/pref/feeds.php:1820 — validate_feed_url() returns
                false → skip with error status.
        """
        session = _session()

        with patch("ttrss.prefs.feeds_crud.validate_feed_url", return_value=False):
            from ttrss.prefs.feeds_crud import batch_subscribe_feeds
            results = batch_subscribe_feeds(
                session, owner_uid=1,
                feeds_text="not-a-url\n",
                cat_id=None, login="", password="",
            )

        assert results[0]["status"] == "invalid_url"
        session.add.assert_not_called()

    def test_existing_feed_returns_already_subscribed(self):
        """
        A URL already in ttrss_feeds for this user results in status='already_subscribed'.

        Source: ttrss/classes/pref/feeds.php:1825-1827 — duplicate check before
                INSERT.
        """
        session = _session()
        session.execute.return_value.scalar_one_or_none.return_value = 42  # existing feed id

        with patch("ttrss.prefs.feeds_crud.validate_feed_url", return_value=True):
            from ttrss.prefs.feeds_crud import batch_subscribe_feeds
            results = batch_subscribe_feeds(
                session, owner_uid=1,
                feeds_text="http://example.com/feed\n",
                cat_id=None, login="", password="",
            )

        assert results[0]["status"] == "already_subscribed"
        session.add.assert_not_called()


# ---------------------------------------------------------------------------
# save_feed_order
# ---------------------------------------------------------------------------


class TestSaveFeedOrder:
    """Source: ttrss/classes/pref/feeds.php:savefeedorder (line 386)"""

    def test_save_feed_order_executes_and_commits(self):
        """
        save_feed_order must execute UPDATE statements for the ordering and commit.

        Source: ttrss/classes/pref/feeds.php:400-418 — build data_map and process
                category/feed ordering.
        """
        session = _session()

        from ttrss.prefs.feeds_crud import save_feed_order
        # Minimal items list with a root node having a FEED reference
        items = [
            {
                "id": "root",
                "items": [{"_reference": "FEED:1"}],
            }
        ]
        save_feed_order(session, owner_uid=1, items=items)

        session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# get_inactive_feeds
# ---------------------------------------------------------------------------


class TestGetInactiveFeeds:
    """Source: ttrss/classes/pref/feeds.php:inactiveFeeds (line 1529)"""

    def test_returns_list_of_dicts(self):
        """
        get_inactive_feeds executes the correlated-subquery SELECT and returns
        a list of dicts with id/title/site_url/feed_url/last_article keys.

        Source: ttrss/classes/pref/feeds.php:1537-1547 — correlated subquery
                for max(updated) < cutoff.
        """
        session = _session()

        from datetime import datetime, timezone
        mock_row = MagicMock()
        mock_row.id = 5
        mock_row.title = "Old Feed"
        mock_row.site_url = "http://old.example.com"
        mock_row.feed_url = "http://old.example.com/feed"
        mock_row.last_article = datetime(2020, 1, 1, tzinfo=timezone.utc)
        session.execute.return_value.all.return_value = [mock_row]

        from ttrss.prefs.feeds_crud import get_inactive_feeds
        result = get_inactive_feeds(session, owner_uid=1)

        session.execute.assert_called_once()
        assert isinstance(result, list)
        assert result[0]["id"] == 5
        assert result[0]["title"] == "Old Feed"
        assert "last_article" in result[0]


# ---------------------------------------------------------------------------
# rescore_feed_impl
# ---------------------------------------------------------------------------


class TestRescoreFeedImpl:
    """Source: ttrss/classes/pref/feeds.php:1094-1147 / 1149-1200"""

    def test_rescore_executes_score_updates(self):
        """
        rescore_feed_impl must load filters, fetch article rows, compute scores,
        then execute UPDATE ttrss_user_entries SET score=... for each score bucket.

        Source: ttrss/classes/pref/feeds.php:1116 — get_article_tags($line["ref_id"])
        Source: ttrss/classes/pref/feeds.php:1129-1142 — bulk score update per bucket.
        """
        session = _session()

        mock_article_row = MagicMock()
        mock_article_row.ref_id = 99
        mock_article_row.title = "Test Article"
        mock_article_row.content = "Content"
        mock_article_row.link = "http://example.com/1"
        mock_article_row.author = "Author"
        mock_article_row.updated = None
        mock_article_row.tag_cache = ""
        session.execute.return_value.all.return_value = [mock_article_row]

        mock_filters = []

        with patch("ttrss.prefs.feeds_crud.load_filters", return_value=mock_filters), \
             patch("ttrss.prefs.feeds_crud.get_article_tags", return_value=[]), \
             patch("ttrss.prefs.feeds_crud.get_article_filters", return_value=[]), \
             patch("ttrss.prefs.feeds_crud.calculate_article_score", return_value=0):
            from ttrss.prefs.feeds_crud import rescore_feed_impl
            rescore_feed_impl(session, feed_id=3, owner_uid=1)

        # Score update execute must have been called at least once
        assert session.execute.call_count >= 2  # select + update


# ---------------------------------------------------------------------------
# clear_feed_articles
# ---------------------------------------------------------------------------


class TestClearFeedArticles:
    """Source: ttrss/classes/pref/feeds.php:clear (line 1089) /
               clear_feed_articles (line 1683)
    """

    def test_clear_executes_delete_and_calls_ccache_update(self):
        """
        clear_feed_articles must DELETE non-starred user entries, purge orphaned
        entries, then call ccache_update and commit.

        Source: ttrss/classes/pref/feeds.php:1685-1694 — delete user_entries,
                purge orphans, update ccache.
        """
        session = _session()

        with patch("ttrss.prefs.feeds_crud.ccache_update") as mock_ccache:
            from ttrss.prefs.feeds_crud import clear_feed_articles
            clear_feed_articles(session, feed_id=5, owner_uid=1)

        # At least two executes: DELETE user_entries and DELETE orphaned entries
        assert session.execute.call_count >= 2
        mock_ccache.assert_called_once_with(session, 5, 1)
        session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# remove_feed
# ---------------------------------------------------------------------------


class TestRemoveFeed:
    """Source: ttrss/classes/pref/feeds.php:remove (line 1078) /
               remove_feed (line 1707)
    """

    def test_remove_positive_feed_id_calls_ccache_remove(self):
        """
        For a positive feed_id, remove_feed must delete the feed then call
        ccache_remove and commit.

        Source: ttrss/classes/pref/feeds.php:1759 — ccache_remove($id, $owner_uid)
        Source: ttrss/classes/pref/feeds.php:1750-1751 — DELETE FROM ttrss_feeds.
        """
        session = _session()

        mock_feed = MagicMock()
        mock_feed.feed_url = "http://example.com/feed"
        mock_feed.title = "Example"
        mock_feed.site_url = "http://example.com"

        # Simulate: feed found, no existing archive
        execute_returns = iter([
            MagicMock(**{"scalar_one_or_none.return_value": mock_feed}),   # feed lookup
            MagicMock(**{"scalar_one_or_none.return_value": None}),         # archive lookup
            MagicMock(**{"scalar.return_value": 0}),                        # max(id)
            MagicMock(),                                                     # update starred
            MagicMock(),                                                     # delete access key
            MagicMock(),                                                     # delete feed
        ])
        session.execute.side_effect = lambda *a, **kw: next(execute_returns)

        with patch("ttrss.prefs.feeds_crud.ccache_remove") as mock_ccache:
            from ttrss.prefs.feeds_crud import remove_feed
            result = remove_feed(session, feed_id=10, owner_uid=1)

        assert result is None
        mock_ccache.assert_called_once_with(session, 10, 1)
        session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# update_feed_access_key
# ---------------------------------------------------------------------------


class TestUpdateFeedAccessKey:
    """Source: ttrss/classes/pref/feeds.php:update_feed_access_key (line 1880)"""

    def test_existing_key_is_updated(self):
        """
        When an access key already exists for (feed_id_str, is_cat, owner_uid),
        update its access_key value and commit.

        Source: ttrss/classes/pref/feeds.php:1880 — SELECT existing key, then UPDATE.
        """
        session = _session()
        existing_key_obj = MagicMock()
        existing_key_obj.access_key = "old_key_value"
        session.execute.return_value.scalar_one_or_none.return_value = existing_key_obj

        from ttrss.prefs.feeds_crud import update_feed_access_key
        new_key = update_feed_access_key(
            session, feed_id_str="10", is_cat=False, owner_uid=1
        )

        assert isinstance(new_key, str)
        assert len(new_key) > 0
        # The ORM object's access_key must have been updated
        assert existing_key_obj.access_key == new_key
        session.add.assert_not_called()
        session.commit.assert_called_once()

    def test_no_existing_key_inserts_new(self):
        """
        When no access key exists for (feed_id_str, is_cat, owner_uid),
        INSERT a new TtRssAccessKey row and commit.

        Source: ttrss/classes/pref/feeds.php:1880 — INSERT new key when none exists.
        """
        session = _session()
        session.execute.return_value.scalar_one_or_none.return_value = None

        from ttrss.prefs.feeds_crud import update_feed_access_key
        new_key = update_feed_access_key(
            session, feed_id_str="10", is_cat=False, owner_uid=1
        )

        assert isinstance(new_key, str)
        assert len(new_key) > 0
        session.add.assert_called_once()
        added_obj = session.add.call_args[0][0]
        assert added_obj.feed_id == "10"
        assert added_obj.is_cat is False
        assert added_obj.owner_uid == 1
        assert added_obj.access_key == new_key
        session.commit.assert_called_once()
