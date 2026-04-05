"""
Integration tests for SQLAlchemy models — CRUD, FK constraints, cascade deletes.

Source: ttrss/schema/ttrss_schema_pgsql.sql (all table definitions)
        ttrss/include/functions.php (model creation patterns)
Requires: docker compose -f docker-compose.test.yml up -d
AR07: No SQLite — FK enforcement and cascade semantics must match Postgres.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from ttrss.auth.password import hash_password
from ttrss.models.category import TtRssFeedCategory
from ttrss.models.entry import TtRssEntry
from ttrss.models.feed import TtRssFeed
from ttrss.models.label import TtRssLabel2
from ttrss.models.plugin_storage import TtRssPluginStorage
from ttrss.models.user import TtRssUser
from ttrss.models.user_entry import TtRssUserEntry


# ---------------------------------------------------------------------------
# User model
# ---------------------------------------------------------------------------


class TestUserModel:
    """Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_users, lines 40-53)."""

    def test_create_user(self, app, db_session):
        """Insert TtRssUser, read back, verify fields.

        Source: ttrss_schema_pgsql.sql lines 40-53 — all columns present.
        """
        login = f"model_user_{uuid.uuid4().hex[:8]}"
        with app.app_context():
            user = TtRssUser(
                login=login,
                pwd_hash=hash_password("pass"),
                access_level=0,
                email="test@example.com",
                full_name="Test User",
            )
            db_session.add(user)
            db_session.commit()

            read_back = db_session.get(TtRssUser, user.id)
            assert read_back is not None
            assert read_back.login == login
            assert read_back.access_level == 0
            assert read_back.email == "test@example.com"

            db_session.delete(read_back)
            db_session.commit()

    def test_user_login_unique_constraint(self, app, db_session):
        """Inserting two users with same login → UniqueViolation.

        Source: ttrss_schema_pgsql.sql line 41 — login varchar(120) not null unique.
        """
        from sqlalchemy.exc import IntegrityError

        login = f"dupuser_{uuid.uuid4().hex[:8]}"
        with app.app_context():
            u1 = TtRssUser(login=login, pwd_hash=hash_password("x"), access_level=0)
            u2 = TtRssUser(login=login, pwd_hash=hash_password("y"), access_level=0)
            db_session.add(u1)
            db_session.commit()

            db_session.add(u2)
            with pytest.raises(IntegrityError):
                db_session.commit()
            db_session.rollback()

            db_session.delete(db_session.get(TtRssUser, u1.id))
            db_session.commit()

    def test_delete_user_cascades_to_feed(self, app, db_session):
        """Deleting a user cascades to their feeds (ON DELETE CASCADE).

        Source: ttrss_schema_pgsql.sql line 67 — owner_uid → ttrss_users(id) ON DELETE CASCADE.
        """
        with app.app_context():
            user = TtRssUser(login=f"cuser_{uuid.uuid4().hex[:8]}", pwd_hash=hash_password("p"), access_level=0)
            db_session.add(user)
            db_session.flush()

            feed = TtRssFeed(owner_uid=user.id, title="Cascade Feed", feed_url="https://cascade.test/feed")
            db_session.add(feed)
            db_session.commit()

            feed_id = feed.id
            db_session.delete(user)
            db_session.commit()

            assert db_session.get(TtRssFeed, feed_id) is None


# ---------------------------------------------------------------------------
# Feed model
# ---------------------------------------------------------------------------


class TestFeedModel:
    """Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_feeds, lines 66-99)."""

    def test_create_feed(self, app, db_session, api_user):
        """Insert TtRssFeed, read back, verify fields.

        Source: ttrss_schema_pgsql.sql lines 66-99 — all columns present.
        """
        with app.app_context():
            feed = TtRssFeed(
                owner_uid=api_user.id,
                title="Test Feed",
                feed_url="https://model-test.example.com/feed.xml",
            )
            db_session.add(feed)
            db_session.commit()

            read_back = db_session.get(TtRssFeed, feed.id)
            assert read_back is not None
            assert read_back.title == "Test Feed"
            assert read_back.feed_url == "https://model-test.example.com/feed.xml"
            assert read_back.owner_uid == api_user.id

            db_session.delete(read_back)
            db_session.commit()

    def test_feed_with_category(self, app, db_session, api_user):
        """TtRssFeed with cat_id FK → category row required.

        Source: ttrss_schema_pgsql.sql line 69 — cat_id → ttrss_feed_categories(id).
        """
        with app.app_context():
            cat = TtRssFeedCategory(owner_uid=api_user.id, title="Test Cat")
            db_session.add(cat)
            db_session.flush()

            feed = TtRssFeed(
                owner_uid=api_user.id,
                title="Categorized Feed",
                feed_url="https://cat-feed.example.com/feed",
                cat_id=cat.id,
            )
            db_session.add(feed)
            db_session.commit()

            assert feed.cat_id == cat.id

            db_session.delete(feed)
            db_session.delete(cat)
            db_session.commit()

    def test_delete_feed_cascades_to_user_entry(self, app, db_session, api_user):
        """Deleting a feed cascades to ttrss_user_entries (ON DELETE CASCADE).

        Source: ttrss_schema_pgsql.sql line 160 — feed_id → ttrss_feeds(id) ON DELETE CASCADE.
        """
        now = datetime.now(timezone.utc)
        with app.app_context():
            feed = TtRssFeed(owner_uid=api_user.id, title="Del Feed", feed_url="https://delfeed.test/")
            db_session.add(feed)
            db_session.flush()

            entry = TtRssEntry(
                title="E", guid=f"guid-{uuid.uuid4().hex}", link="https://e.com",
                updated=now, content="c", content_hash="h", date_entered=now, date_updated=now,
            )
            db_session.add(entry)
            db_session.flush()

            ue = TtRssUserEntry(
                ref_id=entry.id, uuid=str(uuid.uuid4()), feed_id=feed.id,
                owner_uid=api_user.id, tag_cache="", label_cache="",
            )
            db_session.add(ue)
            db_session.commit()

            ue_id = ue.int_id
            db_session.delete(feed)
            db_session.commit()

            assert db_session.get(TtRssUserEntry, ue_id) is None

            # Cleanup entry (not cascade-deleted with feed)
            db_session.delete(db_session.get(TtRssEntry, entry.id))
            db_session.commit()


# ---------------------------------------------------------------------------
# Entry model
# ---------------------------------------------------------------------------


class TestEntryModel:
    """Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_entries, lines 134-149)."""

    def test_create_entry(self, app, db_session):
        """Insert TtRssEntry, read back, verify all required fields.

        Source: ttrss_schema_pgsql.sql lines 134-149.
        """
        now = datetime.now(timezone.utc)
        guid = f"guid-{uuid.uuid4().hex}"
        with app.app_context():
            entry = TtRssEntry(
                title="Test Article",
                guid=guid,
                link="https://example.com/article",
                updated=now,
                content="<p>Content</p>",
                content_hash="abc123",
                date_entered=now,
                date_updated=now,
                author="Test Author",
            )
            db_session.add(entry)
            db_session.commit()

            read_back = db_session.get(TtRssEntry, entry.id)
            assert read_back.title == "Test Article"
            assert read_back.guid == guid
            assert read_back.author == "Test Author"

            db_session.delete(read_back)
            db_session.commit()

    def test_entry_guid_unique_constraint(self, app, db_session):
        """Duplicate GUID → IntegrityError (UNIQUE constraint).

        Source: ttrss_schema_pgsql.sql line 136 — guid text not null unique.
        Critical: GUID uniqueness is the feed deduplication mechanism (rssfuncs.php).
        """
        from sqlalchemy.exc import IntegrityError

        now = datetime.now(timezone.utc)
        shared_guid = f"dupguid-{uuid.uuid4().hex}"
        with app.app_context():
            e1 = TtRssEntry(
                title="E1", guid=shared_guid, link="https://a.com",
                updated=now, content="c", content_hash="h1", date_entered=now, date_updated=now,
            )
            db_session.add(e1)
            db_session.commit()

            e2 = TtRssEntry(
                title="E2", guid=shared_guid, link="https://b.com",
                updated=now, content="c", content_hash="h2", date_entered=now, date_updated=now,
            )
            db_session.add(e2)
            with pytest.raises(IntegrityError):
                db_session.commit()
            db_session.rollback()

            db_session.delete(db_session.get(TtRssEntry, e1.id))
            db_session.commit()


# ---------------------------------------------------------------------------
# UserEntry model
# ---------------------------------------------------------------------------


class TestUserEntryModel:
    """Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_user_entries, lines 156-172)."""

    def test_user_entry_state_transitions(self, app, db_session, api_user, test_feed):
        """UserEntry state fields can be toggled: unread, marked, published, note.

        Source: ttrss/classes/rpc.php:RPC::mark (article marking logic).
        """
        now = datetime.now(timezone.utc)
        with app.app_context():
            entry = TtRssEntry(
                title="State Test", guid=f"state-{uuid.uuid4().hex}", link="https://state.test",
                updated=now, content="c", content_hash="h", date_entered=now, date_updated=now,
            )
            db_session.add(entry)
            db_session.flush()

            ue = TtRssUserEntry(
                ref_id=entry.id, uuid=str(uuid.uuid4()),
                feed_id=test_feed.id, owner_uid=api_user.id,
                tag_cache="", label_cache="", unread=True,
            )
            db_session.add(ue)
            db_session.commit()

            # Mark as read
            ue.unread = False
            db_session.commit()
            db_session.expire_all()
            assert db_session.get(TtRssUserEntry, ue.int_id).unread is False

            # Star
            ue.marked = True
            db_session.commit()
            db_session.expire_all()
            assert db_session.get(TtRssUserEntry, ue.int_id).marked is True

            # Add note
            ue.note = "My annotation"
            db_session.commit()
            db_session.expire_all()
            assert db_session.get(TtRssUserEntry, ue.int_id).note == "My annotation"

            # Cleanup
            db_session.delete(db_session.get(TtRssUserEntry, ue.int_id))
            db_session.commit()
            db_session.delete(db_session.get(TtRssEntry, entry.id))
            db_session.commit()


# ---------------------------------------------------------------------------
# Category model
# ---------------------------------------------------------------------------


class TestCategoryModel:
    """Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_feed_categories, lines 58-64)."""

    def test_category_self_referential_fk(self, app, db_session, api_user):
        """TtRssFeedCategory supports parent_cat self-referential FK.

        Source: ttrss_schema_pgsql.sql line 63 — parent_cat → ttrss_feed_categories(id).
        """
        with app.app_context():
            parent = TtRssFeedCategory(owner_uid=api_user.id, title="Parent")
            db_session.add(parent)
            db_session.flush()

            child = TtRssFeedCategory(owner_uid=api_user.id, title="Child", parent_cat=parent.id)
            db_session.add(child)
            db_session.commit()

            assert child.parent_cat == parent.id

            db_session.delete(child)
            db_session.delete(parent)
            db_session.commit()

    def test_delete_parent_category_sets_child_parent_null(self, app, db_session, api_user):
        """Deleting parent category → child.parent_cat SET NULL (ON DELETE SET NULL).

        Source: ttrss_schema_pgsql.sql line 63 — ON DELETE SET NULL.
        """
        with app.app_context():
            parent = TtRssFeedCategory(owner_uid=api_user.id, title="ParentDel")
            db_session.add(parent)
            db_session.flush()

            child = TtRssFeedCategory(owner_uid=api_user.id, title="ChildDel", parent_cat=parent.id)
            db_session.add(child)
            db_session.commit()

            child_id = child.id
            db_session.delete(parent)
            db_session.commit()

            db_session.expire_all()
            child_row = db_session.get(TtRssFeedCategory, child_id)
            assert child_row is not None
            assert child_row.parent_cat is None

            db_session.delete(child_row)
            db_session.commit()


# ---------------------------------------------------------------------------
# Label model
# ---------------------------------------------------------------------------


class TestLabelModel:
    """Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_labels2)."""

    def test_create_label(self, app, db_session, api_user):
        """Insert TtRssLabel2, read back.

        Source: ttrss_schema_pgsql.sql — ttrss_labels2 table.
        """
        with app.app_context():
            label = TtRssLabel2(
                owner_uid=api_user.id,
                caption="Test Label",
                fg_color="#ffffff",
                bg_color="#000000",
            )
            db_session.add(label)
            db_session.commit()

            read_back = db_session.get(TtRssLabel2, label.id)
            assert read_back.caption == "Test Label"
            assert read_back.fg_color == "#ffffff"

            db_session.delete(read_back)
            db_session.commit()


# ---------------------------------------------------------------------------
# Plugin storage model
# ---------------------------------------------------------------------------


class TestPluginStorageModel:
    """Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_plugin_storage)."""

    def test_create_plugin_storage(self, app, db_session, api_user):
        """Insert TtRssPluginStorage, read back JSON content.

        Source: ttrss/classes/pluginhost.php:PluginHost::set (lines 217-235)
        Adapted: PHP serialize() → Python json.dumps() for content storage.
        """
        import json
        with app.app_context():
            ps = TtRssPluginStorage(
                owner_uid=api_user.id,
                name="test_plugin",
                content=json.dumps({"key": "value"}),
            )
            db_session.add(ps)
            db_session.commit()

            read_back = db_session.query(TtRssPluginStorage).filter_by(
                owner_uid=api_user.id, name="test_plugin"
            ).first()
            assert read_back is not None
            assert json.loads(read_back.content) == {"key": "value"}

            db_session.delete(read_back)
            db_session.commit()

    def test_plugin_storage_cascade_on_user_delete(self, app, db_session):
        """Deleting user cascades to plugin_storage rows.

        Source: ttrss_schema_pgsql.sql — ttrss_plugin_storage.owner_uid ON DELETE CASCADE.
        """
        import json
        with app.app_context():
            user = TtRssUser(login=f"psuser_{uuid.uuid4().hex[:8]}", pwd_hash=hash_password("x"), access_level=0)
            db_session.add(user)
            db_session.flush()

            ps = TtRssPluginStorage(owner_uid=user.id, name="p", content=json.dumps({}))
            db_session.add(ps)
            db_session.commit()

            db_session.delete(user)
            db_session.commit()

            remaining = db_session.query(TtRssPluginStorage).filter_by(owner_uid=user.id).first()
            assert remaining is None
