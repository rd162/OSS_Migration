"""HTTP-handler tests for ttrss/blueprints/prefs/labels.py.

Source: ttrss/classes/pref/labels.php (Pref_Labels handler, 331 lines)
New: Python test suite — no PHP equivalent.

Each test drives the Blueprint via app.test_request_context() with the
login_required decorator bypassed through _unwrap(), following the project's
established unit-test pattern (see tests/unit/test_prefs_blueprint.py).

All CRUD collaborators are mocked; no Postgres connection is required.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unwrap(fn):
    """Return the innermost wrapped function (bypasses login_required etc.)."""
    while hasattr(fn, "__wrapped__"):
        fn = fn.__wrapped__
    return fn


def _mock_user(user_id: int = 1, access_level: int = 10) -> MagicMock:
    m = MagicMock()
    m.id = user_id
    m.access_level = access_level
    return m


def _make_label(label_id: int = 1, caption: str = "News") -> MagicMock:
    lbl = MagicMock()
    lbl.id = label_id
    lbl.caption = caption
    lbl.fg_color = "#ffffff"
    lbl.bg_color = "#cc0000"
    return lbl


# ---------------------------------------------------------------------------
# GET /prefs/labels — label list
# ---------------------------------------------------------------------------


class TestLabelsList:
    """GET /prefs/labels — return label list and HOOK_PREFS_TAB content."""

    def test_get_labels_returns_200(self, app):
        """GET /prefs/labels returns 200 with labels list and plugin_tab_content.

        Source: ttrss/classes/pref/labels.php:93 — getlabeltree
        Source: ttrss/classes/pref/labels.php:322 — run_hooks(HOOK_PREFS_TAB)
        """
        mock_pm = MagicMock()
        mock_pm.hook.hook_prefs_tab.return_value = []
        mock_user = _mock_user()

        lbl = _make_label(1, "Sports")

        with app.test_request_context():
            with patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm), \
                 patch("ttrss.blueprints.prefs.labels.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.labels.labels_crud") as mock_crud:
                mock_crud.fetch_labels.return_value = [lbl]
                from ttrss.blueprints.prefs import labels
                resp = _unwrap(labels.labels)()

        assert resp.status_code == 200
        data = resp.get_json()
        assert "labels" in data
        assert len(data["labels"]) == 1
        assert data["labels"][0]["caption"] == "Sports"
        assert "plugin_tab_content" in data


# ---------------------------------------------------------------------------
# POST /prefs/labels — create label
# ---------------------------------------------------------------------------


class TestAddLabel:
    """POST /prefs/labels — create a new label."""

    def test_create_label_returns_201(self, app):
        """POST /prefs/labels creates label and returns 200 (status ok).

        Source: ttrss/classes/pref/labels.php:224 — add / label_create
        """
        mock_user = _mock_user()

        with app.test_request_context(method="POST", data={"caption": "Tech"}):
            with patch("ttrss.blueprints.prefs.labels.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.labels.labels_crud") as mock_crud:
                mock_crud.create_label.return_value = True
                from ttrss.blueprints.prefs import labels
                resp = _unwrap(labels.add_label)()

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"

    def test_create_duplicate_label_returns_409(self, app):
        """POST /prefs/labels returns 409 when label caption already exists.

        Source: ttrss/classes/pref/labels.php:224 — label_create returns false on duplicate
        """
        mock_user = _mock_user()

        with app.test_request_context(method="POST", data={"caption": "Tech"}):
            with patch("ttrss.blueprints.prefs.labels.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.labels.labels_crud") as mock_crud:
                mock_crud.create_label.return_value = False  # already exists
                from ttrss.blueprints.prefs import labels
                result = _unwrap(labels.add_label)()
            resp = app.make_response(result)

        assert resp.status_code == 409
        assert resp.get_json()["error"] == "label_already_exists"

    def test_create_label_empty_caption_returns_400(self, app):
        """POST /prefs/labels returns 400 when caption is empty.

        Source: ttrss/classes/pref/labels.php:224 — add validates caption non-empty
        """
        mock_user = _mock_user()

        with app.test_request_context(method="POST", data={"caption": "   "}):
            with patch("ttrss.blueprints.prefs.labels.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.labels.labels_crud") as mock_crud:
                from ttrss.blueprints.prefs import labels
                result = _unwrap(labels.add_label)()
            resp = app.make_response(result)

        assert resp.status_code == 400
        assert resp.get_json()["error"] == "caption_required"


# ---------------------------------------------------------------------------
# POST /prefs/labels/<id> — rename / update colors
# ---------------------------------------------------------------------------


class TestSaveLabel:
    """POST /prefs/labels/<id> — rename a label."""

    def test_rename_label_returns_200(self, app):
        """POST /prefs/labels/<id> renames label and returns 200.

        Source: ttrss/classes/pref/labels.php:176 — save
        Source: ttrss/classes/pref/labels.php:182-185 — duplicate check
        Source: ttrss/classes/pref/labels.php:187-198 — rename + update filter actions
        """
        mock_user = _mock_user()

        with app.test_request_context(
            method="POST",
            data={"caption": "Technology"},
        ):
            with patch("ttrss.blueprints.prefs.labels.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.labels.labels_crud") as mock_crud:
                mock_crud.fetch_label_caption.return_value = "Tech"
                mock_crud.check_caption_taken.return_value = False
                mock_crud.rename_label.return_value = None
                mock_crud.update_label_colors.return_value = None
                mock_crud.commit_label.return_value = None
                from ttrss.blueprints.prefs import labels
                resp = _unwrap(labels.save_label)(label_id=1)

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"
        mock_crud.rename_label.assert_called_once()


# ---------------------------------------------------------------------------
# DELETE /prefs/labels/<id>
# ---------------------------------------------------------------------------


class TestDeleteLabel:
    """DELETE /prefs/labels/<id> — remove a label."""

    def test_delete_label_returns_200(self, app):
        """DELETE /prefs/labels/<id> deletes label and returns 200.

        Source: ttrss/classes/pref/labels.php:214 — remove
        """
        mock_user = _mock_user()

        with app.test_request_context(method="DELETE"):
            with patch("ttrss.blueprints.prefs.labels.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.labels.labels_crud") as mock_crud:
                mock_crud.delete_label.return_value = None
                from ttrss.blueprints.prefs import labels
                resp = _unwrap(labels.delete_label)(label_id=1)

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"
        mock_crud.delete_label.assert_called_once()


# ---------------------------------------------------------------------------
# POST /prefs/labels/<id>/color
# ---------------------------------------------------------------------------


class TestSetLabelColor:
    """POST /prefs/labels/<id>/color — set label foreground/background color."""

    def test_set_color_returns_200(self, app):
        """POST /prefs/labels/<id>/color sets color and returns 200.

        Source: ttrss/classes/pref/labels.php:128 — colorset
        Source: ttrss/classes/pref/labels.php:128-143 — set fg/bg or both, invalidate cache
        """
        mock_user = _mock_user()

        with app.test_request_context(
            method="POST",
            data={"kind": "fg", "color": "#ff0000"},
        ):
            with patch("ttrss.blueprints.prefs.labels.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.labels.labels_crud") as mock_crud:
                mock_crud.set_label_color.return_value = None
                from ttrss.blueprints.prefs import labels
                resp = _unwrap(labels.set_label_color)(label_id=1)

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"
        mock_crud.set_label_color.assert_called_once()


# ---------------------------------------------------------------------------
# POST /prefs/labels/<id>/color/reset
# ---------------------------------------------------------------------------


class TestResetLabelColor:
    """POST /prefs/labels/<id>/color/reset — reset label colors to defaults."""

    def test_reset_color_returns_200(self, app):
        """POST /prefs/labels/<id>/color/reset clears colors and returns 200.

        Source: ttrss/classes/pref/labels.php:155 — colorreset
        Source: ttrss/classes/pref/labels.php:155-164 — reset fg/bg to empty, invalidate cache
        """
        mock_user = _mock_user()

        with app.test_request_context(method="POST"):
            with patch("ttrss.blueprints.prefs.labels.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.labels.labels_crud") as mock_crud:
                mock_crud.reset_label_color.return_value = None
                from ttrss.blueprints.prefs import labels
                resp = _unwrap(labels.reset_label_color)(label_id=1)

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"
        mock_crud.reset_label_color.assert_called_once()
