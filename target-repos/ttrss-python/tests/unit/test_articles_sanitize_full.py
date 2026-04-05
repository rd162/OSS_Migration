"""
Full unit-test suite for ttrss/articles/sanitize.py (sanitize + strip_harmful_tags).

Every test cites the PHP source line(s) it exercises.

Source: ttrss/include/functions2.php:sanitize       (lines 831-965)
        ttrss/include/functions2.php:strip_harmful_tags (lines 967-997)

Mocking strategy
----------------
``get_plugin_manager`` is imported lazily inside ``sanitize()`` via
``from ttrss.plugins.manager import get_plugin_manager``.  Because the import
happens at call time rather than module load time, the correct patch target is
``ttrss.plugins.manager.get_plugin_manager`` — this replaces the name in the
source module so the lazy import picks up the mock.

The default mock returns a PluginManager-like object whose
``hook.hook_sanitize()`` returns ``[]`` (no plugin implementations), which
mirrors the zero-plugin path in PHP.

For test 19 (HOOK_SANITIZE plugin loop) a real pluggy PM with a minimal test
plugin is injected so that the doc-mutation code path is exercised exactly.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import lxml.html
import pluggy
import pytest

from ttrss.articles.sanitize import sanitize
from ttrss.plugins.hookspecs import TtRssHookSpec, hookimpl


# ---------------------------------------------------------------------------
# Helper: build a throw-away mock plugin manager that returns no hook results.
# ---------------------------------------------------------------------------

def _make_null_pm() -> MagicMock:
    """Return a MagicMock PM whose hook_sanitize call returns an empty list."""
    pm = MagicMock()
    pm.hook.hook_sanitize.return_value = []
    return pm


# Convenience: a context-manager that patches get_plugin_manager for one test.
# ``_pm`` defaults to the null PM; callers can supply a real PM for hook tests.
def _patch_pm(pm=None):
    target_pm = pm if pm is not None else _make_null_pm()
    return patch(
        "ttrss.plugins.manager.get_plugin_manager",
        return_value=target_pm,
    )


# ---------------------------------------------------------------------------
# 1. Empty string → empty string
# ---------------------------------------------------------------------------

def test_sanitize_empty_string_returns_empty():
    """
    sanitize('') must return '' immediately.

    Source: ttrss/include/functions2.php:sanitize line 834
        $res = trim($str); if (!$res) return '';
    """
    with _patch_pm():
        assert sanitize("") == ""


# ---------------------------------------------------------------------------
# 2. Whitespace-only → empty string
# ---------------------------------------------------------------------------

def test_sanitize_whitespace_only_returns_empty():
    """
    sanitize('   ') trims to '' and returns '' early.

    Source: ttrss/include/functions2.php:sanitize line 834
        $res = trim($str); if (!$res) return '';
    Adapted: Python strip() mirrors PHP trim(); both produce an empty string for
             whitespace-only input, triggering the early-return branch.
    """
    with _patch_pm():
        assert sanitize("   ") == ""


# ---------------------------------------------------------------------------
# 3. Allowed element preserved
# ---------------------------------------------------------------------------

def test_sanitize_allowed_element_preserved():
    """
    <p> is in $allowed_elements and must survive strip_harmful_tags.

    Source: ttrss/include/functions2.php:sanitize lines 903-913 — $allowed_elements array
            ttrss/include/functions2.php:strip_harmful_tags lines 971-974 — removeChild only
            for elements NOT in $allowed_elements.
    """
    with _patch_pm():
        result = sanitize("<p>hello</p>")
    assert "<p>hello</p>" in result


# ---------------------------------------------------------------------------
# 4. Harmful element removed
# ---------------------------------------------------------------------------

def test_sanitize_script_tag_removed():
    """
    <script> is not in $allowed_elements; strip_harmful_tags must remove it.

    Source: ttrss/include/functions2.php:strip_harmful_tags lines 971-974
        if (!in_array($entry->nodeName, $allowed_elements))
            $entry->parentNode->removeChild($entry);
    """
    with _patch_pm():
        result = sanitize("<script>evil()</script>text")
    assert "<script>" not in result
    assert "evil()" not in result


# ---------------------------------------------------------------------------
# 5. Relative <a href> rewritten to absolute URL
# ---------------------------------------------------------------------------

def test_sanitize_relative_href_becomes_absolute():
    """
    When site_url is provided, a relative href must be rewritten to absolute.

    Source: ttrss/include/functions2.php:sanitize lines 854-856
        $entry->setAttribute('href',
            rewrite_relative_url($site_url, $entry->getAttribute('href')));
    """
    with _patch_pm():
        result = sanitize('<a href="/rel">x</a>', site_url="http://x.com")
    assert 'href="http://x.com/rel"' in result


# ---------------------------------------------------------------------------
# 6. Relative <img src> rewritten to absolute URL
# ---------------------------------------------------------------------------

def test_sanitize_relative_img_src_becomes_absolute():
    """
    When site_url is provided, a relative img src must be rewritten to absolute.

    Source: ttrss/include/functions2.php:sanitize lines 861-870
        $src = rewrite_relative_url($site_url, $entry->getAttribute('src'));
        $entry->setAttribute('src', $src);
    """
    with _patch_pm():
        result = sanitize('<img src="/img.png">', site_url="http://x.com")
    assert 'src="http://x.com/img.png"' in result


# ---------------------------------------------------------------------------
# 7. Already-absolute href unchanged
# ---------------------------------------------------------------------------

def test_sanitize_absolute_href_unchanged():
    """
    An already-absolute href must not be mangled by rewrite_relative_url.

    Source: ttrss/include/functions2.php:rewrite_relative_url line 1966
        if (strpos($rel_url, ':') !== false) return $rel_url;
    The ':' check causes absolute URLs to be returned as-is, so the href
    value in the output must equal the original absolute URL.
    """
    with _patch_pm():
        result = sanitize(
            '<a href="http://abs.com">x</a>', site_url="http://x.com"
        )
    assert 'href="http://abs.com"' in result


# ---------------------------------------------------------------------------
# 8. <a> gets target="_blank"
# ---------------------------------------------------------------------------

def test_sanitize_anchor_gets_target_blank():
    """
    All <a> elements must receive target="_blank" regardless of site_url.

    Source: ttrss/include/functions2.php:sanitize lines 892-894
        if (strtolower($entry->nodeName) == "a")
            $entry->setAttribute("target", "_blank");
    """
    with _patch_pm():
        result = sanitize('<a href="/x">link</a>')
    assert 'target="_blank"' in result


# ---------------------------------------------------------------------------
# 9. <a> gets rel="noreferrer" when site_url provided
# ---------------------------------------------------------------------------

def test_sanitize_anchor_gets_rel_noreferrer():
    """
    When site_url is set, every <a href> must receive rel="noreferrer".

    Source: ttrss/include/functions2.php:sanitize lines 857-858
        $entry->setAttribute('rel', 'noreferrer');
    """
    with _patch_pm():
        result = sanitize('<a href="/x">link</a>', site_url="http://x.com")
    assert 'rel="noreferrer"' in result


# ---------------------------------------------------------------------------
# 10. <iframe> removed when has_sandbox=False
# ---------------------------------------------------------------------------

def test_sanitize_iframe_removed_without_sandbox():
    """
    <iframe> is not in $allowed_elements unless $_SESSION['hasSandbox'] is set.
    With has_sandbox=False the iframe must be stripped entirely.

    Source: ttrss/include/functions2.php:sanitize line 915
        if ($_SESSION['hasSandbox']) $allowed_elements[] = 'iframe';
    Adapted: PHP $_SESSION['hasSandbox'] → Python has_sandbox parameter.
    """
    with _patch_pm():
        result = sanitize('<iframe src="x"></iframe>', has_sandbox=False)
    assert "<iframe" not in result


# ---------------------------------------------------------------------------
# 11. <iframe> kept with sandbox attribute when has_sandbox=True
# ---------------------------------------------------------------------------

def test_sanitize_iframe_kept_with_sandbox():
    """
    When has_sandbox=True, iframe is added to $allowed_elements and must survive;
    strip_harmful_tags must also preserve the sandbox attribute set earlier.

    Source: ttrss/include/functions2.php:sanitize line 915
        if ($_SESSION['hasSandbox']) $allowed_elements[] = 'iframe';
            lines 897-901 — $entry->setAttribute('sandbox', 'allow-scripts');
    Adapted: PHP $_SESSION['hasSandbox'] → Python has_sandbox parameter.
    """
    with _patch_pm():
        result = sanitize('<iframe src="x"></iframe>', has_sandbox=True)
    assert "<iframe" in result
    assert 'sandbox="allow-scripts"' in result


# ---------------------------------------------------------------------------
# 12. id / class / style attributes stripped
# ---------------------------------------------------------------------------

def test_sanitize_disallowed_attributes_stripped():
    """
    id, class, and style are in $disallowed_attributes and must be removed.

    Source: ttrss/include/functions2.php:sanitize line 917
        $disallowed_attributes = array('id', 'style', 'class');
            strip_harmful_tags lines 985-987 — if (in_array($attr->nodeName, $disallowed_attributes))
    """
    with _patch_pm():
        result = sanitize('<p id="x" class="y" style="z">hi</p>')
    assert 'id="x"' not in result
    assert 'class="y"' not in result
    assert 'style="z"' not in result
    assert "hi" in result


# ---------------------------------------------------------------------------
# 13. on* event handler attributes stripped
# ---------------------------------------------------------------------------

def test_sanitize_on_event_attributes_stripped():
    """
    Any attribute whose name starts with 'on' (e.g. onclick) must be removed.

    Source: ttrss/include/functions2.php:strip_harmful_tags lines 980-983
        if (strpos($attr->nodeName, 'on') === 0)
            array_push($attrs_to_remove, $attr);
    """
    with _patch_pm():
        result = sanitize('<p onclick="evil()">hi</p>')
    assert "onclick" not in result
    assert "evil()" not in result
    assert "hi" in result


# ---------------------------------------------------------------------------
# 14. Allowed attribute (href) preserved
# ---------------------------------------------------------------------------

def test_sanitize_allowed_attribute_href_preserved():
    """
    href is not in $disallowed_attributes and does not start with 'on',
    so it must survive strip_harmful_tags unmodified.

    Source: ttrss/include/functions2.php:strip_harmful_tags lines 979-992 —
        attribute is only removed if it starts with 'on' OR is in
        $disallowed_attributes; href is in neither set.
    """
    with _patch_pm():
        result = sanitize('<a href="http://x.com">link</a>')
    assert 'href="http://x.com"' in result


# ---------------------------------------------------------------------------
# 15. force_remove_images replaces <img> with <a> link
# ---------------------------------------------------------------------------

def test_sanitize_force_remove_images_replaces_img_with_link():
    """
    When force_remove_images=True the <img> must be replaced by a <p><a> block
    whose href and text equal the original src.

    Source: ttrss/include/functions2.php:sanitize lines 877-888
        $p = $doc->createElement('p');
        $a = $doc->createElement('a');
        $a->setAttribute('href', $entry->getAttribute('src'));
        $a->appendChild(new DOMText($entry->getAttribute('src')));
        $a->setAttribute('target', '_blank');
        $p->appendChild($a);
        $entry->parentNode->replaceChild($p, $entry);
    Note: PHP guard condition includes $site_url check (line 873); Python implementation
          mirrors that: force_remove_images only activates inside the site_url block.
    """
    with _patch_pm():
        result = sanitize(
            '<img src="x.png">',
            force_remove_images=True,
            site_url="http://x.com",
        )
    assert "<img" not in result
    assert "<a" in result
    assert "x.png" in result


# ---------------------------------------------------------------------------
# 16. highlight_words wraps matched text in <span class="highlight">
# ---------------------------------------------------------------------------

def test_sanitize_highlight_words_wraps_match():
    """
    When highlight_words=['hello'], the word 'hello' in body text must be
    wrapped in <span class="highlight">hello</span>.

    Source: ttrss/include/functions2.php:sanitize lines 933-959
        while (($pos = mb_stripos($text, $word)) !== false) {
            $highlight = $doc->createElement('span');
            $highlight->setAttribute('class', 'highlight');
        }
    Adapted: PHP DOM node replacement → Python regex substitution on serialised HTML.
    """
    with _patch_pm():
        result = sanitize("<p>hello world</p>", highlight_words=["hello"])
    assert '<span class="highlight">hello</span>' in result


# ---------------------------------------------------------------------------
# 17. highlight_words is case-insensitive
# ---------------------------------------------------------------------------

def test_sanitize_highlight_words_case_insensitive():
    """
    highlight_words matching must be case-insensitive (PHP mb_stripos is case-insensitive).

    Source: ttrss/include/functions2.php:sanitize line 945
        while (($pos = mb_stripos($text, $word)) !== false) { ... }
        — mb_stripos performs case-insensitive multibyte search.
    Adapted: Python re.IGNORECASE flag mirrors PHP mb_stripos semantics.
    """
    with _patch_pm():
        result = sanitize("<p>Hello World</p>", highlight_words=["hello"])
    # Either the original casing or lower is acceptable; what matters is the span wrapper.
    assert '<span class="highlight">' in result
    assert "Hello" in result or "hello" in result


# ---------------------------------------------------------------------------
# 18. Malformed HTML does not raise an exception
# ---------------------------------------------------------------------------

def test_sanitize_malformed_html_does_not_crash():
    """
    When lxml fails to parse the content, sanitize must log a warning and return
    the original (stripped) string rather than propagating the exception.

    Source: ttrss/include/functions2.php:sanitize lines 842-845 — PHP wraps
        DOMDocument::loadHTML in libxml_use_internal_errors(true) to suppress
        parse errors silently; Python equivalent logs and returns original content.
    New: explicit exception guard added in Python (no direct PHP equivalent for the
         return-on-failure path; PHP crashes or silently produces a broken doc).
    """
    # lxml is very forgiving; use a completely unparseable byte sequence to trigger
    # the except branch reliably by patching fragment_fromstring directly.
    with _patch_pm():
        with patch(
            "lxml.html.fragment_fromstring",
            side_effect=Exception("parse failure"),
        ):
            result = sanitize("malformed<html")
    # Must return the stripped input without raising.
    assert result == "malformed<html"


# ---------------------------------------------------------------------------
# 19. HOOK_SANITIZE: plugin modifies the doc and the change is reflected in output
# ---------------------------------------------------------------------------

class _SanitizePlugin:
    """
    Minimal pluggy plugin that implements hook_sanitize.
    Appends a sentinel <p> to the doc so we can verify the hook result is used.

    Source: ttrss/include/functions2.php:sanitize lines 919-927
        foreach (PluginHost::getInstance()->get_hooks(HOOK_SANITIZE) as $plugin) {
            $retval = $plugin->hook_sanitize($doc, $site_url, ...);
            if (is_array($retval)) { $doc=$retval[0]; ... } else { $doc=$retval; }
        }
    """

    @hookimpl
    def hook_sanitize(
        self,
        doc,
        site_url,
        allowed_elements,
        disallowed_attributes,
        article_id,
    ):
        """
        Return (modified_doc, allowed_elements, disallowed_attributes) as a 3-tuple.

        Source: ttrss/include/functions2.php:sanitize lines 921-924 — PHP is_array branch:
            $doc = $retval[0];
            $allowed_elements = $retval[1];
            $disallowed_attributes = $retval[2];
        """
        sentinel = lxml.html.Element("p")
        sentinel.text = "__sentinel__"
        doc.append(sentinel)
        # Also allow 'p' explicitly (it's already in defaults, but be explicit).
        allowed_elements.add("p")
        return (doc, allowed_elements, disallowed_attributes)


def _make_real_pm_with_plugin() -> object:
    """
    Build a real pluggy PluginManager registered with TtRssHookSpec and
    _SanitizePlugin so that hook_sanitize fires with an actual implementation.
    """
    pm = pluggy.PluginManager("ttrss")
    pm.add_hookspecs(TtRssHookSpec)
    pm.register(_SanitizePlugin(), name="test_sanitize_plugin")
    return pm


def test_sanitize_hook_sanitize_plugin_modifies_doc():
    """
    A plugin registered for HOOK_SANITIZE may mutate the doc (or return a new one);
    the resulting document must appear in sanitize()'s output.

    Source: ttrss/include/functions2.php:sanitize lines 919-927
        foreach (PluginHost::getInstance()->get_hooks(HOOK_SANITIZE) as $plugin) {
            $retval = $plugin->hook_sanitize($doc, $site_url,
                $allowed_elements, $disallowed_attributes, $article_id);
            if (is_array($retval)) {
                $doc = $retval[0];
                $allowed_elements = $retval[1];
                $disallowed_attributes = $retval[2];
            } else {
                $doc = $retval;
            }
        }
    Adapted: PHP PluginHost::get_hooks loop → pluggy pm.hook.hook_sanitize() collecting call;
             PHP is_array($retval) check → Python isinstance(result, (list, tuple)).
    """
    real_pm = _make_real_pm_with_plugin()
    with patch(
        "ttrss.plugins.manager.get_plugin_manager",
        return_value=real_pm,
    ):
        result = sanitize("<p>original content</p>", article_id=42)

    assert "__sentinel__" in result, (
        f"Expected sentinel text from hook plugin in output, got: {result!r}"
    )
