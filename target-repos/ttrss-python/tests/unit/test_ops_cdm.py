"""Tests for HOOK_RENDER_ARTICLE_CDM and HOOK_HEADLINE_TOOLBAR_BUTTON in articles/ops.py.

Source: ttrss/classes/feeds.php:517 — HOOK_RENDER_ARTICLE_CDM
        ttrss/classes/feeds.php:138 — HOOK_HEADLINE_TOOLBAR_BUTTON
New: Python test suite.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone


def _make_article_row(**overrides):
    """Minimal article row mirroring what format_article's JOIN query returns."""
    defaults = dict(
        id=1,
        title="Test",
        link="http://example.com",
        content="<p>body</p>",
        comments="",
        lang="en",
        updated=datetime(2025, 1, 1, tzinfo=timezone.utc),
        num_comments=0,
        author="author",
        int_id=100,
        feed_id=1,
        orig_feed_id=None,
        tag_cache="",
        note=None,
        unread=True,
        marked=False,
        published=False,
        score=0,
        site_url="http://example.com",
        feed_title="Feed",
        hide_images=False,
        always_display_enclosures=False,
    )
    defaults.update(overrides)
    row = MagicMock()
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _make_session_with_row(row):
    """Build a mock session whose execute() returns appropriate results for format_article."""
    session = MagicMock()
    call_count = [0]

    def side_effect(*args, **kwargs):
        call_count[0] += 1
        r = MagicMock()
        if call_count[0] == 1:
            # feed_id lookup
            r.scalar_one_or_none.return_value = 1
        elif call_count[0] == 3:
            # main article query (after mark_as_read UPDATE at call 2)
            r.one_or_none.return_value = row
        else:
            r.one_or_none.return_value = row
        return r

    session.execute.side_effect = side_effect
    return session


class TestFormatArticleCDM:
    """format_article(cdm=True) fires HOOK_RENDER_ARTICLE_CDM; cdm=False does not."""

    def test_cdm_true_fires_hook_render_article_cdm(self):
        """CDM path fires hook_render_article_cdm pipeline.

        Source: ttrss/classes/feeds.php:517 — HOOK_RENDER_ARTICLE_CDM
        AR-7: must NOT fire when cdm=False.
        """
        from ttrss.articles.ops import format_article

        mock_pm = MagicMock()
        mock_pm.hook.hook_render_article_cdm = MagicMock(return_value=[])
        mock_pm.hook.hook_render_article = MagicMock()
        mock_pm.hook.hook_article_button = MagicMock(return_value=[])
        mock_pm.hook.hook_article_left_button = MagicMock(return_value=[])

        row = _make_article_row()
        session = _make_session_with_row(row)

        with patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm), \
             patch("ttrss.articles.ops.ccache_update"), \
             patch("ttrss.articles.ops.get_article_tags", return_value=[]), \
             patch("ttrss.articles.ops.get_article_enclosures", return_value=[]), \
             patch("ttrss.articles.ops.get_article_labels", return_value=[]):
            format_article(session, article_id=1, owner_uid=1, cdm=True)

        mock_pm.hook.hook_render_article_cdm.assert_called_once()
        mock_pm.hook.hook_render_article.assert_not_called()

    def test_cdm_false_fires_hook_render_article_not_cdm(self):
        """Non-CDM path fires hook_render_article, NOT hook_render_article_cdm.

        AR-7: CDM hook must be absent from non-CDM path.
        """
        from ttrss.articles.ops import format_article

        mock_pm = MagicMock()
        mock_pm.hook.hook_render_article_cdm = MagicMock(return_value=[])
        mock_pm.hook.hook_render_article = MagicMock()
        mock_pm.hook.hook_article_button = MagicMock(return_value=[])
        mock_pm.hook.hook_article_left_button = MagicMock(return_value=[])

        row = _make_article_row()
        session = _make_session_with_row(row)

        with patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm), \
             patch("ttrss.articles.ops.ccache_update"), \
             patch("ttrss.articles.ops.get_article_tags", return_value=[]), \
             patch("ttrss.articles.ops.get_article_enclosures", return_value=[]), \
             patch("ttrss.articles.ops.get_article_labels", return_value=[]):
            format_article(session, article_id=1, owner_uid=1, cdm=False)

        mock_pm.hook.hook_render_article.assert_called_once()
        mock_pm.hook.hook_render_article_cdm.assert_not_called()


class TestFormatHeadlineRow:
    """format_headline_row fires HOOK_HEADLINE_TOOLBAR_BUTTON."""

    def test_hook_headline_toolbar_button_fires(self):
        """format_headline_row calls hook_headline_toolbar_button and attaches result.

        Source: ttrss/classes/feeds.php:138 — HOOK_HEADLINE_TOOLBAR_BUTTON
        """
        from ttrss.articles.ops import format_headline_row

        mock_pm = MagicMock()
        mock_pm.hook.hook_headline_toolbar_button = MagicMock(return_value=["btn1", "btn2"])

        with patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm):
            article = {"id": 1, "title": "T"}
            result = format_headline_row(article)

        mock_pm.hook.hook_headline_toolbar_button.assert_called_once()
        assert result["toolbar_buttons"] == ["btn1", "btn2"]
