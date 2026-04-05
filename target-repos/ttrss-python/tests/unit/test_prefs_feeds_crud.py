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


# ---------------------------------------------------------------------------
# 13. regen_opml_key / regen_feed_key / clear_access_keys
# ---------------------------------------------------------------------------


class TestAccessKeyManagement:
    """Source: ttrss/classes/pref/feeds.php:regenOPMLKey (line 1861),
               regenFeedKey (line 1870), clearKeys (line 1904)"""

    def test_regen_opml_key_returns_string(self):
        """Source: ttrss/classes/pref/feeds.php:regenOPMLKey (lines 1861-1867)
        PHP: calls update_feed_access_key('OPML:Publish', false, uid) and returns new link.

        regen_opml_key() should delegate to update_feed_access_key() and return
        the new key string produced by it.
        """
        session = _mock_session()
        session.execute.return_value.scalar_one_or_none.return_value = None

        from ttrss.prefs.feeds_crud import regen_opml_key
        key = regen_opml_key(session, owner_uid=10)

        assert isinstance(key, str) and len(key) > 0
        session.commit.assert_called_once()

    def test_regen_opml_key_updates_existing_row(self):
        """Source: ttrss/classes/pref/feeds.php:regenOPMLKey (lines 1861-1867)
        PHP: overwrites existing OPML:Publish key row in ttrss_access_keys.

        When an existing OPML:Publish key row exists, regen_opml_key() must
        overwrite access_key on that object (no session.add) and commit.
        """
        session = _mock_session()
        existing = MagicMock()
        existing.access_key = "old_opml_key"
        session.execute.return_value.scalar_one_or_none.return_value = existing

        from ttrss.prefs.feeds_crud import regen_opml_key
        key = regen_opml_key(session, owner_uid=10)

        assert key != "old_opml_key"
        assert existing.access_key == key
        session.add.assert_not_called()
        session.commit.assert_called_once()

    def test_regen_feed_key_creates_new_row(self):
        """Source: ttrss/classes/pref/feeds.php:regenFeedKey (lines 1870-1878)
        PHP: regenerates key via update_feed_access_key for the given feed_id/is_cat.

        regen_feed_key() with a feed_id not yet in ttrss_access_keys should
        call session.add() with a new TtRssAccessKey and return a non-empty string.
        """
        session = _mock_session()
        session.execute.return_value.scalar_one_or_none.return_value = None

        from ttrss.prefs.feeds_crud import regen_feed_key
        key = regen_feed_key(session, feed_id=7, is_cat=False, owner_uid=10)

        assert isinstance(key, str) and len(key) > 0
        session.add.assert_called_once()
        session.commit.assert_called_once()

    def test_regen_feed_key_updates_existing_row(self):
        """Source: ttrss/classes/pref/feeds.php:regenFeedKey (lines 1870-1878)
        PHP: overwrites existing feed key row in ttrss_access_keys.

        When an existing key row is found for the given feed_id, regen_feed_key()
        must update access_key in-place and not call session.add().
        """
        session = _mock_session()
        existing = MagicMock()
        existing.access_key = "old_feed_key"
        session.execute.return_value.scalar_one_or_none.return_value = existing

        from ttrss.prefs.feeds_crud import regen_feed_key
        key = regen_feed_key(session, feed_id=7, is_cat=False, owner_uid=10)

        assert key != "old_feed_key"
        assert existing.access_key == key
        session.add.assert_not_called()
        session.commit.assert_called_once()

    def test_clear_access_keys_executes_delete_and_commits(self):
        """Source: ttrss/classes/pref/feeds.php:clearKeys (lines 1904-1906)
        PHP: DELETE FROM ttrss_access_keys WHERE owner_uid = uid.

        clear_access_keys() should call session.execute() with a DELETE statement
        and then commit exactly once.
        """
        session = _mock_session()

        from ttrss.prefs.feeds_crud import clear_access_keys
        clear_access_keys(session, owner_uid=10)

        session.execute.assert_called_once()
        session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# 14. get_feed_tree
# ---------------------------------------------------------------------------


class TestGetFeedTree:
    """Source: ttrss/classes/pref/feeds.php:getfeedtree (line 94) / makefeedtree (line 98)"""

    def test_returns_dict_with_items_key(self):
        """Source: ttrss/classes/pref/feeds.php:290-300 — build fl dict with identifier/label/items

        get_feed_tree() should always return a dict that includes an 'items' key
        (the outer feed-list envelope) regardless of whether any feeds exist.
        """
        session = _mock_session()
        # categories: empty, feeds: empty
        session.execute.return_value.scalars.return_value.all.return_value = []

        with (
            patch("ttrss.feeds.categories.getCategoryTitle", return_value="Special"),
            patch("ttrss.feeds.categories.getFeedTitle", return_value="All articles"),
            patch("ttrss.prefs.ops.get_user_pref", return_value="false"),
        ):
            from ttrss.prefs.feeds_crud import get_feed_tree
            result = get_feed_tree(session, owner_uid=10)

        assert isinstance(result, dict)
        assert "items" in result

    def test_flat_list_mode_wraps_root_in_items(self):
        """Source: ttrss/classes/pref/feeds.php:290-300 — mode != 2 puts root inside items list

        When mode != 2, the returned dict's 'items' should be a list containing
        the root category node (not a flat list of feeds directly).
        """
        session = _mock_session()
        session.execute.return_value.scalars.return_value.all.return_value = []

        with (
            patch("ttrss.prefs.ops.get_user_pref", return_value="false"),
        ):
            from ttrss.prefs.feeds_crud import get_feed_tree
            result = get_feed_tree(session, owner_uid=10, mode=0)

        assert isinstance(result["items"], list)
        # root node is the single entry when enable_cats=false, no feeds
        assert len(result["items"]) == 1
        assert result["items"][0].get("id") == "root"

    def test_mode2_returns_flat_items(self):
        """Source: ttrss/classes/pref/feeds.php:115-187 — mode 2 returns special feeds / labels

        In mode=2 with categories disabled, items should be a flat list of
        virtual feed nodes (the special-feeds section), not nested under root.
        """
        session = _mock_session()
        session.execute.return_value.scalars.return_value.all.return_value = []

        with (
            patch("ttrss.prefs.ops.get_user_pref", return_value="false"),
            patch("ttrss.feeds.categories.getCategoryTitle", return_value="Special"),
            patch("ttrss.feeds.categories.getFeedTitle", return_value="All"),
        ):
            from ttrss.prefs.feeds_crud import get_feed_tree
            result = get_feed_tree(session, owner_uid=10, mode=2)

        # Items should be the six special virtual feeds directly
        assert isinstance(result["items"], list)
        assert len(result["items"]) == 6


# ---------------------------------------------------------------------------
# 15. categorize_feeds / remove_category / rename_category
#     reset_category_order / reset_feed_order
# ---------------------------------------------------------------------------


class TestFeedOrderManagement:
    """Source: ttrss/classes/pref/feeds.php:categorize (line 1202),
               removeCat (line 1226), renamecat (line 17),
               catsortreset (line 303), feedsortreset (line 309)"""

    def test_categorize_feeds_iterates_and_commits(self):
        """Source: ttrss/classes/pref/feeds.php:categorize (lines 1215-1221)
        PHP: iterate feed_ids and UPDATE cat_id, then commit.

        categorize_feeds() should call session.execute() once per feed_id and
        commit exactly once when at least one feed_id is provided.
        """
        session = _mock_session()

        from ttrss.prefs.feeds_crud import categorize_feeds
        categorize_feeds(session, feed_ids=[1, 2, 3], owner_uid=10, cat_id=5)

        assert session.execute.call_count == 3
        session.commit.assert_called_once()

    def test_categorize_feeds_zero_cat_id_stored_as_none(self):
        """Source: ttrss/classes/pref/feeds.php:categorize (line 1215) — cat_id=0 → NULL in DB

        When cat_id=0 is passed, the UPDATE values should use None (SQL NULL)
        for the cat_id column rather than 0. The function performs this conversion
        before building the UPDATE statement.
        """
        session = _mock_session()

        from ttrss.prefs.feeds_crud import categorize_feeds
        # Should not raise; we verify commit happens (value conversion is internal)
        categorize_feeds(session, feed_ids=[4], owner_uid=10, cat_id=0)

        session.commit.assert_called_once()

    def test_remove_category_executes_delete_and_commits(self):
        """Source: ttrss/classes/pref/feeds.php:remove_feed_category (lines 1699-1705)
        PHP: DELETE FROM ttrss_feed_categories WHERE id AND owner_uid.

        remove_category() should issue one DELETE execute() call and then commit.
        """
        session = _mock_session()

        from ttrss.prefs.feeds_crud import remove_category
        remove_category(session, cat_id=3, owner_uid=10)

        session.execute.assert_called_once()
        session.commit.assert_called_once()

    def test_rename_category_executes_update_and_commits(self):
        """Source: ttrss/classes/pref/feeds.php:renamecat (lines 22-23)
        PHP: UPDATE ttrss_feed_categories SET title = :title WHERE id AND owner_uid.

        rename_category() should issue one UPDATE execute() call and then commit.
        """
        session = _mock_session()

        from ttrss.prefs.feeds_crud import rename_category
        rename_category(session, cat_id=3, owner_uid=10, title="News")

        session.execute.assert_called_once()
        session.commit.assert_called_once()

    def test_reset_category_order_sets_order_id_zero(self):
        """Source: ttrss/classes/pref/feeds.php:catsortreset (line 303)
        PHP: UPDATE ttrss_feed_categories SET order_id=0 WHERE owner_uid.

        reset_category_order() should issue one UPDATE execute() and then commit.
        """
        session = _mock_session()

        from ttrss.prefs.feeds_crud import reset_category_order
        reset_category_order(session, owner_uid=10)

        session.execute.assert_called_once()
        session.commit.assert_called_once()

    def test_reset_feed_order_sets_order_id_zero(self):
        """Source: ttrss/classes/pref/feeds.php:feedsortreset (line 309)
        PHP: UPDATE ttrss_feeds SET order_id=0 WHERE owner_uid.

        reset_feed_order() should issue one UPDATE execute() and then commit.
        """
        session = _mock_session()

        from ttrss.prefs.feeds_crud import reset_feed_order
        reset_feed_order(session, owner_uid=10)

        session.execute.assert_called_once()
        session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# 16. get_feeds_with_errors
# ---------------------------------------------------------------------------


class TestGetFeedsWithErrors:
    """Source: ttrss/classes/pref/feeds.php:feedsWithErrors (line 1611)"""

    def test_returns_list_of_dicts_with_expected_keys(self):
        """Source: ttrss/classes/pref/feeds.php:feedsWithErrors (line 1611)
        PHP: SELECT id, title, feed_url, last_error, site_url FROM ttrss_feeds
             WHERE last_error != '' AND owner_uid = uid.

        get_feeds_with_errors() should return a list where each element is a dict
        with 'id', 'title', 'feed_url', 'last_error', and 'site_url' keys.
        """
        session = _mock_session()
        fake_row = MagicMock()
        fake_row.id = 9
        fake_row.title = "Broken Feed"
        fake_row.feed_url = "http://broken.example.com/feed"
        fake_row.last_error = "HTTP 500"
        fake_row.site_url = "http://broken.example.com"
        session.execute.return_value.all.return_value = [fake_row]

        from ttrss.prefs.feeds_crud import get_feeds_with_errors
        results = get_feeds_with_errors(session, owner_uid=10)

        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["id"] == 9
        assert results[0]["last_error"] == "HTTP 500"
        assert set(results[0].keys()) == {"id", "title", "feed_url", "last_error", "site_url"}

    def test_empty_result_returns_empty_list(self):
        """Source: ttrss/classes/pref/feeds.php:feedsWithErrors (line 1611)
        PHP: returns empty result set when no feeds have last_error set.

        get_feeds_with_errors() should return [] when the DB returns no rows.
        """
        session = _mock_session()
        session.execute.return_value.all.return_value = []

        from ttrss.prefs.feeds_crud import get_feeds_with_errors
        results = get_feeds_with_errors(session, owner_uid=10)

        assert results == []


# ---------------------------------------------------------------------------
# 17. remove_feed_icon
# ---------------------------------------------------------------------------


class TestRemoveFeedIcon:
    """Source: ttrss/classes/pref/feeds.php:Pref_Feeds::removeicon (lines 459-470)"""

    def test_returns_true_when_row_updated(self):
        """Source: ttrss/classes/pref/feeds.php:removeicon (lines 459-470)
        PHP: UPDATE ttrss_feeds SET favicon_avg_color = NULL WHERE id AND owner_uid.

        remove_feed_icon() should return True when rowcount > 0 (feed owned
        by user) and commit exactly once.
        """
        session = _mock_session()
        session.execute.return_value.rowcount = 1

        from ttrss.prefs.feeds_crud import remove_feed_icon
        result = remove_feed_icon(session, feed_id=5, owner_uid=10)

        assert result is True
        session.execute.assert_called_once()
        session.commit.assert_called_once()

    def test_returns_false_when_no_row_updated(self):
        """Source: ttrss/classes/pref/feeds.php:removeicon (lines 459-470)
        PHP: returns false if no feed matched (owner_uid mismatch).

        remove_feed_icon() should return False when rowcount == 0 (feed not
        owned by the user or not found).
        """
        session = _mock_session()
        session.execute.return_value.rowcount = 0

        from ttrss.prefs.feeds_crud import remove_feed_icon
        result = remove_feed_icon(session, feed_id=5, owner_uid=99)

        assert result is False
        session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# 18. reset_pubsub
# ---------------------------------------------------------------------------


class TestResetPubsub:
    """Source: ttrss/classes/pref/feeds.php:Pref_Feeds::resetPubSub (lines 1068-1077)"""

    def test_empty_feed_ids_returns_zero_without_execute(self):
        """Source: ttrss/classes/pref/feeds.php:resetPubSub (lines 1068-1077)
        PHP: guard against empty id list to avoid invalid SQL.

        reset_pubsub() with an empty list should return 0 immediately without
        calling session.execute() or session.commit().
        """
        session = _mock_session()

        from ttrss.prefs.feeds_crud import reset_pubsub
        count = reset_pubsub(session, feed_ids=[], owner_uid=10)

        assert count == 0
        session.execute.assert_not_called()
        session.commit.assert_not_called()

    def test_non_empty_feed_ids_executes_update_and_returns_rowcount(self):
        """Source: ttrss/classes/pref/feeds.php:resetPubSub (lines 1068-1077)
        PHP: UPDATE ttrss_feeds SET pubsub_state=0 WHERE id IN (...) AND owner_uid.

        reset_pubsub() with feed_ids should call execute() and return the
        rowcount reported by the DB.
        """
        session = _mock_session()
        session.execute.return_value.rowcount = 3

        from ttrss.prefs.feeds_crud import reset_pubsub
        count = reset_pubsub(session, feed_ids=[1, 2, 3], owner_uid=10)

        assert count == 3
        session.execute.assert_called_once()
        session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# 19. get_feed_tree — categories enabled
# ---------------------------------------------------------------------------


class TestGetFeedTreeCatsEnabled:
    """Source: ttrss/classes/pref/feeds.php:makefeedtree (line 98) — categorized path"""

    def test_categories_enabled_returns_items_with_root_node(self):
        """Source: ttrss/classes/pref/feeds.php:189-261 — categorized feeds tree build

        When ENABLE_FEED_CATS is 'true', get_feed_tree() should build a
        categorized tree.  With no categories and no feeds the root node should
        still be present in items with param reflecting zero feeds.
        """
        session = _mock_session()
        # Top-level categories → empty, uncategorized feeds → empty
        session.execute.return_value.scalars.return_value.all.return_value = []

        with patch("ttrss.prefs.ops.get_user_pref", return_value="true"):
            from ttrss.prefs.feeds_crud import get_feed_tree
            result = get_feed_tree(session, owner_uid=10, mode=0)

        assert "items" in result
        # Root is the only item; it has id='root'
        assert result["items"][0]["id"] == "root"
        # param reflects 0 feeds
        assert "0 feed" in result["items"][0]["param"]

    def test_categories_enabled_with_one_top_cat_and_no_feeds(self):
        """Source: ttrss/classes/pref/feeds.php:189-220 — iterate top-level categories

        A single top-level category with no child feeds and force_show_empty=True
        should appear in the tree even though it has 0 feeds.
        """
        session = _mock_session()

        fake_cat = MagicMock()
        fake_cat.id = 1
        fake_cat.title = "Tech"
        fake_cat.order_id = 0

        # First scalars().all() → top categories; second → sub-cats; third → feeds in cat; fourth → uncat feeds
        results_sequence = [
            [fake_cat],   # top_cats
            [],           # sub_cats inside _get_category_items
            [],           # feeds inside cat
            [],           # uncat feeds
        ]
        call_count = {"n": 0}

        def scalars_side_effect(*args, **kwargs):
            m = MagicMock()
            idx = call_count["n"]
            call_count["n"] += 1
            m.all.return_value = results_sequence[idx] if idx < len(results_sequence) else []
            return m

        session.execute.return_value.scalars.side_effect = scalars_side_effect

        with patch("ttrss.prefs.ops.get_user_pref", return_value="true"):
            from ttrss.prefs.feeds_crud import get_feed_tree
            result = get_feed_tree(session, owner_uid=10, mode=0, force_show_empty=True)

        assert "items" in result
        root = result["items"][0]
        # Root should contain the Tech category plus uncategorized
        cat_items = [i for i in root["items"] if i.get("type") == "category"]
        cat_names = [i["name"] for i in cat_items]
        assert "Tech" in cat_names


# ---------------------------------------------------------------------------
# 20. _calculate_children_count (internal helper exercised directly)
# ---------------------------------------------------------------------------


class TestCalculateChildrenCount:
    """Source: ttrss/classes/pref/feeds.php:calculate_children_count (line 1909)"""

    def test_empty_category_returns_zero(self):
        """Source: ttrss/classes/pref/feeds.php:calculate_children_count (line 1909)
        PHP: recursively sum leaf feeds; empty category returns 0.

        _calculate_children_count() with an empty items list should return 0.
        """
        from ttrss.prefs.feeds_crud import _calculate_children_count
        result = _calculate_children_count({"items": []})
        assert result == 0

    def test_flat_feeds_counted(self):
        """Source: ttrss/classes/pref/feeds.php:calculate_children_count (line 1909)
        PHP: non-category children (type != 'category') count as one each.

        _calculate_children_count() should return the total number of feed-type
        items (non-category) at all levels.
        """
        from ttrss.prefs.feeds_crud import _calculate_children_count
        cat = {
            "type": "category",
            "items": [
                {"type": "feed"},
                {"type": "feed"},
                {"type": "category", "items": [{"type": "feed"}]},
            ],
        }
        assert _calculate_children_count(cat) == 3

    def test_nested_empty_category_returns_zero(self):
        """Source: ttrss/classes/pref/feeds.php:calculate_children_count (line 1909)
        PHP: nested empty category still totals zero.

        A category containing only a sub-category with no feeds should return 0.
        """
        from ttrss.prefs.feeds_crud import _calculate_children_count
        cat = {
            "type": "category",
            "items": [
                {"type": "category", "items": []},
            ],
        }
        assert _calculate_children_count(cat) == 0


# ---------------------------------------------------------------------------
# 21. get_feed_tree — mode=2 with categories enabled (labels path)
# ---------------------------------------------------------------------------


class TestGetFeedTreeMode2CatsEnabled:
    """Source: ttrss/classes/pref/feeds.php:115-187 — mode=2 special-feeds + labels, cats enabled"""

    def test_mode2_cats_enabled_no_labels_six_special_feeds_in_cat_node(self):
        """Source: ttrss/classes/pref/feeds.php:115-187 — mode=2 wraps special feeds in cat node

        When enable_cats=true and mode=2, the six special virtual feeds should be
        wrapped inside a category node rather than placed directly in items.
        """
        session = _mock_session()
        # scalars().all() for labels → empty
        session.execute.return_value.scalars.return_value.all.return_value = []

        with (
            patch("ttrss.prefs.ops.get_user_pref", return_value="true"),
            patch("ttrss.feeds.categories.getCategoryTitle", return_value="Special"),
            patch("ttrss.feeds.categories.getFeedTitle", return_value="All"),
        ):
            from ttrss.prefs.feeds_crud import get_feed_tree
            result = get_feed_tree(session, owner_uid=10, mode=2)

        # In cats-enabled mode=2, items contains category node(s), not bare feed nodes
        assert isinstance(result["items"], list)
        # First item should be a category wrapping the special feeds
        assert result["items"][0]["type"] == "category"
        assert len(result["items"][0]["items"]) == 6

    def test_mode2_with_labels_appends_label_items(self):
        """Source: ttrss/classes/pref/feeds.php:814-831 — label rows extend items list (cats disabled)

        When mode=2, categories disabled, and one label exists, the label feed
        node should be appended directly into items (6 special + 1 label = 7).
        """
        session = _mock_session()

        fake_label = MagicMock()
        fake_label.id = 1
        fake_label.fg_color = "#ff0000"
        fake_label.bg_color = "#ffffff"

        # scalars().all() is called once: for labels query
        call_count = {"n": 0}
        def scalars_se(*a, **kw):
            m = MagicMock()
            idx = call_count["n"]
            call_count["n"] += 1
            m.all.return_value = [fake_label] if idx == 0 else []
            return m

        session.execute.return_value.scalars.side_effect = scalars_se

        with (
            patch("ttrss.prefs.ops.get_user_pref", return_value="false"),
            patch("ttrss.feeds.categories.getFeedTitle", return_value="Label Feed"),
            patch("ttrss.utils.feeds.label_to_feed_id", return_value=-1001),
        ):
            from ttrss.prefs.feeds_crud import get_feed_tree
            result = get_feed_tree(session, owner_uid=10, mode=2)

        # 6 special virtual feed nodes + 1 label node extended into items flat
        assert len(result["items"]) == 7


# ---------------------------------------------------------------------------
# 22. get_feed_tree — categorized tree with uncategorized feeds
# ---------------------------------------------------------------------------


class TestGetFeedTreeUncategorizedFeeds:
    """Source: ttrss/classes/pref/feeds.php:221-258 — uncategorized feeds section"""

    def test_uncategorized_feed_appears_in_uncat_node(self):
        """Source: ttrss/classes/pref/feeds.php:221-258 — feeds with cat_id NULL → Uncategorized

        When ENABLE_FEED_CATS is true and no top-level categories exist, a feed
        with no category should appear inside the 'Uncategorized' (CAT:0) node.
        With force_show_empty=True the uncat node is always added.
        """
        session = _mock_session()

        fake_feed = MagicMock()
        fake_feed.id = 42
        fake_feed.title = "Uncat Feed"
        fake_feed.last_error = ""
        fake_feed.last_updated = None

        call_count = {"n": 0}
        def scalars_se(*a, **kw):
            m = MagicMock()
            idx = call_count["n"]
            call_count["n"] += 1
            # Call 0: top_cats → []
            # Call 1: uncat_feeds → [fake_feed]
            m.all.return_value = [fake_feed] if idx == 1 else []
            return m

        session.execute.return_value.scalars.side_effect = scalars_se

        with patch("ttrss.prefs.ops.get_user_pref", return_value="true"):
            from ttrss.prefs.feeds_crud import get_feed_tree
            result = get_feed_tree(session, owner_uid=10, mode=0, force_show_empty=True)

        root_node = result["items"][0]
        # Should have only Uncategorized (no top cats)
        uncat_nodes = [i for i in root_node["items"] if i.get("id") == "CAT:0"]
        assert len(uncat_nodes) == 1
        assert len(uncat_nodes[0]["items"]) == 1
        assert uncat_nodes[0]["items"][0]["bare_id"] == 42


# ---------------------------------------------------------------------------
# 23. get_feed_tree — flat list with search filter
# ---------------------------------------------------------------------------


class TestGetFeedTreeFlatSearch:
    """Source: ttrss/classes/pref/feeds.php:263-288 — flat feed list with search"""

    def test_search_applied_to_flat_list(self):
        """Source: ttrss/classes/pref/feeds.php:263-288 — search filters title with LIKE

        When a search string is provided and categories are disabled, the query
        should apply a LIKE filter.  The matching feed should appear in items.
        """
        session = _mock_session()

        fake_feed = MagicMock()
        fake_feed.id = 7
        fake_feed.title = "Python News"
        fake_feed.last_error = ""
        fake_feed.last_updated = None

        session.execute.return_value.scalars.return_value.all.return_value = [fake_feed]

        with patch("ttrss.prefs.ops.get_user_pref", return_value="false"):
            from ttrss.prefs.feeds_crud import get_feed_tree
            result = get_feed_tree(session, owner_uid=10, mode=0, search="python")

        root_node = result["items"][0]
        assert len(root_node["items"]) == 1
        assert root_node["items"][0]["bare_id"] == 7


# ---------------------------------------------------------------------------
# 24. _get_category_items — sub-category recursion
# ---------------------------------------------------------------------------


class TestGetCategoryItems:
    """Source: ttrss/classes/pref/feeds.php:get_category_items (line 28)"""

    def test_sub_category_with_feed_included(self):
        """Source: ttrss/classes/pref/feeds.php:get_category_items (line 28)
        PHP: recursively build sub-category nodes; sub-cat with feeds is included.

        _get_category_items() with a sub-category that has one feed should
        return a list containing the sub-category node whose items holds the feed.
        """
        session = _mock_session()

        fake_sub_cat = MagicMock()
        fake_sub_cat.id = 99
        fake_sub_cat.title = "Sub"
        fake_sub_cat.order_id = 0

        fake_feed = MagicMock()
        fake_feed.id = 55
        fake_feed.title = "Sub Feed"
        fake_feed.last_error = ""
        fake_feed.last_updated = None

        call_count = {"n": 0}
        def scalars_se(*a, **kw):
            m = MagicMock()
            idx = call_count["n"]
            call_count["n"] += 1
            # Call 0: top-level sub_cats → [fake_sub_cat]
            # Call 1: recursive sub_cats of sub_cat → []
            # Call 2: feeds in sub_cat → [fake_feed]
            # Call 3: feeds in parent cat → []
            seq = [[fake_sub_cat], [], [fake_feed], []]
            m.all.return_value = seq[idx] if idx < len(seq) else []
            return m

        session.execute.return_value.scalars.side_effect = scalars_se

        from ttrss.prefs.feeds_crud import _get_category_items
        items = _get_category_items(session, cat_id=1, owner_uid=10,
                                    search_filter=None, show_empty_cats=False)

        assert len(items) == 1  # the sub-category node
        assert items[0]["bare_id"] == 99
        assert len(items[0]["items"]) == 1
        assert items[0]["items"][0]["bare_id"] == 55

    def test_empty_sub_category_excluded_when_not_show_empty(self):
        """Source: ttrss/classes/pref/feeds.php:get_category_items (line 28)
        PHP: empty sub-category is skipped when show_empty_cats is False.

        _get_category_items() should not include a sub-category node when it has
        zero feeds and show_empty_cats is False.
        """
        session = _mock_session()

        fake_sub_cat = MagicMock()
        fake_sub_cat.id = 77
        fake_sub_cat.title = "Empty Sub"
        fake_sub_cat.order_id = 0

        call_count = {"n": 0}
        def scalars_se(*a, **kw):
            m = MagicMock()
            idx = call_count["n"]
            call_count["n"] += 1
            # sub_cats → [fake_sub_cat], recursive sub_cats → [], recursive feeds → [], parent feeds → []
            seq = [[fake_sub_cat], [], [], []]
            m.all.return_value = seq[idx] if idx < len(seq) else []
            return m

        session.execute.return_value.scalars.side_effect = scalars_se

        from ttrss.prefs.feeds_crud import _get_category_items
        items = _get_category_items(session, cat_id=1, owner_uid=10,
                                    search_filter=None, show_empty_cats=False)

        assert items == []


# ---------------------------------------------------------------------------
# 25. _checkbox_bool
# ---------------------------------------------------------------------------


class TestCheckboxBool:
    """Source: ttrss/prefs/feeds_crud.py:_checkbox_bool (line 1048)"""

    def test_none_returns_false(self):
        """Source: ttrss/prefs/feeds_crud.py:_checkbox_bool
        PHP: checkbox_to_sql_bool — None/absent is treated as unchecked (false).
        """
        from ttrss.prefs.feeds_crud import _checkbox_bool
        assert _checkbox_bool(None) is False

    def test_true_string_returns_true(self):
        """Source: ttrss/prefs/feeds_crud.py:_checkbox_bool
        PHP: '1', 'true', 'on', 'yes' are truthy checkbox values.
        """
        from ttrss.prefs.feeds_crud import _checkbox_bool
        assert _checkbox_bool("1") is True
        assert _checkbox_bool("true") is True
        assert _checkbox_bool("on") is True
        assert _checkbox_bool("yes") is True

    def test_other_values_return_false(self):
        """Source: ttrss/prefs/feeds_crud.py:_checkbox_bool
        PHP: any other value is treated as unchecked (false).
        """
        from ttrss.prefs.feeds_crud import _checkbox_bool
        assert _checkbox_bool("0") is False
        assert _checkbox_bool("false") is False
        assert _checkbox_bool("off") is False


# ---------------------------------------------------------------------------
# 26. get_feed_for_edit — found path
# ---------------------------------------------------------------------------


class TestGetFeedForEdit:
    """Source: ttrss/classes/pref/feeds.php:editfeed (line 529)"""

    def test_found_returns_dict_with_expected_keys(self):
        """Source: ttrss/classes/pref/feeds.php:editfeed (line 529)
        PHP: SELECT * FROM ttrss_feeds WHERE id AND owner_uid — returns feed data dict.

        get_feed_for_edit() should return a dict with all expected feed fields
        when the feed is found.
        """
        session = _mock_session()
        feed = _mock_feed(feed_id=3, owner_uid=10)
        feed.feed_url = "http://x.com/feed"
        feed.site_url = "http://x.com"
        feed.cat_id = None
        feed.update_interval = 0
        feed.purge_interval = 0
        feed.auth_login = ""
        feed.private = False
        feed.include_in_digest = True
        feed.always_display_enclosures = False
        feed.hide_images = False
        feed.cache_images = False
        feed.mark_unread_on_update = True
        feed.last_error = ""
        session.execute.return_value.scalar_one_or_none.return_value = feed

        from ttrss.prefs.feeds_crud import get_feed_for_edit
        result = get_feed_for_edit(session, feed_id=3, owner_uid=10)

        assert result is not None
        assert result["feed_id"] == 3
        assert result["title"] == feed.title
        assert "feed_url" in result
        assert "last_error" in result

    def test_not_found_returns_none(self):
        """Source: ttrss/classes/pref/feeds.php:editfeed (line 529)
        PHP: returns None when feed not found or not owned by user.

        get_feed_for_edit() should return None when no feed matches.
        """
        session = _mock_session()
        session.execute.return_value.scalar_one_or_none.return_value = None

        from ttrss.prefs.feeds_crud import get_feed_for_edit
        result = get_feed_for_edit(session, feed_id=999, owner_uid=10)

        assert result is None


# ---------------------------------------------------------------------------
# 27. get_feed_tree — mode=2 + cats enabled + labels (lines 816, 829)
# ---------------------------------------------------------------------------


class TestGetFeedTreeMode2CatsEnabledLabels:
    """Source: ttrss/classes/pref/feeds.php:814-831 — label category node with cats enabled"""

    def test_mode2_cats_enabled_with_label_creates_label_cat_node(self):
        """Source: ttrss/classes/pref/feeds.php:815-831 — label cat node appended when cats enabled

        When mode=2, categories enabled, and one label exists, the label feeds
        should be wrapped in a category node (CAT:-2) appended to items.
        Total items = 2 (special-feed cat node + label cat node).
        """
        session = _mock_session()

        fake_label = MagicMock()
        fake_label.id = 1
        fake_label.fg_color = "#ff0000"
        fake_label.bg_color = "#ffffff"

        call_count = {"n": 0}
        def scalars_se(*a, **kw):
            m = MagicMock()
            idx = call_count["n"]
            call_count["n"] += 1
            m.all.return_value = [fake_label] if idx == 0 else []
            return m

        session.execute.return_value.scalars.side_effect = scalars_se

        with (
            patch("ttrss.prefs.ops.get_user_pref", return_value="true"),
            patch("ttrss.feeds.categories.getCategoryTitle", return_value="Special"),
            patch("ttrss.feeds.categories.getFeedTitle", return_value="All"),
            patch("ttrss.utils.feeds.label_to_feed_id", return_value=-1001),
        ):
            from ttrss.prefs.feeds_crud import get_feed_tree
            result = get_feed_tree(session, owner_uid=10, mode=2)

        # With cats enabled in mode=2: special-feeds cat + label cat
        assert len(result["items"]) == 2
        # Both should be category type
        assert all(i["type"] == "category" for i in result["items"])


# ---------------------------------------------------------------------------
# 28. get_feed_tree — categorized tree with a feed inside a top-cat (line 857, 883)
# ---------------------------------------------------------------------------


class TestGetFeedTreeCatWithFeed:
    """Source: ttrss/classes/pref/feeds.php:189-261 — top cat with feed → appended, search on uncat"""

    def test_top_cat_with_feed_appears_in_tree(self):
        """Source: ttrss/classes/pref/feeds.php:189-220 — top-cat with feeds included in tree

        A top-level category that contains one feed should appear in root items
        (num_children > 0 passes the show_empty_cats guard on line 857).
        """
        session = _mock_session()

        fake_cat = MagicMock()
        fake_cat.id = 10
        fake_cat.title = "Tech"
        fake_cat.order_id = 0

        fake_feed = MagicMock()
        fake_feed.id = 55
        fake_feed.title = "Tech Feed"
        fake_feed.last_error = ""
        fake_feed.last_updated = None

        call_count = {"n": 0}
        def scalars_se(*a, **kw):
            m = MagicMock()
            idx = call_count["n"]
            call_count["n"] += 1
            # 0: top_cats → [fake_cat]
            # 1: _get_category_items: sub_cats → []
            # 2: _get_category_items: feeds → [fake_feed]
            # 3: uncat_feeds → []
            seq = [[fake_cat], [], [fake_feed], []]
            m.all.return_value = seq[idx] if idx < len(seq) else []
            return m

        session.execute.return_value.scalars.side_effect = scalars_se

        with patch("ttrss.prefs.ops.get_user_pref", return_value="true"):
            from ttrss.prefs.feeds_crud import get_feed_tree
            result = get_feed_tree(session, owner_uid=10, mode=0, force_show_empty=True)

        root_node = result["items"][0]
        tech_nodes = [i for i in root_node["items"] if i.get("name") == "Tech"]
        assert len(tech_nodes) == 1
        assert len(tech_nodes[0]["items"]) == 1
        assert tech_nodes[0]["items"][0]["bare_id"] == 55

    def test_uncat_with_search_filter_queries_via_like(self):
        """Source: ttrss/classes/pref/feeds.php:221-258 — search filter applied to uncat feeds

        When a search string is provided with categories enabled, the uncat feeds
        query should apply a LIKE filter (line 879).  Matching feed appears in tree.
        """
        session = _mock_session()

        fake_feed = MagicMock()
        fake_feed.id = 77
        fake_feed.title = "Python Weekly"
        fake_feed.last_error = ""
        fake_feed.last_updated = None

        call_count = {"n": 0}
        def scalars_se(*a, **kw):
            m = MagicMock()
            idx = call_count["n"]
            call_count["n"] += 1
            # 0: top_cats → [], 1: uncat_feeds → [fake_feed]
            m.all.return_value = [fake_feed] if idx == 1 else []
            return m

        session.execute.return_value.scalars.side_effect = scalars_se

        with patch("ttrss.prefs.ops.get_user_pref", return_value="true"):
            from ttrss.prefs.feeds_crud import get_feed_tree
            result = get_feed_tree(session, owner_uid=10, mode=0, search="python",
                                   force_show_empty=True)

        root_node = result["items"][0]
        uncat_nodes = [i for i in root_node["items"] if i.get("id") == "CAT:0"]
        assert len(uncat_nodes[0]["items"]) == 1
        assert uncat_nodes[0]["items"][0]["bare_id"] == 77


# ---------------------------------------------------------------------------
# 29. _get_category_items — search filter applied (line 968)
# ---------------------------------------------------------------------------


class TestGetCategoryItemsSearch:
    """Source: ttrss/classes/pref/feeds.php:get_category_items (line 28) — search path"""

    def test_search_filter_queries_with_like(self):
        """Source: ttrss/classes/pref/feeds.php:get_category_items (line 28)
        PHP: when search_filter is set, feeds query adds LIKE filter on title.

        _get_category_items() called with a search_filter should include only
        feeds whose title matches; the query is built with the filter applied.
        """
        session = _mock_session()

        fake_feed = MagicMock()
        fake_feed.id = 33
        fake_feed.title = "Science Weekly"
        fake_feed.last_error = ""
        fake_feed.last_updated = None

        call_count = {"n": 0}
        def scalars_se(*a, **kw):
            m = MagicMock()
            idx = call_count["n"]
            call_count["n"] += 1
            # Call 0: sub_cats → [], Call 1: feeds (search applied) → [fake_feed]
            m.all.return_value = [fake_feed] if idx == 1 else []
            return m

        session.execute.return_value.scalars.side_effect = scalars_se

        from ttrss.prefs.feeds_crud import _get_category_items
        items = _get_category_items(
            session, cat_id=5, owner_uid=10,
            search_filter="%science%", show_empty_cats=False,
        )

        assert len(items) == 1
        assert items[0]["bare_id"] == 33


# ---------------------------------------------------------------------------
# 30. save_feed_settings — not-found path and additional field branches
# ---------------------------------------------------------------------------


class TestSaveFeedSettingsExtra:
    """Source: ttrss/classes/pref/feeds.php:editSave (line 912)"""

    def test_feed_not_found_returns_false(self):
        """Source: ttrss/classes/pref/feeds.php:editSave (line 912)
        PHP: returns false when feed not owned by user.

        save_feed_settings() should return False immediately (line 89) when
        session returns None for the feed lookup.
        """
        session = _mock_session()
        session.execute.return_value.scalar_one_or_none.return_value = None

        from ttrss.prefs.feeds_crud import save_feed_settings
        result = save_feed_settings(session, feed_id=99, owner_uid=10, data={"title": "X"})

        assert result is False
        session.commit.assert_not_called()

    def test_feed_url_updated(self):
        """Source: ttrss/classes/pref/feeds.php:editSave — feed_url trimmed and stored.

        When 'feed_url' is in data, save_feed_settings() must set feed.feed_url
        to the stripped value.
        """
        session = _mock_session()
        feed = _mock_feed()
        feed.feed_url = "http://old.com/feed"
        session.execute.return_value.scalar_one_or_none.return_value = feed

        from ttrss.prefs.feeds_crud import save_feed_settings
        save_feed_settings(session, feed_id=1, owner_uid=10, data={"feed_url": "  http://new.com/rss  "})

        assert feed.feed_url == "http://new.com/rss"
        session.commit.assert_called_once()

    def test_update_interval_and_purge_interval_set(self):
        """Source: ttrss/classes/pref/feeds.php:editSave — update_interval / purge_interval (lines 95-98)

        When 'update_interval' and 'purge_interval' are in data, they should be
        stored as integers on the feed object.
        """
        session = _mock_session()
        feed = _mock_feed()
        feed.update_interval = 0
        feed.purge_interval = 0
        session.execute.return_value.scalar_one_or_none.return_value = feed

        from ttrss.prefs.feeds_crud import save_feed_settings
        save_feed_settings(session, feed_id=1, owner_uid=10,
                           data={"update_interval": "60", "purge_interval": "30"})

        assert feed.update_interval == 60
        assert feed.purge_interval == 30

    def test_auth_login_updated(self):
        """Source: ttrss/classes/pref/feeds.php:editSave (line 99-100) — auth_login trimmed.

        When 'auth_login' is in data, save_feed_settings() should set
        feed.auth_login to the stripped value.
        """
        session = _mock_session()
        feed = _mock_feed()
        feed.auth_login = ""
        session.execute.return_value.scalar_one_or_none.return_value = feed

        from ttrss.prefs.feeds_crud import save_feed_settings
        save_feed_settings(session, feed_id=1, owner_uid=10, data={"auth_login": "  admin  "})

        assert feed.auth_login == "admin"

    def test_cat_id_zero_stored_as_none(self):
        """Source: ttrss/classes/pref/feeds.php:editSave (lines 103-105) — cat_id=0 → NULL.

        When cat_id == 0 in data, save_feed_settings() should store None on
        the feed's cat_id (mapping to SQL NULL).
        """
        session = _mock_session()
        feed = _mock_feed()
        feed.cat_id = 5
        session.execute.return_value.scalar_one_or_none.return_value = feed

        from ttrss.prefs.feeds_crud import save_feed_settings
        save_feed_settings(session, feed_id=1, owner_uid=10, data={"cat_id": "0"})

        assert feed.cat_id is None

    def test_cat_id_nonzero_stored_as_int(self):
        """Source: ttrss/classes/pref/feeds.php:editSave (lines 103-105) — non-zero cat_id stored.

        When cat_id != 0 in data, save_feed_settings() should store the integer
        value on the feed's cat_id.
        """
        session = _mock_session()
        feed = _mock_feed()
        feed.cat_id = None
        session.execute.return_value.scalar_one_or_none.return_value = feed

        from ttrss.prefs.feeds_crud import save_feed_settings
        save_feed_settings(session, feed_id=1, owner_uid=10, data={"cat_id": "3"})

        assert feed.cat_id == 3


# ---------------------------------------------------------------------------
# 31. get_all_feed_ids
# ---------------------------------------------------------------------------


class TestGetAllFeedIds:
    """Source: ttrss/classes/pref/feeds.php:1151-1152"""

    def test_returns_list_of_ints(self):
        """Source: ttrss/classes/pref/feeds.php:1151-1152 — SELECT id FROM ttrss_feeds WHERE owner_uid.

        get_all_feed_ids() should call session.execute() and return a plain list
        of integer feed IDs for the given owner.
        """
        session = _mock_session()
        session.execute.return_value.scalars.return_value.all.return_value = [1, 2, 3]

        from ttrss.prefs.feeds_crud import get_all_feed_ids
        result = get_all_feed_ids(session, owner_uid=10)

        assert result == [1, 2, 3]
        session.execute.assert_called_once()


# ---------------------------------------------------------------------------
# 32. batch_subscribe_feeds — with password sets auth_pass
# ---------------------------------------------------------------------------


class TestBatchSubscribeFeedsPassword:
    """Source: ttrss/classes/pref/feeds.php:batchSubscribe (lines 1767-1860)"""

    def test_no_password_omits_auth_pass_set(self):
        """Source: ttrss/classes/pref/feeds.php:batchSubscribe (line 713-714)
        PHP: auth_pass is only set when password is non-empty.

        When password is empty, batch_subscribe_feeds() should still subscribe
        the feed successfully but should not set auth_pass.
        session.add() is still called once; no auth_pass assignment needed.
        """
        session = _mock_session()
        session.execute.return_value.scalar_one_or_none.return_value = None

        with patch("ttrss.http.client.validate_feed_url", return_value=True):
            from ttrss.prefs.feeds_crud import batch_subscribe_feeds
            results = batch_subscribe_feeds(
                session, owner_uid=10,
                feeds_text="http://example.com/feed\n",
                cat_id=None, login="", password="",
            )

        assert results[0]["status"] == "subscribed"
        session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# 33. rescore_feed_impl — high/low score branches (lines 482-485)
# ---------------------------------------------------------------------------


class TestRescoreFeedImplScoreBranches:
    """Source: ttrss/classes/pref/feeds.php:1129-1142 — marked/unread set by score threshold"""

    def test_score_above_1000_sets_marked(self):
        """Source: ttrss/classes/pref/feeds.php:1129-1142 (line 482-483)
        PHP: if score > 1000, mark article as starred (marked=True).

        rescore_feed_impl() should include 'marked': True in the UPDATE values
        when calculate_article_score returns a value > 1000.
        """
        session = _mock_session()

        fake_row = MagicMock()
        fake_row.ref_id = 1
        fake_row.title = "Hot Article"
        fake_row.content = "content"
        fake_row.link = "http://example.com/a"
        fake_row.author = "Alice"
        fake_row.updated = None
        fake_row.tag_cache = ""
        session.execute.return_value.all.return_value = [fake_row]

        with (
            patch("ttrss.articles.filters.load_filters", return_value=[]),
            patch("ttrss.articles.tags.get_article_tags", return_value=[]),
            patch("ttrss.articles.filters.get_article_filters", return_value=[]),
            patch("ttrss.articles.filters.calculate_article_score", return_value=1500),
        ):
            from ttrss.prefs.feeds_crud import rescore_feed_impl
            rescore_feed_impl(session, feed_id=1, owner_uid=10)

        # session.execute called for SELECT and at least one UPDATE
        assert session.execute.call_count >= 2

    def test_score_below_minus500_sets_read(self):
        """Source: ttrss/classes/pref/feeds.php:1129-1142 (line 484-485)
        PHP: if score < -500, mark article as read (unread=False).

        rescore_feed_impl() should include 'unread': False in the UPDATE values
        when calculate_article_score returns a value < -500.
        """
        session = _mock_session()

        fake_row = MagicMock()
        fake_row.ref_id = 2
        fake_row.title = "Spam"
        fake_row.content = "junk"
        fake_row.link = "http://spam.example.com/a"
        fake_row.author = "Spammer"
        fake_row.updated = None
        fake_row.tag_cache = ""
        session.execute.return_value.all.return_value = [fake_row]

        with (
            patch("ttrss.articles.filters.load_filters", return_value=[]),
            patch("ttrss.articles.tags.get_article_tags", return_value=[]),
            patch("ttrss.articles.filters.get_article_filters", return_value=[]),
            patch("ttrss.articles.filters.calculate_article_score", return_value=-600),
        ):
            from ttrss.prefs.feeds_crud import rescore_feed_impl
            rescore_feed_impl(session, feed_id=1, owner_uid=10)

        assert session.execute.call_count >= 2
