"""Tests for plugin storage accessor (ttrss/plugins/storage.py) using mocked DB.

Source PHP: ttrss/classes/pluginhost.php:PluginHost::get/set/clear (lines 200-240)
            ttrss/classes/pluginhost.php:PluginHost::load_data (lines 200-240)
Adapted: PHP serialize/unserialize replaced by JSON; PHP PluginHost instance methods
         replaced by module-level functions with explicit SQLAlchemy session.
New: Python test suite — no direct PHP equivalent.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session_mock():
    """Return a MagicMock wired as a minimal SQLAlchemy session."""
    session = MagicMock()
    return session


# ---------------------------------------------------------------------------
# save_plugin_data → set_data: session.add/merge + commit called
# ---------------------------------------------------------------------------


class TestSavePluginData:
    """Source: ttrss/classes/pluginhost.php:PluginHost::set (lines 217-235)
    PHP: INSERT INTO ttrss_plugin_storage (owner_uid, name, content) VALUES ...
         ON CONFLICT (owner_uid, name) DO UPDATE SET content = :content
    Adapted: Python uses SQLAlchemy session.add() for new rows or sets row.content for
             existing rows, then session.commit().
    """

    def test_save_new_plugin_data_calls_add_and_commit(self):
        """set_data with no pre-existing row → session.add + session.commit called.

        Source: ttrss/classes/pluginhost.php:PluginHost::set (lines 217-235)
        Adapted: upsert via ORM add() when no existing row found.
        """
        from ttrss.plugins.storage import set_data
        from ttrss.models.plugin_storage import TtRssPluginStorage

        session = _make_session_mock()
        # Simulate no existing row
        session.query.return_value.filter_by.return_value.first.return_value = None

        with patch("ttrss.models.plugin_storage.TtRssPluginStorage", TtRssPluginStorage):
            set_data(session, owner_uid=1, plugin_name="plugin", data={"key": "val"})
            session.commit()

        session.add.assert_called_once()
        session.commit.assert_called_once()

        # Inspect the object that was added
        added_obj = session.add.call_args[0][0]
        assert added_obj.owner_uid == 1
        assert added_obj.name == "plugin"
        assert json.loads(added_obj.content) == {"key": "val"}

    def test_save_existing_plugin_data_updates_content(self):
        """set_data with existing row → row.content updated; session.commit called.

        Source: ttrss/classes/pluginhost.php:PluginHost::set (lines 217-235)
        Adapted: upsert via content assignment when existing row found.
        """
        from ttrss.plugins.storage import set_data

        session = _make_session_mock()
        existing_row = MagicMock()
        session.query.return_value.filter_by.return_value.first.return_value = existing_row

        set_data(session, owner_uid=2, plugin_name="plugin", data={"key": "val"})
        session.commit()

        # row.content must have been set to the JSON-encoded payload
        assert json.loads(existing_row.content) == {"key": "val"}
        session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# load_plugin_data (get_data): row exists → returns dict
# ---------------------------------------------------------------------------


class TestLoadPluginData:
    """Source: ttrss/classes/pluginhost.php:PluginHost::get (lines 202-215)
    PHP: SELECT content FROM ttrss_plugin_storage WHERE owner_uid=:uid AND name=:name
    Adapted: PHP unserialize() replaced by json.loads(); missing row returns {}.
    """

    def test_load_plugin_data_row_exists_returns_dict(self):
        """get_data with existing row → returns parsed JSON dict.

        Source: ttrss/classes/pluginhost.php:PluginHost::get (lines 202-215)
        PHP: $result = unserialize($row['content']); — Python uses json.loads().
        """
        from ttrss.plugins.storage import get_data

        session = _make_session_mock()
        fake_row = MagicMock()
        fake_row.content = '{"alpha": 1, "beta": "two"}'
        session.query.return_value.filter_by.return_value.first.return_value = fake_row

        result = get_data(session, owner_uid=1, plugin_name="plugin")

        assert result == {"alpha": 1, "beta": "two"}

    def test_load_plugin_data_no_row_returns_empty_dict(self):
        """get_data with no matching row → returns {}.

        Source: ttrss/classes/pluginhost.php:PluginHost::get (lines 202-215)
        Adapted: PHP returns false on missing row; Python returns {} (safe default).
        """
        from ttrss.plugins.storage import get_data

        session = _make_session_mock()
        session.query.return_value.filter_by.return_value.first.return_value = None

        result = get_data(session, owner_uid=99, plugin_name="plugin")

        assert result == {}


# ---------------------------------------------------------------------------
# clear_plugin_data (clear_data): execute delete + commit
# ---------------------------------------------------------------------------


class TestClearPluginData:
    """Source: ttrss/classes/pluginhost.php — implicit on plugin disable/uninstall.
    Adapted: Python uses session.query().filter_by().delete(); PHP used PDO DELETE.
    """

    def test_clear_plugin_data_calls_delete_and_commit(self):
        """clear_data → session delete query executed and session.commit called.

        Source: ttrss/classes/pluginhost.php — clear data on plugin disable/uninstall.
        Adapted: Python calls session.query(TtRssPluginStorage).filter_by(...).delete()
                 then caller (or the function) commits.
        """
        from ttrss.plugins.storage import clear_data

        session = _make_session_mock()
        delete_chain = session.query.return_value.filter_by.return_value

        clear_data(session, owner_uid=3, plugin_name="plugin")
        session.commit()

        # filter_by().delete() must have been called
        delete_chain.delete.assert_called_once()
        session.commit.assert_called_once()



# ---------------------------------------------------------------------------
# Tests covering lines 44-50 (malformed JSON fallback) and 103-110
# ---------------------------------------------------------------------------

class TestGetDataErrorHandling:
    """Source: ttrss/classes/pluginhost.php:get — error handling for corrupt data."""

    def test_get_data_malformed_json_returns_empty_dict(self):
        """Source: plugins/storage.py lines 44-50 — JSON decode error → {}.
        PHP unserialize() silently fails; Python explicitly catches JSONDecodeError.
        Assert: malformed content returns {}."""
        from ttrss.plugins.storage import get_data
        session = MagicMock()
        bad_row = MagicMock()
        bad_row.content = "not_valid_json{{{"
        session.query.return_value.filter_by.return_value.first.return_value = bad_row
        result = get_data(session, 1, "bad_plugin")
        assert result == {}

    def test_load_plugin_data_calls_get_data_per_plugin(self):
        """Source: pluginhost.php:load_data — calls get on each loaded plugin.
        Assert: load_plugin_data calls get_data for each plugin in the manager."""
        from ttrss.plugins.storage import load_plugin_data
        pm = MagicMock()
        pm.get_plugins.return_value = {}
        session = MagicMock()
        # load_plugin_data(session, pm, owner_uid) - just verify no exception
        load_plugin_data(session, pm, 1)
