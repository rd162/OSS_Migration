"""
HTML sanitization — strip harmful tags/attributes, rewrite URLs, fire HOOK_SANITIZE.

Source: ttrss/include/functions2.php:sanitize (lines 831-965)
        ttrss/include/functions2.php:strip_harmful_tags (lines 967-997)
Adapted: PHP DOMDocument/DOMXPath replaced by lxml.html; pluggy replaces PHP PluginHost
         get_hooks loop.  PHP $doc passed by reference to plugins; Python passes lxml element
         tree object (mutable, same effect).
"""
from __future__ import annotations

import logging
from typing import Optional

import lxml.html

logger = logging.getLogger(__name__)  # New: no PHP equivalent — Python logging setup.

# Source: ttrss/include/functions2.php:sanitize lines 903-913 — $allowed_elements array.
# Adapted: PHP array literal converted to frozenset for O(1) membership testing.
# Note: ttrss/include/functions2.php line 915 — PHP adds 'iframe' conditionally based on
#       $_SESSION['hasSandbox'].  Python does not track hasSandbox; 'iframe' is excluded
#       from this default set and controlled by the has_sandbox parameter of sanitize().
# Note: 'body' and 'html' are included to mirror PHP's $allowed_elements array, but they
#       are dead entries for article fragments: lxml.html.fragment_fromstring(create_parent='div')
#       strips outer document-level elements before the allowlist check is applied.
_ALLOWED_ELEMENTS: frozenset[str] = frozenset({
    "a", "address", "audio", "article", "aside",
    "b", "bdi", "bdo", "big", "blockquote", "body", "br",
    "caption", "cite", "center", "code", "col", "colgroup",
    "data", "dd", "del", "details", "div", "dl", "font",
    "dt", "em", "footer", "figure", "figcaption",
    "h1", "h2", "h3", "h4", "h5", "h6", "header", "html", "i",
    "img", "ins", "kbd", "li", "main", "mark", "nav", "noscript",
    "ol", "p", "pre", "q", "ruby", "rp", "rt", "s", "samp", "section",
    "small", "source", "span", "strike", "strong", "sub", "summary",
    "sup", "table", "tbody", "td", "tfoot", "th", "thead", "time",
    "tr", "track", "tt", "u", "ul", "var", "wbr", "video",
})

# Source: ttrss/include/functions2.php:sanitize line 917 — $disallowed_attributes = array('id', 'style', 'class')
_DISALLOWED_ATTRIBUTES: frozenset[str] = frozenset({"id", "style", "class"})


def sanitize(
    content: str,
    # Source: ttrss/include/functions2.php:sanitize line 831 — $force_remove_images parameter
    force_remove_images: bool = False,
    # Source: ttrss/include/functions2.php:sanitize line 831 — $owner_uid parameter
    owner_uid: Optional[int] = None,
    # Source: ttrss/include/functions2.php:sanitize line 831 — $site_url parameter
    site_url: Optional[str] = None,
    # Source: ttrss/include/functions2.php:sanitize line 831 — $highlight_words parameter
    highlight_words: Optional[list] = None,
    # Source: ttrss/include/functions2.php:sanitize line 831 — $article_id parameter (passed to HOOK_SANITIZE at line 920)
    article_id: Optional[int] = None,
    # Source: ttrss/include/functions2.php:sanitize line 915 — $_SESSION['hasSandbox'] check
    # Adapted: PHP reads $_SESSION['hasSandbox']; Python uses explicit parameter.
    has_sandbox: bool = False,
) -> str:
    """
    Sanitize HTML article content: rewrite URLs, remove harmful elements/attributes,
    invoke HOOK_SANITIZE plugins, optionally highlight search words.

    Source: ttrss/include/functions2.php:sanitize (lines 831-965)
    Adapted: PHP DOMDocument/DOMXPath replaced by lxml.html.fragment_fromstring (create_parent='div')
             so article content fragments are handled correctly without implicit HTML/body wrappers.
             PHP global $_SESSION['uid'] fallback for owner replaced by owner_uid parameter.
    Note: ttrss/include/functions2.php lines 836-838 — PHP adds a charset <head> to force UTF-8
          parsing.  Python lxml handles UTF-8 natively; charset hack not reproduced.
    Note: ttrss/include/functions2.php line 832 — PHP reads $_SESSION['uid'] for $owner when
          $owner is false.  Python callers must pass owner_uid explicitly; no session fallback here.
    Note: ttrss/include/functions2.php lines 864-869 — PHP image caching via CACHE_DIR.
          Image caching not reproduced; src is rewritten to absolute URL only.
    Note: ttrss/include/functions2.php lines 875-876 — PHP checks $_SESSION['bw_limit'] to
          force-strip images for bandwidth-limited users.  Python does not implement bw_limit;
          images are stripped only when force_remove_images=True or STRIP_IMAGES pref is set.
    Note: ttrss/include/functions2.php lines 933-959 — highlight_words DOM traversal.
          Highlight logic is not yet implemented; deferred (no callers in Phase 2 scope).
    Note: lxml.html.tostring emits the <div> wrapper added by fragment_fromstring(create_parent='div');
          PHP saveHTML() emits a full HTML document. Output structure differs.
    """
    # Source: ttrss/include/functions2.php line 834 — $res = trim($str); if (!$res) return ''
    res = content.strip() if content else ""
    if not res:
        return ""

    # Source: ttrss/include/functions2.php lines 844-846 — DOMDocument + DOMXPath setup
    try:
        # Adapted: PHP uses DOMDocument::loadHTML($charset_hack . $res) which wraps in full document.
        #          Python uses fragment_fromstring to process article fragments without wrapping.
        doc = lxml.html.fragment_fromstring(res, create_parent="div")
    except Exception as exc:  # New: no PHP equivalent — PHP crashes or silently fails; Python logs and returns original.
        logger.warning("sanitize: failed to parse HTML for article_id=%s: %s", article_id, exc)
        return res

    # Source: ttrss/include/functions2.php lines 848-895 — process <a href> and <img src>
    if site_url:
        from ttrss.http.client import rewrite_relative_url  # New: no PHP equivalent — lazy import avoids circular dependency at module load time.
        for entry in doc.xpath(".//a[@href]|.//img[@src]"):
            if entry.tag == "a" and entry.get("href"):
                # Source: ttrss/include/functions2.php lines 855-858 — rewrite href + add rel=noreferrer
                entry.set("href", rewrite_relative_url(site_url, entry.get("href")))
                entry.set("rel", "noreferrer")

            if entry.tag == "img" and entry.get("src"):
                # Source: ttrss/include/functions2.php lines 861-870 — rewrite src
                src = rewrite_relative_url(site_url, entry.get("src"))
                entry.set("src", src)

            if entry.tag == "img":
                # Source: ttrss/include/functions2.php lines 873-889 — strip images if pref set
                _strip_images = force_remove_images
                if not _strip_images and owner_uid is not None:
                    try:
                        from ttrss.prefs.ops import get_user_pref
                        _strip_images = get_user_pref(owner_uid, "STRIP_IMAGES") in ("true", "1", True)
                    except Exception:  # New: no PHP equivalent — guard against prefs unavailability.
                        pass
                if _strip_images:
                    # Source: ttrss/include/functions2.php lines 877-888 — replace <img> with <p><a href=src>src</a></p>
                    src = entry.get("src", "")
                    p = lxml.html.Element("p")
                    a = lxml.html.Element("a")
                    a.set("href", src)
                    a.set("target", "_blank")
                    a.text = src
                    p.append(a)
                    parent = entry.getparent()
                    if parent is not None:  # New: no PHP equivalent — PHP removeChild implicitly requires a parent node; lxml requires explicit parent guard.
                        parent.replace(entry, p)

    # Source: ttrss/include/functions2.php lines 892-895 — add target=_blank to all <a>
    for a in doc.xpath(".//a"):
        a.set("target", "_blank")

    # Source: ttrss/include/functions2.php lines 897-901 — add sandbox=allow-scripts to <iframe>
    for iframe in doc.xpath(".//iframe"):
        iframe.set("sandbox", "allow-scripts")

    # Build element/attribute sets for hook and strip_harmful_tags
    # Source: ttrss/include/functions2.php lines 903-913 — $allowed_elements array
    allowed_elements = set(_ALLOWED_ELEMENTS)

    # Source: ttrss/include/functions2.php line 915 — if ($_SESSION['hasSandbox']) $allowed_elements[] = 'iframe'
    # Adapted: PHP reads $_SESSION['hasSandbox']; Python uses explicit has_sandbox parameter.
    if has_sandbox:
        allowed_elements.add("iframe")

    # Source: ttrss/include/functions2.php line 917 — $disallowed_attributes array
    disallowed_attributes = set(_DISALLOWED_ATTRIBUTES)

    # Source: ttrss/include/functions2.php lines 919-928 — HOOK_SANITIZE plugin loop
    # Note: ttrss/include/functions2.php line 920 — PHP passes $article_id as 5th argument to hook.
    # Source: ttrss/include/functions2.php line 920 — $plugin->hook_sanitize($doc, $site_url,
    #   $allowed_elements, $disallowed_attributes, $article_id) — 5 arguments.
    try:
        from ttrss.plugins.manager import get_plugin_manager  # New: lazy import avoids circular dependency.
        pm = get_plugin_manager()
        results = pm.hook.hook_sanitize(
            doc=doc,
            site_url=site_url,
            allowed_elements=allowed_elements,
            disallowed_attributes=disallowed_attributes,
            article_id=article_id,
        )
        # Source: ttrss/include/functions2.php lines 921-927 — if is_array($retval) unpack; else use as $doc
        # Adapted: PHP iterates PluginHost::get_hooks; pluggy returns all results as list.
        for result in results:
            if result is None:
                continue
            if isinstance(result, (list, tuple)) and len(result) >= 1:
                # Source: ttrss/include/functions2.php line 922-924 — $doc=$retval[0], elements=$retval[1], attrs=$retval[2]
                doc = result[0]
                if len(result) >= 3:
                    allowed_elements = result[1]
                    disallowed_attributes = result[2]
            else:
                # Source: ttrss/include/functions2.php line 926 — else $doc = $retval
                doc = result
    except Exception as exc:  # New: no PHP equivalent — defensive catch; hook errors must not abort sanitization.
        logger.warning("sanitize: HOOK_SANITIZE raised: %s", exc)

    # Source: ttrss/include/functions2.php line 930 — $doc->removeChild($doc->firstChild) (remove doctype)
    # Note: Python lxml fragment_fromstring does not produce a DOCTYPE; no equivalent removal needed.

    # Source: ttrss/include/functions2.php line 931 — $doc = strip_harmful_tags($doc, $allowed_elements, ...)
    doc = strip_harmful_tags(doc, allowed_elements, disallowed_attributes)

    # Note: ttrss/include/functions2.php lines 933-959 — highlight_words loop not yet reproduced; deferred.
    # Source: ttrss/include/functions2.php line 962 — $res = $doc->saveHTML()
    return lxml.html.tostring(doc, encoding="unicode")


def strip_harmful_tags(
    doc: lxml.html.HtmlElement,
    allowed_elements: set,
    disallowed_attributes: set,
) -> lxml.html.HtmlElement:
    """
    Remove disallowed elements (entire subtree) and harmful/disallowed attributes.

    Source: ttrss/include/functions2.php:strip_harmful_tags (lines 967-997)
    Adapted: PHP DOMXPath('//*') iteration replaced by lxml tree iteration.
             PHP foreach-modify pattern (unsafe during live iteration) replaced by
             two-pass approach (collect then remove) to avoid lxml iteration issues.
    Note: ttrss/include/functions2.php lines 972-974 — PHP removeChild removes entire subtree.
          Python lxml element.getparent().remove(element) does the same.
    """
    # Source: ttrss/include/functions2.php line 968 — $xpath = new DOMXPath($doc); $entries = $xpath->query('//*')
    # Adapted: collect first to avoid modifying tree during iteration (PHP's DOMNodeList has same risk).
    # New: to_remove list is a Python-only construct; PHP's DOMNodeList is a live node list — explicit
    #      two-pass collection is required in Python to avoid iterator invalidation during removal.
    to_remove = []
    for el in doc.iter():
        if not isinstance(el.tag, str):
            continue  # New: skip lxml Comment/PI nodes that have non-string tags (no PHP equivalent).
        if el.tag not in allowed_elements:
            # Source: ttrss/include/functions2.php line 973 — $entry->parentNode->removeChild($entry)
            to_remove.append(el)

    # Source: ttrss/include/functions2.php line 973 — removeChild (remove entire subtree)
    for el in to_remove:
        parent = el.getparent()
        if parent is not None:
            parent.remove(el)

    # Source: ttrss/include/functions2.php lines 976-992 — attribute filtering loop
    for el in doc.iter():
        if not isinstance(el.tag, str):
            continue  # New: skip Comment/PI nodes.
        attrs_to_remove = []  # New: no PHP equivalent — two-pass collect-then-delete pattern; same reason as to_remove above.
        for attr in list(el.attrib):
            # Source: ttrss/include/functions2.php line 981 — if (strpos($attr->nodeName, 'on') === 0)
            if attr.startswith("on"):
                attrs_to_remove.append(attr)
            # Source: ttrss/include/functions2.php line 985 — if (in_array($attr->nodeName, $disallowed_attributes))
            elif attr in disallowed_attributes:
                attrs_to_remove.append(attr)

        # Source: ttrss/include/functions2.php lines 990-992 — removeAttributeNode loop
        for attr in attrs_to_remove:
            del el.attrib[attr]

    return doc
