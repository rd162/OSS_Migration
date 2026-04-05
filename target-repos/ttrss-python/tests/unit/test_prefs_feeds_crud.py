"""Unit tests for ttrss/prefs/feeds_crud.py.

Source PHP: ttrss/classes/pref/feeds.php (Pref_Feeds handler, 1925 lines)

All functions in feeds_crud.py accept a SQLAlchemy ``Session`` as their first
argument.  Tests pass a MagicMock session directly — no db patching required.
"""
from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_session():
    """Return a fresh MagicMock that behaves as a minimal SQLAlchemy Session."""
    s = MagicMock()
    # scalar_one_or_none() chain used by most SELECT helpers
    s.execute.return_value.scalar_one_or_none.return_value = None
    s.execute.return_value.scalars.return_value.all.return_value = []
    return s


def _mock_feed(feed_id=1, owner_uid=10, title="Test Feed", auth_pass=None):
    feed = MagicMock()
    feed.id = feed_id
    feed.owner_uid = owner_uid
    feed.title = title
    feed.auth_pass = auth_pass
    feed.feed_url = "http://example.com/feed"
    feed.site_url = "http://example.com"
    return feed


# ---------------------------------------------------------------------------
# 1. save_feed_settings — title update
# ---------------------------------------------------------------------------


class TestSaveFeedSettings:
    """Source: ttrss/classes/pref/feeds.php:editSave (line 912) / editsaveops(false) (line 916)"""

    def test_title_update_executes_and_commits(self):
        """Source: ttrss/classes/pref/feeds.php:918 — feed_title = trim($_POST["title"])

        save_feed_settings() should apply the title to the feed ORM object and
        call session.commit() exactly once.
        """
        session = _mock_session()
        feed = _mock_feed()
        session.execute.return_value.scalar_one_or_none.return_value = feed

        from ttrss.prefs.feeds_crud import save_feed_settings
        result = save_feed_settings(session, feed_id=1, owner_uid=10, data={"title": "  New Title  "})

        assert result is True
        assert feed.title == "New Title"
        session.commit.assert_called_once()

    def test_auth_pass_set_when_provided(self):
        """Source: ttrss/classes/pref/feeds.php:927-938 — auth_pass via property setter

        When ``auth_pass`` is included in data, the feed's auth_pass attribute
        should be set to the stripped value (the property setter handles encryption).
        """
        session = _mock_session()
        feed = _mock_feed()
        session.execute.return_value.scalar_one_or_none.return_value = feed

        from ttrss.prefs.feeds_crud import save_feed_settings
        result = save_feed_settings(session, feed_id=1, owner_uid=10, data={"auth_pass": "  s3cr3t  "})

        assert result is True
        assert feed.auth_pass == "s3cr3t"
        session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# 3. batch_edit_feeds
# ---------------------------------------------------------------------------


class TestBatchEditFeeds:
    """Source: ttrss/classes/pref/feeds.php:batchEditSave (line 908) / editsaveops(true) (line 984)"""

    def test_update_executed_for_given_feed_ids(self):
        """Source: ttrss/classes/pref/feeds.php:984-1064 — iterate posted keys and UPDATE feeds

        batch_edit_feeds() should call session.execute() with an UPDATE statement
        when at least one valid field is supplied, then commit.
        """
        session = _mock_session()
        # scalars().all() needed for the auth_pass branch — not triggered here
        session.execute.return_value.scalars.return_value.all.return_value = []

        from ttrss.prefs.feeds_crud import batch_edit_feeds
        batch_edit_feeds(session, feed_ids=[1, 2], owner_uid=10, data={"title": "Bulk"})

        # execute called at least once (for the UPDATE) and commit called once
        session.execute.assert_called()
        session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# 4-6. batch_subscribe_feeds
# ---------------------------------------------------------------------------


class TestBatchSubscribeFeeds:
    """Source: ttrss/classes/pref/feeds.php:batchSubscribe (lines 1767-1860)"""

    def test_valid_url_returns_subscribed_status(self):
        """Source: ttrss/classes/pref/feeds.php:1820 — validate_feed_url() before subscribe

        A valid, new URL should produce a result entry with status 'subscribed'.
        """
        session = _mock_session()
        # No existing feed for this URL
        session.execute.return_value.scalar_one_or_none.return_value = None

        with patch("ttrss.http.client.validate_feed_url", return_value=True):
            from ttrss.prefs.feeds_crud import batch_subscribe_feeds
            results = batch_subscribe_feeds(
                session, owner_uid=10,
                feeds_text="http://a.com/feed\n",
                cat_id=None, login="", password="",
            )

        assert results == [{"url": "http://a.com/feed", "status": "subscribed"}]
        session.commit.assert_called_once()

    def test_invalid_url_returns_invalid_url_status(self):
        """Source: ttrss/classes/pref/feeds.php:1820 — skip URL if validate_feed_url() is False

        An URL that fails validation should appear in results with status
        'invalid_url' and should NOT be added to the session.
        """
        session = _mock_session()

        with patch("ttrss.http.client.validate_feed_url", return_value=False):
            from ttrss.prefs.feeds_crud import batch_subscribe_feeds
            results = batch_subscribe_feeds(
                session, owner_uid=10,
                feeds_text="not-a-url\n",
                cat_id=None, login="", password="",
            )

        assert results == [{"url": "not-a-url", "status": "invalid_url"}]
        session.add.assert_not_called()

    def test_existing_subscription_returns_already_subscribed(self):
        """Source: ttrss/classes/pref/feeds.php:batchSubscribe — skip already-subscribed feeds

        When a feed_url already exists for the user, the status should be
        'already_subscribed' and no new feed should be added.
        """
        session = _mock_session()
        # Simulate existing subscription
        session.execute.return_value.scalar_one_or_none.return_value = 99  # existing id

        with patch("ttrss.http.client.validate_feed_url", return_value=True):
            from ttrss.prefs.feeds_crud import batch_subscribe_feeds
            results = batch_subscribe_feeds(
                session, owner_uid=10,
                feeds_text="http://a.com/feed\n",
                cat_id=None, login="", password="",
            )

        assert results == [{"url": "http://a.com/feed", "status": "already_subscribed"}]
        session.add.assert_not_called()


# ---------------------------------------------------------------------------
# 7. save_feed_order
# ---------------------------------------------------------------------------


class TestSaveFeedOrder:
    """Source: ttrss/classes/pref/feeds.php:savefeedorder (line 386)"""

    def test_commit_called_on_empty_items(self):
        """Source: ttrss/classes/pref/feeds.php:400-418 — build data_map and process

        Even with an empty items list, save_feed_order() must call commit() to
        complete the transaction (matches PHP behaviour of always committing).
        """
        session = _mock_session()

        from ttrss.prefs.feeds_crud import save_feed_order
        save_feed_order(session, owner_uid=10, items=[])

        session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# 8. get_inactive_feeds
# ---------------------------------------------------------------------------


class TestGetInactiveFeeds:
    """Source: ttrss/classes/pref/feeds.php:inactiveFeeds (line 1529)"""

    def test_returns_list_of_dicts(self):
        """Source: ttrss/classes/pref/feeds.php:1537-1547 — correlated subquery for max(updated)

        get_inactive_feeds() should return a list of dicts with the expected keys.
        When the DB returns rows, each should be serialised into a dict.
        """
        session = _mock_session()

        import datetime
        fake_row = MagicMock()
        fake_row.id = 5
        fake_row.title = "Old Feed"
        fake_row.site_url = "http://old.example.com"
        fake_row.feed_url = "http://old.example.com/rss"
        fake_row.last_article = datetime.datetime(2023, 1, 1, tzinfo=datetime.timezone.utc)
        session.execute.return_value.all.return_value = [fake_row]

        from ttrss.prefs.feeds_crud import get_inactive_feeds
        results = get_inactive_feeds(session, owner_uid=10)

        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["id"] == 5
        assert results[0]["title"] == "Old Feed"
        assert "last_article" in results[0]


# ---------------------------------------------------------------------------
# 9. rescore_feed_impl
# ---------------------------------------------------------------------------


class TestRescoreFeedImpl:
    """Source: ttrss/classes/pref/feeds.php:1094-1147 / 1149-1200"""

    def test_execute_called_with_filters_mocked(self):
        """Source: ttrss/classes/pref/feeds.php:1116 — get_article_tags($line["ref_id"])
                   ttrss/classes/pref/feeds.php:1129-1142 — UPDATE score per article group

        rescore_feed_impl() should call session.execute() for the UPDATE statement
        that writes rescored values back to ttrss_user_entries.
        """
        session = _mock_session()
        # Return one fake article row
        fake_row = MagicMock()
        fake_row.ref_id = 7
        fake_row.title = "Article"
        fake_row.content = "body"
        fake_row.link = "http://example.com/a"
        fake_row.author = "Bob"
        fake_row.updated = None
        fake_row.tag_cache = ""
        session.execute.return_value.all.return_value = [fake_row]

        with (
            patch("ttrss.articles.filters.load_filters", return_value=[]) as mock_load,
            patch("ttrss.articles.tags.get_article_tags", return_value=[]) as mock_tags,
            patch("ttrss.articles.filters.get_article_filters", return_value=[]) as mock_af,
            patch("ttrss.articles.filters.calculate_article_score", return_value=0) as mock_score,
        ):
            from ttrss.prefs.feeds_crud import rescore_feed_impl
            rescore_feed_impl(session, feed_id=1, owner_uid=10)

        mock_load.assert_called_once()
        mock_tags.assert_called_once()
        mock_af.assert_called_once()
        mock_score.assert_called_once()
        # session.execute should have been called for the SELECT and for the UPDATE
        assert session.execute.call_count >= 1


# ---------------------------------------------------------------------------
# 10. clear_feed_articles
# ---------------------------------------------------------------------------


class TestClearFeedArticles:
    """Source: ttrss/classes/pref/feeds.php:clear (line 1089) / clear_feed_articles (line 1683)"""

    def test_delete_and_ccache_update_called(self):
        """Source: ttrss/classes/pref/feeds.php:1685-1694 — delete user_entries, purge orphans, ccache

        clear_feed_articles() must call session.execute() for the DELETEs and then
        call ccache_update() before committing.
        """
        session = _mock_session()

        with patch("ttrss.ccache.ccache_update") as mock_ccache:
            from ttrss.prefs.feeds_crud import clear_feed_articles
            clear_feed_articles(session, feed_id=1, owner_uid=10)

        assert session.execute.call_count >= 2  # DELETE user_entries + DELETE orphan entries
        mock_ccache.assert_called_once_with(session, 1, 10)
        session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# 11. remove_feed — positive (feed_id > 0)
# ---------------------------------------------------------------------------


class TestRemoveFeed:
    """Source: ttrss/classes/pref/feeds.php:remove (line 1078) / remove_feed (line 1707)"""

    def test_ccache_remove_called_for_positive_feed_id(self):
        """Source: ttrss/classes/pref/feeds.php:1759 — ccache_remove($id, $owner_uid)

        remove_feed() with a positive feed_id should call ccache_remove() with
        the session, feed_id, and owner_uid after deleting the feed.
        """
        session = _mock_session()
        feed = _mock_feed(feed_id=3, owner_uid=10)
        # First execute → scalar_one_or_none returns the feed row
        session.execute.return_value.scalar_one_or_none.return_value = feed
        # For the archived-feed lookup (second execute), return None → will create archive
        exec_results = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=feed)),   # feed lookup
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),   # archive lookup
            MagicMock(scalar=MagicMock(return_value=0)),                  # max(id) for archive
        ]
        session.execute.side_effect = exec_results + [MagicMock()] * 10  # remaining calls

        with patch("ttrss.ccache.ccache_remove") as mock_ccache_remove:
            from ttrss.prefs.feeds_crud import remove_feed
            err = remove_feed(session, feed_id=3, owner_uid=10)

        assert err is None
        mock_ccache_remove.assert_called_once_with(session, 3, 10)


# ---------------------------------------------------------------------------
# 12-13. update_feed_access_key
# ---------------------------------------------------------------------------


class TestUpdateFeedAccessKey:
    """Source: ttrss/classes/pref/feeds.php:update_feed_access_key (line 1880)"""

    def test_existing_key_updated_in_place(self):
        """Source: ttrss/classes/pref/feeds.php:1880 — regenerate access_key for existing row

        When an existing TtRssAccessKey row is found, its access_key attribute
        should be overwritten and session.add() should NOT be called.
        """
        session = _mock_session()
        existing_key_obj = MagicMock()
        existing_key_obj.access_key = "old_key"
        session.execute.return_value.scalar_one_or_none.return_value = existing_key_obj

        from ttrss.prefs.feeds_crud import update_feed_access_key
        new_key = update_feed_access_key(session, feed_id_str="1", is_cat=False, owner_uid=10)

        assert new_key != "old_key"
        assert existing_key_obj.access_key == new_key
        session.add.assert_not_called()
        session.commit.assert_called_once()

    def test_missing_key_triggers_session_add(self):
        """Source: ttrss/classes/pref/feeds.php:1880 — INSERT new access key row when missing

        When no existing row is found, a new TtRssAccessKey should be added via
        session.add() rather than mutating an existing object.
        """
        session = _mock_session()
        session.execute.return_value.scalar_one_or_none.return_value = None

        from ttrss.prefs.feeds_crud import update_feed_access_key
        new_key = update_feed_access_key(session, feed_id_str="1", is_cat=False, owner_uid=10)

        assert isinstance(new_key, str) and len(new_key) > 0
        session.add.assert_called_once()
        session.commit.assert_called_once()
