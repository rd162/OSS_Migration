"""Tests for plugin storage accessor (ttrss/plugins/storage.py).

Source: ttrss/classes/pluginhost.php:PluginHost::get_data/set_data/load_data
New: Python test suite.
"""
import pytest


@pytest.fixture()
def storage_user(app, db_session):
    """Create a user for plugin storage FK constraint."""
    from ttrss.auth.password import hash_password
    from ttrss.models.user import TtRssUser

    with app.app_context():
        user = TtRssUser(
            login="storage_test_user",
            pwd_hash=hash_password("password"),
            access_level=0,
        )
        db_session.add(user)
        db_session.commit()
        yield user
        db_session.delete(user)
        db_session.commit()


class TestPluginStorage:
    """get_data / set_data / clear_data / load_plugin_data round-trips."""

    def test_get_nonexistent_returns_empty_dict(self, app, storage_user):
        """get_data returns {} when no storage row exists."""
        from ttrss.plugins.storage import get_data
        from ttrss.extensions import db

        with app.app_context():
            data = get_data(db.session, owner_uid=storage_user.id, plugin_name="nonexistent_xyz")
        assert data == {}

    def test_set_and_get_roundtrip(self, app, storage_user):
        """set_data persists; get_data returns same payload."""
        from ttrss.plugins.storage import get_data, set_data
        from ttrss.extensions import db

        payload = {"key": "value", "num": 42}
        with app.app_context():
            set_data(db.session, owner_uid=storage_user.id, plugin_name="test_plugin_rt", data=payload)
            db.session.commit()
            result = get_data(db.session, owner_uid=storage_user.id, plugin_name="test_plugin_rt")
        assert result == payload

    def test_clear_data_removes_entry(self, app, storage_user):
        """clear_data removes the storage entry; subsequent get returns {}."""
        from ttrss.plugins.storage import clear_data, get_data, set_data
        from ttrss.extensions import db

        with app.app_context():
            set_data(db.session, owner_uid=storage_user.id, plugin_name="clr_plugin_rt", data={"x": 1})
            db.session.commit()
            clear_data(db.session, owner_uid=storage_user.id, plugin_name="clr_plugin_rt")
            db.session.commit()
            result = get_data(db.session, owner_uid=storage_user.id, plugin_name="clr_plugin_rt")
        assert result == {}

    def test_set_data_overwrites_existing(self, app, storage_user):
        """set_data on existing entry replaces data (upsert semantics)."""
        from ttrss.plugins.storage import get_data, set_data
        from ttrss.extensions import db

        with app.app_context():
            set_data(db.session, owner_uid=storage_user.id, plugin_name="upd_plugin_rt", data={"v": 1})
            db.session.commit()
            set_data(db.session, owner_uid=storage_user.id, plugin_name="upd_plugin_rt", data={"v": 2})
            db.session.commit()
            result = get_data(db.session, owner_uid=storage_user.id, plugin_name="upd_plugin_rt")
        assert result == {"v": 2}
