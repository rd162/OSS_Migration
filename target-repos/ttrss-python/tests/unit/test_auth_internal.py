"""Tests for AuthInternal plugin hookimpl.

Source: ttrss/plugins/auth_internal/init.php (Auth_Internal class, lines 1-196)
New: no PHP equivalent — Python test suite.
"""
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture()
def test_user(app, db_session):
    """Create a test user with argon2id-hashed password."""
    from ttrss.auth.password import hash_password
    from ttrss.models.user import TtRssUser

    with app.app_context():
        user = TtRssUser(
            login="testuser_auth",
            pwd_hash=hash_password("testpassword"),
            access_level=0,
        )
        db_session.add(user)
        db_session.commit()
        yield user
        db_session.delete(user)
        db_session.commit()


class TestAuthInternalHookImpl:
    """Auth_Internal.authenticate → hook_auth_user hookimpl."""

    def test_valid_credentials_returns_user_id(self, app, test_user):
        """hook_auth_user returns user_id (int > 0) for valid login + password."""
        from ttrss.plugins.auth_internal import AuthInternal

        plugin = AuthInternal()
        with app.app_context():
            result = plugin.hook_auth_user(login="testuser_auth", password="testpassword")
        assert result is not None
        assert isinstance(result, int)
        assert result > 0

    def test_wrong_password_returns_none(self, app, test_user):
        """hook_auth_user returns None when password is wrong."""
        from ttrss.plugins.auth_internal import AuthInternal

        plugin = AuthInternal()
        with app.app_context():
            result = plugin.hook_auth_user(login="testuser_auth", password="wrongpassword")
        assert result is None

    def test_unknown_user_returns_none(self, app):
        """hook_auth_user returns None for unknown login."""
        from ttrss.plugins.auth_internal import AuthInternal

        plugin = AuthInternal()
        with app.app_context():
            result = plugin.hook_auth_user(login="nobody_xyz", password="pass")
        assert result is None

    def test_empty_login_returns_none(self, app):
        """hook_auth_user returns None for empty login string."""
        from ttrss.plugins.auth_internal import AuthInternal

        plugin = AuthInternal()
        with app.app_context():
            result = plugin.hook_auth_user(login="", password="pass")
        assert result is None

    def test_empty_password_returns_none(self, app, test_user):
        """hook_auth_user returns None for empty password string."""
        from ttrss.plugins.auth_internal import AuthInternal

        plugin = AuthInternal()
        with app.app_context():
            result = plugin.hook_auth_user(login="testuser_auth", password="")
        assert result is None

    def test_plugin_class_attribute(self):
        """plugin_class attribute must point to AuthInternal for loader discovery."""
        from ttrss.plugins.auth_internal import plugin_class, AuthInternal
        assert plugin_class is AuthInternal
