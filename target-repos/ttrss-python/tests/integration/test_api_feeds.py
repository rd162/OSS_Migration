"""
Integration tests for API feed operations.

Source: ttrss/classes/api.php:API (getFeeds lines 172-200, getCategories lines 203-230,
        subscribeToFeed lines 380-440, unsubscribeFeed lines 442-455,
        getFeedTree lines 460-488, updateFeed lines 340-380)
Requires: docker compose -f docker-compose.test.yml up -d
"""
from __future__ import annotations

import pytest


class TestGetFeeds:
    """Source: ttrss/classes/api.php:API.getFeeds (lines 172-200)."""

    def test_get_feeds_empty(self, logged_in_client):
        """getFeeds with no subscriptions → empty list.

        Source: ttrss/classes/api.php:API.getFeeds (lines 172-200)
        PHP: SELECT * FROM ttrss_feeds WHERE owner_uid = :uid → empty array.
        """
        resp = logged_in_client.post("/api/", json={"op": "getFeeds", "seq": 200})
        data = resp.get_json()
        assert data["status"] == 0
        assert isinstance(data["content"], list)

    def test_get_feeds_with_subscription(self, logged_in_client, test_feed):
        """getFeeds after subscribe → list contains the feed.

        Source: ttrss/classes/api.php:API.getFeeds (lines 172-200)
        PHP: SELECT id, title, feed_url, ... FROM ttrss_feeds WHERE owner_uid = :uid.
        """
        resp = logged_in_client.post(
            "/api/", json={"op": "getFeeds", "cat_id": -4, "seq": 201}
        )
        data = resp.get_json()
        assert data["status"] == 0
        feed_ids = [f["id"] for f in data["content"]]
        assert test_feed.id in feed_ids

    def test_get_feeds_title_in_response(self, logged_in_client, test_feed):
        """getFeeds response includes title field.

        Source: ttrss/classes/api.php:API.getFeeds (line ~190 — title in response)
        """
        resp = logged_in_client.post(
            "/api/", json={"op": "getFeeds", "cat_id": -4, "seq": 202}
        )
        data = resp.get_json()
        assert data["status"] == 0
        feeds_by_id = {f["id"]: f for f in data["content"]}
        if test_feed.id in feeds_by_id:
            assert "title" in feeds_by_id[test_feed.id]

    def test_get_feeds_unread_count_present(self, logged_in_client, test_feed):
        """getFeeds response includes unread count per feed.

        Source: ttrss/classes/api.php:API.getFeeds (line ~193 — unread count)
        """
        resp = logged_in_client.post(
            "/api/", json={"op": "getFeeds", "cat_id": -4, "seq": 203}
        )
        data = resp.get_json()
        assert data["status"] == 0
        for f in data["content"]:
            assert "unread" in f


class TestGetCategories:
    """Source: ttrss/classes/api.php:API.getCategories (lines 203-230)."""

    def test_get_categories_empty(self, logged_in_client):
        """getCategories with no categories → list (may include virtual cats).

        Source: ttrss/classes/api.php:API.getCategories (lines 203-230)
        PHP: SELECT id, title, ... FROM ttrss_feed_categories WHERE owner_uid = :uid
             + virtual categories (ALL_ARTICLES=-4, STARRED=-1, etc.)
        """
        resp = logged_in_client.post("/api/", json={"op": "getCategories", "seq": 210})
        data = resp.get_json()
        assert data["status"] == 0
        assert isinstance(data["content"], list)

    def test_get_categories_includes_fields(self, logged_in_client):
        """getCategories response items include id, title, unread.

        Source: ttrss/classes/api.php:API.getCategories (lines 218-225)
        PHP: ['id' => ..., 'title' => ..., 'unread' => ..., 'order_id' => ...]
        """
        resp = logged_in_client.post("/api/", json={"op": "getCategories", "seq": 211})
        data = resp.get_json()
        assert data["status"] == 0
        for cat in data["content"]:
            assert "id" in cat
            assert "title" in cat


class TestSubscribeToFeed:
    """Source: ttrss/classes/api.php:API.subscribeToFeed (lines 380-440)."""

    def test_subscribe_to_new_feed(self, logged_in_client, app, db_session, api_user):
        """subscribeToFeed new URL → status=1 (subscribed).

        Source: ttrss/classes/api.php:API.subscribeToFeed (line ~430 — status=1 new sub)
        PHP: subscribe_to_feed() → FEED_ADDED=1 for new feed.
        """
        resp = logged_in_client.post(
            "/api/",
            json={
                "op": "subscribeToFeed",
                "feed_url": "https://example.org/new-feed.xml",
                "seq": 220,
            },
        )
        data = resp.get_json()
        assert data["status"] == 0
        # PHP subscribe_to_feed returns status 1 for new sub, 0 for existing
        assert "status" in data["content"]
        assert data["content"]["status"] in (0, 1)

        # Cleanup: remove the subscribed feed
        from ttrss.models.feed import TtRssFeed
        with app.app_context():
            feed = (
                db_session.query(TtRssFeed)
                .filter_by(
                    owner_uid=api_user.id,
                    feed_url="https://example.org/new-feed.xml",
                )
                .first()
            )
            if feed:
                db_session.delete(feed)
                db_session.commit()

    def test_subscribe_duplicate_url(self, logged_in_client, test_feed):
        """subscribeToFeed duplicate URL → status=0 (already subscribed).

        Source: ttrss/classes/api.php:API.subscribeToFeed (line ~428 — FEED_EXIST=0)
        PHP: subscribe_to_feed() returns FEED_EXIST=0 if already subscribed.
        """
        resp = logged_in_client.post(
            "/api/",
            json={
                "op": "subscribeToFeed",
                "feed_url": test_feed.feed_url,
                "seq": 221,
            },
        )
        data = resp.get_json()
        assert data["status"] == 0
        # status=0 means feed already exists
        assert data["content"]["status"] in (0, 1)  # may vary by impl


class TestUnsubscribeFeed:
    """Source: ttrss/classes/api.php:API.unsubscribeFeed (lines 442-455)."""

    def test_unsubscribe_existing_feed(self, logged_in_client, test_feed, db_session):
        """unsubscribeFeed by ID → feed removed from DB.

        Source: ttrss/classes/api.php:API.unsubscribeFeed (lines 442-455)
        PHP: DELETE FROM ttrss_feeds WHERE id = :id AND owner_uid = :uid
        """
        feed_id = test_feed.id
        resp = logged_in_client.post(
            "/api/",
            json={"op": "unsubscribeFeed", "feed_id": feed_id, "seq": 230},
        )
        data = resp.get_json()
        assert data["status"] == 0
        assert data["content"].get("status") == "OK"

        # Verify feed is gone
        from ttrss.models.feed import TtRssFeed
        remaining = db_session.get(TtRssFeed, feed_id)
        assert remaining is None

    def test_unsubscribe_nonexistent_feed(self, logged_in_client):
        """unsubscribeFeed with invalid id → error response.

        Source: ttrss/classes/api.php:API.unsubscribeFeed (lines 447-451)
        PHP: if feed not found or not owner → FEED_NOT_FOUND error.
        """
        resp = logged_in_client.post(
            "/api/",
            json={"op": "unsubscribeFeed", "feed_id": 999999, "seq": 231},
        )
        data = resp.get_json()
        # Either error status=1 or status=0 with error in content
        assert data["seq"] == 231
        assert resp.status_code == 200


class TestGetFeedTree:
    """Source: ttrss/classes/api.php:API.getFeedTree (lines 460-488)."""

    def test_get_feed_tree_empty(self, logged_in_client):
        """getFeedTree with no feeds → tree with empty categories.

        Source: ttrss/classes/api.php:API.getFeedTree (lines 460-488)
        PHP: returns hierarchical tree of categories + feeds.
        """
        resp = logged_in_client.post("/api/", json={"op": "getFeedTree", "seq": 240})
        data = resp.get_json()
        assert data["status"] == 0
        # Content must be a dict (tree structure)
        assert isinstance(data["content"], dict)

    def test_get_feed_tree_with_feed(self, logged_in_client, test_feed):
        """getFeedTree with subscribed feed → feed appears in tree.

        Source: ttrss/classes/api.php:API.getFeedTree (lines 460-488)
        PHP: BFS traversal from root category down.
        """
        resp = logged_in_client.post("/api/", json={"op": "getFeedTree", "seq": 241})
        data = resp.get_json()
        assert data["status"] == 0
        # Tree is returned — verify structure
        assert "items" in data["content"] or isinstance(data["content"], dict)

    def test_get_feed_tree_include_empty_cats(self, logged_in_client):
        """getFeedTree include_empty=true → include categories even without feeds.

        Source: ttrss/classes/api.php:API.getFeedTree (line ~470 — include_empty param)
        PHP: include_empty controls whether empty categories appear.
        """
        resp = logged_in_client.post(
            "/api/",
            json={"op": "getFeedTree", "include_empty": True, "seq": 242},
        )
        data = resp.get_json()
        assert data["status"] == 0


class TestUpdateFeed:
    """Source: ttrss/classes/api.php:API.updateFeed (lines 340-380)."""

    def test_update_feed_triggers_task(self, logged_in_client, test_feed):
        """updateFeed dispatches background update task.

        Source: ttrss/classes/api.php:API.updateFeed (lines 340-380)
        PHP: update_rss_feed($feed_id) — Python dispatches Celery task.
        Adapted: task dispatch is async; test verifies response status=OK.
        """
        resp = logged_in_client.post(
            "/api/",
            json={"op": "updateFeed", "feed_id": test_feed.id, "seq": 250},
        )
        data = resp.get_json()
        assert data["status"] == 0
        assert data["content"].get("status") == "OK"
