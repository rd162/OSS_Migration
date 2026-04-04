"""Unit tests for ttrss/tasks/feed_tasks.py — dispatch_feed_updates, update_feed, _fetch_feed_async."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx


# ---------------------------------------------------------------------------
# Helpers — mock Flask app context
# ---------------------------------------------------------------------------


def _make_app_ctx(session=None):
    """Return a mock Flask app with a usable app_context() context manager."""
    if session is None:
        session = MagicMock()
    mock_app = MagicMock()
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=None)
    ctx.__exit__ = MagicMock(return_value=False)
    mock_app.app_context.return_value = ctx
    return mock_app, session


def _make_feed(feed_id=5, owner_uid=1, **overrides):
    feed = MagicMock()
    feed.id = feed_id
    feed.owner_uid = owner_uid
    feed.feed_url = "http://example.com/feed.xml"
    feed.auth_login = None
    feed._auth_pass = None
    feed.auth_pass_encrypted = False
    feed.last_etag = None
    feed.last_modified = None
    feed.last_error = ""
    for k, v in overrides.items():
        setattr(feed, k, v)
    return feed


# ---------------------------------------------------------------------------
# _fetch_feed_async — pure async helper
# ---------------------------------------------------------------------------


def test_fetch_feed_async_get_called():
    """_fetch_feed_async issues a GET and returns (status, body, headers)."""
    from ttrss.tasks.feed_tasks import _fetch_feed_async

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"<rss/>"
    mock_resp.headers = {"etag": '"abc"', "last-modified": "Mon, 1 Jan 2025 00:00:00 GMT"}

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        status, body, headers = asyncio.run(
            _fetch_feed_async("http://example.com/feed", None, None, None, None)
        )

    assert status == 200
    assert body == b"<rss/>"
    assert headers["etag"] == '"abc"'


def test_fetch_feed_async_sets_if_none_match():
    from ttrss.tasks.feed_tasks import _fetch_feed_async

    mock_resp = MagicMock()
    mock_resp.status_code = 304
    mock_resp.content = b""
    mock_resp.headers = {}

    captured_headers = {}

    async def fake_get(url, headers, auth):
        captured_headers.update(headers)
        return mock_resp

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = fake_get
        mock_cls.return_value = mock_client

        asyncio.run(_fetch_feed_async("http://x.com", '"etag123"', None, None, None))

    assert captured_headers.get("If-None-Match") == '"etag123"'


def test_fetch_feed_async_sets_if_modified_since():
    from ttrss.tasks.feed_tasks import _fetch_feed_async

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b""
    mock_resp.headers = {}

    captured_headers = {}

    async def fake_get(url, headers, auth):
        captured_headers.update(headers)
        return mock_resp

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = fake_get
        mock_cls.return_value = mock_client

        asyncio.run(_fetch_feed_async("http://x.com", None, "Mon, 1 Jan 2025 00:00:00 GMT", None, None))

    assert "If-Modified-Since" in captured_headers


def test_fetch_feed_async_basic_auth():
    from ttrss.tasks.feed_tasks import _fetch_feed_async

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b""
    mock_resp.headers = {}

    captured_auth = [None]

    async def fake_get(url, headers, auth):
        captured_auth[0] = auth
        return mock_resp

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = fake_get
        mock_cls.return_value = mock_client

        asyncio.run(_fetch_feed_async("http://x.com", None, None, "user", "pass"))

    assert isinstance(captured_auth[0], httpx.BasicAuth)


# ---------------------------------------------------------------------------
# dispatch_feed_updates
# ---------------------------------------------------------------------------


def _make_dispatch_session(feed_ids=None):
    session = MagicMock()
    if feed_ids is None:
        feed_ids = [1, 2]
    rows = [(fid,) for fid in feed_ids]
    session.execute.return_value.fetchall.return_value = rows
    return session


def test_dispatch_feed_updates_dispatches_feeds():
    from ttrss.tasks.feed_tasks import dispatch_feed_updates

    mock_app, session = _make_app_ctx(_make_dispatch_session([1, 2, 3]))
    pm_mock = MagicMock()

    with patch("ttrss.tasks.feed_tasks.update_feed") as mock_update_feed, \
         patch("ttrss.create_app", return_value=mock_app), \
         patch("ttrss.extensions.db") as mock_db:
        mock_db.session = session
        result = dispatch_feed_updates.run()

    assert result["dispatched"] == 3
    assert mock_update_feed.delay.call_count == 3


def test_dispatch_feed_updates_no_feeds():
    from ttrss.tasks.feed_tasks import dispatch_feed_updates

    mock_app, session = _make_app_ctx(_make_dispatch_session([]))

    with patch("ttrss.tasks.feed_tasks.update_feed") as mock_update_feed, \
         patch("ttrss.create_app", return_value=mock_app), \
         patch("ttrss.extensions.db") as mock_db:
        mock_db.session = session
        result = dispatch_feed_updates.run()

    assert result["dispatched"] == 0
    mock_update_feed.delay.assert_not_called()


# ---------------------------------------------------------------------------
# update_feed
# ---------------------------------------------------------------------------


def _run_update_feed(feed_id, feed, fetch_result=None, parsed=None, session=None):
    """Helper to run update_feed.run() with common mocking."""
    from ttrss.tasks.feed_tasks import update_feed

    if session is None:
        session = MagicMock()
    mock_app, _ = _make_app_ctx(session)
    pm_mock = MagicMock()
    pm_mock.hook.hook_fetch_feed.return_value = []
    pm_mock.hook.hook_feed_fetched.return_value = []
    pm_mock.hook.hook_feed_parsed.return_value = []
    pm_mock.hook.hook_article_filter.return_value = []

    with patch("ttrss.create_app", return_value=mock_app), \
         patch("ttrss.extensions.db") as mock_db, \
         patch("ttrss.plugins.manager.get_plugin_manager", return_value=pm_mock):
        mock_db.session = session
        session.get.return_value = feed
        if fetch_result is not None:
            with patch("ttrss.tasks.feed_tasks.asyncio.run", return_value=fetch_result):
                if parsed is not None:
                    with patch("ttrss.tasks.feed_tasks.feedparser.parse", return_value=parsed):
                        result = update_feed.run(feed_id)
                else:
                    result = update_feed.run(feed_id)
        else:
            result = update_feed.run(feed_id)
    return result


def test_update_feed_not_found():
    from ttrss.tasks.feed_tasks import update_feed

    session = MagicMock()
    session.get.return_value = None
    mock_app, _ = _make_app_ctx(session)

    with patch("ttrss.create_app", return_value=mock_app), \
         patch("ttrss.extensions.db") as mock_db:
        mock_db.session = session
        result = update_feed.run(99)

    assert result["status"] == "not_found"


def test_update_feed_304_not_modified():
    from ttrss.tasks.feed_tasks import update_feed

    feed = _make_feed()
    session = MagicMock()
    session.get.return_value = feed
    mock_app, _ = _make_app_ctx(session)
    pm_mock = MagicMock()
    pm_mock.hook.hook_fetch_feed.return_value = []

    with patch("ttrss.create_app", return_value=mock_app), \
         patch("ttrss.extensions.db") as mock_db, \
         patch("ttrss.plugins.manager.get_plugin_manager", return_value=pm_mock), \
         patch("ttrss.tasks.feed_tasks.asyncio.run", return_value=(304, b"", {})):
        mock_db.session = session
        result = update_feed.run(5)

    assert result["status"] == "not_modified"


def test_update_feed_http_error_400():
    from ttrss.tasks.feed_tasks import update_feed

    feed = _make_feed()
    session = MagicMock()
    session.get.return_value = feed
    mock_app, _ = _make_app_ctx(session)
    pm_mock = MagicMock()
    pm_mock.hook.hook_fetch_feed.return_value = []

    with patch("ttrss.create_app", return_value=mock_app), \
         patch("ttrss.extensions.db") as mock_db, \
         patch("ttrss.plugins.manager.get_plugin_manager", return_value=pm_mock), \
         patch("ttrss.tasks.feed_tasks.asyncio.run", return_value=(404, b"", {})):
        mock_db.session = session
        result = update_feed.run(5)

    assert result["status"] == "http_error"
    assert result["code"] == 404


def test_update_feed_parse_error_bozo():
    from ttrss.tasks.feed_tasks import update_feed

    feed = _make_feed()
    session = MagicMock()
    session.get.return_value = feed
    mock_app, _ = _make_app_ctx(session)
    pm_mock = MagicMock()
    pm_mock.hook.hook_fetch_feed.return_value = []
    pm_mock.hook.hook_feed_fetched.return_value = []

    bozo_parsed = MagicMock()
    bozo_parsed.bozo = True
    bozo_parsed.entries = []
    bozo_parsed.bozo_exception = Exception("bad xml")

    with patch("ttrss.create_app", return_value=mock_app), \
         patch("ttrss.extensions.db") as mock_db, \
         patch("ttrss.plugins.manager.get_plugin_manager", return_value=pm_mock), \
         patch("ttrss.tasks.feed_tasks.asyncio.run", return_value=(200, b"bad", {})), \
         patch("ttrss.tasks.feed_tasks.feedparser.parse", return_value=bozo_parsed):
        mock_db.session = session
        result = update_feed.run(5)

    assert result["status"] == "parse_error"


def test_update_feed_ok_no_entries():
    from ttrss.tasks.feed_tasks import update_feed

    feed = _make_feed()
    session = MagicMock()
    session.get.return_value = feed
    mock_app, _ = _make_app_ctx(session)
    pm_mock = MagicMock()
    pm_mock.hook.hook_fetch_feed.return_value = []
    pm_mock.hook.hook_feed_fetched.return_value = []
    pm_mock.hook.hook_feed_parsed.return_value = []

    parsed = MagicMock()
    parsed.bozo = False
    parsed.entries = []

    with patch("ttrss.create_app", return_value=mock_app), \
         patch("ttrss.extensions.db") as mock_db, \
         patch("ttrss.plugins.manager.get_plugin_manager", return_value=pm_mock), \
         patch("ttrss.tasks.feed_tasks.asyncio.run", return_value=(200, b"<rss/>", {})), \
         patch("ttrss.tasks.feed_tasks.feedparser.parse", return_value=parsed), \
         patch("ttrss.articles.filters.load_filters", return_value=[]):
        mock_db.session = session
        result = update_feed.run(5)

    assert result["status"] == "ok"
    assert result["entries"] == 0


def test_update_feed_ok_with_entries():
    from ttrss.tasks.feed_tasks import update_feed

    feed = _make_feed()
    session = MagicMock()
    session.get.return_value = feed
    mock_app, _ = _make_app_ctx(session)
    pm_mock = MagicMock()
    pm_mock.hook.hook_fetch_feed.return_value = []
    pm_mock.hook.hook_feed_fetched.return_value = []
    pm_mock.hook.hook_feed_parsed.return_value = []
    pm_mock.hook.hook_article_filter.return_value = []

    entry = MagicMock()
    entry.get.side_effect = lambda k, d=None: {
        "id": "http://x.com/1",
        "title": "Article",
        "link": "http://x.com/1",
        "summary": "Content",
        "author": "Bob",
        "tags": [],
        "enclosures": [],
        "updated_parsed": None,
        "published_parsed": None,
        "plugin_data": "",
    }.get(k, d)

    parsed = MagicMock()
    parsed.bozo = False
    parsed.entries = [entry]

    with patch("ttrss.create_app", return_value=mock_app), \
         patch("ttrss.extensions.db") as mock_db, \
         patch("ttrss.plugins.manager.get_plugin_manager", return_value=pm_mock), \
         patch("ttrss.tasks.feed_tasks.asyncio.run", return_value=(200, b"<rss/>", {})), \
         patch("ttrss.tasks.feed_tasks.feedparser.parse", return_value=parsed), \
         patch("ttrss.articles.filters.load_filters", return_value=[]), \
         patch("ttrss.articles.persist.persist_article", return_value=True), \
         patch("ttrss.tasks.feed_tasks.sanitize", return_value="clean"):
        mock_db.session = session
        result = update_feed.run(5)

    assert result["status"] == "ok"
    assert result["entries"] == 1
    assert result["new"] == 1


def test_update_feed_plugin_provides_feed_data():
    """HOOK_FETCH_FEED returning non-None skips HTTP fetch."""
    from ttrss.tasks.feed_tasks import update_feed

    feed = _make_feed()
    session = MagicMock()
    session.get.return_value = feed
    mock_app, _ = _make_app_ctx(session)
    pm_mock = MagicMock()
    pm_mock.hook.hook_fetch_feed.return_value = [b"<rss/>"]  # plugin provides data
    pm_mock.hook.hook_feed_fetched.return_value = []
    pm_mock.hook.hook_feed_parsed.return_value = []
    pm_mock.hook.hook_article_filter.return_value = []

    parsed = MagicMock()
    parsed.bozo = False
    parsed.entries = []

    with patch("ttrss.create_app", return_value=mock_app), \
         patch("ttrss.extensions.db") as mock_db, \
         patch("ttrss.plugins.manager.get_plugin_manager", return_value=pm_mock), \
         patch("ttrss.tasks.feed_tasks.asyncio") as mock_asyncio, \
         patch("ttrss.tasks.feed_tasks.feedparser.parse", return_value=parsed), \
         patch("ttrss.articles.filters.load_filters", return_value=[]):
        mock_db.session = session
        result = update_feed.run(5)

    # asyncio.run should NOT be called — plugin bypassed HTTP
    mock_asyncio.run.assert_not_called()
    assert result["status"] == "ok"


def test_update_feed_http_exception_sets_last_error():
    """httpx.HTTPError updates feed.last_error before re-raising."""
    from ttrss.tasks.feed_tasks import update_feed

    feed = _make_feed()
    session = MagicMock()
    session.get.return_value = feed
    mock_app, _ = _make_app_ctx(session)
    pm_mock = MagicMock()
    pm_mock.hook.hook_fetch_feed.return_value = []

    with patch("ttrss.create_app", return_value=mock_app), \
         patch("ttrss.extensions.db") as mock_db, \
         patch("ttrss.plugins.manager.get_plugin_manager", return_value=pm_mock), \
         patch("ttrss.tasks.feed_tasks.asyncio.run",
               side_effect=httpx.HTTPError("connection refused")):
        mock_db.session = session
        with pytest.raises(httpx.HTTPError):
            update_feed.run(5)

    assert "connection refused" in feed.last_error


def test_update_feed_stores_etag_and_last_modified():
    from ttrss.tasks.feed_tasks import update_feed

    feed = _make_feed()
    session = MagicMock()
    session.get.return_value = feed
    mock_app, _ = _make_app_ctx(session)
    pm_mock = MagicMock()
    pm_mock.hook.hook_fetch_feed.return_value = []
    pm_mock.hook.hook_feed_fetched.return_value = []
    pm_mock.hook.hook_feed_parsed.return_value = []

    parsed = MagicMock()
    parsed.bozo = False
    parsed.entries = []

    resp_headers = {"etag": '"v2"', "last-modified": "Thu, 1 Jan 2026 00:00:00 GMT"}

    with patch("ttrss.create_app", return_value=mock_app), \
         patch("ttrss.extensions.db") as mock_db, \
         patch("ttrss.plugins.manager.get_plugin_manager", return_value=pm_mock), \
         patch("ttrss.tasks.feed_tasks.asyncio.run", return_value=(200, b"<rss/>", resp_headers)), \
         patch("ttrss.tasks.feed_tasks.feedparser.parse", return_value=parsed), \
         patch("ttrss.articles.filters.load_filters", return_value=[]):
        mock_db.session = session
        update_feed.run(5)

    assert feed.last_etag == '"v2"'
    assert feed.last_modified == "Thu, 1 Jan 2026 00:00:00 GMT"
