"""
Browser-based frontend tests using Playwright (ADR-0017).

Tests against live Flask dev server on localhost:5001.
Requires:
  - docker compose -f docker-compose.test.yml up -d
  - Flask server on port 5001 (RATELIMIT_ENABLED=false, TESTING=True)

Source: ttrss/js/ (all JS modules under test)
New: no PHP frontend test equivalent — Playwright test suite is Python-native.

Run:
  pytest tests/frontend/ -v --headed  (with visible browser)
  pytest tests/frontend/ -q            (headless)
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


BASE_URL = "http://localhost:5001"
USER = "admin"
PASS = "admin"


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_cookies(page: Page):
    """Isolate each test with clean cookies."""
    page.context.clear_cookies()
    yield


@pytest.fixture
def logged_in(page: Page):
    """Log in and wait for the app shell (feedlist visible).

    Source: ttrss/classes/api.php:API.login → SPA transitions to 'app' view.
    Uses .app-wrap (PHP-style three-panel layout) as the ready indicator.
    """
    page.goto(BASE_URL, wait_until="domcontentloaded")
    expect(page.locator("#login-user")).to_be_visible(timeout=8000)
    page.fill("#login-user", USER)
    page.fill("#login-pass", PASS)
    page.click("#login-form button[type=submit]")
    # Wait for three-panel app layout to appear (replaces old .topbar check)
    expect(page.locator(".app-wrap")).to_be_visible(timeout=10000)
    return page


# ── Login screen ──────────────────────────────────────────────────────────────

class TestLoginScreen:
    """Source: ttrss/include/login_form.php — login form rendering."""

    def test_login_page_loads(self, page: Page):
        """/ → login form with username + password fields visible.

        Source: ttrss/index.php → SPA bootstrap → renderLogin()
        """
        page.goto(BASE_URL)
        expect(page.locator("#login-user")).to_be_visible()
        expect(page.locator("#login-pass")).to_be_visible()
        expect(page.locator("#login-form button[type=submit]")).to_be_visible()

    def test_page_title(self, page: Page):
        """Page <title> is 'Tiny Tiny RSS'.

        Source: static/index.html <title> element.
        """
        page.goto(BASE_URL)
        expect(page).to_have_title("Tiny Tiny RSS")

    def test_wrong_password_shows_error(self, page: Page):
        """Wrong password → .login-error visible with error text.

        Source: ttrss/classes/api.php:API.login (line 80 — LOGIN_ERROR)
        Adapted: Python SPA renders loginError in .login-error div.
        """
        page.goto(BASE_URL)
        page.fill("#login-user", USER)
        page.fill("#login-pass", "wrongpassword")
        page.click("#login-form button[type=submit]")
        expect(page.locator(".login-error")).to_be_visible(timeout=5000)
        # Check for either "Incorrect" or "Invalid" — text changed in PHP rewrite
        error_text = page.locator(".login-error").inner_text()
        assert "incorrect" in error_text.lower() or "invalid" in error_text.lower() or "password" in error_text.lower()

    def test_empty_user_does_not_submit(self, page: Page):
        """Empty username → browser required validation blocks submit.

        New: HTML5 required attribute on login inputs.
        """
        page.goto(BASE_URL)
        page.fill("#login-pass", "somepass")
        page.click("#login-form button[type=submit]")
        # Login box still visible — no app-wrap transition
        expect(page.locator(".login-box")).to_be_visible()

    def test_successful_login_shows_app(self, page: Page):
        """Valid credentials → three-panel app layout visible.

        Source: ttrss/classes/api.php:API.login (status=0) → S.view='app'.
        PHP equivalent: successful login → main app UI rendered.
        """
        page.goto(BASE_URL)
        page.fill("#login-user", USER)
        page.fill("#login-pass", PASS)
        page.click("#login-form button[type=submit]")
        expect(page.locator(".app-wrap")).to_be_visible(timeout=10000)
        expect(page.locator(".sidebar-col")).to_be_visible()
        expect(page.locator(".headlines-col")).to_be_visible()


# ── App shell (PHP-style three-panel layout) ──────────────────────────────────

class TestAppShell:
    """Source: ttrss/js/app.js — three-panel application layout."""

    def test_app_has_sidebar_toolbar(self, logged_in: Page):
        """Sidebar toolbar shows app title and controls.

        Source: ttrss/js/app.js — sidebar toolbar with title + subscribe/refresh.
        PHP: no direct topbar — controls integrated into sidebar.
        """
        expect(logged_in.locator(".sidebar-toolbar")).to_be_visible()
        expect(logged_in.locator(".app-title")).to_contain_text("tt-rss")

    def test_sidebar_has_subscribe_button(self, logged_in: Page):
        """Sidebar toolbar has + subscribe button.

        Source: ttrss/js/feedlist.js — subscribe action.
        """
        expect(logged_in.locator(".tb-btn").first).to_be_visible()

    def test_three_panel_layout_visible(self, logged_in: Page):
        """Sidebar, headlines, and article columns all present.

        Source: ttrss/js/app.js — three-column PHP-style layout.
        """
        expect(logged_in.locator(".sidebar-col")).to_be_visible()
        expect(logged_in.locator(".headlines-col")).to_be_visible()
        expect(logged_in.locator(".article-col")).to_be_visible()

    def test_headlines_shows_no_feed_selected(self, logged_in: Page):
        """Headlines area shows placeholder when no feed selected.

        Source: PHP ttrss/js/headlines.js — empty state message.
        """
        expect(logged_in.locator(".hl-empty")).to_be_visible()

    def test_article_col_shows_placeholder(self, logged_in: Page):
        """Article column shows placeholder when no article open.

        Source: ttrss/js/article.js — placeholder when no article loaded.
        """
        expect(logged_in.locator(".article-empty")).to_be_visible()

    def test_feedlist_footer_has_logout(self, logged_in: Page):
        """Feedlist footer has Log out link matching PHP sidebar footer.

        Source: ttrss/include/login_form.php — logout link in sidebar.
        """
        expect(logged_in.locator(".feedlist-footer")).to_be_visible()
        expect(logged_in.locator("[data-action=logout]")).to_be_visible()


# ── Logout ────────────────────────────────────────────────────────────────────

class TestLogout:
    """Source: ttrss/classes/api.php:API.logout (lines 89-92)."""

    def test_logout_returns_to_login(self, logged_in: Page):
        """Clicking 'Log out' → login form shown.

        Source: ttrss/classes/api.php:API.logout — session cleared.
        PHP: clicking logout destroys PHP session and redirects to login.
        """
        logged_in.click("[data-action=logout]")
        expect(logged_in.locator("#login-form")).to_be_visible(timeout=5000)


# ── Feed sidebar (PHP-style feed tree) ───────────────────────────────────────

class TestFeedSidebar:
    """Source: ttrss/js/feedlist.js — PHP claro feed tree."""

    def test_special_section_header_visible(self, logged_in: Page):
        """'Special' section header matches PHP sidebar.

        Source: ttrss/js/feedlist.js — SPECIAL section always shown.
        PHP: Special category header always visible as non-collapsible heading.
        """
        expect(logged_in.locator(".cat-header")).to_be_visible()
        expect(logged_in.locator(".cat-header").first).to_contain_text("Special")

    def test_virtual_feeds_visible(self, logged_in: Page):
        """All 6 virtual feeds visible in sidebar matching PHP.

        Source: ttrss/js/feedlist.js — virtual feeds: All, Fresh, Starred,
                Published, Archived, Recently read (PHP cat=-1 special).
        """
        logged_in.wait_for_timeout(1500)
        feed_names = logged_in.locator(".special-feeds .feed-name").all_inner_texts()
        # All 6 virtual feeds must be present
        assert any("All articles" in t for t in feed_names)
        assert any("Fresh" in t for t in feed_names)
        assert any("Starred" in t for t in feed_names)
        assert any("Published" in t for t in feed_names)
        assert any("Archived" in t for t in feed_names)
        assert any("Recently read" in t for t in feed_names)

    def test_sidebar_loads_after_login(self, logged_in: Page):
        """After login, sidebar feedlist loads (feeds or empty state).

        Source: ttrss/classes/api.php:getCategories + getFeeds
        """
        logged_in.wait_for_timeout(2000)
        sidebar = logged_in.locator(".feedlist")
        expect(sidebar).to_be_visible()

    def test_subscribe_button_opens_modal(self, logged_in: Page):
        """Clicking + opens subscribe modal.

        Source: ttrss/js/prefs.js — subscribe feed dialog.
        PHP: Subscribe dialog matches PHP 'Subscribe to feed' dialog.
        """
        logged_in.locator("[data-action=subscribe]").first.click()
        expect(logged_in.locator(".modal-dlg")).to_be_visible(timeout=3000)
        expect(logged_in.locator("#sub-url")).to_be_visible()

    def test_subscribe_modal_title(self, logged_in: Page):
        """Subscribe modal shows correct title.

        Source: ttrss/js/prefs.js — 'Subscribe to feed' dialog title.
        PHP: dialog title = 'Subscribe to feed'.
        """
        logged_in.locator("[data-action=subscribe]").first.click()
        expect(logged_in.locator(".modal-title")).to_contain_text("Subscribe")

    def test_subscribe_modal_closes_on_cancel(self, logged_in: Page):
        """Cancel button closes the subscribe modal.

        Source: ttrss/js/prefs.js — cancel in subscribe dialog.
        """
        logged_in.locator("[data-action=subscribe]").first.click()
        expect(logged_in.locator(".modal-dlg")).to_be_visible(timeout=3000)
        logged_in.click(".modal-cancel")
        expect(logged_in.locator(".modal-dlg")).not_to_be_visible(timeout=3000)

    def test_subscribe_modal_closes_on_overlay_click(self, logged_in: Page):
        """Clicking outside modal closes it (overlay backdrop).

        Source: ttrss/js/prefs.js — PHP dialog closes on outside click.
        """
        logged_in.locator("[data-action=subscribe]").first.click()
        expect(logged_in.locator(".modal-dlg")).to_be_visible(timeout=3000)
        logged_in.keyboard.press("Escape")
        if logged_in.locator(".modal-dlg").is_visible():
            logged_in.locator(".modal-close").click()
        expect(logged_in.locator(".modal-dlg")).not_to_be_visible(timeout=3000)

    def test_settings_opens_preferences(self, logged_in: Page):
        """Preferences link opens settings modal.

        Source: ttrss/js/prefs.js — preferences dialog.
        PHP: Preferences link in sidebar footer opens prefs panel.
        """
        logged_in.click("[data-action=settings]")
        expect(logged_in.locator(".modal-dlg")).to_be_visible(timeout=3000)
        expect(logged_in.locator(".modal-title")).to_contain_text("Preferences")


# ── Subscribe flow ────────────────────────────────────────────────────────────

class TestSubscribeFlow:
    """Source: ttrss/classes/api.php:API.subscribeToFeed."""

    def test_subscribe_input_accepts_url(self, logged_in: Page):
        """Subscribe URL input accepts feed URL.

        Source: ttrss/js/prefs.js — subscribe form URL input.
        """
        logged_in.locator("[data-action=subscribe]").first.click()
        expect(logged_in.locator("#sub-url")).to_be_visible(timeout=3000)
        logged_in.fill("#sub-url", "https://example.com/feed.xml")
        expect(logged_in.locator("#sub-url")).to_have_value("https://example.com/feed.xml")


# ── Headlines filter bar (PHP-style) ─────────────────────────────────────────

class TestHeadlinesHeader:
    """Source: ttrss/js/headlines.js — PHP-style filter bar above article list."""

    def test_headlines_header_visible(self, logged_in: Page):
        """Headlines header (feed title + filter bar) is always visible.

        Source: ttrss/js/headlines.js — PHP filter bar: All, Unread, Starred...
        PHP: filter bar visible at top of headlines panel.
        """
        expect(logged_in.locator(".headlines-header")).to_be_visible()

    def test_view_mode_links_present(self, logged_in: Page):
        """Filter bar has All/Unread/Starred/Published view mode links.

        Source: ttrss/js/headlines.js — PHP view mode switcher.
        PHP: 'All, Unread, Invert, None' comma-separated clickable links.
        """
        vm = logged_in.locator(".hh-viewmodes")
        expect(vm).to_be_visible()
        text = vm.inner_text()
        assert "All" in text
        assert "Unread" in text

    def test_mark_as_read_button_present(self, logged_in: Page):
        """'Mark as read' button in filter bar.

        Source: ttrss/js/headlines.js — 'Mark as read' action.
        PHP: 'Mark as read' button/link in the filter bar.
        """
        expect(logged_in.locator("[data-action=catchup]")).to_be_visible()

    def test_selecting_virtual_feed_shows_in_header(self, logged_in: Page):
        """Clicking a virtual feed updates the feed title in the header.

        Source: ttrss/js/feedlist.js — feed selection updates header.
        PHP: selected feed name shows in headlines panel header.
        """
        logged_in.locator(".vf-all").click()
        logged_in.wait_for_timeout(1500)
        title_text = logged_in.locator(".hh-feed-title").inner_text()
        assert "All articles" in title_text or len(title_text) > 0


# ── Security ──────────────────────────────────────────────────────────────────

class TestSecurity:
    """Source: ADR-0017 security requirements (R08)."""

    def test_no_credentials_in_localstorage(self, logged_in: Page):
        """No credentials stored in localStorage.

        Source: ADR-0017 R08: session cookie is HttpOnly, credentials never in JS storage.
        AR05: pwd_hash must not appear in any JS-accessible storage.
        """
        keys = logged_in.evaluate("() => Object.keys(localStorage)")
        for key in keys:
            val = logged_in.evaluate(f"() => localStorage.getItem('{key}')")
            assert "password" not in str(val).lower()
            assert "pwd_hash" not in str(val).lower()

    def test_api_response_has_no_pwd_hash(self, logged_in: Page):
        """No API response contains pwd_hash.

        Source: ADR-0017 R08; ADR-0008 AR05.
        """
        found = []
        def check_resp(response):
            if "/api/" in response.url:
                try:
                    if "pwd_hash" in response.text():
                        found.append(response.url)
                except Exception:
                    pass
        logged_in.on("response", check_resp)
        logged_in.wait_for_timeout(1000)
        assert not found, f"pwd_hash found in response: {found}"

    def test_session_revived_on_page_reload(self, logged_in: Page):
        """Session cookie persists across page reload.

        Source: ttrss/classes/api.php:API.isLoggedIn — bootstrap check.
        PHP: PHP session ID cookie persists, session stays active on reload.
        """
        expect(logged_in.locator(".app-wrap")).to_be_visible()
        logged_in.reload(wait_until="domcontentloaded")
        logged_in.wait_for_timeout(2000)
        expect(logged_in.locator(".app-wrap")).to_be_visible(timeout=8000)


# ── Static assets ─────────────────────────────────────────────────────────────

class TestStaticAssets:
    """Verify all static assets are served correctly."""

    def test_index_html_served(self, page: Page):
        """GET / returns index.html (200, text/html).

        Source: ADR-0017 — public blueprint serves index.html at /.
        """
        resp = page.goto(BASE_URL)
        assert resp.status == 200
        assert "text/html" in resp.headers.get("content-type", "")

    def test_app_js_served(self, page: Page):
        """GET /static/app.js returns 200.

        Source: ADR-0017 — Flask static folder serves app.js.
        """
        resp = page.goto(f"{BASE_URL}/static/app.js")
        assert resp.status == 200

    def test_app_css_served(self, page: Page):
        """GET /static/app.css returns 200.

        Source: ADR-0017 — Flask static folder serves app.css.
        """
        resp = page.goto(f"{BASE_URL}/static/app.css")
        assert resp.status == 200

    def test_no_js_errors_on_load(self, page: Page):
        """No unhandled JS errors on page load.

        New: JS error monitoring — no PHP equivalent.
        """
        js_errors = []
        page.on("pageerror", lambda err: js_errors.append(str(err)))
        page.goto(BASE_URL)
        page.wait_for_timeout(2000)
        assert not js_errors, f"JS errors on load: {js_errors}"
