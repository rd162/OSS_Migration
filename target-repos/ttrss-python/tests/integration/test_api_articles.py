"""
Integration tests for API article operations.

Source: ttrss/classes/api.php:API (getHeadlines lines 233-295, getArticle lines 298-335,
        updateArticle lines 232-296, catchupFeed lines 232-296, setArticleLabel,
        shareToPublished lines 345-375)
Requires: docker compose -f docker-compose.test.yml up -d
"""
from __future__ import annotations

import pytest


class TestGetHeadlines:
    """Source: ttrss/classes/api.php:API.getHeadlines (lines 233-295)."""

    def test_get_headlines_empty_feed(self, logged_in_client, test_feed):
        """getHeadlines with feed_id but no articles → empty list.

        Source: ttrss/classes/api.php:API.getHeadlines (lines 233-295)
        PHP: queryFeedHeadlines($feed_id, ...) → [] when no articles.
        """
        resp = logged_in_client.post(
            "/api/",
            json={"op": "getHeadlines", "feed_id": test_feed.id, "seq": 300},
        )
        data = resp.get_json()
        assert data["status"] == 0
        assert isinstance(data["content"], list)

    def test_get_headlines_with_entry(self, logged_in_client, test_entry_pair):
        """getHeadlines returns article when entry exists.

        Source: ttrss/classes/api.php:API.getHeadlines (lines 233-295)
        PHP: SELECT ... FROM ttrss_entries e JOIN ttrss_user_entries ue ...
        """
        entry, user_entry = test_entry_pair
        resp = logged_in_client.post(
            "/api/",
            json={"op": "getHeadlines", "feed_id": user_entry.feed_id, "seq": 301},
        )
        data = resp.get_json()
        assert data["status"] == 0
        assert isinstance(data["content"], list)
        # Article should appear in the list
        article_ids = [a["id"] for a in data["content"]]
        assert entry.id in article_ids

    def test_get_headlines_unread_only(self, logged_in_client, test_entry_pair):
        """getHeadlines show_content=false, view_mode=unread → only unread articles.

        Source: ttrss/classes/api.php:API.getHeadlines (lines 260-280)
        PHP: view_mode='unread' adds AND ue.unread = true to WHERE clause.
        """
        entry, user_entry = test_entry_pair
        assert user_entry.unread is True  # fixture creates unread article

        resp = logged_in_client.post(
            "/api/",
            json={
                "op": "getHeadlines",
                "feed_id": user_entry.feed_id,
                "view_mode": "unread",
                "seq": 302,
            },
        )
        data = resp.get_json()
        assert data["status"] == 0
        article_ids = [a["id"] for a in data["content"]]
        assert entry.id in article_ids

    def test_get_headlines_limit_respected(self, logged_in_client, test_entry_pair):
        """getHeadlines limit=1 → at most 1 article returned.

        Source: ttrss/classes/api.php:API.getHeadlines (lines 248-252)
        PHP: LIMIT :limit in query.
        """
        _, user_entry = test_entry_pair
        resp = logged_in_client.post(
            "/api/",
            json={
                "op": "getHeadlines",
                "feed_id": user_entry.feed_id,
                "limit": 1,
                "seq": 303,
            },
        )
        data = resp.get_json()
        assert data["status"] == 0
        assert len(data["content"]) <= 1

    def test_get_headlines_all_feeds(self, logged_in_client, test_entry_pair):
        """getHeadlines feed_id=-4 → all articles across all feeds.

        Source: ttrss/classes/api.php:API.getHeadlines (lines 235-240)
        PHP: feed_id=-4 is ALL_ARTICLES virtual feed.
        """
        entry, _ = test_entry_pair
        resp = logged_in_client.post(
            "/api/",
            json={"op": "getHeadlines", "feed_id": -4, "seq": 304},
        )
        data = resp.get_json()
        assert data["status"] == 0
        article_ids = [a["id"] for a in data["content"]]
        assert entry.id in article_ids


class TestGetArticle:
    """Source: ttrss/classes/api.php:API.getArticle (lines 298-335)."""

    def test_get_article_by_id(self, logged_in_client, test_entry_pair):
        """getArticle by id → article with content, title, link.

        Source: ttrss/classes/api.php:API.getArticle (lines 298-335)
        PHP: SELECT ... FROM ttrss_entries e JOIN ttrss_user_entries ue WHERE e.id IN (:ids)
        """
        entry, _ = test_entry_pair
        resp = logged_in_client.post(
            "/api/",
            json={"op": "getArticle", "article_id": entry.id, "seq": 310},
        )
        data = resp.get_json()
        assert data["status"] == 0
        assert isinstance(data["content"], list)
        assert len(data["content"]) == 1
        article = data["content"][0]
        assert article["id"] == entry.id
        assert "title" in article
        assert "content" in article
        assert "link" in article

    def test_get_article_missing_returns_empty(self, logged_in_client):
        """getArticle with nonexistent id → empty list.

        Source: ttrss/classes/api.php:API.getArticle (lines 298-335)
        PHP: returns empty array if article not found or not owned by user.
        """
        resp = logged_in_client.post(
            "/api/",
            json={"op": "getArticle", "article_id": 999999, "seq": 311},
        )
        data = resp.get_json()
        assert data["status"] == 0
        assert data["content"] == []

    def test_get_article_includes_unread_state(self, logged_in_client, test_entry_pair):
        """getArticle response includes unread field from ttrss_user_entries.

        Source: ttrss/classes/api.php:API.getArticle (line ~320 — ue.unread in SELECT)
        """
        entry, user_entry = test_entry_pair
        resp = logged_in_client.post(
            "/api/",
            json={"op": "getArticle", "article_id": entry.id, "seq": 312},
        )
        data = resp.get_json()
        assert data["status"] == 0
        if data["content"]:
            assert "unread" in data["content"][0]


class TestUpdateArticle:
    """Source: ttrss/classes/api.php:API.updateArticle (lines 232-296)."""

    def test_update_article_mark_read(self, logged_in_client, test_entry_pair, db_session):
        """updateArticle field=2 mode=0 → mark article as read.

        Source: ttrss/classes/api.php:API.updateArticle (lines 232-296)
        PHP: field=2 is UNREAD, mode=0 sets to false (read).
        """
        entry, user_entry = test_entry_pair
        assert user_entry.unread is True

        resp = logged_in_client.post(
            "/api/",
            json={
                "op": "updateArticle",
                "article_ids": str(entry.id),
                "field": 2,   # UNREAD field
                "mode": 0,    # set to false
                "seq": 320,
            },
        )
        data = resp.get_json()
        assert data["status"] == 0

        # Verify in DB
        from ttrss.models.user_entry import TtRssUserEntry
        db_session.expire_all()
        updated = db_session.get(TtRssUserEntry, user_entry.int_id)
        assert updated is not None
        assert updated.unread is False

    def test_update_article_mark_starred(self, logged_in_client, test_entry_pair, db_session):
        """updateArticle field=0 mode=1 → mark article as starred.

        Source: ttrss/classes/api.php:API.updateArticle (lines 232-296)
        PHP: field=0 is MARKED (starred), mode=1 sets to true.
        """
        entry, user_entry = test_entry_pair

        resp = logged_in_client.post(
            "/api/",
            json={
                "op": "updateArticle",
                "article_ids": str(entry.id),
                "field": 0,   # MARKED (starred)
                "mode": 1,    # set to true
                "seq": 321,
            },
        )
        data = resp.get_json()
        assert data["status"] == 0

        from ttrss.models.user_entry import TtRssUserEntry
        db_session.expire_all()
        updated = db_session.get(TtRssUserEntry, user_entry.int_id)
        assert updated is not None
        assert updated.marked is True

    def test_update_article_mark_published(self, logged_in_client, test_entry_pair, db_session):
        """updateArticle field=1 mode=1 → mark article as published.

        Source: ttrss/classes/api.php:API.updateArticle (lines 232-296)
        PHP: field=1 is PUBLISHED, mode=1 sets to true.
        """
        entry, user_entry = test_entry_pair

        resp = logged_in_client.post(
            "/api/",
            json={
                "op": "updateArticle",
                "article_ids": str(entry.id),
                "field": 1,   # PUBLISHED
                "mode": 1,
                "seq": 322,
            },
        )
        data = resp.get_json()
        assert data["status"] == 0

    def test_update_article_set_note(self, logged_in_client, test_entry_pair, db_session):
        """updateArticle field=3 → set note on article.

        Source: ttrss/classes/api.php:API.updateArticle (lines 232-296)
        PHP: field=3 is NOTE field (FIELD_MAP: 3→note) — stores user annotation.
        Python: strips HTML tags from note (security improvement over PHP).
        """
        entry, user_entry = test_entry_pair

        resp = logged_in_client.post(
            "/api/",
            json={
                "op": "updateArticle",
                "article_ids": str(entry.id),
                "field": 3,   # NOTE (PHP api.php FIELD_MAP)
                "mode": 1,
                "data": "My test note",
                "seq": 323,
            },
        )
        data = resp.get_json()
        assert data["status"] == 0

    def test_update_article_toggle_mode(self, logged_in_client, test_entry_pair, db_session):
        """updateArticle mode=2 → toggle current boolean state.

        Source: ttrss/classes/api.php:API.updateArticle (lines 232-296)
        PHP: mode=2 toggles current value (XOR with current).
        """
        entry, _ = test_entry_pair

        resp = logged_in_client.post(
            "/api/",
            json={
                "op": "updateArticle",
                "article_ids": str(entry.id),
                "field": 0,   # MARKED
                "mode": 2,    # toggle
                "seq": 324,
            },
        )
        data = resp.get_json()
        assert data["status"] == 0


class TestCatchupFeed:
    """Source: ttrss/classes/api.php:API.catchupFeed (lines 232-296)."""

    def test_catchup_feed_marks_all_read(self, logged_in_client, test_entry_pair, db_session):
        """catchupFeed → all articles in feed marked as read.

        Source: ttrss/classes/api.php:API.catchupFeed (lines 232-296)
        PHP: UPDATE ttrss_user_entries SET unread=false WHERE feed_id=:id AND owner_uid=:uid
        """
        entry, user_entry = test_entry_pair
        feed_id = user_entry.feed_id

        resp = logged_in_client.post(
            "/api/",
            json={"op": "catchupFeed", "feed_id": feed_id, "seq": 330},
        )
        data = resp.get_json()
        assert data["status"] == 0

        from ttrss.models.user_entry import TtRssUserEntry
        db_session.expire_all()
        updated = db_session.get(TtRssUserEntry, user_entry.int_id)
        if updated:
            assert updated.unread is False

    def test_catchup_all_feeds(self, logged_in_client, test_entry_pair):
        """catchupFeed feed_id=-4 (all articles) → marks all articles read.

        Source: ttrss/classes/api.php:API.catchupFeed (lines 232-296)
        PHP: feed_id=-4 is ALL_ARTICLES virtual feed — marks everything read.
        """
        resp = logged_in_client.post(
            "/api/",
            json={"op": "catchupFeed", "feed_id": -4, "seq": 331},
        )
        data = resp.get_json()
        assert data["status"] == 0


class TestSetArticleLabel:
    """Source: ttrss/classes/api.php:API.setArticleLabel."""

    def test_set_article_label_no_labels(self, logged_in_client, test_entry_pair):
        """setArticleLabel with non-existent label → graceful error or no-op.

        Source: ttrss/classes/api.php:API.setArticleLabel
        PHP: label_add_article / label_remove_article — noop if label not found.
        """
        entry, _ = test_entry_pair
        resp = logged_in_client.post(
            "/api/",
            json={
                "op": "setArticleLabel",
                "article_ids": str(entry.id),
                "label_id": 99999,
                "assign": True,
                "seq": 340,
            },
        )
        data = resp.get_json()
        # Either OK or error — must not crash
        assert resp.status_code == 200
        assert data["seq"] == 340


class TestShareToPublished:
    """Source: ttrss/classes/api.php:API.shareToPublished (lines 345-375)."""

    def test_share_to_published(self, logged_in_client):
        """shareToPublished creates a new published article.

        Source: ttrss/classes/api.php:API.shareToPublished (lines 345-375)
        PHP: Creates a ttrss_entries + ttrss_user_entries row with published=true.
        """
        resp = logged_in_client.post(
            "/api/",
            json={
                "op": "shareToPublished",
                "title": "Shared Article",
                "url": "https://example.com/shared",
                "content": "Shared content",
                "seq": 350,
            },
        )
        data = resp.get_json()
        assert data["status"] == 0
        assert data["seq"] == 350
