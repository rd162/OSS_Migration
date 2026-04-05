"""Tests for /prefs/user* HTTP handlers.

Source: ttrss/classes/pref/prefs.php (Pref_Prefs, 1129 lines)
New: Python test suite — handler-level HTTP tests via Flask test client.

All tests mock flask_login.current_user so no real session or DB is needed
for the auth layer; CRUD helpers are patched at the call site.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(uid: int = 42) -> MagicMock:
    """Return a minimal mock user compatible with current_user checks."""
    u = MagicMock()
    u.id = uid
    u.is_authenticated = True
    u.is_active = True
    u.is_anonymous = False
    u.get_id.return_value = str(uid)
    return u


# ---------------------------------------------------------------------------
# POST /prefs/user/password
# ---------------------------------------------------------------------------


class TestChangePassword:
    """Source: ttrss/classes/pref/prefs.php:62 — changepassword"""

    def test_correct_password_returns_200(self, client):
        """Correct old password + matching confirm → 200 ok.

        Source: ttrss/classes/pref/prefs.php:83-89 — verify old password,
                ttrss/classes/pref/prefs.php:62 — hash update on success.
        """
        mock_user = _make_user()
        db_user = MagicMock()
        db_user.pwd_hash = "hash"
        db_user.salt = "salt"

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.blueprints.prefs.user_prefs.user_prefs_crud") as mock_crud, \
             patch("ttrss.auth.password.verify_password", return_value=True):
            mock_crud.get_user_for_password_change.return_value = db_user

            resp = client.post(
                "/prefs/user/password",
                data={
                    "old_password": "correct",
                    "new_password": "newpass1",
                    "confirm_password": "newpass1",
                },
            )

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"

    def test_wrong_old_password_returns_403(self, client):
        """Wrong old password → 403 incorrect_password.

        Source: ttrss/classes/pref/prefs.php:83-89 — reject if hash mismatch.
        """
        mock_user = _make_user()
        db_user = MagicMock()
        db_user.pwd_hash = "hash"
        db_user.salt = "salt"

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.blueprints.prefs.user_prefs.user_prefs_crud") as mock_crud, \
             patch("ttrss.auth.password.verify_password", return_value=False):
            mock_crud.get_user_for_password_change.return_value = db_user

            resp = client.post(
                "/prefs/user/password",
                data={
                    "old_password": "wrong",
                    "new_password": "newpass1",
                    "confirm_password": "newpass1",
                },
            )

        assert resp.status_code == 403
        assert resp.get_json()["error"] == "incorrect_password"

    def test_mismatched_confirm_returns_400(self, client):
        """Confirm password mismatch → 400 before touching the DB.

        Source: ttrss/classes/pref/prefs.php:62 — pre-check before hash update.
        """
        mock_user = _make_user()

        with patch("flask_login.utils._get_user", return_value=mock_user):
            resp = client.post(
                "/prefs/user/password",
                data={
                    "old_password": "old",
                    "new_password": "abc",
                    "confirm_password": "xyz",
                },
            )

        assert resp.status_code == 400
        assert resp.get_json()["error"] == "passwords_do_not_match"


# ---------------------------------------------------------------------------
# POST /prefs/user/config
# ---------------------------------------------------------------------------


class TestSaveConfig:
    """Source: ttrss/classes/pref/prefs.php:106 — saveconfig"""

    def test_save_config_returns_200(self, client):
        """Valid pref_name + value saves successfully.

        Source: ttrss/classes/pref/prefs.php:106 — saveconfig calls set_pref.
        """
        mock_user = _make_user()

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.prefs.ops.set_user_pref") as mock_set:
            resp = client.post(
                "/prefs/user/config",
                data={"pref_name": "HIDE_READ_FEEDS", "value": "true"},
            )

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"


# ---------------------------------------------------------------------------
# POST /prefs/user/config/reset
# ---------------------------------------------------------------------------


class TestResetConfig:
    """Source: ttrss/classes/pref/prefs.php:161 — resetconfig"""

    def test_reset_config_returns_200(self, client):
        """Resetting config deletes overrides and re-initialises defaults.

        Source: ttrss/classes/pref/prefs.php:170-174 — DELETE prefs then
                reinitialize defaults.
        """
        mock_user = _make_user()

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.blueprints.prefs.user_prefs.user_prefs_crud") as mock_crud:
            resp = client.post("/prefs/user/config/reset", data={})

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"
        mock_crud.reset_user_prefs.assert_called_once()


# ---------------------------------------------------------------------------
# Additional route coverage: /prefs/user/plugin_data/clear,
#   /prefs/user/plugins variant, /prefs/user/email, /prefs/user/config
# ---------------------------------------------------------------------------


class TestAdditionalRoutes:
    """Extra coverage for routes not yet exhaustively tested.

    Source: ttrss/classes/pref/prefs.php (Pref_Prefs, 1129 lines)
    """

    # ------------------------------------------------------------------
    # POST /prefs/user/plugin_data/clear
    # ------------------------------------------------------------------

    def test_clear_plugin_data_valid_returns_200(self, client):
        """POST /prefs/user/plugin_data/clear with plugin name → 200 ok.

        Source: ttrss/classes/pref/prefs.php:962 — clearplugindata:
                DELETE FROM ttrss_plugin_storage WHERE owner_uid AND plugin_name.
        """
        mock_user = _make_user()

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.blueprints.prefs.user_prefs.user_prefs_crud") as mock_crud:
            resp = client.post(
                "/prefs/user/plugin_data/clear",
                data={"plugin": "my_plugin"},
            )

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"
        mock_crud.clear_plugin_data.assert_called_once_with(mock_user.id, "my_plugin")

    def test_clear_plugin_data_missing_plugin_returns_400(self, client):
        """POST /prefs/user/plugin_data/clear without plugin param → 400.

        Source: ttrss/classes/pref/prefs.php:962 — clearplugindata:
                plugin name is required; empty/missing triggers 400.
        """
        mock_user = _make_user()

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.blueprints.prefs.user_prefs.user_prefs_crud"):
            resp = client.post("/prefs/user/plugin_data/clear", data={})

        assert resp.status_code == 400
        assert resp.get_json()["error"] == "plugin_required"

    # ------------------------------------------------------------------
    # POST /prefs/user/plugins — variant: allowed plugin passes filter
    # ------------------------------------------------------------------

    def test_set_plugins_allowed_plugin_is_saved(self, client):
        """POST /prefs/user/plugins with an allowed KIND_USER plugin → saved in pref.

        Source: ttrss/classes/pref/prefs.php:950-954 — setplugins:
                ttrss/classes/pref/prefs.php:806-820 — only KIND_USER plugins shown in UI.
        """
        from ttrss.plugins.hookspecs import KIND_USER

        mock_user = _make_user()
        allowed_plugin = MagicMock()
        allowed_plugin.KIND = KIND_USER

        mock_pm = MagicMock()
        mock_pm.get_plugins.return_value = {"my_user_plugin": allowed_plugin}

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm), \
             patch("ttrss.prefs.ops.set_user_pref") as mock_set:
            resp = client.post(
                "/prefs/user/plugins",
                data={"plugins[]": ["my_user_plugin"]},
            )

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"
        mock_set.assert_called_once_with(mock_user.id, "_ENABLED_PLUGINS", "my_user_plugin")

    def test_set_plugins_disallowed_plugin_is_filtered(self, client):
        """POST /prefs/user/plugins with a non-KIND_USER plugin → filtered out, empty saved.

        Source: ttrss/classes/pref/prefs.php:806-820 — enforce KIND_USER to
                prevent injection of system plugin names via crafted POST.
        """
        mock_user = _make_user()
        system_plugin = MagicMock()
        system_plugin.KIND = "system"  # not KIND_USER

        mock_pm = MagicMock()
        mock_pm.get_plugins.return_value = {"system_plugin": system_plugin}

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm), \
             patch("ttrss.prefs.ops.set_user_pref") as mock_set:
            resp = client.post(
                "/prefs/user/plugins",
                data={"plugins[]": ["system_plugin"]},
            )

        assert resp.status_code == 200
        mock_set.assert_called_once_with(mock_user.id, "_ENABLED_PLUGINS", "")

    # ------------------------------------------------------------------
    # POST /prefs/user/email
    # ------------------------------------------------------------------

    def test_change_email_returns_200(self, client):
        """POST /prefs/user/email with email + full_name → 200 ok.

        Source: ttrss/classes/pref/prefs.php:153 — changeemail:
                UPDATE ttrss_users SET email, full_name.
        """
        mock_user = _make_user()

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.blueprints.prefs.user_prefs.user_prefs_crud") as mock_crud:
            resp = client.post(
                "/prefs/user/email",
                data={"email": "new@example.com", "full_name": "New Name"},
            )

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"
        mock_crud.save_email_and_name.assert_called_once_with(
            mock_user.id, "new@example.com", "New Name"
        )

    def test_change_email_empty_values_still_returns_200(self, client):
        """POST /prefs/user/email with empty strings → 200 (PHP allows clearing).

        Source: ttrss/classes/pref/prefs.php:153 — changeemail:
                empty email/full_name clears the fields in the DB.
        """
        mock_user = _make_user()

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.blueprints.prefs.user_prefs.user_prefs_crud"):
            resp = client.post("/prefs/user/email", data={})

        assert resp.status_code == 200

    # ------------------------------------------------------------------
    # POST /prefs/user/config — pref_name required
    # ------------------------------------------------------------------

    def test_save_config_missing_pref_name_returns_400(self, client):
        """POST /prefs/user/config without pref_name → 400.

        Source: ttrss/classes/pref/prefs.php:106 — saveconfig:
                pref_name is required; empty triggers 400.
        """
        mock_user = _make_user()

        with patch("flask_login.utils._get_user", return_value=mock_user):
            resp = client.post("/prefs/user/config", data={"value": "true"})

        assert resp.status_code == 400
        assert resp.get_json()["error"] == "pref_name_required"

    def test_save_config_digest_time_change_clears_sent_time(self, client):
        """POST /prefs/user/config for DIGEST_PREFERRED_TIME with changed value calls clear.

        Source: ttrss/classes/pref/prefs.php:107 — only clear digest time
                if value actually changed; calls clear_digest_sent_time.
        """
        mock_user = _make_user()

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.blueprints.prefs.user_prefs.user_prefs_crud") as mock_crud, \
             patch("ttrss.prefs.ops.get_user_pref", return_value="08:00"), \
             patch("ttrss.prefs.ops.set_user_pref"):
            resp = client.post(
                "/prefs/user/config",
                data={"pref_name": "DIGEST_PREFERRED_TIME", "value": "09:00"},
            )

        assert resp.status_code == 200
        mock_crud.clear_digest_sent_time.assert_called_once_with(mock_user.id)

    def test_save_config_digest_time_unchanged_skips_clear(self, client):
        """POST /prefs/user/config for DIGEST_PREFERRED_TIME with same value → no clear.

        Source: ttrss/classes/pref/prefs.php:107 — clear only if value CHANGED;
                same value must not trigger clear_digest_sent_time.
        """
        mock_user = _make_user()

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.blueprints.prefs.user_prefs.user_prefs_crud") as mock_crud, \
             patch("ttrss.prefs.ops.get_user_pref", return_value="08:00"), \
             patch("ttrss.prefs.ops.set_user_pref"):
            resp = client.post(
                "/prefs/user/config",
                data={"pref_name": "DIGEST_PREFERRED_TIME", "value": "08:00"},
            )

        assert resp.status_code == 200
        mock_crud.clear_digest_sent_time.assert_not_called()

    # ------------------------------------------------------------------
    # POST /prefs/user/config/reset — with profile param
    # ------------------------------------------------------------------

    def test_reset_config_with_profile_passes_profile_id(self, client):
        """POST /prefs/user/config/reset with profile=3 → reset_user_prefs called with profile=3.

        Source: ttrss/classes/pref/prefs.php:170-174 — resetconfig:
                profile parameter scopes which prefs are deleted/reset.
        """
        mock_user = _make_user()

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.blueprints.prefs.user_prefs.user_prefs_crud") as mock_crud:
            resp = client.post("/prefs/user/config/reset", data={"profile": "3"})

        assert resp.status_code == 200
        mock_crud.reset_user_prefs.assert_called_once_with(mock_user.id, profile=3)


# ---------------------------------------------------------------------------
# POST /prefs/user/otp/enable
# ---------------------------------------------------------------------------


class TestOtpEnable:
    """Source: ttrss/classes/pref/prefs.php:896-932 — otpenable"""

    def test_correct_pass_and_otp_returns_200(self, client):
        """Correct password + valid OTP code enables OTP.

        Source: ttrss/classes/pref/prefs.php:912-919 — verify OTP code
                before setting otp_enabled=True.
        """
        mock_user = _make_user()
        db_user = MagicMock()
        db_user.pwd_hash = "hash"
        db_user.salt = ""  # empty salt skips TOTP verification path

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.blueprints.prefs.user_prefs.user_prefs_crud") as mock_crud, \
             patch("ttrss.auth.password.verify_password", return_value=True):
            mock_crud.get_user_for_password_change.return_value = db_user

            resp = client.post(
                "/prefs/user/otp/enable",
                data={"password": "correct", "otp": "123456"},
            )

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"
        mock_crud.set_otp_enabled.assert_called_once_with(mock_user.id, enabled=True)

    def test_wrong_password_returns_403(self, client):
        """Wrong password for OTP enable → 403.

        Source: ttrss/classes/pref/prefs.php:900-910 — verify password via
                authenticator before proceeding.
        """
        mock_user = _make_user()
        db_user = MagicMock()
        db_user.pwd_hash = "hash"
        db_user.salt = ""

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.blueprints.prefs.user_prefs.user_prefs_crud") as mock_crud, \
             patch("ttrss.auth.password.verify_password", return_value=False):
            mock_crud.get_user_for_password_change.return_value = db_user

            resp = client.post(
                "/prefs/user/otp/enable",
                data={"password": "wrong", "otp": "000000"},
            )

        assert resp.status_code == 403
        assert resp.get_json()["error"] == "incorrect_password"


# ---------------------------------------------------------------------------
# POST /prefs/user/otp/disable
# ---------------------------------------------------------------------------


class TestOtpDisable:
    """Source: ttrss/classes/pref/prefs.php:933-949 — otpdisable"""

    def test_correct_password_disables_otp(self, client):
        """Correct password disables OTP.

        Source: ttrss/classes/pref/prefs.php:940-941 — set otp_enabled=False.
        """
        mock_user = _make_user()
        db_user = MagicMock()
        db_user.pwd_hash = "hash"
        db_user.salt = ""

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.blueprints.prefs.user_prefs.user_prefs_crud") as mock_crud, \
             patch("ttrss.auth.password.verify_password", return_value=True):
            mock_crud.get_user_for_password_change.return_value = db_user

            resp = client.post(
                "/prefs/user/otp/disable",
                data={"password": "correct"},
            )

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"
        mock_crud.set_otp_enabled.assert_called_once_with(mock_user.id, enabled=False)

    def test_wrong_password_returns_403(self, client):
        """Wrong password for OTP disable → 403.

        Source: ttrss/classes/pref/prefs.php:937-942 — verify password
                before disabling OTP.
        """
        mock_user = _make_user()
        db_user = MagicMock()
        db_user.pwd_hash = "hash"
        db_user.salt = ""

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.blueprints.prefs.user_prefs.user_prefs_crud") as mock_crud, \
             patch("ttrss.auth.password.verify_password", return_value=False):
            mock_crud.get_user_for_password_change.return_value = db_user

            resp = client.post(
                "/prefs/user/otp/disable",
                data={"password": "wrong"},
            )

        assert resp.status_code == 403
        assert resp.get_json()["error"] == "incorrect_password"


# ---------------------------------------------------------------------------
# GET /prefs/user
# ---------------------------------------------------------------------------


class TestUserPrefs:
    """Source: ttrss/classes/pref/prefs.php:435,661,697,863 — HOOK_PREFS_TAB_SECTION,
              HOOK_PREFS_TAB"""

    def test_get_user_prefs_returns_json(self, client):
        """GET /prefs/user returns preferences data structure.

        Source: ttrss/classes/pref/prefs.php:435 — HOOK_PREFS_TAB_SECTION (section 1)
                ttrss/classes/pref/prefs.php:863 — HOOK_PREFS_TAB.
        """
        mock_user = _make_user(uid=0)  # uid=0 skips profile DB call

        mock_pm = MagicMock()
        mock_pm.hook.hook_prefs_tab_section.return_value = []
        mock_pm.hook.hook_prefs_tab.return_value = []

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm), \
             patch("ttrss.prefs.ops.get_user_pref", return_value=""):
            resp = client.get("/prefs/user")

        assert resp.status_code == 200
        data = resp.get_json()
        assert "plugin_sections" in data
        assert "plugin_tab_content" in data
        assert "profiles" in data


# ---------------------------------------------------------------------------
# POST /prefs/user/plugins
# ---------------------------------------------------------------------------


class TestSetPlugins:
    """Source: ttrss/classes/pref/prefs.php:950-954 — setplugins"""

    def test_set_plugins_returns_200(self, client):
        """Plugin list saved as comma-separated _ENABLED_PLUGINS pref.

        Source: ttrss/classes/pref/prefs.php:950-954 — joins plugins[] array
                to comma string, calls set_pref("_ENABLED_PLUGINS", plugins).
        """
        mock_user = _make_user()

        mock_pm = MagicMock()
        mock_pm.get_plugins.return_value = {}  # no plugins allowed → empty list

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm), \
             patch("ttrss.prefs.ops.set_user_pref") as mock_set:
            resp = client.post(
                "/prefs/user/plugins",
                data={"plugins[]": []},
            )

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"
