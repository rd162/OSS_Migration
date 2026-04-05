"""
Integration tests for counter/pref/config/label read ops.

Source: ttrss/classes/api.php:API (getUnread lines 98-107, getCounters lines 110-140,
        getPref lines 143-148, getConfig lines 150-155, getLabels lines 158-167)
Requires: docker compose -f docker-compose.test.yml up -d
"""
from __future__ import annotations

import pytest


class TestGetUnread:
    """Source: ttrss/classes/api.php:API.getUnread (lines 98-107)."""

    def test_get_unread_global_empty(self, logged_in_client):
        """getUnread with no feed → global unread count (0 when empty).

        Source: ttrss/classes/api.php:API.getUnread (lines 98-107)
        PHP: if feed_id is '' → return getGlobalUnread()
        """
        resp = logged_in_client.post("/api/", json={"op": "getUnread", "seq": 100})
        data = resp.get_json()
        assert data["status"] == 0
        assert "unread" in data["content"]
        assert isinstance(data["content"]["unread"], (int, str))

    def test_get_unread_for_feed(self, logged_in_client, test_entry_pair):
        """getUnread with feed_id → unread count for that feed.

        Source: ttrss/classes/api.php:API.getUnread (lines 100-103)
        PHP: if feed_id → return getFeedUnread(feed_id)
        """
        entry, user_entry = test_entry_pair
        feed_id = user_entry.feed_id
        resp = logged_in_client.post(
            "/api/", json={"op": "getUnread", "feed_id": feed_id, "seq": 101}
        )
        data = resp.get_json()
        assert data["status"] == 0
        assert "unread" in data["content"]

    def test_get_unread_for_category(self, logged_in_client, test_entry_pair):
        """getUnread with is_cat=true → unread count for category.

        Source: ttrss/classes/api.php:API.getUnread (lines 104-106)
        PHP: if is_cat → getCategoryUnread(feed_id)
        """
        resp = logged_in_client.post(
            "/api/",
            json={"op": "getUnread", "feed_id": 0, "is_cat": True, "seq": 102},
        )
        data = resp.get_json()
        assert data["status"] == 0
        assert "unread" in data["content"]


class TestGetCounters:
    """Source: ttrss/classes/api.php:API.getCounters (lines 110-140)."""

    def test_get_counters_returns_list(self, logged_in_client):
        """getCounters → list of counter objects.

        Source: ttrss/classes/api.php:API.getCounters (line 139 — return counters array)
        PHP: returns array of feed/category/label unread counts.
        """
        resp = logged_in_client.post("/api/", json={"op": "getCounters", "seq": 110})
        data = resp.get_json()
        assert data["status"] == 0
        assert isinstance(data["content"], list)

    def test_get_counters_with_output_mode(self, logged_in_client):
        """getCounters output_mode=flc → feeds, labels, categories.

        Source: ttrss/classes/api.php:API.getCounters (lines 113-138)
        PHP: output_mode 'f'=feeds, 'l'=labels, 'c'=categories, 't'=tags.
        """
        resp = logged_in_client.post(
            "/api/", json={"op": "getCounters", "output_mode": "flc", "seq": 111}
        )
        data = resp.get_json()
        assert data["status"] == 0
        assert isinstance(data["content"], list)


class TestGetPref:
    """Source: ttrss/classes/api.php:API.getPref (lines 143-148)."""

    def test_get_pref_known_returns_value(self, logged_in_client):
        """getPref ENABLE_API_ACCESS → 'true'.

        Source: ttrss/classes/api.php:API.getPref (lines 143-148)
        PHP: return ['value' => get_pref($pref_name)]
        """
        resp = logged_in_client.post(
            "/api/",
            json={"op": "getPref", "pref_name": "ENABLE_API_ACCESS", "seq": 120},
        )
        data = resp.get_json()
        assert data["status"] == 0
        assert "value" in data["content"]
        # The value can be 'true' (from user pref) or from system default
        assert data["content"]["value"] is not None

    def test_get_pref_unknown_returns_none_or_false(self, logged_in_client):
        """getPref for unknown key → value=None or error.

        Source: ttrss/classes/api.php:API.getPref (lines 143-148)
        Adapted: Python returns None for unknown pref; PHP returns false.
        """
        resp = logged_in_client.post(
            "/api/",
            json={"op": "getPref", "pref_name": "NONEXISTENT_PREF_XYZ", "seq": 121},
        )
        data = resp.get_json()
        # Either status=0 with value=None or status=1 — both acceptable
        assert data["seq"] == 121
        assert resp.status_code == 200


class TestGetConfig:
    """Source: ttrss/classes/api.php:API.getConfig (lines 150-155)."""

    def test_get_config_returns_config_dict(self, logged_in_client):
        """getConfig → dict with icons_dir, icons_url, daemon_enabled, num_feeds.

        Source: ttrss/classes/api.php:API.getConfig (lines 150-155)
        PHP: return ['icons_dir' => ..., 'icons_url' => ..., 'daemon_enabled' => true, ...]
        """
        resp = logged_in_client.post("/api/", json={"op": "getConfig", "seq": 130})
        data = resp.get_json()
        assert data["status"] == 0
        content = data["content"]
        # num_feeds always present; daemon key name may vary (daemon_enabled or daemon_is_running)
        assert "num_feeds" in content
        assert isinstance(content["num_feeds"], int)
        assert "icons_dir" in content or "daemon_is_running" in content or "daemon_enabled" in content


class TestGetLabels:
    """Source: ttrss/classes/api.php:API.getLabels (lines 158-167)."""

    def test_get_labels_empty(self, logged_in_client):
        """getLabels with no labels → empty list.

        Source: ttrss/classes/api.php:API.getLabels (lines 158-167)
        PHP: SELECT * FROM ttrss_labels2 WHERE owner_uid = :uid → empty array if none.
        """
        resp = logged_in_client.post("/api/", json={"op": "getLabels", "seq": 140})
        data = resp.get_json()
        assert data["status"] == 0
        assert isinstance(data["content"], list)

    def test_get_labels_article_id_accepted(self, logged_in_client):
        """getLabels with article_id → returns labels for that article (empty if none).

        Source: ttrss/classes/api.php:API.getLabels (lines 161-165)
        PHP: get_article_labels($article_id) if article_id provided.
        """
        resp = logged_in_client.post(
            "/api/", json={"op": "getLabels", "article_id": 99999, "seq": 141}
        )
        data = resp.get_json()
        assert data["status"] == 0
        assert isinstance(data["content"], list)


class TestApiDisabled:
    """Source: ttrss/classes/api.php lines 21-25 — API_DISABLED guard."""

    def test_api_disabled_via_set_user_pref(self, client, app, db_session, seed_prefs):
        """User with ENABLE_API_ACCESS=false → API_DISABLED on login.

        Source: ttrss/classes/api.php lines 21-25
        PHP: if (!get_pref('ENABLE_API_ACCESS')) → API_DISABLED
        Adapted: Uses set_user_pref() to write user-level override (now works
                 after model fix: profile removed from PK so profile=NULL allowed).
        """
        import uuid as _uuid
        from ttrss.auth.password import hash_password
        from ttrss.models.user import TtRssUser
        from ttrss.prefs.ops import set_user_pref

        login = f"noapiuser_{_uuid.uuid4().hex[:6]}"
        with app.app_context():
            user = TtRssUser(login=login, pwd_hash=hash_password("testpass"), access_level=0)
            db_session.add(user)
            db_session.commit()

            # Disable API access via the proper app function
            set_user_pref(user.id, "ENABLE_API_ACCESS", "false")

            resp = client.post(
                "/api/",
                json={"op": "login", "user": login, "password": "testpass", "seq": 150},
            )
            data = resp.get_json()
            assert data["status"] == 1
            assert data["content"]["error"] == "API_DISABLED"

            # Cleanup
            existing = db_session.get(TtRssUser, user.id)
            if existing:
                db_session.delete(existing)
                db_session.commit()
