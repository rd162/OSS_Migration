"""
Pluggy hookspec unit tests (R7, R8, R13, R15, R16).

New: no PHP equivalent — PHP PluginHost had no formal test coverage.
Source: ttrss/classes/pluginhost.php (constants and semantics verified here).
"""
import pytest


@pytest.fixture(autouse=True)
def reset_pm():
    """Reset singleton before each test for isolation."""
    from ttrss.plugins.manager import reset_plugin_manager

    reset_plugin_manager()
    yield
    reset_plugin_manager()


def test_plugin_manager_singleton():
    """R8: get_plugin_manager() returns the same instance on repeated calls."""
    from ttrss.plugins.manager import get_plugin_manager

    pm1 = get_plugin_manager()
    pm2 = get_plugin_manager()
    assert pm1 is pm2


def test_plugin_manager_no_flask_import():
    """R8/R18: PluginManager accessible without Flask app context."""
    # If this import fails inside a Celery worker (no Flask), the test fails.
    from ttrss.plugins.manager import get_plugin_manager

    pm = get_plugin_manager()
    assert pm is not None


def test_all_24_hookspecs_registered():
    """R7: All 24 hook methods are registered on the PluginManager."""
    from ttrss.plugins.manager import get_plugin_manager

    pm = get_plugin_manager()
    # Collect hook names from the pm.hook proxy namespace
    hook_names = [name for name in dir(pm.hook) if name.startswith("hook_")]
    assert len(hook_names) == 24, f"Expected 24 hooks, got {len(hook_names)}: {hook_names}"


def test_auth_user_is_firstresult():
    """R15: HOOK_AUTH_USER (const 8) must be firstresult=True — only hook with PHP break."""
    from ttrss.plugins.manager import get_plugin_manager

    pm = get_plugin_manager()
    spec = pm.hook.hook_auth_user.spec
    assert spec is not None
    assert spec.opts.get("firstresult") is True, (
        "hook_auth_user must be firstresult=True "
        "(PHP functions.php:711-718 breaks on first truthy user_id)"
    )


def test_fetch_feed_is_collecting():
    """R15: HOOK_FETCH_FEED (const 22) must be collecting — PHP rssfuncs.php:270-272 has no break."""
    from ttrss.plugins.manager import get_plugin_manager

    pm = get_plugin_manager()
    spec = pm.hook.hook_fetch_feed.spec
    assert spec is not None
    assert not spec.opts.get("firstresult"), (
        "hook_fetch_feed must NOT be firstresult — "
        "PHP rssfuncs.php:270-272 passes $feed_data through all plugins (pipeline)"
    )


def test_no_other_hook_is_firstresult():
    """R15: No hook other than hook_auth_user uses firstresult=True."""
    from ttrss.plugins.manager import get_plugin_manager

    pm = get_plugin_manager()
    firstresult_hooks = [
        name
        for name in dir(pm.hook)
        if name.startswith("hook_")
        and getattr(pm.hook, name).spec is not None
        and getattr(pm.hook, name).spec.opts.get("firstresult")
    ]
    assert firstresult_hooks == ["hook_auth_user"], (
        f"Only hook_auth_user should be firstresult, got: {firstresult_hooks}"
    )


def test_kind_constants():
    """R16: KIND_ALL, KIND_SYSTEM, KIND_USER constants match PHP pluginhost.php:43-45."""
    from ttrss.plugins.hookspecs import KIND_ALL, KIND_SYSTEM, KIND_USER

    # Source: ttrss/classes/pluginhost.php (lines 43-45)
    assert KIND_ALL == 1
    assert KIND_SYSTEM == 2
    assert KIND_USER == 3
    assert KIND_SYSTEM != KIND_USER
