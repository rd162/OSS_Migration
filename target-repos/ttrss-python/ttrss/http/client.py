"""
HTTP client — feed fetching and URL normalization helpers.

Source: ttrss/include/functions.php:fetch_file_contents (lines 343-495)
        ttrss/include/functions2.php:fix_url (lines 1708-1725)
        ttrss/include/functions2.php:validate_feed_url (lines 1727-1732)
        ttrss/include/functions2.php:is_html (lines 1815-1817)
        ttrss/include/functions2.php:url_is_html (lines 1819-1821)
        ttrss/include/functions2.php:build_url (lines 1953-1955)
        ttrss/include/functions2.php:rewrite_relative_url (lines 1965-1993)
Adapted: PHP cURL replaced by httpx async (ADR-0015); global error variables replaced by
         return value of None and logged errors.  SSL verification hardened (G4 requirement).

# Eliminated (stdlib): ttrss/include/functions2.php::geturl — httpx handles HTTP; no direct equivalent.
# Eliminated (stdlib): ttrss/include/functions2.php::convertUrlQuery — urllib.parse replaces.
# Eliminated (client-side): ttrss/include/functions.php::getFeedIcon — favicon fetched client-side.
# Eliminated (browser-specific): ttrss/include/functions2.php::add_feed_url — Firefox-specific URL builder.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)  # New: no PHP equivalent — Python logging setup.

# Source: ttrss/include/functions.php line 40 — define_default('FEED_FETCH_TIMEOUT', 45)
# Source: ttrss/include/functions.php line 42 — define_default('FEED_FETCH_NO_CACHE_TIMEOUT', 15)
# Adapted: PHP uses separate cURL connect/read timeouts; Python httpx uses a single Timeout object.
# New: write=10.0 and pool=5.0 have no PHP cURL equivalent — added for httpx Timeout completeness.
FEED_FETCH_TIMEOUT = httpx.Timeout(connect=10.0, read=45.0, write=10.0, pool=5.0)

# Source: ttrss/include/functions.php line 42 — define_default('FEED_FETCH_NO_CACHE_TIMEOUT', 15)
# New: write=10.0 and pool=5.0 have no PHP cURL equivalent — added for httpx Timeout completeness.
FEED_FETCH_NO_CACHE_TIMEOUT = httpx.Timeout(connect=10.0, read=15.0, write=10.0, pool=5.0)


async def fetch_file_contents(
    url: str,
    type: Optional[str] = None,
    login: Optional[str] = None,
    password: Optional[str] = None,
    post_query: Optional[str] = None,
    timeout: Optional[httpx.Timeout] = None,
    timestamp: int = 0,
    useragent: Optional[str] = None,
) -> Optional[bytes]:
    """
    Fetch URL contents using httpx async, returning raw bytes or None on failure.

    Source: ttrss/include/functions.php:fetch_file_contents (lines 343-495)
    Adapted: PHP cURL (CURLOPT_URL, CURLOPT_TIMEOUT, CURLOPT_USERPWD, CURLOPT_HTTPHEADER,
             CURLOPT_FOLLOWLOCATION, CURLOPT_MAXREDIRS, CURLOPT_RETURNTRANSFER) replaced
             by httpx.AsyncClient with equivalent settings (ADR-0015).
    Note: ttrss/include/functions.php line 343 — $url = str_replace(' ', '%20', $url).
          Preserved below via url.replace(' ', '%20').
    Note: ttrss/include/functions.php lines 345-357 — PHP uses globals $fetch_last_error,
          $fetch_last_error_code, $fetch_last_content_type to communicate errors to callers.
          Python returns None on failure and logs the error; no globals used.
    Note: ttrss/include/functions.php lines 359-372 — PHP checks ini_get("safe_mode") and
          falls back to geturl() for redirect handling; safe_mode path not reproduced.
          Adapted: Python httpx handles redirects natively via follow_redirects=True (always
          enabled); the safe_mode conditional branch is not reproduced.
    Note: ttrss/include/functions.php line 378 — CURLOPT_SSL_VERIFYPEER set to false in PHP;
          httpx verifies SSL by default (G4 security hardening — intentional divergence).
    Note: ttrss/include/functions.php line 379 — CURLOPT_HTTPAUTH = CURLAUTH_ANY in PHP
          (allows digest, NTLM, etc. in addition to Basic).
          Adapted: Python uses httpx.BasicAuth only; digest/NTLM auth not reproduced.
    Note: ttrss/include/functions.php line 423 — CURLOPT_USERAGENT uses SELF_USER_AGENT
          constant when no useragent is supplied.  Python sends no User-Agent header when
          useragent is None; SELF_USER_AGENT default not reproduced.
    Note: ttrss/include/functions.php — CURLOPT_ENCODING (accept-encoding for gzip/deflate).
          httpx performs transparent content-encoding negotiation automatically; equivalent
          behaviour without explicit configuration.
    """
    # Source: ttrss/include/functions.php line 343 — $url = str_replace(' ', '%20', $url)
    url = url.replace(" ", "%20")

    headers: dict[str, str] = {}

    # Source: ttrss/include/functions.php line ~375 — CURLOPT_HTTPHEADER with If-Modified-Since
    if timestamp > 0:
        # Source: ttrss/include/functions.php — $timestamp used as If-Modified-Since value
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        headers["If-Modified-Since"] = dt.strftime("%a, %d %b %Y %H:%M:%S GMT")

    # Source: ttrss/include/functions.php line 423 — CURLOPT_HTTPHEADER Content-Type response filter
    # Adapted: PHP passes $type as a response Content-Type filter (CURLINFO_CONTENT_TYPE check);
    #          Python sends it as an Accept request header — a behavioural difference.  PHP does
    #          not send $type in the request; it validates the response Content-Type after fetch.
    if type:
        headers["Accept"] = type

    # Source: ttrss/include/functions.php line 423 — CURLOPT_USERAGENT ($useragent parameter)
    if useragent:
        headers["User-Agent"] = useragent

    auth = None
    if login and password:
        # Source: ttrss/include/functions.php line ~390 — CURLOPT_USERPWD "$login:$pass"
        auth = httpx.BasicAuth(login, password)

    # Source: ttrss/include/functions.php line 40 — FEED_FETCH_TIMEOUT default (45 s read)
    # Source: ttrss/include/functions.php line 42 — FEED_FETCH_NO_CACHE_TIMEOUT (15 s read); caller may override.
    effective_timeout = timeout or FEED_FETCH_TIMEOUT

    try:
        async with httpx.AsyncClient(
            timeout=effective_timeout,
            # Source: ttrss/include/functions.php lines 374-376 — CURLOPT_FOLLOWLOCATION set
            # conditionally (only when safe_mode is off); safe_mode branch not reproduced.
            # Adapted: Python always enables follow_redirects=True (safe_mode does not exist).
            follow_redirects=True,
            max_redirects=20,  # Source: ttrss/include/functions.php — CURLOPT_MAXREDIRS default 20
        ) as client:
            if post_query is not None:
                # Source: ttrss/include/functions.php — CURLOPT_POST + CURLOPT_POSTFIELDS
                resp = await client.post(url, content=post_query.encode(), headers=headers, auth=auth)
            else:
                resp = await client.get(url, headers=headers, auth=auth)

            if resp.status_code >= 400:
                logger.warning(
                    "fetch_file_contents: HTTP %d for %r",
                    resp.status_code, url,
                )
                return None  # New: no PHP equivalent for this guard — PHP uses $fetch_last_error_code; Python returns None.

            return resp.content

    except httpx.HTTPError as exc:
        # Source: ttrss/include/functions.php — $fetch_last_error = curl_error($ch); returns false
        # Adapted: PHP stores error in global; Python logs and returns None.
        logger.warning("fetch_file_contents: HTTP error fetching %r: %s", url, exc)
        return None
    except Exception as exc:  # New: no PHP equivalent — catch unexpected errors (DNS, timeout, etc.)
        logger.warning("fetch_file_contents: unexpected error fetching %r: %s", url, exc)
        return None


def fix_url(url: str) -> str:
    """
    Normalize feed URL: add missing scheme, convert feed: to http:, append trailing slash.

    Source: ttrss/include/functions2.php:fix_url (lines 1708-1725)
    Adapted: PHP strpos/substr replaced by Python str methods; behavior preserved exactly.
    """
    # Source: ttrss/include/functions2.php line 1709 — if (strpos($url, '://') === false)
    if "://" not in url:
        url = "http://" + url
    # Source: ttrss/include/functions2.php line 1711 — else if (substr($url, 0, 5) == 'feed:')
    elif url.startswith("feed:"):
        url = "http:" + url[5:]  # Source: ttrss/include/functions2.php line 1712 — 'http:' . substr($url, 5)

    # Source: ttrss/include/functions2.php lines 1716-1719 — append slash if no slash after scheme+host
    # PHP: strpos($url, '/', strpos($url, ':') + 3) === false
    colon_pos = url.index(":")
    if "/" not in url[colon_pos + 3:]:
        url += "/"

    # Source: ttrss/include/functions2.php lines 1721-1724 — return '' for degenerate 'http:///'
    if url == "http:///":
        return ""
    return url


def validate_feed_url(url: str) -> bool:
    """
    Return True if the URL scheme is http, https, or feed.

    Source: ttrss/include/functions2.php:validate_feed_url (lines 1727-1732)
    Adapted: PHP parse_url() replaced by urllib.parse.urlparse(); scheme comparison identical.
    """
    # Source: ttrss/include/functions2.php line 1728 — $parts = parse_url($url)
    # Source: ttrss/include/functions2.php line 1730 — $parts['scheme'] == 'http' || 'feed' || 'https'
    parts = urlparse(url)
    return parts.scheme in ("http", "https", "feed")


def is_html(content: bytes) -> bool:
    """
    Return True if the content looks like HTML (checks first 20 bytes).

    Source: ttrss/include/functions2.php:is_html (lines 1815-1817)
    Adapted: PHP preg_match on a string replaced by bytes search; substr(0,20) limit preserved.
             PHP operates on a decoded string; Python receives raw bytes — callers must not
             decode before passing (behavioural difference: bytes vs. string input).
    """
    # Source: ttrss/include/functions2.php line 1816 — preg_match("/<html|DOCTYPE html/i", substr($content, 0, 20))
    head = content[:20].lower()
    return b"<html" in head or b"doctype html" in head


async def url_is_html(url: str, login: Optional[str] = None, password: Optional[str] = None) -> bool:
    """
    Fetch URL and return True if the response content is HTML.

    Source: ttrss/include/functions2.php:url_is_html (lines 1819-1821)
    Adapted: PHP call to fetch_file_contents() preserved; Python awaits async version.
    """
    # Source: ttrss/include/functions2.php line 1820 — return is_html(fetch_file_contents($url, ...))
    content = await fetch_file_contents(url, login=login, password=password)
    if content is None:
        return False  # New: no PHP equivalent — PHP is_html(false) returns falsy; Python explicit guard.
    return is_html(content)


def build_url(parts: dict) -> str:
    """
    Assemble URL from parsed parts dict (scheme, host, path).

    Source: ttrss/include/functions2.php:build_url (lines 1953-1955)
    Adapted: PHP array dict replaced by Python dict; output format identical.
    Note: ttrss/include/functions2.php line 1954 — only scheme/host/path used; query/fragment dropped.
          This matches PHP behaviour: build_url() ignores query strings and fragments.
    """
    # Source: ttrss/include/functions2.php line 1954 — $parts['scheme'] . "://" . $parts['host'] . $parts['path']
    return f"{parts['scheme']}://{parts['host']}{parts['path']}"


def rewrite_relative_url(url: str, rel_url: str) -> str:
    """
    Resolve rel_url against base url, returning an absolute URL.

    Source: ttrss/include/functions2.php:rewrite_relative_url (lines 1965-1993)
    Adapted: PHP parse_url()/build_url() replaced by urllib.parse.urlparse()/urljoin()-style
             logic; PHP behaviour preserved exactly (query strings dropped via build_url).
    """
    # Source: ttrss/include/functions2.php line 1966 — if (strpos($rel_url, ":") !== false) return $rel_url
    if ":" in rel_url:
        return rel_url

    # Source: ttrss/include/functions2.php line 1968 — else if (strpos($rel_url, "://") !== false) return $rel_url
    # Note: this branch is unreachable because line 1966 already returns for any ':'-containing URL,
    #       which is a superset of all '://'-containing URLs.  Reproduced verbatim for faithfulness.

    # Source: ttrss/include/functions2.php line 1970 — protocol-relative URL (// prefix) returned as-is
    if rel_url.startswith("//"):
        return rel_url

    parsed = urlparse(url)
    parts = {
        "scheme": parsed.scheme,
        "host": parsed.netloc,
        "path": parsed.path,
    }

    # Source: ttrss/include/functions2.php line 1973 — if (strpos($rel_url, "/") === 0)
    if rel_url.startswith("/"):
        # Source: ttrss/include/functions2.php lines 1975-1978 — absolute path: replace path component
        parts["path"] = rel_url
        return build_url(parts)

    # Source: ttrss/include/functions2.php lines 1981-1992 — relative path: resolve against dir
    if not parts["path"]:
        parts["path"] = "/"  # Source: ttrss/include/functions2.php line 1983 — if (!isset($parts['path'])) $parts['path'] = '/'

    dir_path = parts["path"]
    # Source: ttrss/include/functions2.php lines 1986-1988 — if last char != '/' use dirname
    if not dir_path.endswith("/"):
        import posixpath  # New: no PHP equivalent — PHP uses native dirname(); Python uses posixpath for cross-platform POSIX path semantics.
        dir_path = posixpath.dirname(dir_path)
        if dir_path != "/":
            dir_path += "/"  # Source: ttrss/include/functions2.php line 1988 — $dir !== '/' && $dir .= '/'

    # Source: ttrss/include/functions2.php line 1990 — $parts['path'] = $dir . $rel_url
    parts["path"] = dir_path + rel_url
    return build_url(parts)
