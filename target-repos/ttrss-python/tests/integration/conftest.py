"""
Shared fixtures for integration tests (requires real Postgres + Redis).

Setup:
  docker compose -f docker-compose.test.yml up -d
  pytest tests/integration/

AR07: No SQLite. All ORM tests use real Postgres via docker-compose.test.yml.

Key fixtures:
  seed_prefs       — session-scoped, seeds minimal pref data (ENABLE_API_ACCESS)
  api_user         — function-scoped, creates TtRssUser with API access enabled
  logged_in_client — function-scoped, POST /api/ login → authenticated Flask test client
  test_feed        — function-scoped, TtRssFeed owned by api_user
  test_entry_pair  — function-scoped, TtRssEntry + TtRssUserEntry linked to test_feed
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from ttrss.auth.password import hash_password
from ttrss.extensions import db as _db
from ttrss.models.entry import TtRssEntry
from ttrss.models.feed import TtRssFeed
from ttrss.models.pref import TtRssPref, TtRssPrefsSection, TtRssPrefsType
from ttrss.models.user import TtRssUser
from ttrss.models.user_entry import TtRssUserEntry


# ---------------------------------------------------------------------------
# Pref seed (session-scoped — runs once; DB is dropped after the whole session)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def seed_prefs(app):
    """
    Seed the minimal pref reference data required for ENABLE_API_ACCESS checks.

    Source: ttrss/schema/ttrss_schema_pgsql.sql (ttrss_prefs_types lines 283-285,
            ttrss_prefs_sections lines 291-294, ttrss_prefs lines 302-352)
    Adapted: Alembic seeder inserts all ~51 prefs at migration time; integration
             tests bypass Alembic (create_all only), so we seed the minimum here.

    Rows inserted:
      ttrss_prefs_types:    id=1 (bool), id=2 (string), id=3 (integer)
      ttrss_prefs_sections: id=1 (General)
      ttrss_prefs:          ENABLE_API_ACCESS bool true (required by API dispatch guard)
    """
    with app.app_context():
        session = _db.session

        # Types (id=1 bool, id=2 string, id=3 integer)
        # Source: ttrss_schema_pgsql.sql lines 283-285
        for tid, tname in [(1, "bool"), (2, "string"), (3, "integer")]:
            if not session.get(TtRssPrefsType, tid):
                session.add(TtRssPrefsType(id=tid, type_name=tname))

        # Sections (only id=1 General is needed for minimal API access pref)
        # Source: ttrss_schema_pgsql.sql lines 291-294
        if not session.get(TtRssPrefsSection, 1):
            session.add(TtRssPrefsSection(id=1, order_id=0, section_name="General"))

        # ENABLE_API_ACCESS pref with def_value='true'
        # Source: ttrss_schema_pgsql.sql line ~313
        if not session.get(TtRssPref, "ENABLE_API_ACCESS"):
            session.add(
                TtRssPref(
                    pref_name="ENABLE_API_ACCESS",
                    type_id=1,
                    section_id=1,
                    access_level=0,
                    def_value="true",
                )
            )

        session.commit()


# ---------------------------------------------------------------------------
# Test user with API access
# ---------------------------------------------------------------------------


@pytest.fixture()
def api_user(app, db_session, seed_prefs):
    """
    Create a TtRssUser with a known password.

    API access is enabled via the system default: seed_prefs sets
    TtRssPref(ENABLE_API_ACCESS, def_value='true'), so get_user_pref() returns
    'true' for all users without a user-level override.

    Source: ttrss/classes/pref/users.php:Pref_Users::save (user creation)
            ttrss/include/db-prefs.php:get_pref — system default fallback.
    """
    login = f"int_user_{uuid.uuid4().hex[:8]}"
    with app.app_context():
        user = TtRssUser(
            login=login,
            pwd_hash=hash_password("integration_pass"),
            access_level=0,
        )
        db_session.add(user)
        db_session.commit()
        yield user

        # Teardown: cascade delete via user (feeds, entries, prefs all cascade)
        try:
            existing = db_session.get(TtRssUser, user.id)
            if existing:
                db_session.delete(existing)
                db_session.commit()
        except Exception:
            db_session.rollback()


# ---------------------------------------------------------------------------
# Authenticated client
# ---------------------------------------------------------------------------


@pytest.fixture()
def logged_in_client(client, api_user):
    """
    Flask test client with an active session after POST /api/ op=login.

    Source: ttrss/classes/api.php:API.login (lines 49-88)
    Adapted: Flask test_client() maintains cookies between requests (session cookie).
    """
    resp = client.post(
        "/api/",
        json={
            "op": "login",
            "user": api_user.login,
            "password": "integration_pass",
            "seq": 0,
        },
    )
    data = resp.get_json()
    assert data["status"] == 0, f"Login failed: {data}"
    return client


# ---------------------------------------------------------------------------
# Feed fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_feed(app, db_session, api_user):
    """
    Create a TtRssFeed owned by api_user.

    Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_feeds, lines 66-99)
            ttrss/include/functions.php:add_feed (lines 1673-1738)
    """
    with app.app_context():
        feed = TtRssFeed(
            owner_uid=api_user.id,
            title="Integration Test Feed",
            feed_url="https://example.com/feed.xml",
        )
        db_session.add(feed)
        db_session.commit()
        yield feed
        # User cascade delete in api_user teardown covers this; explicit cleanup here
        # in case api_user teardown is not yet called.
        try:
            existing = db_session.get(TtRssFeed, feed.id)
            if existing:
                db_session.delete(existing)
                db_session.commit()
        except Exception:
            db_session.rollback()


# ---------------------------------------------------------------------------
# Entry + UserEntry fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_entry_pair(app, db_session, api_user, test_feed):
    """
    Create a TtRssEntry (shared content) + TtRssUserEntry (per-user state).

    Source: ttrss/schema/ttrss_schema_pgsql.sql (ttrss_entries lines 134-149,
            ttrss_user_entries lines 156-172)
            ttrss/include/rssfuncs.php (feed parser creates these pairs)
    Adapted: Python creates both rows directly for test isolation.
    """
    now = datetime.now(timezone.utc)
    with app.app_context():
        entry = TtRssEntry(
            title="Integration Test Article",
            guid=f"test-guid-{uuid.uuid4().hex}",
            link="https://example.com/article/1",
            updated=now,
            content="<p>Test content for integration test.</p>",
            content_hash="testhash123",
            date_entered=now,
            date_updated=now,
        )
        db_session.add(entry)
        db_session.flush()  # get entry.id

        user_entry = TtRssUserEntry(
            ref_id=entry.id,
            uuid=str(uuid.uuid4()),
            feed_id=test_feed.id,
            owner_uid=api_user.id,
            tag_cache="",
            label_cache="",
            unread=True,
        )
        db_session.add(user_entry)
        db_session.commit()
        yield entry, user_entry

        # Teardown: delete user_entry first (FK), then entry
        try:
            ue = db_session.get(TtRssUserEntry, user_entry.int_id)
            if ue:
                db_session.delete(ue)
                db_session.commit()
            e = db_session.get(TtRssEntry, entry.id)
            if e:
                db_session.delete(e)
                db_session.commit()
        except Exception:
            db_session.rollback()
