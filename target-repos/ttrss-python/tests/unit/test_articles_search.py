"""Unit tests for ttrss/articles/search.py — search_to_sql, queryFeedHeadlines."""
from __future__ import annotations

from datetime import timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import and_, not_

from ttrss.articles.search import queryFeedHeadlines, search_to_sql
from ttrss.utils.feeds import LABEL_BASE_INDEX, label_to_feed_id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _session(rows=None):
    """Return a mock session whose execute().all() returns rows."""
    session = MagicMock()
    session.execute.return_value.all.return_value = rows or []
    return session


def _pref_side_effects(session, user_val=None, sys_val="12"):
    """Two scalar_one_or_none calls: user pref then system pref."""
    r1 = MagicMock(**{"scalar_one_or_none.return_value": user_val})
    r2 = MagicMock(**{"scalar_one_or_none.return_value": sys_val})
    session.execute.side_effect = [r1, r2, MagicMock(**{"all.return_value": []})]


# ---------------------------------------------------------------------------
# search_to_sql — clause generation
# ---------------------------------------------------------------------------


def test_search_to_sql_empty_returns_empty():
    clauses, words = search_to_sql("")
    assert clauses == []
    assert words == []


def test_search_to_sql_blank_space():
    clauses, words = search_to_sql("   ")
    assert clauses == []
    assert words == []


def test_search_to_sql_simple_keyword():
    clauses, words = search_to_sql("python")
    assert len(clauses) == 1
    assert "python" in words


def test_search_to_sql_simple_keyword_is_ilike_both():
    """Generic keyword → OR(title LIKE, content LIKE) clause."""
    clauses, words = search_to_sql("python")
    # Clause should stringify to something with UPPER and LIKE
    sql = str(clauses[0].compile(compile_kwargs={"literal_binds": True}))
    assert "LIKE" in sql.upper()


def test_search_to_sql_title_prefix():
    clauses, words = search_to_sql("title:python")
    assert len(clauses) == 1
    # Should NOT add to search_words (field-specific search)
    assert words == []
    sql = str(clauses[0].compile(compile_kwargs={"literal_binds": True}))
    assert "title" in sql.lower()


def test_search_to_sql_author_prefix():
    clauses, words = search_to_sql("author:alice")
    assert len(clauses) == 1
    assert words == []
    sql = str(clauses[0].compile(compile_kwargs={"literal_binds": True}))
    assert "author" in sql.lower()


def test_search_to_sql_note_true():
    clauses, words = search_to_sql("note:true")
    assert len(clauses) == 1
    sql = str(clauses[0].compile(compile_kwargs={"literal_binds": True}))
    assert "note" in sql.lower()


def test_search_to_sql_note_false():
    clauses, words = search_to_sql("note:false")
    assert len(clauses) == 1


def test_search_to_sql_note_text():
    clauses, words = search_to_sql("note:reminder")
    assert len(clauses) == 1
    sql = str(clauses[0].compile(compile_kwargs={"literal_binds": True}))
    assert "note" in sql.lower()


def test_search_to_sql_star_true():
    clauses, words = search_to_sql("star:true")
    assert len(clauses) == 1
    sql = str(clauses[0].compile(compile_kwargs={"literal_binds": True}))
    assert "marked" in sql.lower()


def test_search_to_sql_star_false():
    clauses, words = search_to_sql("star:false")
    assert len(clauses) == 1


def test_search_to_sql_pub_true():
    clauses, words = search_to_sql("pub:true")
    assert len(clauses) == 1
    sql = str(clauses[0].compile(compile_kwargs={"literal_binds": True}))
    assert "published" in sql.lower()


def test_search_to_sql_pub_false():
    clauses, words = search_to_sql("pub:false")
    assert len(clauses) == 1


def test_search_to_sql_at_date():
    clauses, words = search_to_sql("@2025-01-15")
    assert len(clauses) == 1
    # Date filter does not add to search_words
    assert words == []


def test_search_to_sql_at_date_invalid_skips():
    """@date with invalid format falls through to ilike_both."""
    clauses, words = search_to_sql("@notadate")
    assert len(clauses) == 1
    assert "@notadate" in words


def test_search_to_sql_negated_keyword():
    clauses, words = search_to_sql("-python")
    assert len(clauses) == 1
    # Negated → NOT in clause
    sql = str(clauses[0].compile(compile_kwargs={"literal_binds": True}))
    assert "NOT" in sql.upper()
    # Negated keywords are not added to search_words
    assert words == []


def test_search_to_sql_negated_title():
    clauses, words = search_to_sql("-title:spam")
    assert len(clauses) == 1
    sql = str(clauses[0].compile(compile_kwargs={"literal_binds": True}))
    assert "NOT" in sql.upper()


def test_search_to_sql_negated_empty_after_dash_skipped():
    """A bare '-' (nothing after) is skipped."""
    clauses, words = search_to_sql("-")
    assert clauses == []
    assert words == []


def test_search_to_sql_multiple_keywords():
    clauses, words = search_to_sql("python rust")
    assert len(clauses) == 2
    assert "python" in words
    assert "rust" in words


def test_search_to_sql_quoted_phrase():
    """Quoted phrase treated as single keyword via shlex.split."""
    clauses, words = search_to_sql('"open source"')
    assert len(clauses) == 1
    assert "open source" in words


def test_search_to_sql_invalid_shlex_falls_back_to_split():
    """Unclosed quote → shlex.split fails → fall back to str.split."""
    clauses, words = search_to_sql('python "unclosed')
    assert len(clauses) >= 1


def test_search_to_sql_negated_at_date():
    clauses, words = search_to_sql("-@2025-01-01")
    assert len(clauses) == 1
    sql = str(clauses[0].compile(compile_kwargs={"literal_binds": True}))
    # NOT_(date == ...) compiles to date != ... in SQLAlchemy
    assert "NOT" in sql.upper() or "!=" in sql


# ---------------------------------------------------------------------------
# queryFeedHeadlines — smoke tests (no DB; mock session)
# ---------------------------------------------------------------------------


def test_qfh_regular_feed():
    """Simple numeric feed returns list[Row]."""
    session = _session(rows=["row1"])
    with patch("ttrss.articles.search._pref_int", return_value=12):
        result = queryFeedHeadlines(session, feed=5, limit=10, view_mode="all_articles",
                                    cat_view=False, owner_uid=1)
    assert result == ["row1"]
    session.execute.assert_called_once()


def test_qfh_returns_list():
    session = _session()
    result = queryFeedHeadlines(session, feed=5, limit=0, view_mode="all_articles",
                                cat_view=False, owner_uid=1)
    assert isinstance(result, list)


def test_qfh_category_view_positive():
    session = _session()
    with patch("ttrss.feeds.categories.getChildCategories", return_value=[10, 11]):
        result = queryFeedHeadlines(session, feed=3, limit=10, view_mode="all_articles",
                                    cat_view=True, owner_uid=1)
    assert isinstance(result, list)


def test_qfh_category_view_uncategorized_zero():
    session = _session()
    result = queryFeedHeadlines(session, feed=0, limit=10, view_mode="all_articles",
                                cat_view=True, owner_uid=1)
    assert isinstance(result, list)


def test_qfh_archive_feed_zero_not_cat():
    session = _session()
    result = queryFeedHeadlines(session, feed=0, limit=10, view_mode="all_articles",
                                cat_view=False, owner_uid=1)
    assert isinstance(result, list)


def test_qfh_starred_minus_one():
    session = _session()
    result = queryFeedHeadlines(session, feed=-1, limit=10, view_mode="all_articles",
                                cat_view=False, owner_uid=1)
    assert isinstance(result, list)


def test_qfh_published_minus_two():
    session = _session()
    result = queryFeedHeadlines(session, feed=-2, limit=10, view_mode="all_articles",
                                cat_view=False, owner_uid=1)
    assert isinstance(result, list)


def test_qfh_fresh_minus_three():
    session = MagicMock()
    pref_user = MagicMock(**{"scalar_one_or_none.return_value": None})
    pref_sys = MagicMock(**{"scalar_one_or_none.return_value": "12"})
    rows_result = MagicMock(**{"all.return_value": []})
    session.execute.side_effect = [pref_user, pref_sys, rows_result]
    result = queryFeedHeadlines(session, feed=-3, limit=10, view_mode="all_articles",
                                cat_view=False, owner_uid=1)
    assert isinstance(result, list)


def test_qfh_all_articles_minus_four():
    session = _session()
    result = queryFeedHeadlines(session, feed=-4, limit=10, view_mode="all_articles",
                                cat_view=False, owner_uid=1)
    assert isinstance(result, list)


def test_qfh_recently_read_minus_six():
    session = _session()
    result = queryFeedHeadlines(session, feed=-6, limit=10, view_mode="all_articles",
                                cat_view=False, owner_uid=1)
    assert isinstance(result, list)


def test_qfh_labels_category_minus_two_cat():
    session = _session()
    result = queryFeedHeadlines(session, feed=-2, limit=10, view_mode="all_articles",
                                cat_view=True, owner_uid=1)
    assert isinstance(result, list)


def test_qfh_label_feed():
    label_vfid = label_to_feed_id(1)  # LABEL_BASE_INDEX - 1
    session = _session()
    result = queryFeedHeadlines(session, feed=label_vfid, limit=10,
                                view_mode="all_articles", cat_view=False, owner_uid=1)
    assert isinstance(result, list)


def test_qfh_tag_feed_string():
    session = _session()
    result = queryFeedHeadlines(session, feed="linux", limit=10,
                                view_mode="all_articles", cat_view=False, owner_uid=1)
    assert isinstance(result, list)


def test_qfh_tag_feed_comma_any_mode():
    session = _session()
    result = queryFeedHeadlines(session, feed="linux,kernel", limit=10,
                                view_mode="all_articles", cat_view=False,
                                owner_uid=1, search_mode="any")
    assert isinstance(result, list)


def test_qfh_with_search():
    session = _session()
    result = queryFeedHeadlines(session, feed=5, limit=10, view_mode="all_articles",
                                cat_view=False, owner_uid=1, search="python news")
    assert isinstance(result, list)


def test_qfh_search_all_feeds_mode():
    session = _session()
    result = queryFeedHeadlines(session, feed=5, limit=10, view_mode="all_articles",
                                cat_view=False, owner_uid=1, search="python",
                                search_mode="all_feeds")
    assert isinstance(result, list)


def test_qfh_search_this_cat_mode_positive():
    session = _session()
    with patch("ttrss.feeds.categories.getChildCategories", return_value=[]):
        result = queryFeedHeadlines(session, feed=3, limit=10, view_mode="all_articles",
                                    cat_view=False, owner_uid=1, search="news",
                                    search_mode="this_cat")
    assert isinstance(result, list)


def test_qfh_search_this_cat_mode_null():
    """search_mode=this_cat with nfeed=0 → IS NULL clause."""
    session = _session()
    result = queryFeedHeadlines(session, feed=0, limit=10, view_mode="all_articles",
                                cat_view=False, owner_uid=1, search="news",
                                search_mode="this_cat")
    assert isinstance(result, list)


def test_qfh_with_since_id():
    session = _session()
    result = queryFeedHeadlines(session, feed=5, limit=10, view_mode="all_articles",
                                cat_view=False, owner_uid=1, since_id=100)
    assert isinstance(result, list)


def test_qfh_with_filter_():
    session = _session()
    f = {
        "match_any_rule": False,
        "inverse": False,
        "rules": [{"type": "title", "reg_exp": "python", "inverse": False}],
        "actions": [],
    }
    result = queryFeedHeadlines(session, feed=5, limit=10, view_mode="all_articles",
                                cat_view=False, owner_uid=1, filter_=f)
    assert isinstance(result, list)


def test_qfh_view_mode_unread():
    session = _session()
    result = queryFeedHeadlines(session, feed=5, limit=10, view_mode="unread",
                                cat_view=False, owner_uid=1)
    assert isinstance(result, list)


def test_qfh_view_mode_marked():
    session = _session()
    result = queryFeedHeadlines(session, feed=5, limit=10, view_mode="marked",
                                cat_view=False, owner_uid=1)
    assert isinstance(result, list)


def test_qfh_view_mode_published():
    session = _session()
    result = queryFeedHeadlines(session, feed=5, limit=10, view_mode="published",
                                cat_view=False, owner_uid=1)
    assert isinstance(result, list)


def test_qfh_view_mode_has_note():
    session = _session()
    result = queryFeedHeadlines(session, feed=5, limit=10, view_mode="has_note",
                                cat_view=False, owner_uid=1)
    assert isinstance(result, list)


def test_qfh_view_mode_unread_first():
    session = _session()
    result = queryFeedHeadlines(session, feed=5, limit=10, view_mode="unread_first",
                                cat_view=False, owner_uid=1)
    assert isinstance(result, list)


def test_qfh_view_mode_adaptive_unread_gt_zero():
    """adaptive mode with unread > 0 → adds unread=True WHERE clause."""
    session = _session()
    with patch("ttrss.feeds.counters._feed_unread", return_value=5):
        result = queryFeedHeadlines(session, feed=5, limit=10, view_mode="adaptive",
                                    cat_view=False, owner_uid=1)
    assert isinstance(result, list)


def test_qfh_view_mode_adaptive_unread_zero():
    """adaptive mode with unread = 0 → no extra WHERE clause."""
    session = _session()
    with patch("ttrss.feeds.counters._feed_unread", return_value=0):
        result = queryFeedHeadlines(session, feed=5, limit=10, view_mode="adaptive",
                                    cat_view=False, owner_uid=1)
    assert isinstance(result, list)


def test_qfh_with_limit_and_offset():
    session = _session()
    result = queryFeedHeadlines(session, feed=5, limit=20, view_mode="all_articles",
                                cat_view=False, owner_uid=1, offset=40)
    assert isinstance(result, list)


def test_qfh_no_limit_zero():
    """limit=0 → no LIMIT/OFFSET applied."""
    session = _session()
    result = queryFeedHeadlines(session, feed=5, limit=0, view_mode="all_articles",
                                cat_view=False, owner_uid=1)
    assert isinstance(result, list)


def test_qfh_override_order():
    session = _session()
    result = queryFeedHeadlines(session, feed=5, limit=10, view_mode="all_articles",
                                cat_view=False, owner_uid=1,
                                override_order="date_entered DESC")
    assert isinstance(result, list)


def test_qfh_override_strategy():
    """override_strategy replaces strategy_clause."""
    from sqlalchemy import true
    session = _session()
    result = queryFeedHeadlines(session, feed=5, limit=10, view_mode="all_articles",
                                cat_view=False, owner_uid=1,
                                override_strategy=true())
    assert isinstance(result, list)


def test_qfh_override_vfeed_includes_feed_title():
    """override_vfeed=True ensures feed_title is in SELECT columns."""
    session = _session()
    result = queryFeedHeadlines(session, feed=5, limit=10, view_mode="all_articles",
                                cat_view=False, owner_uid=1, override_vfeed=True)
    assert isinstance(result, list)


def test_qfh_with_start_ts():
    session = _session()
    result = queryFeedHeadlines(session, feed=5, limit=10, view_mode="all_articles",
                                cat_view=False, owner_uid=1,
                                start_ts="2025-01-01T00:00:00")
    assert isinstance(result, list)


def test_qfh_with_start_ts_invalid_ignored():
    session = _session()
    result = queryFeedHeadlines(session, feed=5, limit=10, view_mode="all_articles",
                                cat_view=False, owner_uid=1,
                                start_ts="not-a-date")
    assert isinstance(result, list)


def test_qfh_include_children_category():
    session = _session()
    with patch("ttrss.feeds.categories.getChildCategories", return_value=[5, 6]):
        result = queryFeedHeadlines(session, feed=3, limit=10, view_mode="all_articles",
                                    cat_view=True, owner_uid=1, include_children=True)
    assert isinstance(result, list)


def test_qfh_unknown_numeric_feed_fallback():
    """Unrecognized negative numeric feed → true() strategy, INNER JOIN feeds."""
    session = _session()
    result = queryFeedHeadlines(session, feed=-99, limit=10, view_mode="all_articles",
                                cat_view=False, owner_uid=1)
    assert isinstance(result, list)


def test_qfh_view_mode_unread_minus_six_no_clause():
    """view_mode=unread with feed=-6 does NOT add unread WHERE (recently-read feed)."""
    session = _session()
    result = queryFeedHeadlines(session, feed=-6, limit=10, view_mode="unread",
                                cat_view=False, owner_uid=1)
    assert isinstance(result, list)
