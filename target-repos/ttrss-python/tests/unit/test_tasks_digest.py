"""Unit tests for ttrss/tasks/digest.py — per-user email digest preparation and sending.

Source PHP: ttrss/include/digest.php (prepare_headlines_digest, send_headlines_digests)

Patching strategy
-----------------
``prepare_headlines_digest`` imports ``db`` and ``get_user_pref`` *inside* the
function body (to avoid circular imports at module level).  We therefore patch
their canonical module paths:

  patch("ttrss.extensions.db")          — db used inside prepare_headlines_digest
  patch("ttrss.prefs.ops.get_user_pref") — get_user_pref used inside prepare_…

``send_headlines_digests`` wraps everything in a nested ``_run()`` closure that
also imports ``db``, ``get_user_pref`` and ``send_mail`` locally, so we patch:

  patch("ttrss.tasks.digest.send_mail")  — via the inline import in _run()
  patch("ttrss.utils.mail.send_mail")    — underlying implementation path
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Shared row factory
# ---------------------------------------------------------------------------


def _make_row(
    title="T",
    link="http://x.com",
    content="<p>body</p>",
    ref_id=1,
    feed_title="Feed",
    score=0,
    int_id=1,
    cat_title=None,
    date_updated=None,
):
    """Build a MagicMock row that mirrors the SQLAlchemy result row columns.

    Source: ttrss/include/digest.php lines 107-128 — SELECT columns used in the
    main query: title, link, content, date_updated, ref_id, feed_title, score,
    int_id, cat_title.
    """
    row = MagicMock()
    row.title = title
    row.link = link
    row.content = content
    row.date_updated = date_updated or datetime.now(timezone.utc)
    row.ref_id = ref_id
    row.feed_title = feed_title
    row.score = score
    row.int_id = int_id
    row.cat_title = cat_title
    return row


# ---------------------------------------------------------------------------
# Context manager that wires up db + get_user_pref mocks for prepare_headlines_digest
# ---------------------------------------------------------------------------


def _patch_prepare(rows, tz_pref="UTC", enable_cats_pref="false"):
    """Return a dict of patch objects and mock handles for prepare_headlines_digest.

    ``rows``             — list of row objects returned by db.session.execute().fetchall()
    ``tz_pref``          — value returned for USER_TIMEZONE pref
    ``enable_cats_pref`` — value returned for ENABLE_FEED_CATS pref
    """
    mock_db = MagicMock()
    mock_db.session.execute.return_value.fetchall.return_value = rows

    def _get_user_pref(uid, key):
        if key == "USER_TIMEZONE":
            return tz_pref
        if key == "ENABLE_FEED_CATS":
            return enable_cats_pref
        return None

    return mock_db, _get_user_pref


# ===========================================================================
# prepare_headlines_digest — no rows
# ===========================================================================


def test_prepare_headlines_digest_no_rows_returns_none():
    """prepare_headlines_digest returns None when DB query returns no rows.

    Source: ttrss/include/digest.php lines 65-67 — "No headlines" branch returns null.
    """
    mock_db, pref_fn = _patch_prepare(rows=[])

    with patch("ttrss.extensions.db", mock_db), \
         patch("ttrss.prefs.ops.get_user_pref", side_effect=pref_fn):
        from ttrss.tasks.digest import prepare_headlines_digest

        result = prepare_headlines_digest(user_id=1)

    assert result is None


# ===========================================================================
# prepare_headlines_digest — with rows
# ===========================================================================


def test_prepare_headlines_digest_with_rows_returns_dict_with_required_keys():
    """prepare_headlines_digest returns dict with subject, html, text, article_count, affected_ids.

    Source: ttrss/include/digest.php line 190 — return array($tmp, $headlines_count, $affected_ids, $tmp_t).
    Adapted: PHP tuple replaced by named dict.
    """
    rows = [_make_row(ref_id=1), _make_row(ref_id=2)]
    mock_db, pref_fn = _patch_prepare(rows=rows)

    with patch("ttrss.extensions.db", mock_db), \
         patch("ttrss.prefs.ops.get_user_pref", side_effect=pref_fn):
        from ttrss.tasks.digest import prepare_headlines_digest

        result = prepare_headlines_digest(user_id=1)

    assert result is not None
    for key in ("subject", "html", "text", "article_count", "affected_ids"):
        assert key in result, f"Missing key: {key}"


def test_prepare_headlines_digest_article_count_matches_row_count():
    """article_count in result equals the number of rows returned by the query.

    Source: ttrss/include/digest.php line 190 — $headlines_count derived from row count.
    """
    rows = [_make_row(ref_id=i) for i in range(1, 6)]
    mock_db, pref_fn = _patch_prepare(rows=rows)

    with patch("ttrss.extensions.db", mock_db), \
         patch("ttrss.prefs.ops.get_user_pref", side_effect=pref_fn):
        from ttrss.tasks.digest import prepare_headlines_digest

        result = prepare_headlines_digest(user_id=1)

    assert result["article_count"] == 5


def test_prepare_headlines_digest_affected_ids_is_list_of_ref_ids():
    """affected_ids contains each row's ref_id in order.

    Source: ttrss/include/digest.php line 190 — $affected_ids collected from query rows.
    """
    rows = [_make_row(ref_id=10), _make_row(ref_id=20), _make_row(ref_id=30)]
    mock_db, pref_fn = _patch_prepare(rows=rows)

    with patch("ttrss.extensions.db", mock_db), \
         patch("ttrss.prefs.ops.get_user_pref", side_effect=pref_fn):
        from ttrss.tasks.digest import prepare_headlines_digest

        result = prepare_headlines_digest(user_id=1)

    assert result["affected_ids"] == [10, 20, 30]


def test_prepare_headlines_digest_html_contains_feed_title_in_h3():
    """HTML body wraps each feed section title in an <h3> tag.

    Source: ttrss/include/digest.php lines 177-180 — addBlock('feed') outputs feed title header.
    """
    rows = [_make_row(feed_title="My Feed")]
    mock_db, pref_fn = _patch_prepare(rows=rows)

    with patch("ttrss.extensions.db", mock_db), \
         patch("ttrss.prefs.ops.get_user_pref", side_effect=pref_fn):
        from ttrss.tasks.digest import prepare_headlines_digest

        result = prepare_headlines_digest(user_id=1)

    assert "<h3>" in result["html"]
    assert "My Feed" in result["html"]


def test_prepare_headlines_digest_excerpt_truncated_at_300_chars():
    """HTML body excerpt is truncated to 300 chars with trailing '...'.

    Source: ttrss/include/digest.php line 161-162 — truncate_string(strip_tags(...), 300).
    The excerpt is embedded in the HTML body inside an <em> tag; plain text does not
    include the excerpt (only title, link, and updated fields).
    """
    long_text = "A" * 400
    rows = [_make_row(content=f"<p>{long_text}</p>")]
    mock_db, pref_fn = _patch_prepare(rows=rows)

    with patch("ttrss.extensions.db", mock_db), \
         patch("ttrss.prefs.ops.get_user_pref", side_effect=pref_fn):
        from ttrss.tasks.digest import prepare_headlines_digest

        result = prepare_headlines_digest(user_id=1)

    # The excerpt in HTML is html.escape'd then wrapped in <em>; the raw "..." suffix
    # appears as literal characters in the HTML body.
    assert "..." in result["html"]
    # Verify the truncation: the content was 400 chars, so excerpt must end with "..."
    # and must not be longer than 303 chars (300 + "...")
    import re as _re
    # Extract the excerpt from the <em>...</em> block
    match = _re.search(r"<em>(.*?)</em>", result["html"])
    assert match is not None, "Expected <em> block with excerpt in HTML body"
    excerpt_html = match.group(1)
    # html.unescape to get plain text length
    import html as _html
    excerpt_plain = _html.unescape(excerpt_html)
    assert excerpt_plain.endswith("..."), "Excerpt must end with '...'"
    assert len(excerpt_plain) <= 303, "Excerpt must not exceed 300 chars + '...'"


def test_prepare_headlines_digest_html_tags_stripped_from_excerpt():
    """HTML tags are stripped from article content before building the excerpt.

    Source: ttrss/include/digest.php line 161 — strip_tags applied before truncation.
    """
    rows = [_make_row(content="<b>Bold</b> and <i>italic</i> text")]
    mock_db, pref_fn = _patch_prepare(rows=rows)

    with patch("ttrss.extensions.db", mock_db), \
         patch("ttrss.prefs.ops.get_user_pref", side_effect=pref_fn):
        from ttrss.tasks.digest import prepare_headlines_digest

        result = prepare_headlines_digest(user_id=1)

    # The raw tags must NOT appear in the HTML excerpt portion
    # (they will be HTML-escaped, so <b> → &lt;b&gt; would appear — check raw tags absent)
    html_body = result["html"]
    # The content "<b>Bold</b> and <i>italic</i> text" should have tags stripped.
    # After strip, "Bold  and  italic  text" → normalised.  Verify no raw <b>/<i> in excerpt.
    assert "<b>" not in html_body
    assert "<i>" not in html_body


def test_prepare_headlines_digest_enable_feed_cats_true_adds_cat_prefix():
    """When ENABLE_FEED_CATS=true, feed section title is prefixed with category name.

    Source: ttrss/include/digest.php lines 171-175 — if ENABLE_FEED_CATS prepend cat_title.
    """
    rows = [_make_row(feed_title="My Feed", cat_title="Cat")]
    mock_db, pref_fn = _patch_prepare(rows=rows, enable_cats_pref="true")

    with patch("ttrss.extensions.db", mock_db), \
         patch("ttrss.prefs.ops.get_user_pref", side_effect=pref_fn):
        from ttrss.tasks.digest import prepare_headlines_digest

        result = prepare_headlines_digest(user_id=1)

    assert "Cat / My Feed" in result["html"]


def test_prepare_headlines_digest_enable_feed_cats_false_no_cat_prefix():
    """When ENABLE_FEED_CATS=false, category name is NOT prefixed to feed title.

    Source: ttrss/include/digest.php lines 171-175 — ENABLE_FEED_CATS guard condition.
    """
    rows = [_make_row(feed_title="My Feed", cat_title="Cat")]
    mock_db, pref_fn = _patch_prepare(rows=rows, enable_cats_pref="false")

    with patch("ttrss.extensions.db", mock_db), \
         patch("ttrss.prefs.ops.get_user_pref", side_effect=pref_fn):
        from ttrss.tasks.digest import prepare_headlines_digest

        result = prepare_headlines_digest(user_id=1)

    assert "Cat / My Feed" not in result["html"]
    assert "My Feed" in result["html"]


def test_prepare_headlines_digest_user_timezone_applied():
    """USER_TIMEZONE preference is fetched and used to compute the local date/time header.

    Source: ttrss/include/digest.php lines 88-96 — CUR_DATE/CUR_TIME from user timezone pref.
    """
    rows = [_make_row()]
    mock_db, pref_fn = _patch_prepare(rows=rows, tz_pref="UTC")

    calls = []

    def _tracking_pref(uid, key):
        calls.append(key)
        return pref_fn(uid, key)

    with patch("ttrss.extensions.db", mock_db), \
         patch("ttrss.prefs.ops.get_user_pref", side_effect=_tracking_pref):
        from ttrss.tasks.digest import prepare_headlines_digest

        result = prepare_headlines_digest(user_id=1)

    assert "USER_TIMEZONE" in calls
    assert result is not None


# ===========================================================================
# send_headlines_digests — integration-style unit tests
# ===========================================================================


def _make_send_db(users):
    """Build a MagicMock db object suitable for send_headlines_digests._run()."""
    mock_db = MagicMock()
    mock_db.session.execute.return_value.scalars.return_value.all.return_value = users
    return mock_db


def _make_send_user(uid=1, email="user@example.com", login="u1",
                    last_digest_sent=None):
    user = MagicMock()
    user.id = uid
    user.email = email
    user.login = login
    user.last_digest_sent = last_digest_sent
    return user


def test_send_headlines_digests_skips_user_with_digest_enable_false():
    """send_headlines_digests does not send to users with DIGEST_ENABLE=false.

    Source: ttrss/include/digest.php line 29 — if (get_pref('DIGEST_ENABLE', ...)) guard.
    """
    user = _make_send_user()
    mock_db = _make_send_db([user])

    payload = {
        "subject": "s", "html": "<p>h</p>", "text": "t",
        "article_count": 1, "affected_ids": [1],
    }

    def _pref(uid, key):
        if key == "DIGEST_ENABLE":
            return "false"
        if key == "DIGEST_PREFERRED_TIME":
            return "00:00"
        return None

    with patch("ttrss.extensions.db", mock_db), \
         patch("ttrss.prefs.ops.get_user_pref", side_effect=_pref), \
         patch("ttrss.utils.mail.send_mail") as mock_mail, \
         patch("ttrss.tasks.digest.prepare_headlines_digest", return_value=payload):
        from ttrss.tasks.digest import send_headlines_digests

        count = send_headlines_digests(app=None)

    mock_mail.assert_not_called()
    assert count == 0


def test_send_headlines_digests_respects_preferred_time_window():
    """send_headlines_digests skips users whose DIGEST_PREFERRED_TIME window hasn't started.

    Source: ttrss/include/digest.php lines 33-34 — time() >= $preferred_ts &&
    time() - $preferred_ts <= 7200 (2-hour window).
    """
    from datetime import timedelta

    user = _make_send_user()
    mock_db = _make_send_db([user])

    # Set preferred time to 6 hours in the future — outside the 2h window
    future_time = (datetime.now(timezone.utc) + timedelta(hours=6)).strftime("%H:%M")

    def _pref(uid, key):
        if key == "DIGEST_ENABLE":
            return "true"
        if key == "DIGEST_PREFERRED_TIME":
            return future_time
        return None

    with patch("ttrss.extensions.db", mock_db), \
         patch("ttrss.prefs.ops.get_user_pref", side_effect=_pref), \
         patch("ttrss.utils.mail.send_mail") as mock_mail, \
         patch("ttrss.tasks.digest.prepare_headlines_digest", return_value=None):
        from ttrss.tasks.digest import send_headlines_digests

        count = send_headlines_digests(app=None)

    mock_mail.assert_not_called()
    assert count == 0


def test_send_headlines_digests_calls_catchup_when_digest_catchup_true():
    """send_headlines_digests calls _catchup_digest_articles when DIGEST_CATCHUP=true.

    Source: ttrss/include/digest.php lines 61-63 — catchupArticlesById($affected_ids, 0, ...) call.
    """
    user = _make_send_user()
    mock_db = _make_send_db([user])

    affected = [1, 2, 3]
    payload = {
        "subject": "s", "html": "<p>h</p>", "text": "t",
        "article_count": 3, "affected_ids": affected,
    }

    # preferred time = now so the window check passes
    now_str = datetime.now(timezone.utc).strftime("%H:%M")

    def _pref(uid, key):
        if key == "DIGEST_ENABLE":
            return "true"
        if key == "DIGEST_PREFERRED_TIME":
            return now_str
        if key == "DIGEST_CATCHUP":
            return "true"
        return None

    with patch("ttrss.extensions.db", mock_db), \
         patch("ttrss.prefs.ops.get_user_pref", side_effect=_pref), \
         patch("ttrss.utils.mail.send_mail", return_value=True), \
         patch("ttrss.tasks.digest.prepare_headlines_digest", return_value=payload), \
         patch("ttrss.tasks.digest._catchup_digest_articles") as mock_catchup:
        from ttrss.tasks.digest import send_headlines_digests

        send_headlines_digests(app=None)

    mock_catchup.assert_called_once_with(user.id, affected, mock_db)


def test_send_headlines_digests_updates_last_digest_sent():
    """send_headlines_digests sets last_digest_sent=NOW() for each processed user.

    Source: ttrss/include/digest.php lines 69-71 — UPDATE ttrss_users SET last_digest_sent=NOW().
    This update happens regardless of whether articles were found.
    """
    user = _make_send_user()
    mock_db = _make_send_db([user])

    now_str = datetime.now(timezone.utc).strftime("%H:%M")

    def _pref(uid, key):
        if key == "DIGEST_ENABLE":
            return "true"
        if key == "DIGEST_PREFERRED_TIME":
            return now_str
        if key == "DIGEST_CATCHUP":
            return "false"
        return None

    payload = {
        "subject": "s", "html": "<p>h</p>", "text": "t",
        "article_count": 1, "affected_ids": [1],
    }

    with patch("ttrss.extensions.db", mock_db), \
         patch("ttrss.prefs.ops.get_user_pref", side_effect=_pref), \
         patch("ttrss.utils.mail.send_mail", return_value=True), \
         patch("ttrss.tasks.digest.prepare_headlines_digest", return_value=payload):
        from ttrss.tasks.digest import send_headlines_digests

        send_headlines_digests(app=None)

    # execute() must have been called at least once for the last_digest_sent UPDATE
    mock_db.session.execute.assert_called()
    mock_db.session.commit.assert_called()
