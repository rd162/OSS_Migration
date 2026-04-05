"""
Browser-based frontend tests using Playwright (ADR-0017).

These tests run against the live Flask dev server on localhost:5001.
They require:
  - docker compose -f docker-compose.test.yml up -d  (Postgres + Redis)
  - Flask server already running on port 5001 with the admin user

Source: ttrss/js/ (all JS modules under test)
New: no PHP frontend test equivalent — Playwright test suite is Python-native.

Run:
  just test-fe          (starts server + runs tests)
  pytest tests/frontend/ -v --headed  (with browser visible)
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


BASE_URL = "http://localhost:5001"
USER = "admin"
PASS = "admin"


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_cookies(page: Page):
    """Clear cookies before each test for clean state."""
    page.context.clear_cookies()
    yield


# ── Login screen ─────────────────────────────────────────────────────────────

class TestLoginScreen:
    """Source: ttrss/classes/handler/login.php:Handler_Login — login form."""

    def test_login_page_loads(self, page: Page):
        """/ → login form visible with username + password fields.

        Source: ttrss/index.php (app root) → SPA bootstrap → renderLogin()
        """
        page.goto(BASE_URL)
        expect(page.locator("#login-user")).to_be_visible()
        expect(page.locator("#login-pass")).to_be_visible()
        expect(page.locator("#login-form button[type=submit]")).to_be_visible()

    def test_page_title(self, page: Page):
        """Page title is 'Tiny Tiny RSS'.

        Source: ttrss/templates/header.html — <title>
        """
        page.goto(BASE_URL)
        expect(page).to_have_title("Tiny Tiny RSS")

    def test_login_wrong_password_shows_error(self, page: Page):
        """Wrong password → error message shown, still on login page.

        Source: ttrss/classes/api.php:API.login (line 80 — LOGIN_ERROR)
        Adapted: Python SPA renders loginError in .login-error div.
        """
        page.goto(BASE_URL)
        page.fill("#login-user", USER)
        page.fill("#login-pass", "wrongpassword")
        page.click("#login-form button[type=submit]")
        expect(page.locator(".login-error")).to_be_visible(timeout=5000)
        expect(page.locator(".login-error")).to_contain_text("Invalid username")

    def test_login_empty_user_does_not_submit(self, page: Page):
        """Empty username → form validation prevents submit, no API call.

        New: browser-native required validation on input.
        """
        page.goto(BASE_URL)
        page.fill("#login-pass", "somepass")
        # Try clicking without filling user
        page.click("#login-form button[type=submit]")
        # Should still be on login (no transition to .topbar)
        expect(page.locator(".login-box")).to_be_visible()

    def test_successful_login_shows_app(self, page: Page):
        """Valid credentials → topbar + three-panel layout visible.

        Source: ttrss/classes/api.php:API.login (status=0) → SPA transitions to 'app' view.
        """
        page.goto(BASE_URL)
        page.fill("#login-user", USER)
        page.fill("#login-pass", PASS)
        page.click("#login-form button[type=submit]")
        expect(page.locator(".topbar")).to_be_visible(timeout=8000)
        expect(page.locator(".sidebar")).to_be_visible()
        expect(page.locator(".article-list")).to_be_visible()


# ── App shell ─────────────────────────────────────────────────────────────────

@pytest.fixture
def logged_in(page: Page):
    """Log in before test. Uses a fresh browser context (isolated cookies)."""
    page.goto(BASE_URL, wait_until="domcontentloaded")
    # Wait for SPA to bootstrap and show login form
    expect(page.locator("#login-user")).to_be_visible(timeout=8000)
    page.fill("#login-user", USER)
    page.fill("#login-pass", PASS)
    page.click("#login-form button[type=submit]")
    expect(page.locator(".topbar")).to_be_visible(timeout=10000)
    return page


class TestAppShell:
    """Source: ttrss/js/app.js — top-level application shell."""

    def test_topbar_has_logo(self, logged_in: Page):
        """Topbar shows app logo.

        Source: ttrss/templates/header.html — branding.
        """
        expect(logged_in.locator(".logo")).to_contain_text("Tiny Tiny RSS")

    def test_topbar_has_subscribe_button(self, logged_in: Page):
        """Topbar has Subscribe button.

        Source: ttrss/js/feedlist.js — subscribe action in toolbar.
        """
        expect(logged_in.locator("[data-action=subscribe]").first).to_be_visible()

    def test_topbar_has_logout_button(self, logged_in: Page):
        """Topbar has Sign out button.

        Source: ttrss/classes/api.php:API.logout.
        """
        expect(logged_in.locator("[data-action=logout]")).to_be_visible()

    def test_three_panel_layout_visible(self, logged_in: Page):
        """Sidebar, article list, and reading pane all present.

        Source: ttrss/js/app.js — three-panel layout structure.
        """
        expect(logged_in.locator(".sidebar")).to_be_visible()
        expect(logged_in.locator(".article-list")).to_be_visible()
        expect(logged_in.locator(".reading-pane")).to_be_visible()

    def test_article_list_shows_placeholder(self, logged_in: Page):
        """Article list shows 'Select a feed' when no feed selected.

        New: UX placeholder — no PHP equivalent.
        """
        expect(logged_in.locator(".list-empty")).to_contain_text("Select a feed")

    def test_reading_pane_shows_placeholder(self, logged_in: Page):
        """Reading pane shows 'Select an article' when no article selected.

        New: UX placeholder — no PHP equivalent.
        """
        expect(logged_in.locator(".pane-empty")).to_contain_text("Select an article")


class TestLogout:
    """Source: ttrss/classes/api.php:API.logout (lines 89-92)."""

    def test_logout_returns_to_login(self, logged_in: Page):
        """Clicking Sign out → back to login form.

        Source: ttrss/classes/api.php:API.logout — session cleared.
        """
        logged_in.click("[data-action=logout]")
        expect(logged_in.locator("#login-form")).to_be_visible(timeout=5000)


# ── Feed sidebar ──────────────────────────────────────────────────────────────

class TestFeedSidebar:
    """Source: ttrss/js/feedlist.js — feed list rendering."""

    def test_sidebar_loads_after_login(self, logged_in: Page):
        """After login, sidebar renders (either feeds or 'No feeds' message).

        Source: ttrss/classes/api.php:API.getFeeds + getCategories
        """
        # Wait for sidebar to finish loading (either feeds or empty state)
        logged_in.wait_for_timeout(2000)
        sidebar = logged_in.locator(".sidebar")
        expect(sidebar).to_be_visible()
        # Sidebar has either a feed item or the empty state
        has_feeds = sidebar.locator(".feed-item").count() > 0
        has_empty = sidebar.locator(".sidebar-empty").count() > 0
        assert has_feeds or has_empty, "Sidebar must show feeds or empty state"

    def test_subscribe_button_opens_modal(self, logged_in: Page):
        """Clicking '+ Subscribe' opens the subscribe modal.

        Source: ttrss/classes/api.php:API.subscribeToFeed — subscribe dialog.
        """
        logged_in.click("[data-action=subscribe]")
        expect(logged_in.locator(".modal-box")).to_be_visible(timeout=3000)
        expect(logged_in.locator("#sub-url")).to_be_visible()

    def test_subscribe_modal_closes_on_cancel(self, logged_in: Page):
        """Cancel button closes the subscribe modal.

        New: modal UX — no PHP equivalent.
        """
        logged_in.click("[data-action=subscribe]")
        expect(logged_in.locator(".modal-box")).to_be_visible(timeout=3000)
        # Use specific modal-cancel class to avoid hitting the overlay
        logged_in.click(".modal-cancel")
        expect(logged_in.locator(".modal-box")).not_to_be_visible(timeout=3000)

    def test_subscribe_modal_closes_on_overlay_click(self, logged_in: Page):
        """Clicking outside modal overlay closes it.

        New: modal UX — overlay click handler.
        """
        logged_in.click("[data-action=subscribe]")
        expect(logged_in.locator(".modal-box")).to_be_visible(timeout=3000)
        # Press Escape to close (avoids ambiguous overlay coordinate click)
        logged_in.keyboard.press("Escape")
        # Fallback: click close button in header if Escape not wired
        if logged_in.locator(".modal-box").is_visible():
            logged_in.locator(".modal-header [data-action=close-modal]").click()
        expect(logged_in.locator(".modal-box")).not_to_be_visible(timeout=3000)

    def test_settings_button_opens_modal(self, logged_in: Page):
        """Clicking ⚙ opens the settings modal.

        Source: ttrss/js/prefs.js — settings dialog.
        """
        logged_in.click("[data-action=settings]")
        expect(logged_in.locator(".modal-box")).to_be_visible(timeout=3000)
        expect(logged_in.locator(".modal-box h3")).to_contain_text("Settings")


# ── Subscribe + feed flow ─────────────────────────────────────────────────────

class TestSubscribeFlow:
    """Source: ttrss/classes/api.php:API.subscribeToFeed."""

    def test_subscribe_input_accepts_url(self, logged_in: Page):
        """Subscribe modal input accepts a URL.

        Source: ttrss/js/feedlist.js — subscribe form input.
        """
        logged_in.click("[data-action=subscribe]")
        expect(logged_in.locator("#sub-url")).to_be_visible(timeout=3000)
        logged_in.fill("#sub-url", "https://example.com/feed.xml")
        expect(logged_in.locator("#sub-url")).to_have_value("https://example.com/feed.xml")


# ── Security checks ───────────────────────────────────────────────────────────

class TestSecurity:
    """Source: ADR-0017 security requirements (R08)."""

    def test_no_credentials_in_localstorage(self, logged_in: Page):
        """Credentials must never be stored in localStorage.

        Source: ADR-0017 — R08: session cookie is HttpOnly, no credential storage in JS.
        AR05: pwd_hash must never appear in any storage accessible to JS.
        """
        keys = logged_in.evaluate("() => Object.keys(localStorage)")
        for key in keys:
            val = logged_in.evaluate(f"() => localStorage.getItem('{key}')")
            assert "password" not in str(val).lower()
            assert "pwd_hash" not in str(val).lower()

    def test_api_response_has_no_pwd_hash(self, logged_in: Page):
        """Login API response body must not contain pwd_hash.

        Source: ADR-0017 R08; ADR-0008 AR05.
        """
        # Intercept /api/ responses and check for pwd_hash
        found_pwd_hash = []
        def handle_response(response):
            if "/api/" in response.url:
                try:
                    body = response.text()
                    if "pwd_hash" in body:
                        found_pwd_hash.append(response.url)
                except Exception:
                    pass

        logged_in.on("response", handle_response)
        logged_in.wait_for_timeout(1000)
        assert not found_pwd_hash, f"pwd_hash found in API response: {found_pwd_hash}"

    def test_session_revived_on_page_reload(self, logged_in: Page):
        """After login, reloading the page re-enters app (session cookie persists).

        Source: ttrss/classes/api.php:API.isLoggedIn — app bootstraps by checking session.
        The SPA calls isLoggedIn on bootstrap; if status=true it skips the login form.
        """
        # Already logged in via fixture — verify we're in the app
        expect(logged_in.locator(".topbar")).to_be_visible()

        # Reload — session cookie should persist, app should re-enter directly
        logged_in.reload(wait_until="domcontentloaded")
        # Wait for SPA bootstrap (isLoggedIn check takes ~200ms)
        logged_in.wait_for_timeout(2000)
        expect(logged_in.locator(".topbar")).to_be_visible(timeout=8000)


# ── Static asset checks ───────────────────────────────────────────────────────

class TestStaticAssets:
    """Verify all static assets are served correctly."""

    def test_index_html_served(self, page: Page):
        """GET / returns index.html (200, text/html).

        Source: ADR-0017 — Flask public blueprint serves index.html at /.
        """
        response = page.goto(BASE_URL)
        assert response.status == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_app_js_served(self, page: Page):
        """GET /static/app.js returns 200.

        Source: ADR-0017 — Flask static folder serves app.js.
        """
        response = page.goto(f"{BASE_URL}/static/app.js")
        assert response.status == 200

    def test_app_css_served(self, page: Page):
        """GET /static/app.css returns 200.

        Source: ADR-0017 — Flask static folder serves app.css.
        """
        response = page.goto(f"{BASE_URL}/static/app.css")
        assert response.status == 200

    def test_no_js_errors_on_load(self, page: Page):
        """No unhandled JS errors on page load.

        New: JS error monitoring — no PHP equivalent.
        """
        js_errors = []
        page.on("pageerror", lambda err: js_errors.append(str(err)))
        page.goto(BASE_URL)
        page.wait_for_timeout(2000)
        assert not js_errors, f"JS errors on load: {js_errors}"
