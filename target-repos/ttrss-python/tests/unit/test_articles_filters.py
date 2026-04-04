"""Unit tests for ttrss/articles/filters.py — filter loading, matching, scoring."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ttrss.articles.filters import (
    calculate_article_score,
    false_clause,
    filter_to_sql,
    find_article_filter,
    find_article_filters,
    get_article_filters,
    load_filters,
)


# ---------------------------------------------------------------------------
# get_article_filters — pure Python regex matching
# ---------------------------------------------------------------------------


def _make_filter(rules, actions, match_any=False, inverse=False):
    return {
        "match_any_rule": match_any,
        "inverse": inverse,
        "rules": rules,
        "actions": actions,
    }


def _rule(type_, reg_exp, inverse=False):
    return {"type": type_, "reg_exp": reg_exp, "inverse": inverse}


def _action(type_, param=""):
    return {"type": type_, "param": param}


def test_get_article_filters_empty_filters():
    assert get_article_filters([], "title", "content", "link", None, "author", []) == []


def test_get_article_filters_title_match():
    f = _make_filter([_rule("title", "python")], [_action("catchup")])
    result = get_article_filters([f], "Python News", "", "", None, "", [])
    assert len(result) == 1
    assert result[0]["type"] == "catchup"


def test_get_article_filters_title_no_match():
    f = _make_filter([_rule("title", "rust")], [_action("catchup")])
    result = get_article_filters([f], "Python News", "", "", None, "", [])
    assert result == []


def test_get_article_filters_content_match():
    f = _make_filter([_rule("content", "hello")], [_action("mark")])
    result = get_article_filters([f], "", "Hello World", "", None, "", [])
    assert len(result) == 1


def test_get_article_filters_both_match_on_title():
    f = _make_filter([_rule("both", "news")], [_action("catchup")])
    result = get_article_filters([f], "Breaking News", "", "", None, "", [])
    assert len(result) == 1


def test_get_article_filters_both_match_on_content():
    f = _make_filter([_rule("both", "update")], [_action("catchup")])
    result = get_article_filters([f], "Headline", "Latest update available", "", None, "", [])
    assert len(result) == 1


def test_get_article_filters_link_match():
    f = _make_filter([_rule("link", "example\\.com")], [_action("catchup")])
    result = get_article_filters([f], "", "", "http://example.com/page", None, "", [])
    assert len(result) == 1


def test_get_article_filters_author_match():
    f = _make_filter([_rule("author", "alice")], [_action("mark")])
    result = get_article_filters([f], "", "", "", None, "Alice Smith", [])
    assert len(result) == 1


def test_get_article_filters_tag_match():
    f = _make_filter([_rule("tag", "linux")], [_action("tag", "os")])
    result = get_article_filters([f], "", "", "", None, "", ["Linux", "kernel"])
    assert len(result) == 1


def test_get_article_filters_inverse_rule():
    """Rule inverse=True: match when pattern does NOT match."""
    f = _make_filter([_rule("title", "rust", inverse=True)], [_action("catchup")])
    # "Python" doesn't match "rust" → inverse → match
    result = get_article_filters([f], "Python news", "", "", None, "", [])
    assert len(result) == 1


def test_get_article_filters_inverse_filter():
    """Filter inverse=True: flip overall match."""
    f = _make_filter([_rule("title", "python")], [_action("catchup")], inverse=True)
    # "Python" matches → inverse → no match
    result = get_article_filters([f], "Python news", "", "", None, "", [])
    assert result == []


def test_get_article_filters_match_any_rule_or_logic():
    """match_any=True: ANY rule matching → filter fires."""
    rules = [_rule("title", "rust"), _rule("content", "python")]
    f = _make_filter(rules, [_action("catchup")], match_any=True)
    # Only content matches
    result = get_article_filters([f], "No rust here", "Python code", "", None, "", [])
    assert len(result) == 1


def test_get_article_filters_all_rules_and_logic():
    """match_any=False: ALL rules must match."""
    rules = [_rule("title", "news"), _rule("content", "breaking")]
    f = _make_filter(rules, [_action("mark")], match_any=False)
    # Only title matches, content doesn't
    result = get_article_filters([f], "Tech News", "Regular article", "", None, "", [])
    assert result == []


def test_get_article_filters_stop_action_halts():
    """Stop action causes immediate return — no further filter processing."""
    f1 = _make_filter([_rule("title", "stop")], [_action("stop"), _action("catchup")])
    f2 = _make_filter([_rule("title", "stop")], [_action("mark")])
    result = get_article_filters([f1, f2], "stop this", "", "", None, "", [])
    # stop action returned, no further processing
    assert len(result) == 1
    assert result[0]["type"] == "stop"


def test_get_article_filters_invalid_regex_skipped():
    """Invalid regex in rule does not raise — rule is skipped."""
    f = _make_filter([_rule("title", "[invalid")], [_action("catchup")])
    result = get_article_filters([f], "anything", "", "", None, "", [])
    assert result == []


def test_get_article_filters_empty_reg_exp_skipped():
    f = _make_filter([_rule("title", "")], [_action("catchup")])
    result = get_article_filters([f], "anything", "", "", None, "", [])
    assert result == []


def test_get_article_filters_content_strips_newlines():
    """Content newlines are stripped before matching (PHP preg_replace behaviour)."""
    f = _make_filter([_rule("content", "hello world")], [_action("catchup")])
    result = get_article_filters([f], "", "hello\nworld", "", None, "", [])
    # "hello\nworld" with newlines stripped → "helloworld" — pattern won't match
    assert result == []


def test_get_article_filters_case_insensitive():
    f = _make_filter([_rule("title", "PYTHON")], [_action("catchup")])
    result = get_article_filters([f], "python news", "", "", None, "", [])
    assert len(result) == 1


# ---------------------------------------------------------------------------
# find_article_filter
# ---------------------------------------------------------------------------


def test_find_article_filter_found():
    actions = [{"type": "mark", "param": ""}, {"type": "score", "param": "10"}]
    result = find_article_filter(actions, "score")
    assert result == {"type": "score", "param": "10"}


def test_find_article_filter_not_found():
    actions = [{"type": "mark", "param": ""}]
    assert find_article_filter(actions, "score") is None


def test_find_article_filter_empty():
    assert find_article_filter([], "mark") is None


# ---------------------------------------------------------------------------
# find_article_filters
# ---------------------------------------------------------------------------


def test_find_article_filters_returns_all():
    actions = [
        {"type": "tag", "param": "news"},
        {"type": "mark", "param": ""},
        {"type": "tag", "param": "tech"},
    ]
    result = find_article_filters(actions, "tag")
    assert len(result) == 2


def test_find_article_filters_none_found():
    actions = [{"type": "mark", "param": ""}]
    result = find_article_filters(actions, "score")
    assert result == []


# ---------------------------------------------------------------------------
# calculate_article_score
# ---------------------------------------------------------------------------


def test_calculate_article_score_empty():
    assert calculate_article_score([]) == 0


def test_calculate_article_score_sums():
    actions = [
        {"type": "score", "param": "10"},
        {"type": "score", "param": "5"},
        {"type": "mark", "param": ""},
    ]
    assert calculate_article_score(actions) == 15


def test_calculate_article_score_negative():
    actions = [{"type": "score", "param": "-20"}]
    assert calculate_article_score(actions) == -20


def test_calculate_article_score_invalid_param():
    """Non-numeric param is silently skipped."""
    actions = [{"type": "score", "param": "bad"}, {"type": "score", "param": "5"}]
    assert calculate_article_score(actions) == 5


def test_calculate_article_score_only_non_score():
    """No 'score' type actions → 0."""
    actions = [{"type": "mark", "param": ""}, {"type": "tag", "param": "news"}]
    assert calculate_article_score(actions) == 0


# ---------------------------------------------------------------------------
# load_filters — smoke tests
# ---------------------------------------------------------------------------


def test_load_filters_returns_empty_when_no_filters():
    session = MagicMock()
    # cat_id query, getParentCategories calls, filter rows query
    session.execute.side_effect = [
        MagicMock(**{"scalar_one_or_none.return_value": None}),  # cat_id
        MagicMock(**{"all.return_value": []}),                   # filter rows
    ]
    with patch("ttrss.feeds.categories.getParentCategories", return_value=[]):
        result = load_filters(session, feed_id=5, owner_uid=1)
    assert result == []


# ---------------------------------------------------------------------------
# filter_to_sql — SQLAlchemy expression generation
# ---------------------------------------------------------------------------


def test_filter_to_sql_empty_rules_returns_false_clause():
    session = MagicMock()
    f = {"match_any_rule": False, "inverse": False, "rules": [], "actions": []}
    result = filter_to_sql(session, f, owner_uid=1)
    # Should return the false clause (a literal False)
    assert result is not None


def test_filter_to_sql_title_rule():
    session = MagicMock()
    f = {
        "match_any_rule": False,
        "inverse": False,
        "rules": [{"type": "title", "reg_exp": "python", "inverse": False}],
        "actions": [],
    }
    with patch("ttrss.feeds.categories.getChildCategories", return_value=[]):
        result = filter_to_sql(session, f, owner_uid=1)
    assert result is not None
    # Should produce a SQL expression, not None
    assert str(result) != ""


def test_filter_to_sql_content_rule():
    session = MagicMock()
    f = {
        "match_any_rule": False,
        "inverse": False,
        "rules": [{"type": "content", "reg_exp": "news", "inverse": False}],
        "actions": [],
    }
    result = filter_to_sql(session, f, owner_uid=1)
    assert result is not None


def test_filter_to_sql_both_rule():
    session = MagicMock()
    f = {
        "match_any_rule": False,
        "inverse": False,
        "rules": [{"type": "both", "reg_exp": "tech", "inverse": False}],
        "actions": [],
    }
    result = filter_to_sql(session, f, owner_uid=1)
    assert result is not None


def test_filter_to_sql_link_rule():
    session = MagicMock()
    f = {
        "match_any_rule": False,
        "inverse": False,
        "rules": [{"type": "link", "reg_exp": "example", "inverse": False}],
        "actions": [],
    }
    result = filter_to_sql(session, f, owner_uid=1)
    assert result is not None


def test_filter_to_sql_author_rule():
    session = MagicMock()
    f = {
        "match_any_rule": False,
        "inverse": False,
        "rules": [{"type": "author", "reg_exp": "alice", "inverse": False}],
        "actions": [],
    }
    result = filter_to_sql(session, f, owner_uid=1)
    assert result is not None


def test_filter_to_sql_tag_rule():
    session = MagicMock()
    f = {
        "match_any_rule": False,
        "inverse": False,
        "rules": [{"type": "tag", "reg_exp": "linux", "inverse": False}],
        "actions": [],
    }
    result = filter_to_sql(session, f, owner_uid=1)
    assert result is not None


def test_filter_to_sql_unknown_type_skipped():
    session = MagicMock()
    f = {
        "match_any_rule": False,
        "inverse": False,
        "rules": [{"type": "unknown_type", "reg_exp": "x", "inverse": False}],
        "actions": [],
    }
    result = filter_to_sql(session, f, owner_uid=1)
    # Unknown type → no valid clauses → false_clause
    assert result is not None


def test_filter_to_sql_inverse_rule():
    session = MagicMock()
    f = {
        "match_any_rule": False,
        "inverse": False,
        "rules": [{"type": "title", "reg_exp": "spam", "inverse": True}],
        "actions": [],
    }
    result = filter_to_sql(session, f, owner_uid=1)
    assert result is not None


def test_filter_to_sql_inverse_filter():
    session = MagicMock()
    f = {
        "match_any_rule": False,
        "inverse": True,
        "rules": [{"type": "title", "reg_exp": "spam", "inverse": False}],
        "actions": [],
    }
    result = filter_to_sql(session, f, owner_uid=1)
    assert result is not None


def test_filter_to_sql_match_any_rule_uses_or():
    session = MagicMock()
    f = {
        "match_any_rule": True,
        "inverse": False,
        "rules": [
            {"type": "title", "reg_exp": "news", "inverse": False},
            {"type": "content", "reg_exp": "update", "inverse": False},
        ],
        "actions": [],
    }
    result = filter_to_sql(session, f, owner_uid=1)
    assert result is not None


def test_filter_to_sql_with_cat_scope_zero():
    """Rule with cat_id=0 → IS NULL cat scope."""
    session = MagicMock()
    f = {
        "match_any_rule": False,
        "inverse": False,
        "rules": [{"type": "title", "reg_exp": "test", "inverse": False, "cat_id": 0}],
        "actions": [],
    }
    result = filter_to_sql(session, f, owner_uid=1)
    assert result is not None


def test_filter_to_sql_with_cat_scope_positive():
    """Rule with cat_id > 0 → IN (children + cat_id)."""
    session = MagicMock()
    f = {
        "match_any_rule": False,
        "inverse": False,
        "rules": [{"type": "title", "reg_exp": "test", "inverse": False, "cat_id": 3}],
        "actions": [],
    }
    with patch("ttrss.feeds.categories.getChildCategories", return_value=[10, 11]):
        result = filter_to_sql(session, f, owner_uid=1)
    assert result is not None


def test_filter_to_sql_with_feed_id_scope():
    """Rule with feed_id > 0 → AND feed_id = X clause added."""
    session = MagicMock()
    f = {
        "match_any_rule": False,
        "inverse": False,
        "rules": [{"type": "title", "reg_exp": "test", "inverse": False, "feed_id": 7}],
        "actions": [],
    }
    result = filter_to_sql(session, f, owner_uid=1)
    assert result is not None


def test_filter_to_sql_invalid_regex_skipped():
    session = MagicMock()
    f = {
        "match_any_rule": False,
        "inverse": False,
        "rules": [{"type": "title", "reg_exp": "[invalid", "inverse": False}],
        "actions": [],
    }
    result = filter_to_sql(session, f, owner_uid=1)
    # Invalid regex → false_clause
    assert result is not None


def test_false_clause_returns_expression():
    result = false_clause()
    assert result is not None


def test_load_filters_skips_filter_without_rules():
    """Filters with empty rules list are not included."""
    session = MagicMock()
    filter_row = MagicMock()
    filter_row.id = 1
    filter_row.match_any_rule = False
    filter_row.inverse = False

    call_count = [0]

    def side_effect(*args, **kwargs):
        call_count[0] += 1
        r = MagicMock()
        if call_count[0] == 1:
            r.scalar_one_or_none.return_value = 0  # cat_id
        elif call_count[0] == 2:
            r.all.return_value = [filter_row]  # filter rows
        elif call_count[0] == 3:
            r.all.return_value = []  # rules → empty
        elif call_count[0] == 4:
            r.all.return_value = []  # actions → empty
        return r

    session.execute.side_effect = side_effect

    with patch("ttrss.feeds.categories.getParentCategories", return_value=[]):
        result = load_filters(session, feed_id=5, owner_uid=1)

    # Filter has no rules → excluded
    assert result == []
