"""
Frontend test fixtures: DB seeding for UI automation tests.

Seeds test articles directly via psycopg2 so Playwright tests can verify
the full article-reading flow without requiring a running Celery worker.

Source: ttrss/include/rssfuncs.php (feed parser creates these DB rows)
New: no PHP equivalent — Python-native test fixture for browser automation.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import psycopg2
import pytest

DB_URL = "postgresql://ttrss_test:ttrss_test@localhost:5433/ttrss_test"
ADMIN_ID = 1
TEST_FEED_URL = "http://localhost:5001/static/test_feed.xml"
TEST_FEED_TITLE = "TT-RSS Automation Test Feed"


@pytest.fixture(scope="session")
def seeded_articles():
    """
    Seed a TtRssFeed + 3 TtRssEntry + 3 TtRssUserEntry rows directly into
    the running server's DB so UI automation tests can exercise the full
    article-reading flow without a Celery worker.

    Source: ttrss/include/rssfuncs.php — feed parser produces the same rows.
    New: direct psycopg2 seeding (no PHP equivalent for test isolation).
    """
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # ── Create test feed via ORM-consistent insert ────────────────────────
        # Use SELECT after upsert to handle idempotency — avoids enumerating
        # every NOT NULL column (27 total, most without server defaults).
        # Source: ttrss/include/functions.php:add_feed
        cur.execute("""
            SELECT id FROM ttrss_feeds
            WHERE owner_uid = %s AND feed_url = %s
        """, (ADMIN_ID, TEST_FEED_URL))
        existing = cur.fetchone()

        if existing:
            feed_id = existing[0]
        else:
            # Insert with ALL NOT NULL columns explicitly specified
            cur.execute("""
                INSERT INTO ttrss_feeds
                    (owner_uid, title, feed_url,
                     icon_url, site_url, auth_login, auth_pass, last_error,
                     update_interval, purge_interval, update_method,
                     order_id, pubsub_state,
                     private, hidden, include_in_digest, rtl_content,
                     cache_images, hide_images, cache_content,
                     always_display_enclosures,
                     mark_unread_on_update, update_on_checksum_change,
                     strip_images, view_settings, auth_pass_encrypted)
                VALUES (%s, %s, %s,
                        '', '', '', '', '',
                        0, 0, 0,
                        0, 0,
                        false, false, true, false,
                        false, false, false,
                        false,
                        false, false,
                        false, '', false)
                RETURNING id
            """, (ADMIN_ID, TEST_FEED_TITLE, TEST_FEED_URL))
            feed_id = cur.fetchone()[0]
        row = cur.fetchone()

        if row:
            feed_id = row[0]
        else:
            cur.execute("SELECT id FROM ttrss_feeds WHERE feed_url = %s", (TEST_FEED_URL,))
            feed_id = cur.fetchone()[0]

        # ── Seed 3 articles (idempotent by guid) ──────────────────────────────
        # Source: ttrss/include/rssfuncs.php — process_feed_urls() inserts entries
        now = datetime.now(timezone.utc)
        articles = [
            {
                "guid":    "test-e2e-automation-article-1",
                "title":   "Python RSS Migration: Architecture Overview",
                "link":    "https://example.com/articles/python-rss-migration",
                "content": "<p>This article covers the architecture of migrating a PHP RSS aggregator to Python Flask. The migration involved 31 database models, a REST API with 17 operations, and a Celery background task system.</p>",
                "author":  "Tech Team",
            },
            {
                "guid":    "test-e2e-automation-article-2",
                "title":   "Flask Backend: REST API Design Patterns",
                "link":    "https://example.com/articles/flask-api-design",
                "content": "<p>Designing a clean REST API in Flask requires careful attention to response envelopes, error handling, and authentication guards.</p>",
                "author":  "Backend Team",
            },
            {
                "guid":    "test-e2e-automation-article-3",
                "title":   "Playwright UI Automation: End-to-End Testing Strategy",
                "link":    "https://example.com/articles/playwright-e2e-testing",
                "content": "<p>Playwright has become the leading tool for browser automation in 2025. Key advantages over Selenium include parallel execution and auto-waiting.</p>",
                "author":  "QA Team",
            },
        ]

        entry_ids = []
        for art in articles:
            # Source: ttrss/include/rssfuncs.php — INSERT INTO ttrss_entries
            # All NOT NULL columns: title, guid, link, updated, content, content_hash,
            # no_orig_date, date_entered, date_updated, num_comments, comments, author
            cur.execute("""
                INSERT INTO ttrss_entries
                    (title, guid, link, updated, content, content_hash,
                     no_orig_date, date_entered, date_updated,
                     num_comments, comments, author)
                VALUES (%s, %s, %s, %s, %s, %s,
                        false, %s, %s,
                        0, '', %s)
                ON CONFLICT (guid) DO NOTHING
                RETURNING id
            """, (
                art["title"], art["guid"], art["link"],
                now, art["content"], f"hash-{art['guid']}",
                now, now, art["author"],
            ))
            row = cur.fetchone()
            if row:
                entry_ids.append(row[0])
            else:
                cur.execute("SELECT id FROM ttrss_entries WHERE guid = %s", (art["guid"],))
                entry_ids.append(cur.fetchone()[0])

        # Source: ttrss/include/rssfuncs.php — INSERT INTO ttrss_user_entries
        # All NOT NULL columns: ref_id, uuid, owner_uid, marked, published,
        # tag_cache, label_cache, score, unread
        for eid in entry_ids:
            # Skip if user_entry already exists for this article+owner
            cur.execute(
                "SELECT 1 FROM ttrss_user_entries WHERE ref_id=%s AND owner_uid=%s",
                (eid, ADMIN_ID)
            )
            if cur.fetchone():
                continue
            cur.execute("""
                INSERT INTO ttrss_user_entries
                    (ref_id, uuid, feed_id, owner_uid,
                     marked, published, tag_cache, label_cache, score, unread)
                VALUES (%s, %s, %s, %s,
                        false, false, '', '', 0, true)
            """, (eid, str(uuid.uuid4()), feed_id, ADMIN_ID))

        conn.commit()

        yield {
            "feed_id":   feed_id,
            "feed_title": TEST_FEED_TITLE,
            "entry_ids": entry_ids,
            "admin_id":  ADMIN_ID,
        }

    finally:
        # ── Cleanup: remove seeded data ───────────────────────────────────────
        conn2 = psycopg2.connect(DB_URL)
        conn2.autocommit = True
        cur2 = conn2.cursor()
        try:
            # Cascade deletes handle user_entries when feed is deleted
            cur2.execute(
                "DELETE FROM ttrss_feeds WHERE feed_url = %s AND owner_uid = %s",
                (TEST_FEED_URL, ADMIN_ID)
            )
            for g in ["test-e2e-automation-article-1",
                       "test-e2e-automation-article-2",
                       "test-e2e-automation-article-3"]:
                cur2.execute("DELETE FROM ttrss_entries WHERE guid = %s", (g,))
        except Exception:
            pass
        finally:
            conn2.close()

        cur.close()
        conn.close()
