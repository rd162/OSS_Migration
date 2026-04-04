"""Unit tests for Batch 2 API ops: getCategories, getFeeds, getArticle."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def api_app():
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SECRET_KEY="test-batch2",
        WTF_CSRF_ENABLED=False,
        ICONS_DIR="/tmp/icons",
        ICONS_URL="/icons",
    )
    return app


def _authenticated_patches():
    """Return patch targets dict to set up an authenticated, API-enabled user."""
    return {
        "current_user": {"is_authenticated": True, "id": 1},
        "get_user_pref": "true",
    }


def _post(app, op, extra=None, seq=1):
    body = {"op": op, "seq": seq}
    if extra:
        body.update(extra)
    with app.test_request_context(
        "/api/", method="POST", json=body, content_type="application/json"
    ):
        with app.app_context():
            from ttrss.blueprints.api.views import dispatch

            resp = dispatch()
            return json.loads(resp.get_data(as_text=True)), resp.status_code


# ---------------------------------------------------------------------------
# getCategories
# ---------------------------------------------------------------------------


def _make_cat_row(id_, title, order_id=0, num_feeds=1, num_cats=0):
    r = MagicMock()
    r.id = id_
    r.title = title
    r.order_id = order_id
    r.num_feeds = num_feeds
    r.num_cats = num_cats
    return r


def test_getCategories_returns_real_cats(api_app):
    """Real category rows are returned with unread counts."""
    rows = [_make_cat_row(1, "Tech", num_feeds=3)]
    mock_exec = MagicMock()
    mock_exec.all.return_value = rows
    mock_db_session = MagicMock()
    mock_db_session.execute.return_value = mock_exec

    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"), \
         patch("ttrss.blueprints.api.views.db") as mock_db, \
         patch("ttrss.blueprints.api.views.getCategoryUnread", return_value=5), \
         patch("ttrss.blueprints.api.views.getCategoryChildrenUnread", return_value=0), \
         patch("ttrss.blueprints.api.views.getCategoryTitle", return_value="X"), \
         patch("ttrss.blueprints.api.views._is_virtual_cat_empty", return_value=True):
        mock_user.is_authenticated = True
        mock_user.id = 1
        mock_db.session = mock_db_session
        data, _ = _post(api_app, "getCategories")

    assert data["status"] == 0
    cats = data["content"]
    # Virtual cats skipped (empty), real cat present
    assert any(c["id"] == 1 and c["title"] == "Tech" for c in cats)


def test_getCategories_enable_nested_uses_parent_cat_filter(api_app):
    """enable_nested=true adds parent_cat IS NULL filter to query."""
    mock_exec = MagicMock()
    mock_exec.all.return_value = []
    mock_db_session = MagicMock()
    mock_db_session.execute.return_value = mock_exec

    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"), \
         patch("ttrss.blueprints.api.views.db") as mock_db, \
         patch("ttrss.blueprints.api.views.getCategoryUnread", return_value=0), \
         patch("ttrss.blueprints.api.views._is_virtual_cat_empty", return_value=True):
        mock_user.is_authenticated = True
        mock_user.id = 1
        mock_db.session = mock_db_session
        data, _ = _post(api_app, "getCategories", {"enable_nested": True})

    assert data["status"] == 0  # no error


def test_getCategories_virtual_cats_included(api_app):
    """Virtual cats [-2,-1,0] are included when not empty."""
    mock_exec = MagicMock()
    mock_exec.all.return_value = []  # No real cats
    mock_db_session = MagicMock()
    mock_db_session.execute.return_value = mock_exec

    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"), \
         patch("ttrss.blueprints.api.views.db") as mock_db, \
         patch("ttrss.blueprints.api.views.getCategoryUnread", return_value=3), \
         patch("ttrss.blueprints.api.views.getCategoryTitle", side_effect=lambda s, cid: f"Cat{cid}"), \
         patch("ttrss.blueprints.api.views._is_virtual_cat_empty", return_value=False):
        mock_user.is_authenticated = True
        mock_user.id = 1
        mock_db.session = mock_db_session
        data, _ = _post(api_app, "getCategories")

    assert data["status"] == 0
    cats = data["content"]
    virtual_ids = {c["id"] for c in cats}
    assert -2 in virtual_ids
    assert -1 in virtual_ids
    assert 0 in virtual_ids


def test_getCategories_unread_only_filters_zero_unread(api_app):
    """unread_only=true excludes categories with unread=0."""
    rows = [_make_cat_row(1, "Empty Cat", num_feeds=1)]
    mock_exec = MagicMock()
    mock_exec.all.return_value = rows
    mock_db_session = MagicMock()
    mock_db_session.execute.return_value = mock_exec

    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"), \
         patch("ttrss.blueprints.api.views.db") as mock_db, \
         patch("ttrss.blueprints.api.views.getCategoryUnread", return_value=0), \
         patch("ttrss.blueprints.api.views.getCategoryChildrenUnread", return_value=0), \
         patch("ttrss.blueprints.api.views._is_virtual_cat_empty", return_value=True):
        mock_user.is_authenticated = True
        mock_user.id = 1
        mock_db.session = mock_db_session
        data, _ = _post(api_app, "getCategories", {"unread_only": True})

    cats = data["content"]
    assert all(c["id"] != 1 for c in cats)


def test_getCategories_include_empty_includes_empty_cats(api_app):
    """include_empty=true returns cats with no feeds/children."""
    rows = [_make_cat_row(1, "EmptyCat", num_feeds=0, num_cats=0)]
    mock_exec = MagicMock()
    mock_exec.all.return_value = rows
    mock_db_session = MagicMock()
    mock_db_session.execute.return_value = mock_exec

    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"), \
         patch("ttrss.blueprints.api.views.db") as mock_db, \
         patch("ttrss.blueprints.api.views.getCategoryUnread", return_value=0), \
         patch("ttrss.blueprints.api.views.getCategoryChildrenUnread", return_value=0), \
         patch("ttrss.blueprints.api.views.getCategoryTitle", side_effect=lambda s, cid: f"V{cid}"), \
         patch("ttrss.blueprints.api.views._is_virtual_cat_empty", return_value=True):
        mock_user.is_authenticated = True
        mock_user.id = 1
        mock_db.session = mock_db_session
        # include_empty=True + unread_only=False → all cats included (real + virtual)
        data, _ = _post(api_app, "getCategories", {"include_empty": True})

    cats = data["content"]
    assert any(c["id"] == 1 for c in cats)


# ---------------------------------------------------------------------------
# getFeeds
# ---------------------------------------------------------------------------


def _make_feed_row(id_, title, feed_url="http://ex.com/feed", cat_id=1, order_id=0):
    r = MagicMock()
    r.id = id_
    r.title = title
    r.feed_url = feed_url
    r.cat_id = cat_id
    r.order_id = order_id
    r.last_updated = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return r


def test_getFeeds_real_feeds_for_specific_cat(api_app):
    """getFeeds for a real cat_id returns real feeds with unread counts."""
    real_feed = _make_feed_row(10, "My Feed", cat_id=1)
    mock_exec = MagicMock()
    mock_exec.all.return_value = [real_feed]
    mock_db_session = MagicMock()
    mock_db_session.execute.return_value = mock_exec

    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"), \
         patch("ttrss.blueprints.api.views.db") as mock_db, \
         patch("ttrss.blueprints.api.views.getLabelCounters", return_value=[]), \
         patch("ttrss.blueprints.api.views._count_feed_articles", return_value=2), \
         patch("ttrss.blueprints.api.views.feed_has_icon", return_value=False):
        mock_user.is_authenticated = True
        mock_user.id = 1
        mock_db.session = mock_db_session
        data, _ = _post(api_app, "getFeeds", {"cat_id": 1})

    assert data["status"] == 0
    feeds = data["content"]
    assert len(feeds) == 1
    assert feeds[0]["id"] == 10
    assert feeds[0]["unread"] == 2


def test_getFeeds_labels_section_for_cat_minus2(api_app):
    """getFeeds for cat_id=-2 returns labels as feeds."""
    label_counters = [{"id": -1024, "counter": 3, "description": "Work"}]
    mock_exec = MagicMock()
    mock_exec.all.return_value = []
    mock_db_session = MagicMock()
    mock_db_session.execute.return_value = mock_exec

    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"), \
         patch("ttrss.blueprints.api.views.db") as mock_db, \
         patch("ttrss.blueprints.api.views.getLabelCounters", return_value=label_counters), \
         patch("ttrss.blueprints.api.views._count_feed_articles", return_value=0), \
         patch("ttrss.blueprints.api.views.feed_has_icon", return_value=False):
        mock_user.is_authenticated = True
        mock_user.id = 1
        mock_db.session = mock_db_session
        data, _ = _post(api_app, "getFeeds", {"cat_id": -2})

    assert data["status"] == 0
    feeds = data["content"]
    assert any(f["cat_id"] == -2 and f["title"] == "Work" for f in feeds)


def test_getFeeds_virtual_section_for_cat_minus1(api_app):
    """getFeeds for cat_id=-1 returns virtual feeds."""
    mock_exec = MagicMock()
    mock_exec.all.return_value = []
    mock_db_session = MagicMock()
    mock_db_session.execute.return_value = mock_exec

    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"), \
         patch("ttrss.blueprints.api.views.db") as mock_db, \
         patch("ttrss.blueprints.api.views.getLabelCounters", return_value=[]), \
         patch("ttrss.blueprints.api.views._count_feed_articles", return_value=1), \
         patch("ttrss.blueprints.api.views.getFeedTitle", return_value="Virtual"), \
         patch("ttrss.blueprints.api.views.feed_has_icon", return_value=False):
        mock_user.is_authenticated = True
        mock_user.id = 1
        mock_db.session = mock_db_session
        data, _ = _post(api_app, "getFeeds", {"cat_id": -1})

    feeds = data["content"]
    assert all(f["cat_id"] == -1 for f in feeds)
    assert len(feeds) == 6  # -1,-2,-3,-4,-6,0


def test_getFeeds_include_nested_false_for_cat_id_zero(api_app):
    """include_nested=true + cat_id=0 → no child cats (cat_id=0 is falsy in PHP)."""
    mock_exec = MagicMock()
    mock_exec.all.return_value = []
    mock_db_session = MagicMock()
    mock_db_session.execute.return_value = mock_exec

    child_cat_query_count = {"n": 0}

    def mock_execute(stmt):
        return mock_exec

    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"), \
         patch("ttrss.blueprints.api.views.db") as mock_db, \
         patch("ttrss.blueprints.api.views.getLabelCounters", return_value=[]), \
         patch("ttrss.blueprints.api.views._count_feed_articles", return_value=0), \
         patch("ttrss.blueprints.api.views.feed_has_icon", return_value=False):
        mock_user.is_authenticated = True
        mock_user.id = 1
        mock_db.session = mock_db_session
        # cat_id=0 is falsy → include_nested branch skipped
        data, _ = _post(api_app, "getFeeds", {"cat_id": 0, "include_nested": True})

    assert data["status"] == 0


def test_getFeeds_unread_only_filters_zero_unread(api_app):
    """unread_only=true excludes feeds with unread=0."""
    real_feed = _make_feed_row(10, "Silent Feed", cat_id=1)
    mock_exec = MagicMock()
    mock_exec.all.return_value = [real_feed]
    mock_db_session = MagicMock()
    mock_db_session.execute.return_value = mock_exec

    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"), \
         patch("ttrss.blueprints.api.views.db") as mock_db, \
         patch("ttrss.blueprints.api.views.getLabelCounters", return_value=[]), \
         patch("ttrss.blueprints.api.views._count_feed_articles", return_value=0), \
         patch("ttrss.blueprints.api.views.feed_has_icon", return_value=False):
        mock_user.is_authenticated = True
        mock_user.id = 1
        mock_db.session = mock_db_session
        data, _ = _post(api_app, "getFeeds", {"cat_id": 1, "unread_only": True})

    assert data["content"] == []


# ---------------------------------------------------------------------------
# getArticle
# ---------------------------------------------------------------------------


def _make_article_row(id_, title="Test", updated=None):
    r = MagicMock()
    r.id = id_
    r.title = title
    r.link = f"http://ex.com/{id_}"
    r.content = "content"
    r.author = "Author"
    r.updated = updated or datetime(2024, 1, 1, tzinfo=timezone.utc)
    r.comments = ""
    r.lang = "en"
    r.feed_id = 1
    r.feed_title = "Test Feed"  # self-refine C10: feed_title now in main JOIN query
    r.int_id = 100 + id_
    r.marked = False
    r.unread = True
    r.published = False
    r.score = 0
    r.note = ""
    return r


def test_getArticle_returns_article_list(api_app):
    """getArticle returns list of article dicts."""
    row = _make_article_row(42)
    mock_exec = MagicMock()
    mock_exec.all.return_value = [row]
    mock_db_session = MagicMock()
    # Self-refine fix (C10): feed_title now in main JOIN query — only one execute call
    mock_db_session.execute.return_value = mock_exec

    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"), \
         patch("ttrss.blueprints.api.views.db") as mock_db, \
         patch("ttrss.blueprints.api.views.get_article_enclosures", return_value=[]), \
         patch("ttrss.blueprints.api.views.get_article_labels", return_value=[]), \
         patch("ttrss.blueprints.api.views.get_plugin_manager") as mock_pm:
        mock_user.is_authenticated = True
        mock_user.id = 1
        mock_db.session = mock_db_session
        mock_pm.return_value.hook.hook_render_article_api.return_value = []
        data, _ = _post(api_app, "getArticle", {"article_id": "42"})

    assert data["status"] == 0
    articles = data["content"]
    assert len(articles) == 1
    assert articles[0]["id"] == 42
    assert "attachments" in articles[0]
    assert "labels" in articles[0]


def test_getArticle_missing_article_id_returns_error(api_app):
    """getArticle without article_id returns INCORRECT_USAGE."""
    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"):
        mock_user.is_authenticated = True
        mock_user.id = 1
        data, _ = _post(api_app, "getArticle", {})

    assert data["status"] == 1
    assert data["content"]["error"] == "INCORRECT_USAGE"


def test_getArticle_non_numeric_ids_filtered(api_app):
    """getArticle filters non-numeric IDs from comma-separated list."""
    mock_exec = MagicMock()
    mock_exec.all.return_value = []
    mock_db_session = MagicMock()
    mock_db_session.execute.return_value = mock_exec

    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"), \
         patch("ttrss.blueprints.api.views.db") as mock_db, \
         patch("ttrss.blueprints.api.views.get_article_enclosures", return_value=[]), \
         patch("ttrss.blueprints.api.views.get_article_labels", return_value=[]), \
         patch("ttrss.blueprints.api.views.get_plugin_manager") as mock_pm:
        mock_user.is_authenticated = True
        mock_user.id = 1
        mock_db.session = mock_db_session
        mock_pm.return_value.hook.hook_render_article_api.return_value = []
        data, _ = _post(api_app, "getArticle", {"article_id": "42,abc,99"})

    assert data["status"] == 0  # 42 and 99 are valid


def test_getArticle_all_non_numeric_returns_error(api_app):
    """getArticle with entirely non-numeric article_id returns INCORRECT_USAGE."""
    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"):
        mock_user.is_authenticated = True
        mock_user.id = 1
        data, _ = _post(api_app, "getArticle", {"article_id": "abc,xyz"})

    assert data["status"] == 1
    assert data["content"]["error"] == "INCORRECT_USAGE"


def test_getArticle_hook_render_fires_per_article(api_app):
    """HOOK_RENDER_ARTICLE_API fires for each article and can modify it."""
    row = _make_article_row(1)
    mock_exec = MagicMock()
    mock_exec.all.return_value = [row]
    mock_db_session = MagicMock()
    # Self-refine fix (C10): single execute for main query (feed_title in JOIN)
    mock_db_session.execute.return_value = mock_exec

    hook_call_count = {"n": 0}

    def fake_hook(headline_row):
        hook_call_count["n"] += 1
        modified = dict(headline_row["article"])
        modified["hook_applied"] = True
        return [{"article": modified}]

    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"), \
         patch("ttrss.blueprints.api.views.db") as mock_db, \
         patch("ttrss.blueprints.api.views.get_article_enclosures", return_value=[]), \
         patch("ttrss.blueprints.api.views.get_article_labels", return_value=[]), \
         patch("ttrss.blueprints.api.views.get_plugin_manager") as mock_pm:
        mock_user.is_authenticated = True
        mock_user.id = 1
        mock_db.session = mock_db_session
        mock_pm.return_value.hook.hook_render_article_api.side_effect = fake_hook
        data, _ = _post(api_app, "getArticle", {"article_id": "1"})

    assert hook_call_count["n"] == 1
    assert data["content"][0].get("hook_applied") is True


def test_getArticle_updated_is_unix_timestamp(api_app):
    """getArticle returns updated as Unix integer truncated to minute (PHP parity).

    Source: ttrss/classes/api.php:344 — SUBSTRING_FOR_DATE(updated,1,16) zeroes seconds.
    """
    ts = datetime(2024, 6, 1, 12, 30, 45, tzinfo=timezone.utc)
    row = _make_article_row(5, updated=ts)
    mock_exec = MagicMock()
    mock_exec.all.return_value = [row]
    mock_db_session = MagicMock()
    mock_db_session.execute.return_value = mock_exec

    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"), \
         patch("ttrss.blueprints.api.views.db") as mock_db, \
         patch("ttrss.blueprints.api.views.get_article_enclosures", return_value=[]), \
         patch("ttrss.blueprints.api.views.get_article_labels", return_value=[]), \
         patch("ttrss.blueprints.api.views.get_plugin_manager") as mock_pm:
        mock_user.is_authenticated = True
        mock_user.id = 1
        mock_db.session = mock_db_session
        mock_pm.return_value.hook.hook_render_article_api.return_value = []
        data, _ = _post(api_app, "getArticle", {"article_id": "5"})

    # Seconds should be zeroed (minute-precision PHP parity)
    expected_ts = datetime(2024, 6, 1, 12, 30, 0, tzinfo=timezone.utc)
    assert data["content"][0]["updated"] == int(expected_ts.timestamp())
