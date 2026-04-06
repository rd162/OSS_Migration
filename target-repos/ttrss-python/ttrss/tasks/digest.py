"""
Email digest tasks — prepare and send per-user article digests.

Source: ttrss/include/digest.php (prepare_headlines_digest, send_headlines_digests)
Adapted: PHP db_query()/db_fetch_assoc() replaced by SQLAlchemy ORM queries.
         PHP MiniTemplator template engine replaced by Python f-string HTML/text builder.
         PHP ttrssMailer::quickMail() replaced by ttrss.utils.mail.send_mail().
New: returns structured dict instead of PHP array tuple for prepare_headlines_digest.
     Celery task wrapper omitted — send_headlines_digests is a plain function callable
     from a Beat-scheduled Celery task or directly from management scripts.
"""
from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from ttrss.models.category import TtRssFeedCategory

logger = logging.getLogger(__name__)  # New: no PHP equivalent — Python logging setup.

# Source: ttrss/include/digest.php line 55 — define('DIGEST_SUBJECT', ...)
# Inferred from PHP constant usage: subject used in $mail->quickMail(..., DIGEST_SUBJECT, ...)
DIGEST_SUBJECT = "[tt-rss] New headlines for today"


def prepare_headlines_digest(
    user_id: int,
    days: int = 1,
    limit: int = 1000,
) -> Optional[dict]:
    """
    # Source: ttrss/include/digest.php:prepare_headlines_digest
    Build email digest payload for a user: fetch recent unread articles,
    format into subject + HTML body + plain-text body.
    Returns {"subject": str, "html": str, "text": str, "article_count": int}
    or None if no articles.
    """
    # Source: ttrss/include/digest.php lines 88-96 — get user timezone, compute local date/time
    from ttrss.extensions import db
    from ttrss.models.category import TtRssFeedCategory
    from ttrss.models.entry import TtRssEntry
    from ttrss.models.feed import TtRssFeed
    from ttrss.models.user_entry import TtRssUserEntry
    from ttrss.prefs.ops import get_user_pref
    from sqlalchemy import and_, select

    # Source: ttrss/include/digest.php lines 93-97 — CUR_DATE / CUR_TIME from user timezone
    user_tz_string = get_user_pref(user_id, "USER_TIMEZONE") or "UTC"
    try:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        try:
            user_tz = ZoneInfo(user_tz_string)
        except (ZoneInfoNotFoundError, KeyError):
            user_tz = timezone.utc
    except ImportError:
        user_tz = timezone.utc

    now_local = datetime.now(tz=user_tz)
    cur_date = now_local.strftime("%Y/%m/%d")
    cur_time = now_local.strftime("%-H:%M")  # PHP "G:i" — no leading zero on hour

    # Source: ttrss/include/digest.php lines 101-105 — interval query for recent articles
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)

    # Source: ttrss/include/digest.php lines 107-128 — main query joining user_entries, entries, feeds
    # LEFT JOIN ttrss_feed_categories to get cat_title for sorting and display.
    # Source: digest.php ORDER BY ttrss_feed_categories.title, ttrss_feeds.title, score DESC, date_updated DESC
    stmt = (
        select(
            TtRssEntry.title,
            TtRssEntry.link,
            TtRssEntry.content,
            TtRssEntry.date_updated,
            TtRssEntry.id.label("ref_id"),
            TtRssFeed.title.label("feed_title"),
            TtRssUserEntry.score,
            TtRssUserEntry.int_id,
            TtRssFeedCategory.title.label("cat_title"),
        )
        .select_from(TtRssUserEntry)
        .join(TtRssEntry, TtRssUserEntry.ref_id == TtRssEntry.id)
        .join(TtRssFeed, TtRssUserEntry.feed_id == TtRssFeed.id)
        .outerjoin(TtRssFeedCategory, TtRssFeed.cat_id == TtRssFeedCategory.id)
        .where(
            and_(
                TtRssUserEntry.owner_uid == user_id,
                TtRssUserEntry.unread.is_(True),
                TtRssUserEntry.score >= 0,
                TtRssFeed.include_in_digest.is_(True),
                TtRssEntry.date_updated > cutoff,
            )
        )
        .order_by(
            # Source: digest.php — ORDER BY ttrss_feed_categories.title (NULLs first so uncategorised sorts before named cats)
            TtRssFeedCategory.title.nulls_first(),
            TtRssFeed.title,
            TtRssUserEntry.score.desc(),
            TtRssEntry.date_updated.desc(),
        )
        .limit(limit)
    )

    rows = db.session.execute(stmt).fetchall()

    if not rows:
        # Source: ttrss/include/digest.php lines 65-67 — "No headlines" branch
        logger.debug("prepare_headlines_digest: no headlines for uid=%d", user_id)
        return None

    # Source: ttrss/include/digest.php lines 132-182 — iterate headlines, build template output
    article_count = len(rows)
    affected_ids = [row.ref_id for row in rows]

    # Source: ttrss/include/digest.php lines 87-88 — tpl->setVariable('CUR_DATE'), tpl->setVariable('CUR_TIME')
    # HTML body builder (replaces MiniTemplator HTML template)
    html_parts: list[str] = []
    html_parts.append(
        f"<html><body>"
        f"<p><strong>Date:</strong> {html.escape(cur_date)} {html.escape(cur_time)}</p>"
    )

    # Plain-text body builder (replaces MiniTemplator plain-text template)
    text_parts: list[str] = []
    text_parts.append(f"Date: {cur_date} {cur_time}\n")

    # Source: ttrss/include/digest.php lines 171-175 — ENABLE_FEED_CATS: prepend cat_title to feed_title
    enable_feed_cats_raw = get_user_pref(user_id, "ENABLE_FEED_CATS") or "false"
    enable_feed_cats = enable_feed_cats_raw.lower() not in {"false", "0", ""}

    current_feed: Optional[str] = None

    for row in rows:
        feed_title = row.feed_title or ""
        # Source: ttrss/include/digest.php lines 171-175 — if ENABLE_FEED_CATS, prefix "CatTitle / FeedTitle"
        if enable_feed_cats and row.cat_title:
            feed_title = f"{row.cat_title} / {feed_title}"
        article_title = row.title or "(untitled)"
        article_link = row.link or ""
        # Source: ttrss/include/digest.php line 144 — make_local_datetime for display timestamp
        article_updated = (
            row.date_updated.strftime("%Y-%m-%d %H:%M")
            if row.date_updated
            else ""
        )
        # Source: ttrss/include/digest.php line 161-162 — ARTICLE_EXCERPT: truncate_string(strip_tags(...), 300)
        raw_content = row.content or ""
        plain_content = re.sub(r"<[^>]+>", " ", raw_content)  # strip HTML tags
        plain_content = html.unescape(plain_content)
        plain_content = " ".join(plain_content.split())
        excerpt = plain_content[:300]
        if len(plain_content) > 300:
            excerpt += "..."

        # Source: ttrss/include/digest.php lines 177-180 — addBlock('feed') when feed changes
        if feed_title != current_feed:
            if current_feed is not None:
                html_parts.append("</ul>")
                text_parts.append("")
            html_parts.append(
                f"<h3>{html.escape(feed_title)}</h3><ul>"
            )
            text_parts.append(f"\n=== {feed_title} ===")
            current_feed = feed_title

        # Source: ttrss/include/digest.php lines 157-175 — tpl->setVariable per article
        html_parts.append(
            f"<li>"
            f"<a href=\"{html.escape(article_link)}\">{html.escape(article_title)}</a>"
            f" <small>({html.escape(article_updated)})</small>"
            f"<br/><em>{html.escape(excerpt)}</em>"
            f"</li>"
        )

        text_parts.append(
            f"* {article_title}\n"
            f"  Link:    {article_link}\n"
            f"  Updated: {article_updated}"
        )

    # Close last feed section
    if current_feed is not None:
        html_parts.append("</ul>")

    html_parts.append("</body></html>")

    html_body = "\n".join(html_parts)
    text_body = "\n".join(text_parts)

    # Source: ttrss/include/digest.php line 190 — return array($tmp, $headlines_count, $affected_ids, $tmp_t)
    # Adapted: PHP tuple replaced by named dict for clarity.
    return {
        "subject": DIGEST_SUBJECT,
        "html": html_body,
        "text": text_body,
        "article_count": article_count,
        "affected_ids": affected_ids,
    }


def send_headlines_digests(app=None) -> int:
    """
    # Source: ttrss/include/digest.php:send_headlines_digests
    # Source: ttrss/classes/backend.php:digestTest (PHP test trigger; Celery task replaces)
    For each user with DIGEST_ENABLE=true and digest time reached,
    call prepare_headlines_digest + send via send_mail().
    Returns count of digests sent.
    """
    # Source: ttrss/include/digest.php lines 13-14 — batch limits
    user_limit = 15   # Source: ttrss/include/digest.php line 13 — $user_limit = 15
    limit = 1000      # Source: ttrss/include/digest.php line 14 — $limit = 1000

    from ttrss.utils.mail import send_mail

    # Source: ttrss/include/digest.php lines 18-23 — query users with non-empty email,
    # last_digest_sent IS NULL or older than 1 day
    # FLAW 2 fix: removed create_app() fallback — calling it here would mutate shared
    # extension singletons with production settings, breaking test isolation.
    # If app=None and no active context exists, _run() proceeds without one (caller is
    # responsible; unit tests mock ttrss.extensions.db directly so no context is needed).
    if app is None:
        from flask import current_app
        try:
            app = current_app._get_current_object()
        except RuntimeError:
            pass  # No active context; fall through to contextless _run() call below

    def _run() -> int:
        from ttrss.extensions import db
        from ttrss.models.user import TtRssUser
        from ttrss.prefs.ops import get_user_pref
        from sqlalchemy import or_, select, func, update
        import re as _re

        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=1)

        # Source: ttrss/include/digest.php lines 24-26 — SELECT id, email FROM ttrss_users
        # WHERE email != '' AND (last_digest_sent IS NULL OR last_digest_sent < NOW()-1day)
        stmt = select(TtRssUser).where(
            TtRssUser.email != "",
            or_(
                TtRssUser.last_digest_sent.is_(None),
                TtRssUser.last_digest_sent < cutoff,
            ),
        ).limit(user_limit)

        users = db.session.execute(stmt).scalars().all()

        sent_count = 0

        for user in users:
            # Source: ttrss/include/digest.php line 29 — if (get_pref('DIGEST_ENABLE', ...))
            digest_enable = get_user_pref(user.id, "DIGEST_ENABLE")
            if not digest_enable or digest_enable.lower() in {"false", "0", ""}:
                continue

            # Source: ttrss/include/digest.php lines 30-34 — preferred time check (within 2h window)
            preferred_time_str = get_user_pref(user.id, "DIGEST_PREFERRED_TIME") or "00:00"
            # Source: ttrss/include/digest.php line 31 — strtotime(get_pref('DIGEST_PREFERRED_TIME'))
            # Compute today's preferred timestamp in UTC
            try:
                # Parse "HH:MM" format
                match = _re.match(r"^(\d{1,2}):(\d{2})$", preferred_time_str.strip())
                if match:
                    pref_hour = int(match.group(1))
                    pref_minute = int(match.group(2))
                    now_utc = datetime.now(tz=timezone.utc)
                    preferred_ts = now_utc.replace(
                        hour=pref_hour, minute=pref_minute, second=0, microsecond=0
                    )
                else:
                    preferred_ts = None
            except ValueError:
                preferred_ts = None

            # Source: ttrss/include/digest.php lines 33-34 — time() >= $preferred_ts && time() - $preferred_ts <= 7200
            if preferred_ts is not None:
                now_utc = datetime.now(tz=timezone.utc)
                elapsed = (now_utc - preferred_ts).total_seconds()
                if not (0 <= elapsed <= 7200):
                    continue
            # If preferred_ts is None (bad format), skip the window check and send anyway

            logger.debug(
                "send_headlines_digests: sending for uid=%d email=%s",
                user.id,
                user.email,
            )

            # Source: ttrss/include/digest.php line 38 — get_pref('DIGEST_CATCHUP', ...)
            do_catchup_val = get_user_pref(user.id, "DIGEST_CATCHUP") or ""
            do_catchup = do_catchup_val.lower() not in {"false", "0", ""}

            # Source: ttrss/include/digest.php line 45 — $tuple = prepare_headlines_digest(...)
            payload = prepare_headlines_digest(user.id, 1, limit)

            if payload is None or payload["article_count"] == 0:
                # Source: ttrss/include/digest.php lines 65-67 — "No headlines" path
                logger.debug(
                    "send_headlines_digests: no headlines for uid=%d", user.id
                )
            else:
                # Source: ttrss/include/digest.php lines 51-63 — send via ttrssMailer::quickMail
                rc = send_mail(
                    to_address=user.email,
                    to_name=user.login,
                    subject=payload["subject"],
                    body=payload["html"],
                    is_html=True,
                )
                if rc:
                    sent_count += 1
                    logger.debug(
                        "send_headlines_digests: sent to uid=%d RC=%s", user.id, rc
                    )
                    # Source: ttrss/include/digest.php lines 61-63 — catchup articles if DIGEST_CATCHUP
                    if do_catchup:
                        _catchup_digest_articles(
                            user.id, payload["affected_ids"], db
                        )
                else:
                    logger.error(
                        "send_headlines_digests: send_mail failed for uid=%d", user.id
                    )

            # Source: ttrss/include/digest.php lines 69-71 — UPDATE ttrss_users SET last_digest_sent = NOW()
            from sqlalchemy import update as sa_update
            db.session.execute(
                sa_update(TtRssUser)
                .where(TtRssUser.id == user.id)
                .values(last_digest_sent=datetime.now(tz=timezone.utc))
            )
            db.session.commit()

        logger.debug("send_headlines_digests: done, sent=%d", sent_count)
        return sent_count

    if app is not None:
        with app.app_context():
            return _run()
    else:
        # Caller is responsible for app context
        return _run()


def _catchup_digest_articles(user_id: int, article_ids: list[int], db) -> None:
    """
    Mark digest articles as read after a successful digest send.

    # Source: ttrss/include/digest.php lines 61-63 — catchupArticlesById($affected_ids, 0, ...)
    Adapted: PHP catchupArticlesById() call replaced by direct ORM UPDATE.
    New: extracted as a helper for testability (no direct PHP equivalent).
    """
    if not article_ids:
        return
    from ttrss.models.user_entry import TtRssUserEntry
    from sqlalchemy import update as sa_update

    db.session.execute(
        sa_update(TtRssUserEntry)
        .where(
            TtRssUserEntry.ref_id.in_(article_ids),
            TtRssUserEntry.owner_uid == user_id,
        )
        .values(unread=False)
    )
    db.session.commit()
