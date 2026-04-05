"""Unit tests for ttrss/http/client.py — pure sync URL-manipulation functions.

Async functions (fetch_file_contents, url_is_html) are excluded; this file covers
only the synchronous, side-effect-free helpers that can be tested without a network.

PHP source files:
  ttrss/include/functions2.php  (fix_url, validate_feed_url, rewrite_relative_url,
                                  get_feeds_from_html)
"""
from __future__ import annotations

import pytest

from ttrss.http.client import fix_url, rewrite_relative_url, validate_feed_url
from ttrss.feeds.ops import get_feeds_from_html


# ===========================================================================
# fix_url
# ===========================================================================


def test_fix_url_adds_http_scheme():
    """
    Source: ttrss/include/functions2.php:fix_url line 1709
    PHP:    if (strpos($url, '://') === false) { $url = 'http://' . $url; }
    Assert: bare domain with no scheme gets 'http://' prepended and trailing slash appended.
    """
    assert fix_url("example.com") == "http://example.com/"


def test_fix_url_feed_scheme_replaced_with_http():
    """
    Source: ttrss/include/functions2.php:fix_url lines 1711-1712
    PHP:    else if (substr($url, 0, 5) == 'feed:') { $url = 'http:' . substr($url, 5); }
    Assert: 'feed://' prefix is rewritten to 'http://', trailing slash appended.
    """
    assert fix_url("feed://x.com") == "http://x.com/"


def test_fix_url_https_with_path_unchanged():
    """
    Source: ttrss/include/functions2.php:fix_url lines 1717-1718
    PHP:    if (strpos($url, '/', strpos($url, ':') + 3) === false) { $url .= '/'; }
    Assert: URL that already has a scheme and a path component is returned unchanged.
    """
    assert fix_url("https://x.com/path") == "https://x.com/path"


def test_fix_url_bare_https_domain_gets_trailing_slash():
    """
    Source: ttrss/include/functions2.php:fix_url lines 1717-1718
    PHP:    if (strpos($url, '/', strpos($url, ':') + 3) === false) { $url .= '/'; }
    Assert: https URL with no path component (bare domain) gets a trailing slash appended.
    """
    assert fix_url("https://x.com") == "https://x.com/"


def test_fix_url_degenerate_returns_empty_string():
    """
    Source: ttrss/include/functions2.php:fix_url lines 1721-1724
    PHP:    if ($url != "http:///") return $url; else return '';
    Assert: The degenerate URL 'http:///' is returned as an empty string.
    """
    assert fix_url("http:///") == ""


def test_fix_url_http_with_deep_path_unchanged():
    """
    Source: ttrss/include/functions2.php:fix_url lines 1717-1718
    PHP:    if (strpos($url, '/', strpos($url, ':') + 3) === false) { $url .= '/'; }
    Assert: URL with host and multi-segment path is returned unchanged (path already present).
    """
    assert fix_url("http://x.com/a/b") == "http://x.com/a/b"


# ===========================================================================
# validate_feed_url
# ===========================================================================


def test_validate_feed_url_http_is_valid():
    """
    Source: ttrss/include/functions2.php:validate_feed_url lines 1727-1732
    PHP:    return ($parts['scheme'] == 'http' || ...);
    Assert: URL with 'http' scheme returns True.
    """
    assert validate_feed_url("http://x.com") is True


def test_validate_feed_url_https_is_valid():
    """
    Source: ttrss/include/functions2.php:validate_feed_url lines 1727-1732
    PHP:    return (... || $parts['scheme'] == 'https');
    Assert: URL with 'https' scheme returns True.
    """
    assert validate_feed_url("https://x.com") is True


def test_validate_feed_url_feed_scheme_is_valid():
    """
    Source: ttrss/include/functions2.php:validate_feed_url lines 1727-1732
    PHP:    return (... || $parts['scheme'] == 'feed' || ...);
    Assert: URL with 'feed' scheme returns True.
    """
    assert validate_feed_url("feed://x.com") is True


def test_validate_feed_url_ftp_is_invalid():
    """
    Source: ttrss/include/functions2.php:validate_feed_url lines 1727-1732
    PHP:    return ($parts['scheme'] == 'http' || $parts['scheme'] == 'feed' || $parts['scheme'] == 'https');
    Assert: URL with 'ftp' scheme returns False (not in allowed set).
    """
    assert validate_feed_url("ftp://x.com") is False


def test_validate_feed_url_javascript_is_invalid():
    """
    Source: ttrss/include/functions2.php:validate_feed_url lines 1727-1732
    PHP:    return ($parts['scheme'] == 'http' || $parts['scheme'] == 'feed' || $parts['scheme'] == 'https');
    Assert: 'javascript:' pseudo-URL returns False (security: XSS vector rejected).
    """
    assert validate_feed_url("javascript:alert()") is False


def test_validate_feed_url_no_scheme_is_invalid():
    """
    Source: ttrss/include/functions2.php:validate_feed_url lines 1727-1732
    PHP:    $parts = parse_url($url); return ($parts['scheme'] == ...);
    Assert: Bare domain with no scheme has empty/missing scheme → returns False.
    """
    assert validate_feed_url("example.com") is False


# ===========================================================================
# rewrite_relative_url
# ===========================================================================


def test_rewrite_relative_url_simple_relative():
    """
    Source: ttrss/include/functions2.php:rewrite_relative_url lines 1981-1993
    PHP:    $dir = $parts['path']; ... $parts['path'] = $dir . $rel_url; return build_url($parts);
    Assert: Simple relative filename resolved against base URL with trailing slash.
    """
    result = rewrite_relative_url("http://x.com/", "img.png")
    assert result == "http://x.com/img.png"


def test_rewrite_relative_url_dotdot_traversal():
    """
    Source: ttrss/include/functions2.php:rewrite_relative_url lines 1986-1990
    PHP:    if (substr($dir, -1) !== '/') { $dir = dirname($parts['path']); ... }
            $parts['path'] = $dir . $rel_url;
    Assert: '../img.png' relative to '/a/b' resolves to '/img.png' via dirname().

    Note: PHP dirname('/a/b') = '/a', so path becomes '/a/' + '../img.png' = '/a/../img.png'.
          The Python implementation mirrors this exact behavior — posixpath.dirname + concatenate
          without normalizing '..'.  The expected value matches what build_url() returns.
    """
    result = rewrite_relative_url("http://x.com/a/b", "../img.png")
    # PHP/Python: dir = dirname('/a/b') = '/a', appended → '/a/' + '../img.png'
    assert result == "http://x.com/a/../img.png"


def test_rewrite_relative_url_absolute_url_unchanged():
    """
    Source: ttrss/include/functions2.php:rewrite_relative_url line 1967
    PHP:    if (strpos($rel_url, ":") !== false) { return $rel_url; }
    Assert: Absolute URL (contains ':') is returned unchanged — no resolution attempted.
    """
    result = rewrite_relative_url("http://x.com/", "http://other.com/x")
    assert result == "http://other.com/x"


def test_rewrite_relative_url_protocol_relative_unchanged():
    """
    Source: ttrss/include/functions2.php:rewrite_relative_url line 1971
    PHP:    else if (strpos($rel_url, "//") === 0) { return $rel_url; }
    Assert: Protocol-relative URL ('//...') is returned unchanged.
    """
    result = rewrite_relative_url("http://x.com/", "//cdn.com/x")
    assert result == "//cdn.com/x"


# ===========================================================================
# get_feeds_from_html  (imported from ttrss.feeds.ops; uses fix_url internally)
# ===========================================================================

_HTML_WITH_RSS_LINK = """\
<!DOCTYPE html>
<html>
  <head>
    <title>Test</title>
    <link rel="alternate" type="application/rss+xml"
          title="My RSS Feed" href="/feed.rss" />
  </head>
  <body></body>
</html>
"""


def test_get_feeds_from_html_finds_rss_link():
    """
    Source: ttrss/include/functions2.php:get_feeds_from_html lines 1787-1813
    PHP:    foreach ($xpath->query('//link[@rel="alternate"]') as $link) { ... }
            if (strpos($type, "rss") !== false || strpos($type, "atom") !== false) { ... }
    Assert: RSS alternate link is discovered and returned as {abs_url: title} dict entry.
    """
    result = get_feeds_from_html("http://x.com/", _HTML_WITH_RSS_LINK)
    assert isinstance(result, dict)
    assert len(result) >= 1
    # The relative href '/feed.rss' must have been resolved to an absolute URL
    found_urls = list(result.keys())
    assert any("feed.rss" in u for u in found_urls), f"Expected feed.rss in {found_urls}"
    assert any(u.startswith("http://x.com") for u in found_urls), (
        f"Expected absolute URL rooted at http://x.com in {found_urls}"
    )


# ---------------------------------------------------------------------------
# is_html, build_url, url_is_html, SELF_USER_AGENT — cover lines 199-214, 217-225
# ---------------------------------------------------------------------------

from ttrss.http.client import is_html, build_url, SELF_USER_AGENT


class TestIsHtml:
    """Source: ttrss/include/functions2.php:is_html (lines 1815-1816)
    PHP: return preg_match("/<html|DOCTYPE html/i", substr($content, 0, 20))"""

    def test_html_tag_detected(self):
        """Source: functions2.php:1816 '<html' match. Assert: b'<html…' → True."""
        assert is_html(b"<html><body>hi</body></html>") is True

    def test_doctype_detected(self):
        """Source: functions2.php:1816 'DOCTYPE html' match. Assert: True."""
        assert is_html(b"<!DOCTYPE html><html>") is True

    def test_doctype_case_insensitive(self):
        """Source: functions2.php:1816 /i flag. Assert: lowercase also True."""
        assert is_html(b"<!doctype html><html>") is True

    def test_xml_feed_is_not_html(self):
        """Source: functions2.php:1816 only first 20 bytes checked. Assert: XML → False."""
        assert is_html(b"<?xml version='1.0'?>") is False

    def test_rss_feed_is_not_html(self):
        """Source: functions2.php:1816. Assert: RSS content → False."""
        assert is_html(b"<rss version='2.0'>") is False

    def test_empty_bytes_is_not_html(self):
        """Source: functions2.php:1816. Assert: empty bytes → False."""
        assert is_html(b"") is False

    def test_only_first_20_bytes_checked(self):
        """Source: functions2.php:1816 substr($content, 0, 20). Assert: <html after 20 bytes → False."""
        content = b"X" * 20 + b"<html>"
        assert is_html(content) is False


class TestBuildUrl:
    """Source: ttrss/include/functions2.php:build_url (lines 1953-1960)
    PHP: return $parts['scheme'].'://'.$parts['host'].$parts['path']"""

    def test_basic_url_assembly(self):
        """Source: functions2.php:1957. Assert: scheme+host+path assembled."""
        parts = {"scheme": "https", "host": "example.com", "path": "/feed"}
        assert build_url(parts) == "https://example.com/feed"

    def test_root_path(self):
        """Source: functions2.php:1957. Assert: root path /."""
        parts = {"scheme": "http", "host": "x.com", "path": "/"}
        assert build_url(parts) == "http://x.com/"

    def test_empty_path(self):
        """Source: functions2.php:1957. Assert: empty path produces bare host."""
        parts = {"scheme": "http", "host": "x.com", "path": ""}
        assert build_url(parts) == "http://x.com"


class TestSelfUserAgent:
    """Source: ttrss/include/functions.php line 380-381 — SELF_USER_AGENT constant."""

    def test_self_user_agent_is_string(self):
        """Source: functions.php:380 SELF_USER_AGENT constant. Assert: non-empty string."""
        assert isinstance(SELF_USER_AGENT, str)
        assert len(SELF_USER_AGENT) > 0

    def test_self_user_agent_contains_ttrss(self):
        """Source: functions.php SELF_USER_AGENT. Assert: identifies as Tiny Tiny RSS."""
        assert "Tiny Tiny RSS" in SELF_USER_AGENT or "ttrss" in SELF_USER_AGENT.lower()


# ---------------------------------------------------------------------------
# Async fetch_file_contents and url_is_html — lines 84-147, 203-214
# Use pytest-anyio (anyio already installed) to run async tests.
# ---------------------------------------------------------------------------

import anyio
import pytest


def _run(coro):
    """Run a coroutine synchronously using anyio."""
    return anyio.from_thread.run_sync(lambda: None)  # placeholder import


# Use anyio.run() directly — no fixture needed for simple coroutine tests.

from unittest.mock import AsyncMock, MagicMock, patch
from ttrss.http.client import fetch_file_contents, url_is_html


class TestFetchFileContents:
    """Source: ttrss/include/functions.php:fetch_file_contents (lines 343-495)
    PHP: curl-based async-equivalent HTTP fetch."""

    def test_fetch_returns_bytes_on_200(self):
        """
        Source: ttrss/include/functions.php:fetch_file_contents line 138
        PHP: return $res (curl response body)
        Assert: 200 response → bytes content returned.
        """
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"feed content"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("ttrss.http.client.httpx.AsyncClient", return_value=mock_client):
            result = anyio.from_thread.run_sync(
                lambda: anyio.run(fetch_file_contents, "http://x.com/feed.rss")
            ) if False else None

        # Equivalent synchronous test using asyncio.run
        import asyncio

        async def _test():
            with patch("ttrss.http.client.httpx.AsyncClient", return_value=mock_client):
                return await fetch_file_contents("http://x.com/feed.rss")

        result = asyncio.run(_test())
        assert result == b"feed content"

    def test_fetch_returns_none_on_404(self):
        """
        Source: ttrss/include/functions.php:fetch_file_contents line 131
        PHP: $fetch_last_error_code != 200 → returns false
        Assert: 404 → None.
        """
        import asyncio

        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)

        async def _test():
            with patch("ttrss.http.client.httpx.AsyncClient", return_value=mock_client):
                return await fetch_file_contents("http://x.com/missing")

        assert asyncio.run(_test()) is None

    def test_fetch_returns_none_on_http_error(self):
        """
        Source: ttrss/include/functions.php:fetch_file_contents line 140-144
        PHP: $fetch_last_error = curl_error($ch); returns false
        Assert: httpx.HTTPError → None, no exception raised.
        """
        import asyncio
        import httpx

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))

        async def _test():
            with patch("ttrss.http.client.httpx.AsyncClient", return_value=mock_client):
                return await fetch_file_contents("http://x.com/")

        assert asyncio.run(_test()) is None

    def test_fetch_sets_user_agent_header(self):
        """
        Source: ttrss/include/functions.php:380-381 CURLOPT_USERAGENT → SELF_USER_AGENT
        Assert: User-Agent header sent in request.
        """
        import asyncio

        captured_headers = {}

        async def fake_get(url, headers=None, auth=None):
            captured_headers.update(headers or {})
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b""
            return mock_resp

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = fake_get

        async def _test():
            with patch("ttrss.http.client.httpx.AsyncClient", return_value=mock_client):
                await fetch_file_contents("http://x.com/")

        asyncio.run(_test())
        assert "User-Agent" in captured_headers

    def test_fetch_sets_referer_header(self):
        """
        Source: ttrss/include/functions.php:383 CURLOPT_REFERER = $url
        Assert: Referer header always set to the request URL.
        """
        import asyncio

        captured_headers = {}

        async def fake_get(url, headers=None, auth=None):
            captured_headers.update(headers or {})
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b""
            return mock_resp

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = fake_get

        async def _test():
            with patch("ttrss.http.client.httpx.AsyncClient", return_value=mock_client):
                await fetch_file_contents("http://x.com/feed")

        asyncio.run(_test())
        assert captured_headers.get("Referer") == "http://x.com/feed"

    def test_fetch_with_auth_credentials(self):
        """
        Source: ttrss/include/functions.php line ~390 CURLOPT_USERPWD
        Assert: login+password → BasicAuth passed to client.
        """
        import asyncio
        import httpx

        captured_auth = {}

        async def fake_get(url, headers=None, auth=None):
            captured_auth["auth"] = auth
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b""
            return mock_resp

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = fake_get

        async def _test():
            with patch("ttrss.http.client.httpx.AsyncClient", return_value=mock_client):
                await fetch_file_contents("http://x.com/", login="user", password="pass")

        asyncio.run(_test())
        assert isinstance(captured_auth.get("auth"), httpx.BasicAuth)

    def test_url_is_html_true_for_html_response(self):
        """
        Source: ttrss/include/functions2.php:url_is_html line 1820
        PHP: return is_html(fetch_file_contents($url))
        Assert: HTML content → True.
        """
        import asyncio

        async def _test():
            with patch("ttrss.http.client.fetch_file_contents", new=AsyncMock(return_value=b"<html>")):
                return await url_is_html("http://x.com/")

        assert asyncio.run(_test()) is True

    def test_url_is_html_false_for_xml_response(self):
        """
        Source: ttrss/include/functions2.php:url_is_html line 1820
        PHP: return is_html(false) → falsy
        Assert: XML content → False.
        """
        import asyncio

        async def _test():
            with patch("ttrss.http.client.fetch_file_contents", new=AsyncMock(return_value=b"<?xml")):
                return await url_is_html("http://x.com/feed.xml")

        assert asyncio.run(_test()) is False

    def test_url_is_html_false_when_fetch_fails(self):
        """
        Source: ttrss/include/functions2.php:url_is_html — PHP: is_html(false) falsy
        Assert: fetch returns None (404/error) → False.
        """
        import asyncio

        async def _test():
            with patch("ttrss.http.client.fetch_file_contents", new=AsyncMock(return_value=None)):
                return await url_is_html("http://x.com/missing")

        assert asyncio.run(_test()) is False
