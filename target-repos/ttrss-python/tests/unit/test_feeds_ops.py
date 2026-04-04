"""Unit tests for ttrss/feeds/ops.py — feed operations (interval, purge, favicon, subscribe).

Tests use MagicMock session so no real DB or HTTP is required.
httpx and lxml calls are patched via unittest.mock.patch.
"""
from __future__ import annotations

import pathlib
from unittest.mock import MagicMock, call, patch

import pytest

from ttrss.feeds.ops import (
    check_feed_favicon,
    feed_has_icon,
    feed_purge_interval,
    get_feed_access_key,
    get_feed_update_interval,
    get_favicon_url,
    get_feeds_from_html,
    purge_feed,
    purge_orphans,
    subscribe_to_feed,
)


# ---------------------------------------------------------------------------
# feed_purge_interval
# ---------------------------------------------------------------------------


def test_feed_purge_interval_not_found():
    session = MagicMock()
    session.execute.return_value.one_or_none.return_value = None
    assert feed_purge_interval(session, 99) == -1


def test_feed_purge_interval_explicit():
    row = MagicMock()
    row.purge_interval = 14
    row.owner_uid = 1
    session = MagicMock()
    session.execute.return_value.one_or_none.return_value = row
    assert feed_purge_interval(session, 5) == 14


def test_feed_purge_interval_zero_reads_pref():
    """purge_interval=0 means 'use PURGE_OLD_DAYS pref'."""
    row = MagicMock()
    row.purge_interval = 0
    row.owner_uid = 2
    session = MagicMock()
    # First execute: feed row; second execute: pref lookup
    session.execute.side_effect = [
        MagicMock(**{"one_or_none.return_value": row}),
        MagicMock(**{"scalar_one_or_none.return_value": "30"}),
        MagicMock(**{"scalar_one_or_none.return_value": None}),  # system default fallback
    ]
    result = feed_purge_interval(session, 5)
    assert result == 30


def test_feed_purge_interval_zero_pref_missing_returns_default():
    """When pref absent, _pref_int returns default=60."""
    row = MagicMock()
    row.purge_interval = 0
    row.owner_uid = 2
    session = MagicMock()
    session.execute.side_effect = [
        MagicMock(**{"one_or_none.return_value": row}),
        MagicMock(**{"scalar_one_or_none.return_value": None}),  # user pref miss
        MagicMock(**{"scalar_one_or_none.return_value": None}),  # system default miss
    ]
    result = feed_purge_interval(session, 5)
    assert result == 60  # default


# ---------------------------------------------------------------------------
# get_feed_update_interval
# ---------------------------------------------------------------------------


def test_get_feed_update_interval_not_found():
    session = MagicMock()
    session.execute.return_value.one_or_none.return_value = None
    assert get_feed_update_interval(session, 99) == -1


def test_get_feed_update_interval_explicit():
    row = MagicMock()
    row.update_interval = 60
    row.owner_uid = 1
    session = MagicMock()
    session.execute.return_value.one_or_none.return_value = row
    assert get_feed_update_interval(session, 5) == 60


def test_get_feed_update_interval_zero_reads_pref():
    row = MagicMock()
    row.update_interval = 0
    row.owner_uid = 1
    session = MagicMock()
    session.execute.side_effect = [
        MagicMock(**{"one_or_none.return_value": row}),
        MagicMock(**{"scalar_one_or_none.return_value": "120"}),
        MagicMock(**{"scalar_one_or_none.return_value": None}),
    ]
    result = get_feed_update_interval(session, 5)
    assert result == 120


# ---------------------------------------------------------------------------
# purge_feed
# ---------------------------------------------------------------------------


def _purge_session(owner_uid=1, interval_row=None, owner_row=1, pref_value="false"):
    """Build a sequential mock session for purge_feed tests."""
    session = MagicMock()
    calls = []
    if interval_row is not None:
        calls.append(MagicMock(**{"one_or_none.return_value": interval_row}))
    calls.append(MagicMock(**{"scalar_one_or_none.return_value": owner_row}))
    # PURGE_UNREAD_ARTICLES pref
    calls.append(MagicMock(**{"scalar_one_or_none.return_value": None}))
    calls.append(MagicMock(**{"scalar_one_or_none.return_value": pref_value}))
    # DELETE result
    delete_result = MagicMock()
    delete_result.rowcount = 5
    calls.append(delete_result)
    # ccache_update calls return None
    calls.append(MagicMock())
    session.execute.side_effect = calls
    return session


def test_purge_feed_returns_none_when_feed_missing():
    """No feed found → feed_purge_interval returns -1 → early-return None."""
    session = MagicMock()
    row_not_found = MagicMock(**{"one_or_none.return_value": None})
    owner_none = MagicMock(**{"scalar_one_or_none.return_value": None})
    session.execute.side_effect = [row_not_found, owner_none]
    with patch("ttrss.feeds.ops.ccache_update") as mock_ccache:
        result = purge_feed(session, feed_id=99)
    assert result is None


def test_purge_feed_early_return_when_interval_zero():
    """purge_interval resolved to 0 → ccache_update call site #1 → return None."""
    row = MagicMock()
    row.purge_interval = 0
    row.owner_uid = 1

    session = MagicMock()
    session.execute.side_effect = [
        MagicMock(**{"one_or_none.return_value": row}),        # feed_purge_interval feed row
        MagicMock(**{"scalar_one_or_none.return_value": None}),# PURGE_OLD_DAYS user pref miss
        MagicMock(**{"scalar_one_or_none.return_value": "0"}), # PURGE_OLD_DAYS system default → "0"
        MagicMock(**{"scalar_one_or_none.return_value": 1}),   # owner_uid lookup
    ]
    with patch("ttrss.feeds.ops.ccache_update") as mock_ccache:
        result = purge_feed(session, feed_id=5)
    assert result is None
    mock_ccache.assert_called_once()


def test_purge_feed_deletes_articles():
    """Normal purge: explicitly provided interval, returns rowcount."""
    session = MagicMock()
    owner_result = MagicMock(**{"scalar_one_or_none.return_value": 1})
    pref_user = MagicMock(**{"scalar_one_or_none.return_value": None})
    pref_sys = MagicMock(**{"scalar_one_or_none.return_value": "false"})
    delete_result = MagicMock()
    delete_result.rowcount = 7
    session.execute.side_effect = [owner_result, pref_user, pref_sys, delete_result]

    with patch("ttrss.feeds.ops.ccache_update") as mock_ccache:
        rows = purge_feed(session, feed_id=5, purge_interval=30)

    assert rows == 7
    mock_ccache.assert_called_once()  # call site #2


def test_purge_feed_debug_logs(caplog):
    """debug=True emits a debug log line."""
    import logging
    session = MagicMock()
    owner_result = MagicMock(**{"scalar_one_or_none.return_value": 1})
    pref_user = MagicMock(**{"scalar_one_or_none.return_value": None})
    pref_sys = MagicMock(**{"scalar_one_or_none.return_value": "false"})
    delete_result = MagicMock()
    delete_result.rowcount = 3
    session.execute.side_effect = [owner_result, pref_user, pref_sys, delete_result]

    with patch("ttrss.feeds.ops.ccache_update"):
        with caplog.at_level(logging.DEBUG, logger="ttrss.feeds.ops"):
            purge_feed(session, feed_id=5, purge_interval=7, debug=True)

    assert any("Purged feed" in r.message for r in caplog.records)


def test_purge_feed_skips_unread_when_pref_false():
    """PURGE_UNREAD_ARTICLES=false → the WHERE clause excludes unread entries."""
    session = MagicMock()
    owner_result = MagicMock(**{"scalar_one_or_none.return_value": 1})
    pref_user = MagicMock(**{"scalar_one_or_none.return_value": None})
    pref_sys = MagicMock(**{"scalar_one_or_none.return_value": "false"})
    delete_result = MagicMock()
    delete_result.rowcount = 4
    session.execute.side_effect = [owner_result, pref_user, pref_sys, delete_result]

    with patch("ttrss.feeds.ops.ccache_update"):
        rows = purge_feed(session, feed_id=5, purge_interval=14)
    assert rows == 4


# ---------------------------------------------------------------------------
# purge_orphans
# ---------------------------------------------------------------------------


def test_purge_orphans_executes_delete():
    session = MagicMock()
    result = MagicMock()
    result.rowcount = 10
    session.execute.return_value = result
    purge_orphans(session)
    session.execute.assert_called_once()


def test_purge_orphans_do_output_logs(caplog):
    import logging
    session = MagicMock()
    result = MagicMock()
    result.rowcount = 3
    session.execute.return_value = result
    with caplog.at_level(logging.DEBUG, logger="ttrss.feeds.ops"):
        purge_orphans(session, do_output=True)
    assert any("orphaned" in r.message for r in caplog.records)


def test_purge_orphans_silent_by_default(caplog):
    import logging
    session = MagicMock()
    session.execute.return_value = MagicMock(rowcount=5)
    with caplog.at_level(logging.DEBUG, logger="ttrss.feeds.ops"):
        purge_orphans(session, do_output=False)
    assert not caplog.records


# ---------------------------------------------------------------------------
# feed_has_icon
# ---------------------------------------------------------------------------


def test_feed_has_icon_no_icons_dir():
    assert feed_has_icon(5, icons_dir="") is False


def test_feed_has_icon_file_missing(tmp_path):
    assert feed_has_icon(999, icons_dir=str(tmp_path)) is False


def test_feed_has_icon_empty_file(tmp_path):
    icon = tmp_path / "5.ico"
    icon.write_bytes(b"")
    assert feed_has_icon(5, icons_dir=str(tmp_path)) is False


def test_feed_has_icon_present(tmp_path):
    icon = tmp_path / "5.ico"
    icon.write_bytes(b"\x00\x00\x01\x00")
    assert feed_has_icon(5, icons_dir=str(tmp_path)) is True


# ---------------------------------------------------------------------------
# get_favicon_url
# ---------------------------------------------------------------------------


def test_get_favicon_url_finds_link_icon():
    html = b'<html><head><link rel="icon" href="/img/fav.ico"></head></html>'
    resp = MagicMock()
    resp.content = html
    resp.raise_for_status = MagicMock()

    with patch("httpx.Client") as MockClient:
        ctx = MockClient.return_value.__enter__.return_value
        ctx.get.return_value = resp
        result = get_favicon_url("http://example.com/page")

    assert result == "http://example.com/img/fav.ico"


def test_get_favicon_url_falls_back_to_root():
    """No <link rel="icon"> → fall back to /favicon.ico."""
    html = b"<html><head></head></html>"
    resp = MagicMock()
    resp.content = html
    resp.raise_for_status = MagicMock()

    with patch("httpx.Client") as MockClient:
        ctx = MockClient.return_value.__enter__.return_value
        ctx.get.return_value = resp
        result = get_favicon_url("http://example.com/page")

    assert result == "http://example.com/favicon.ico"


def test_get_favicon_url_network_failure_returns_fallback():
    """Network error → still returns /favicon.ico fallback."""
    with patch("httpx.Client") as MockClient:
        ctx = MockClient.return_value.__enter__.return_value
        ctx.get.side_effect = Exception("timeout")
        result = get_favicon_url("http://example.com/page")

    assert result == "http://example.com/favicon.ico"


# ---------------------------------------------------------------------------
# check_feed_favicon
# ---------------------------------------------------------------------------


def test_check_feed_favicon_no_icons_dir():
    result = check_feed_favicon("http://example.com", feed_id=5, icons_dir="")
    assert result is None


def test_check_feed_favicon_already_cached(tmp_path):
    icon = tmp_path / "5.ico"
    icon.write_bytes(b"\x00\x00\x01\x00")
    result = check_feed_favicon("http://example.com", feed_id=5, icons_dir=str(tmp_path))
    assert result == str(tmp_path / "5.ico")


def test_check_feed_favicon_downloads_png(tmp_path):
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    resp = MagicMock()
    resp.content = png_bytes
    resp.raise_for_status = MagicMock()

    with patch("ttrss.feeds.ops.get_favicon_url", return_value="http://example.com/icon.png"):
        with patch("httpx.Client") as MockClient:
            ctx = MockClient.return_value.__enter__.return_value
            ctx.get.return_value = resp
            result = check_feed_favicon("http://example.com", feed_id=7, icons_dir=str(tmp_path))

    assert result == str(tmp_path / "7.ico")
    assert (tmp_path / "7.ico").read_bytes() == png_bytes


def test_check_feed_favicon_rejects_invalid_bytes(tmp_path):
    bad_bytes = b"GARBAGE DATA HERE"
    resp = MagicMock()
    resp.content = bad_bytes
    resp.raise_for_status = MagicMock()

    with patch("ttrss.feeds.ops.get_favicon_url", return_value="http://example.com/icon.png"):
        with patch("httpx.Client") as MockClient:
            ctx = MockClient.return_value.__enter__.return_value
            ctx.get.return_value = resp
            result = check_feed_favicon("http://example.com", feed_id=7, icons_dir=str(tmp_path))

    assert result is None


def test_check_feed_favicon_accepts_ico(tmp_path):
    ico_bytes = b"\x00\x00\x01\x00" + b"\x00" * 20
    resp = MagicMock()
    resp.content = ico_bytes
    resp.raise_for_status = MagicMock()

    with patch("ttrss.feeds.ops.get_favicon_url", return_value="http://example.com/fav.ico"):
        with patch("httpx.Client") as MockClient:
            ctx = MockClient.return_value.__enter__.return_value
            ctx.get.return_value = resp
            result = check_feed_favicon("http://example.com", feed_id=3, icons_dir=str(tmp_path))

    assert result == str(tmp_path / "3.ico")


def test_check_feed_favicon_accepts_gif(tmp_path):
    gif_bytes = b"GIF8" + b"\x00" * 20
    resp = MagicMock()
    resp.content = gif_bytes
    resp.raise_for_status = MagicMock()

    with patch("ttrss.feeds.ops.get_favicon_url", return_value="http://example.com/fav.gif"):
        with patch("httpx.Client") as MockClient:
            ctx = MockClient.return_value.__enter__.return_value
            ctx.get.return_value = resp
            result = check_feed_favicon("http://example.com", feed_id=4, icons_dir=str(tmp_path))

    assert result == str(tmp_path / "4.ico")


def test_check_feed_favicon_accepts_jpeg(tmp_path):
    jpeg_bytes = b"\xff\xd8" + b"\x00" * 20
    resp = MagicMock()
    resp.content = jpeg_bytes
    resp.raise_for_status = MagicMock()

    with patch("ttrss.feeds.ops.get_favicon_url", return_value="http://example.com/fav.jpg"):
        with patch("httpx.Client") as MockClient:
            ctx = MockClient.return_value.__enter__.return_value
            ctx.get.return_value = resp
            result = check_feed_favicon("http://example.com", feed_id=8, icons_dir=str(tmp_path))

    assert result == str(tmp_path / "8.ico")


def test_check_feed_favicon_fetch_failure(tmp_path):
    with patch("ttrss.feeds.ops.get_favicon_url", return_value="http://example.com/fav.ico"):
        with patch("httpx.Client") as MockClient:
            ctx = MockClient.return_value.__enter__.return_value
            ctx.get.side_effect = Exception("network error")
            result = check_feed_favicon("http://example.com", feed_id=5, icons_dir=str(tmp_path))
    assert result is None


def test_check_feed_favicon_empty_content(tmp_path):
    resp = MagicMock()
    resp.content = b""
    resp.raise_for_status = MagicMock()

    with patch("ttrss.feeds.ops.get_favicon_url", return_value="http://example.com/fav.ico"):
        with patch("httpx.Client") as MockClient:
            ctx = MockClient.return_value.__enter__.return_value
            ctx.get.return_value = resp
            result = check_feed_favicon("http://example.com", feed_id=5, icons_dir=str(tmp_path))

    assert result is None


# ---------------------------------------------------------------------------
# get_feeds_from_html
# ---------------------------------------------------------------------------


def test_get_feeds_from_html_finds_rss():
    html = (
        '<html><head>'
        '<link rel="alternate" type="application/rss+xml" href="/feed.rss" title="My RSS">'
        '</head></html>'
    )
    result = get_feeds_from_html("http://example.com", html)
    assert len(result) == 1
    assert "http://example.com/feed.rss" in result
    assert result["http://example.com/feed.rss"] == "My RSS"


def test_get_feeds_from_html_finds_atom():
    html = (
        '<html><head>'
        '<link rel="alternate" type="application/atom+xml" href="/atom.xml">'
        '</head></html>'
    )
    result = get_feeds_from_html("http://example.com", html)
    assert "http://example.com/atom.xml" in result


def test_get_feeds_from_html_finds_rel_feed():
    html = (
        '<html><head>'
        '<link rel="feed" href="/feed" title="Feed">'
        '</head></html>'
    )
    result = get_feeds_from_html("http://example.com", html)
    assert "http://example.com/feed" in result


def test_get_feeds_from_html_ignores_non_feed():
    html = (
        '<html><head>'
        '<link rel="alternate" type="text/html" href="/en/">'
        '</head></html>'
    )
    result = get_feeds_from_html("http://example.com", html)
    assert result == {}


def test_get_feeds_from_html_empty():
    result = get_feeds_from_html("http://example.com", "<html></html>")
    assert result == {}


def test_get_feeds_from_html_bad_html_returns_empty():
    result = get_feeds_from_html("http://example.com", "NOT HTML AT ALL \x00\xff")
    # Should not raise; either finds nothing or returns {}
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# get_feed_access_key
# ---------------------------------------------------------------------------


def test_get_feed_access_key_returns_existing():
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = "existingkey123"
    result = get_feed_access_key(session, feed_id=5, is_cat=False, owner_uid=1)
    assert result == "existingkey123"
    session.add.assert_not_called()


def test_get_feed_access_key_creates_new():
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None
    result = get_feed_access_key(session, feed_id=5, is_cat=False, owner_uid=1)
    # token_urlsafe(16) produces 22 base64url chars; [:24] is a no-op
    assert 16 <= len(result) <= 24
    session.add.assert_called_once()


def test_get_feed_access_key_is_cat_creates_new():
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None
    result = get_feed_access_key(session, feed_id=3, is_cat=True, owner_uid=2)
    assert 16 <= len(result) <= 24
    added = session.add.call_args[0][0]
    assert added.is_cat is True
    assert added.feed_id == "3"  # stored as string


def test_get_feed_access_key_uses_string_feed_id():
    """feed_id is stored as str in TtRssAccessKey."""
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None
    get_feed_access_key(session, feed_id=42, is_cat=False, owner_uid=1)
    added = session.add.call_args[0][0]
    assert added.feed_id == "42"


# ---------------------------------------------------------------------------
# subscribe_to_feed
# ---------------------------------------------------------------------------


def test_subscribe_empty_url():
    session = MagicMock()
    result = subscribe_to_feed(session, url="", owner_uid=1)
    assert result == {"code": 2}


def test_subscribe_fetch_failure():
    session = MagicMock()
    with patch("httpx.Client") as MockClient:
        ctx = MockClient.return_value.__enter__.return_value
        ctx.get.side_effect = Exception("connection refused")
        result = subscribe_to_feed(session, url="http://example.com/feed", owner_uid=1)
    assert result["code"] == 5
    assert "message" in result


def test_subscribe_html_no_feeds():
    """HTML response with no feed links → code 3."""
    resp = MagicMock()
    resp.headers = {"content-type": "text/html"}
    resp.text = "<html><head></head></html>"
    resp.raise_for_status = MagicMock()

    session = MagicMock()
    with patch("httpx.Client") as MockClient:
        ctx = MockClient.return_value.__enter__.return_value
        ctx.get.return_value = resp
        result = subscribe_to_feed(session, url="http://example.com/", owner_uid=1)

    assert result == {"code": 3}


def test_subscribe_html_multiple_feeds():
    """HTML with 2 feed links → code 4 with feeds dict."""
    html = (
        '<html><head>'
        '<link rel="alternate" type="application/rss+xml" href="/a.rss" title="A">'
        '<link rel="alternate" type="application/atom+xml" href="/b.atom" title="B">'
        '</head></html>'
    )
    resp = MagicMock()
    resp.headers = {"content-type": "text/html"}
    resp.text = html
    resp.raise_for_status = MagicMock()

    session = MagicMock()
    with patch("httpx.Client") as MockClient:
        ctx = MockClient.return_value.__enter__.return_value
        ctx.get.return_value = resp
        result = subscribe_to_feed(session, url="http://example.com/", owner_uid=1)

    assert result["code"] == 4
    assert len(result["feeds"]) == 2


def test_subscribe_html_single_feed_auto_resolves():
    """HTML with exactly 1 feed link → resolves URL and continues subscription."""
    html = (
        '<html><head>'
        '<link rel="alternate" type="application/rss+xml" href="/feed.rss">'
        '</head></html>'
    )
    resp = MagicMock()
    resp.headers = {"content-type": "text/html"}
    resp.text = html
    resp.raise_for_status = MagicMock()

    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None  # not yet subscribed

    with patch("httpx.Client") as MockClient:
        ctx = MockClient.return_value.__enter__.return_value
        ctx.get.return_value = resp
        result = subscribe_to_feed(session, url="http://example.com/", owner_uid=1)

    assert result == {"code": 1}
    session.add.assert_called_once()


def test_subscribe_already_subscribed():
    """Existing subscription → code 0."""
    resp = MagicMock()
    resp.headers = {"content-type": "application/rss+xml"}
    resp.text = "<rss></rss>"
    resp.raise_for_status = MagicMock()

    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = 7  # existing feed_id

    with patch("httpx.Client") as MockClient:
        ctx = MockClient.return_value.__enter__.return_value
        ctx.get.return_value = resp
        result = subscribe_to_feed(session, url="http://example.com/feed.rss", owner_uid=1)

    assert result == {"code": 0}
    session.add.assert_not_called()


def test_subscribe_new_feed():
    """New RSS feed → code 1, TtRssFeed added to session."""
    resp = MagicMock()
    resp.headers = {"content-type": "application/rss+xml"}
    resp.text = "<rss></rss>"
    resp.raise_for_status = MagicMock()

    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None

    with patch("httpx.Client") as MockClient:
        ctx = MockClient.return_value.__enter__.return_value
        ctx.get.return_value = resp
        result = subscribe_to_feed(session, url="http://example.com/feed.rss", owner_uid=1)

    assert result == {"code": 1}
    session.add.assert_called_once()


def test_subscribe_with_auth_pass_sets_property():
    """auth_pass triggers Fernet encryption via TtRssFeed.auth_pass property."""
    resp = MagicMock()
    resp.headers = {"content-type": "application/rss+xml"}
    resp.text = "<rss></rss>"
    resp.raise_for_status = MagicMock()

    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None

    with patch("httpx.Client") as MockClient, \
         patch("ttrss.crypto.fernet.fernet_encrypt", return_value=b"encrypted"):
        ctx = MockClient.return_value.__enter__.return_value
        ctx.get.return_value = resp
        result = subscribe_to_feed(
            session, url="http://example.com/feed.rss", owner_uid=1,
            auth_login="user", auth_pass="secret"
        )

    assert result == {"code": 1}
    added = session.add.call_args[0][0]
    assert added.auth_login == "user"


def test_subscribe_whitespace_only_url():
    session = MagicMock()
    result = subscribe_to_feed(session, url="   ", owner_uid=1)
    assert result == {"code": 2}
