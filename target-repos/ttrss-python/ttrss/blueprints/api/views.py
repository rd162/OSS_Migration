"""
TT-RSS REST API (/api/ — equivalent to PHP api/index.php).

Source: ttrss/api/index.php (bootstrap + dispatch, lines 1-74)
        + ttrss/classes/api.php:API (dispatch, wrap, login, logout, isLoggedIn, getVersion, getApiLevel)
        + ttrss/include/functions.php:authenticate_user (lines 706-795)

Protocol (spec/03-api-routing.md, R08, R09):
  POST or GET /api/ with JSON body (or query params for GET).
  Response envelope: {"seq": N, "status": 0|1, "content": {...}}
  seq MUST be echoed from the request in every response (CG-04).
  API level: 8.

Auth (ADR-0007, ADR-0008, R07, AR05):
  Login stores user_id in Redis session only — never pwd_hash (AR05).
  Legacy MODE2/SHA1X/SHA1 hashes are upgraded to argon2id on first successful login (ADR-0008).

CSRF (ADR-0002, spec/03-api-routing.md):
  The PHP API does NOT use CSRF tokens — it authenticates via session_id parameter.
  This blueprint is exempt from Flask-WTF CSRFProtect (see csrf.exempt below).
  Source: ttrss/api/index.php — no CSRF validation in API entry point.
"""
from __future__ import annotations

from typing import Optional

from flask import Blueprint, current_app, jsonify, request, session
from flask_login import current_user, login_user, logout_user
from sqlalchemy import func, select

from ttrss.articles.ops import catchup_feed, get_article_enclosures
from ttrss.articles.search import queryFeedHeadlines
from ttrss.auth.password import hash_password, needs_upgrade, verify_password
from ttrss.ccache import _count_feed_articles, ccache_update
from ttrss.extensions import csrf, db
from ttrss.feeds.categories import MAX_CATEGORY_DEPTH, getCategoryTitle, getFeedTitle
from ttrss.feeds.counters import (
    getAllCounters,
    getCategoryChildrenUnread,
    getCategoryUnread,
    getGlobalUnread,
    getLabelCounters,
)
from ttrss.feeds.ops import feed_has_icon, subscribe_to_feed
from ttrss.labels import (
    get_all_labels,
    get_article_labels,
    label_add_article,
    label_find_caption,
    label_remove_article,
)
from ttrss.models.archived_feed import TtRssArchivedFeed
from ttrss.models.category import TtRssFeedCategory
from ttrss.models.entry import TtRssEntry
from ttrss.models.feed import TtRssFeed
from ttrss.models.label import TtRssLabel2
from ttrss.models.user import TtRssUser
from ttrss.models.user_entry import TtRssUserEntry
from ttrss.plugins.manager import get_plugin_manager
from ttrss.extensions import limiter
from ttrss.prefs.ops import get_user_pref
from ttrss.utils.feeds import feed_to_label_id, label_to_feed_id

# Source: ttrss/api/index.php:1 (entry point), ttrss/classes/api.php:API (handler class)
api_bp = Blueprint("api", __name__, url_prefix="/api")

# Source: ttrss/api/index.php — PHP API has no CSRF protection (uses session_id tokens instead).
# New: csrf.exempt is required because Flask-WTF CSRFProtect is active globally (ADR-0002),
# but the API must remain CSRF-free for compatibility with PHP API clients.
csrf.exempt(api_bp)


def _seq() -> int:
    """
    Extract seq from request data — echoed in every response (CG-04, R08).
    Source: ttrss/classes/api.php:API.__construct (line 26: $this->seq = (int) $_REQUEST['seq'])
    Reads from JSON body first, then query params (matching PHP $_REQUEST merge order).
    """
    data = request.get_json(silent=True) or {}
    return int(data.get("seq", request.args.get("seq", 0)))


def _ok(seq: int, content: dict):
    """
    Success envelope. Source: ttrss/classes/api.php:API.wrap (lines 33-37, STATUS_OK=0).
    """
    return jsonify({"seq": seq, "status": 0, "content": content})


def _err(seq: int, error: str):
    """
    Error envelope. Source: ttrss/classes/api.php:API.wrap (lines 33-37, STATUS_ERR=1).
    """
    return jsonify({"seq": seq, "status": 1, "content": {"error": error}})


def _pref_is_true(val: Optional[str]) -> bool:
    """Convert a raw pref string to bool. Inferred from: ttrss/include/db-prefs.php type coercion."""
    if val is None:
        return False
    return val.lower() not in {"false", "0", ""}


# Source: ttrss/api/index.php (method dispatch via $handler->$method())
#         + ttrss/classes/api.php:API (method routing)
# New: 60 requests per minute per IP — no PHP equivalent (spec/06-security.md: API abuse prevention).
# Disabled in tests via RATELIMIT_ENABLED=False (conftest.py).
@api_bp.route("/", methods=["GET", "POST"])
@limiter.limit("60 per minute")
def dispatch():
    """Single dispatch endpoint for all API operations (spec/03-api-routing.md)."""
    data = request.get_json(silent=True) or {}
    op = data.get("op") or request.args.get("op", "")
    seq = _seq()

    # PHP dispatcher calls strtolower($method) before all routing and guards.
    # Source: ttrss/classes/api.php — index() calls strtolower($method) before before() and dispatch.
    # op_lower is used for all routing comparisons to replicate PHP case-insensitive dispatch.
    op_lower = op.lower()

    # Guard 1: Source: ttrss/classes/api.php:16-20
    # PHP: if (!$_SESSION["uid"]) { if ($method != "login" && $method != "isloggedin") → NOT_LOGGED_IN }
    # Note: PHP lowercases $method via strtolower(); op_lower replicates that.
    if not current_user.is_authenticated and op_lower not in {"login", "isloggedin"}:
        return _err(seq, "NOT_LOGGED_IN")

    # Guard 2: Source: ttrss/classes/api.php:21-25
    # PHP: if ($_SESSION["uid"] && !get_pref("ENABLE_API_ACCESS")) { if ($method != "logout") → API_DISABLED }
    # Note: getVersion and getApiLevel are NOT exempt — only "logout" is.
    if current_user.is_authenticated and op_lower != "logout":
        api_access = get_user_pref(current_user.id, "ENABLE_API_ACCESS")
        if not _pref_is_true(api_access):
            return _err(seq, "API_DISABLED")

    if op_lower == "login":
        return _handle_login(data, seq)
    if op_lower == "logout":
        # Source: ttrss/classes/api.php:API.logout (lines 89-92)
        logout_user()
        session.clear()
        return _ok(seq, {"status": "OK"})
    if op_lower == "isloggedin":
        # Source: ttrss/classes/api.php:API.isLoggedIn (lines 94-95)
        # PHP returns {"status":true/false} as boolean — preserved here.
        return _ok(seq, {"status": current_user.is_authenticated})
    if op_lower == "getversion":
        # Source: ttrss/classes/api.php:API.getVersion (lines 39-42)
        # Source: ttrss/include/version.php:get_version (VERSION_STATIC='1.12', git-hash suffix)
        # Adapted: PHP appends 7-char git hash from .git/refs/heads/master; Python uses
        #          static "1.12.0-python" sentinel — no git runtime lookup in the API process.
        return _ok(seq, {"version": "1.12.0-python"})
    if op_lower == "getapilevel":
        # Source: ttrss/classes/api.php:API.getApiLevel (lines 44-47)
        return _ok(seq, {"level": 8})

    # -----------------------------------------------------------------------
    # Batch 1: counter-only ops (no write side-effects)
    # -----------------------------------------------------------------------

    if op_lower == "getunread":
        return _handle_getUnread(data, seq)
    if op_lower == "getcounters":
        return _handle_getCounters(seq)
    if op_lower == "getpref":
        return _handle_getPref(data, seq)
    if op_lower == "getconfig":
        return _handle_getConfig(seq)
    if op_lower == "getlabels":
        return _handle_getLabels(data, seq)

    # -----------------------------------------------------------------------
    # Batch 2: query ops with category/feed deps
    # -----------------------------------------------------------------------

    if op_lower == "getcategories":
        return _handle_getCategories(data, seq)
    if op_lower == "getfeeds":
        return _handle_getFeeds(data, seq)
    if op_lower == "getarticle":
        return _handle_getArticle(data, seq)

    # -----------------------------------------------------------------------
    # Batch 3: write ops (side-effects on user entries)
    # -----------------------------------------------------------------------

    if op_lower == "updatearticle":
        return _handle_updateArticle(data, seq)
    if op_lower == "catchupfeed":
        return _handle_catchupFeed(data, seq)
    if op_lower == "setarticlelabel":
        return _handle_setArticleLabel(data, seq)
    if op_lower == "updatefeed":
        return _handle_updateFeed(data, seq)

    # -----------------------------------------------------------------------
    # Batch 4: complex chained ops
    # -----------------------------------------------------------------------

    if op_lower == "getheadlines":
        return _handle_getHeadlines(data, seq)
    if op_lower == "subscribetofeed":
        return _handle_subscribeToFeed(data, seq)
    if op_lower == "unsubscribefeed":
        return _handle_unsubscribeFeed(data, seq)
    if op_lower == "sharetopublished":
        return _handle_shareToPublished(data, seq)

    # -----------------------------------------------------------------------
    # Batch 5: getFeedTree (standalone)
    # -----------------------------------------------------------------------

    if op_lower == "getfeedtree":
        return _handle_getFeedTree(data, seq)

    # Source: ttrss/classes/api.php:API.index (line 488 — UNKNOWN_METHOD error with method echo)
    return jsonify({"seq": seq, "status": 1, "content": {"error": "UNKNOWN_METHOD", "method": op}})


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


def _handle_login(data: dict, seq: int):
    """
    Authenticate user and create session.
    Upgrades legacy MODE2/SHA1X/SHA1 hash to argon2id on successful login (ADR-0008, R10).
    Session stores user_id only — never pwd_hash (ADR-0007, R07, AR05).
    Response includes session_id and api_level=8 (R08, spec/03-api-routing.md).

    Source: ttrss/classes/api.php:API.login (lines 49-88)
            + ttrss/include/functions.php:authenticate_user (lines 706-755)
            + ttrss/plugins/auth_internal/init.php:Auth_Internal::authenticate (lines 19-140)
    """
    import base64

    username = data.get("user", "")
    password = data.get("password", "")

    # Source: ttrss/classes/api.php:API.login (line 55)
    # PHP also tries base64-decoded password as fallback (legacy Android/mobile client compat).
    try:
        password_b64 = base64.b64decode(password).decode("utf-8", errors="replace")
    except Exception:
        password_b64 = ""

    # Source: ttrss/plugins/auth_internal/init.php:authenticate — SELECT login, pwd_hash, salt
    user: TtRssUser | None = db.session.scalars(
        db.select(TtRssUser).where(TtRssUser.login == username)
    ).first()

    # Source: ttrss/classes/api.php:API.login (lines 60-70 — uid lookup, return LOGIN_ERROR if not found)
    if not user:
        return _err(seq, "LOGIN_ERROR")

    # Source: ttrss/classes/api.php:API.login (lines 72-85)
    # PHP checks ENABLE_API_ACCESS BEFORE calling authenticate_user — replicated here.
    # This means a user with API disabled gets API_DISABLED without a password attempt.
    api_access = get_user_pref(user.id, "ENABLE_API_ACCESS")
    if not _pref_is_true(api_access):
        # Source: ttrss/classes/api.php:API.login (line 84 — "API_DISABLED")
        return _err(seq, "API_DISABLED")

    # Source: ttrss/classes/api.php:API.login (lines 73-82)
    # Try raw password first, then base64-decoded fallback (PHP tries both).
    password_ok = verify_password(
        user.pwd_hash,
        password,
        salt=user.salt or "",
        login=user.login,
    )
    if not password_ok and password_b64:
        # Source: ttrss/classes/api.php:API.login (lines 76-78 — base64 fallback)
        password_ok = verify_password(
            user.pwd_hash,
            password_b64,
            salt=user.salt or "",
            login=user.login,
        )

    if not password_ok:
        # Source: ttrss/classes/api.php:API.login (line 80 — user_error for failed attempt)
        logger.warning("Failed login attempt for user %r", login)
        return _err(seq, "LOGIN_ERROR")

    # Upgrade legacy hash to argon2id on first successful login (ADR-0008)
    # Source: ttrss/plugins/auth_internal/init.php:authenticate (lines 91-101 — MODE2 upgrade logic)
    if needs_upgrade(user.pwd_hash):
        user.pwd_hash = hash_password(password)
        user.salt = ""  # argon2id embeds its own salt; ttrss_users.salt no longer needed
        # Note: salt column is NOT NULL default '' in PHP schema (line 49) — use "" not None
        db.session.commit()

    # Source: ttrss/include/functions.php:authenticate_user (lines 724-739 — session setup)
    login_user(user)
    # AR05: store only user_id — pwd_hash MUST NOT be stored in session
    # (contrast with PHP: $_SESSION["pwd_hash"] = ... — deliberately NOT replicated)
    session["user_id"] = user.id

    return _ok(
        seq,
        {
            "session_id": getattr(session, "sid", ""),  # Flask-Session sets .sid
            "api_level": 8,
        },
    )


# ---------------------------------------------------------------------------
# Batch 1 handlers
# ---------------------------------------------------------------------------


def _handle_getUnread(data: dict, seq: int):
    """
    Return unread count for a feed/category or globally.

    Source: ttrss/classes/api.php:API.getUnread (lines 98-107)
    feed_id + is_cat=true  → getCategoryUnread(feed_id)
    feed_id + is_cat=false → direct user_entries count (real feeds)
    no feed_id             → getGlobalUnread()
    """
    feed_id_raw = data.get("feed_id") or request.args.get("feed_id", "")
    is_cat = _truthy(data.get("is_cat") or request.args.get("is_cat", ""))

    if feed_id_raw:
        feed_id = int(feed_id_raw)
        if is_cat:
            # Source: ttrss/include/functions.php:getCategoryUnread (lines 1330-1382)
            count = getCategoryUnread(db.session, feed_id, current_user.id)
        else:
            # Adapted: PHP getFeedUnread(feed_id, false) → getFeedArticles → ttrss_counters_cache
            # (ttrss/include/functions.php:getFeedUnread lines 1384-1386 → getFeedArticles lines 1401-1493)
            # Python uses a live ttrss_user_entries count instead of the counters cache, which is
            # more accurate for single-feed queries (cache can lag until next Celery ccache_update).
            # Note: negative feed_id with is_cat=false is unusual API usage; clients should pass is_cat=true
            # for virtual/label feeds. A negative feed_id here produces an empty result (no real feed row).
            count = db.session.execute(
                select(func.count(TtRssUserEntry.int_id))
                .where(TtRssUserEntry.feed_id == feed_id)
                .where(TtRssUserEntry.owner_uid == current_user.id)
                .where(TtRssUserEntry.unread.is_(True))
            ).scalar() or 0
    else:
        # Source: ttrss/include/functions.php:getGlobalUnread (lines 1495-1507)
        count = getGlobalUnread(db.session, current_user.id)

    return _ok(seq, {"unread": count})


def _handle_getCounters(seq: int):
    """
    Return all counter types for the current user.

    Source: ttrss/classes/api.php:API.getCounters (line 111)
    icons_dir from app config for feed icon detection.
    """
    # Source: ttrss/include/functions.php:getAllCounters (lines 1239-1248)
    icons_dir: str = current_app.config.get("ICONS_DIR", "")
    counters = getAllCounters(db.session, current_user.id, icons_dir=icons_dir)
    return _ok(seq, counters)


def _handle_getPref(data: dict, seq: int):
    """
    Return a single preference value for the current user.

    Source: ttrss/classes/api.php:API.getPref (lines 406-410)
    """
    pref_name: str = (
        data.get("pref_name") or request.args.get("pref_name", "")
    )
    # Source: ttrss/include/db-prefs.php:get_pref — returns raw string value
    value = get_user_pref(current_user.id, pref_name)
    return _ok(seq, {"value": value})


def _handle_getConfig(seq: int):
    """
    Return server configuration info (icons paths, daemon status, feed count).

    Source: ttrss/classes/api.php:API.getConfig (lines 370-385)
    daemon_is_running: PHP checks file_is_locked("update_daemon.lock");
    Python uses Celery inspect().ping() (ADR-0011 — Celery replaces daemon lock files).
    """
    icons_dir: str = current_app.config.get("ICONS_DIR", "")
    icons_url: str = current_app.config.get("ICONS_URL", "")

    # Source: ttrss/classes/api.php:375 — file_is_locked("update_daemon.lock")
    # Adapted (ADR-0011): Celery inspect replaces lock-file daemon check
    daemon_is_running = False
    try:
        from ttrss.celery_app import celery_app  # lazy import: avoids circular at module level

        inspector = celery_app.control.inspect(timeout=0.5)
        pong = inspector.ping()
        daemon_is_running = bool(pong)
    except Exception:
        # Celery broker unreachable or inspect failed — treat as not running
        daemon_is_running = False

    # Source: ttrss/classes/api.php:377-382 — SELECT COUNT(*) FROM ttrss_feeds WHERE owner_uid
    num_feeds: int = db.session.execute(
        select(func.count(TtRssFeed.id))
        .where(TtRssFeed.owner_uid == current_user.id)
    ).scalar() or 0

    return _ok(seq, {
        "icons_dir": icons_dir,
        "icons_url": icons_url,
        "daemon_is_running": daemon_is_running,
        "num_feeds": int(num_feeds),
    })


def _handle_getLabels(data: dict, seq: int):
    """
    Return all labels for the current user, with optional "checked" state for an article.

    Source: ttrss/classes/api.php:API.getLabels (lines 412-447)
    article_id truthy → get_article_labels() to determine checked state per label.
    article_id falsy  → all labels unchecked.
    """
    article_id_raw = data.get("article_id") or request.args.get("article_id", "")
    article_id: int = int(article_id_raw) if article_id_raw else 0

    # Source: api.php:423-426 — if ($article_id) get_article_labels($article_id)
    if article_id:
        article_label_entries = get_article_labels(db.session, article_id, current_user.id)
        # article_label_entries: [[virtual_feed_id, caption, fg_color, bg_color], ...]
        # Convert virtual feed ids back to DB label ids for the checked comparison
        # Source: api.php:431-435 — if (feed_to_label_id($al[0]) == $line['id'])
        checked_label_ids: set[int] = {
            feed_to_label_id(al[0]) for al in article_label_entries if al
        }
    else:
        checked_label_ids = set()

    # Source: api.php:419-422 — SELECT id, caption, fg_color, bg_color FROM ttrss_labels2
    #          WHERE owner_uid = ... ORDER BY caption
    label_rows = db.session.execute(
        select(
            TtRssLabel2.id,
            TtRssLabel2.caption,
            TtRssLabel2.fg_color,
            TtRssLabel2.bg_color,
        )
        .where(TtRssLabel2.owner_uid == current_user.id)
        .order_by(TtRssLabel2.caption)
    ).all()

    rv = []
    for row in label_rows:
        # Source: api.php:439 — "id" => (int)label_to_feed_id($line['id'])
        rv.append({
            "id": label_to_feed_id(row.id),
            "caption": row.caption,
            "fg_color": row.fg_color or "",
            "bg_color": row.bg_color or "",
            "checked": row.id in checked_label_ids,
        })

    return _ok(seq, rv)


# ---------------------------------------------------------------------------
# Batch 2 handlers
# ---------------------------------------------------------------------------


def _handle_getCategories(data: dict, seq: int):
    """
    Return category list with unread counts for the current user.

    Source: ttrss/classes/api.php:API.getCategories (lines 126-181)
    enable_nested=true → top-level cats only (parent_cat IS NULL), unread sums children.
    Virtual cats [-2,-1,0] appended after real cats, titles from getCategoryTitle().
    """
    unread_only = _truthy(data.get("unread_only") or request.args.get("unread_only", ""))
    enable_nested = _truthy(data.get("enable_nested") or request.args.get("enable_nested", ""))
    include_empty = _truthy(data.get("include_empty") or request.args.get("include_empty", ""))

    # Source: api.php:133-136 — enable_nested → parent_cat IS NULL, else no filter
    from sqlalchemy.orm import aliased

    c2 = aliased(TtRssFeedCategory, flat=True)
    feed_count_subq = (
        select(func.count(TtRssFeed.id))
        .where(TtRssFeed.cat_id == TtRssFeedCategory.id)
        .correlate(TtRssFeedCategory)
        .scalar_subquery()
    )
    child_count_subq = (
        select(func.count(c2.id))
        .where(c2.parent_cat == TtRssFeedCategory.id)
        .correlate(TtRssFeedCategory)
        .scalar_subquery()
    )

    q = (
        select(
            TtRssFeedCategory.id,
            TtRssFeedCategory.title,
            TtRssFeedCategory.order_id,
            feed_count_subq.label("num_feeds"),
            child_count_subq.label("num_cats"),
        )
        .where(TtRssFeedCategory.owner_uid == current_user.id)
    )
    if enable_nested:
        q = q.where(TtRssFeedCategory.parent_cat.is_(None))

    rows = db.session.execute(q).all()
    cats = []

    for row in rows:
        # Source: api.php:152 — if ($include_empty || num_feeds > 0 || num_cats > 0)
        if include_empty or (row.num_feeds or 0) > 0 or (row.num_cats or 0) > 0:
            # Source: api.php:153 — getFeedUnread($line["id"], true) [is_cat=true → ccache path]
            # Adapted: Python uses getCategoryUnread (live COUNT on ttrss_user_entries) instead of
            # ccache-backed getFeedUnread. More accurate (ccache can lag between Celery ccache_update
            # runs). Same live-count adaptation used throughout getUnread / getFeeds (ADR-0006).
            unread = getCategoryUnread(db.session, row.id, current_user.id)
            if enable_nested:
                # Source: api.php:155-157 — $unread += getCategoryChildrenUnread($line["id"])
                unread += getCategoryChildrenUnread(db.session, row.id, current_user.id)
            if unread or not unread_only:
                cats.append({
                    "id": row.id,
                    "title": row.title,
                    "unread": unread,
                    "order_id": int(row.order_id or 0),
                })

    # Source: api.php:168-178 — virtual cats [-2, -1, 0]
    for cat_id in [-2, -1, 0]:
        if include_empty or not _is_virtual_cat_empty(cat_id):
            # Source: api.php:170 — getFeedUnread($cat_id, true) [is_cat=true → virtual cat path]
            # Adapted: Python uses getCategoryUnread (live query) — same rationale as real cats above.
            unread = getCategoryUnread(db.session, cat_id, current_user.id)
            if unread or not unread_only:
                cats.append({
                    "id": cat_id,
                    "title": getCategoryTitle(db.session, cat_id),
                    "unread": unread,
                })

    return _ok(seq, cats)


def _is_virtual_cat_empty(cat_id: int) -> bool:
    """Return True if virtual category has no feeds/articles.

    Source: ttrss/classes/api.php:isCategoryEmpty (lines 770-787)
    PHP comment: "only works for labels or uncategorized for the time being".
    cat_id == -2: empty if no labels exist for owner.
    cat_id == 0:  empty if no uncategorized feeds (cat_id IS NULL) exist.
    cat_id == -1: PHP always returns false (Special is never considered empty).
    Any other id: PHP always returns false.
    """
    # For -2 (Labels): check if any labels exist
    # Source: api.php:772-776 — SELECT COUNT(*) FROM ttrss_labels2 WHERE owner_uid
    if cat_id == -2:
        count = db.session.execute(
            select(func.count(TtRssLabel2.id))
            .where(TtRssLabel2.owner_uid == current_user.id)
        ).scalar() or 0
        return count == 0
    # For 0 (Uncategorized): check for feeds with cat_id IS NULL
    # Source: api.php:778-782 — SELECT COUNT(*) FROM ttrss_feeds WHERE cat_id IS NULL AND owner_uid
    if cat_id == 0:
        count = db.session.execute(
            select(func.count(TtRssFeed.id))
            .where(TtRssFeed.cat_id.is_(None))
            .where(TtRssFeed.owner_uid == current_user.id)
        ).scalar() or 0
        return count == 0
    # For -1 (Special) and any other id: PHP returns false (not empty).
    # Source: api.php:786 — default return false
    return False


def _handle_getFeeds(data: dict, seq: int):
    """
    Return feed list for a category (or all feeds) with unread counts.

    Source: ttrss/classes/api.php:API.getFeeds + api_get_feeds (lines 114-124, 504-629)
    cat_id: -4=all, -3=all-real, -2=labels, -1=virtual, 0=uncategorized, N=specific cat.
    Note: N+1 query for real feeds (getFeedUnread per row) — accepted PHP-parity trade-off (AR5).
    """
    cat_id_raw = data.get("cat_id", request.args.get("cat_id", ""))
    cat_id: int = int(cat_id_raw) if cat_id_raw != "" else 0
    unread_only = _truthy(data.get("unread_only") or request.args.get("unread_only", ""))
    limit: int = int(data.get("limit") or request.args.get("limit", 0) or 0)
    offset: int = int(data.get("offset") or request.args.get("offset", 0) or 0)
    include_nested = _truthy(data.get("include_nested") or request.args.get("include_nested", ""))

    icons_dir: str = current_app.config.get("ICONS_DIR", "")
    feeds = []

    # Source: api.php:510-528 — Labels section (cat_id == -4 or -2)
    if cat_id in (-4, -2):
        label_counters = getLabelCounters(db.session, current_user.id, descriptions=True)
        for cv in label_counters:
            unread = cv["counter"]
            if unread or not unread_only:
                feeds.append({
                    "id": int(cv["id"]),
                    "title": cv.get("description", ""),
                    "unread": unread,
                    "cat_id": -2,
                })

    # Source: api.php:533-549 — Virtual feeds section (cat_id == -4 or -1)
    if cat_id in (-4, -1):
        for i in (-1, -2, -3, -4, -6, 0):
            # Source: ttrss/include/functions.php:getFeedUnread (lines 1384-1386) — via _count_feed_articles
            unread = _count_feed_articles(db.session, i, current_user.id, unread_only=True)
            if unread or not unread_only:
                title = getFeedTitle(db.session, i)
                feeds.append({
                    "id": i,
                    "title": title,
                    "unread": unread,
                    "cat_id": -1,
                })

    # Source: api.php:554-573 — Child categories section (include_nested AND cat_id truthy)
    # Note: cat_id=0 is falsy in PHP — no child cats for Uncategorized (R13)
    if include_nested and cat_id:
        child_cat_rows = db.session.execute(
            select(TtRssFeedCategory.id, TtRssFeedCategory.title)
            .where(TtRssFeedCategory.parent_cat == cat_id)
            .where(TtRssFeedCategory.owner_uid == current_user.id)
            .order_by(TtRssFeedCategory.id, TtRssFeedCategory.title)
        ).all()
        for row in child_cat_rows:
            unread = (
                getCategoryUnread(db.session, row.id, current_user.id)
                + getCategoryChildrenUnread(db.session, row.id, current_user.id)
            )
            if unread or not unread_only:
                feeds.append({
                    "id": int(row.id),
                    "title": row.title,
                    "unread": unread,
                    "is_cat": True,
                })

    # Source: api.php:576-626 — Real feeds section
    real_q = (
        select(
            TtRssFeed.id,
            TtRssFeed.feed_url,
            TtRssFeed.cat_id,
            TtRssFeed.title,
            TtRssFeed.order_id,
            TtRssFeed.last_updated,
        )
        .where(TtRssFeed.owner_uid == current_user.id)
        .order_by(TtRssFeed.cat_id, TtRssFeed.title)
    )

    if cat_id in (-4, -3):
        # All feeds (no category filter)
        pass
    elif cat_id:
        # Source: api.php:592-593 — if ($cat_id) cat_id = '$cat_id'
        real_q = real_q.where(TtRssFeed.cat_id == cat_id)
    else:
        # Source: api.php:594-595 — else cat_id IS NULL (Uncategorized)
        real_q = real_q.where(TtRssFeed.cat_id.is_(None))

    if limit:
        real_q = real_q.limit(limit).offset(offset)

    real_rows = db.session.execute(real_q).all()
    for row in real_rows:
        # Source: api.php:607 — getFeedUnread($line["id"]) [N+1: accepted PHP-parity trade-off, AR5]
        unread = _count_feed_articles(db.session, row.id, current_user.id, unread_only=True)
        has_icon = feed_has_icon(row.id, icons_dir=icons_dir)
        if unread or not unread_only:
            feeds.append({
                "feed_url": row.feed_url,
                "title": row.title,
                "id": int(row.id),
                "unread": int(unread),
                "has_icon": has_icon,
                "cat_id": int(row.cat_id) if row.cat_id is not None else 0,
                "last_updated": int(row.last_updated.timestamp()) if row.last_updated else 0,
                "order_id": int(row.order_id or 0),
            })

    return _ok(seq, feeds)


def _handle_getArticle(data: dict, seq: int):
    """
    Return article(s) by ID with enclosures, labels, and plugin transforms.

    Source: ttrss/classes/api.php:API.getArticle (lines 310-368)
    article_id: comma-separated list of integer IDs.
    HOOK_RENDER_ARTICLE_API fires per article in the loop (api.php:354).
    """
    article_id_raw: str = (
        str(data.get("article_id") or request.args.get("article_id", "")).strip()
    )
    if not article_id_raw:
        # Source: api.php:365-367 — INCORRECT_USAGE if no article_id
        return _err(seq, "INCORRECT_USAGE")

    # Source: api.php:312 — array_filter(..., is_numeric) — keep only integer IDs
    article_ids = [
        int(x.strip()) for x in article_id_raw.split(",") if x.strip().lstrip("-").isdigit()
    ]
    if not article_ids:
        return _err(seq, "INCORRECT_USAGE")

    # Source: api.php:316-322 — JOIN ttrss_entries + ttrss_user_entries
    #         api.php:319    — (SELECT title FROM ttrss_feeds WHERE id = feed_id) AS feed_title
    # Adapted: feed_title retrieved via LEFT OUTER JOIN on ttrss_feeds in the same query
    # (PHP uses a correlated subquery in the SELECT list; SQLAlchemy outerjoin is equivalent
    # and avoids an N+1 per-article lookup — see C10 in adversarial review 2026-04-04).
    rows = db.session.execute(
        select(
            TtRssEntry.id,
            TtRssEntry.title,
            TtRssEntry.link,
            TtRssEntry.content,
            TtRssEntry.author,
            TtRssEntry.updated,
            TtRssEntry.comments,
            TtRssEntry.lang,
            TtRssUserEntry.feed_id,
            TtRssUserEntry.int_id,
            TtRssUserEntry.marked,
            TtRssUserEntry.unread,
            TtRssUserEntry.published,
            TtRssUserEntry.score,
            TtRssUserEntry.note,
            TtRssFeed.title.label("feed_title"),
        )
        .join(TtRssUserEntry, TtRssUserEntry.ref_id == TtRssEntry.id)
        .outerjoin(TtRssFeed, TtRssFeed.id == TtRssUserEntry.feed_id)
        .where(TtRssEntry.id.in_(article_ids))
        .where(TtRssUserEntry.owner_uid == current_user.id)
    ).all()

    articles = []
    pm = get_plugin_manager()

    for row in rows:
        # Source: api.php:332-333 — get_article_enclosures + get_article_labels
        attachments = get_article_enclosures(db.session, row.id)
        labels = get_article_labels(db.session, row.id, current_user.id)

        # Source: api.php:319 — feed_title from correlated subquery; now from outerjoin above
        feed_title = row.feed_title or ""

        article = {
            "id": row.id,
            "title": row.title,
            "link": row.link,
            "labels": labels,
            "unread": bool(row.unread),
            "marked": bool(row.marked),
            "published": bool(row.published),
            "comments": row.comments or "",
            "author": row.author or "",
            # Source: api.php:316-318 — SUBSTRING_FOR_DATE(updated,1,16) truncates to YYYY-MM-DD HH:MM
            #         api.php:344 — (int)strtotime($line["updated"]) — Unix timestamp
            # PHP truncates seconds before converting to timestamp (SUBSTRING to 16 chars strips :SS).
            # Python replicates by zeroing seconds+microseconds before calling .timestamp().
            "updated": int(row.updated.replace(second=0, microsecond=0).timestamp()) if row.updated else 0,
            "content": row.content or "",
            "feed_id": row.feed_id,
            "attachments": attachments,
            "score": int(row.score or 0),
            "feed_title": feed_title,
            "note": row.note or "",
            "lang": row.lang or "",
        }

        # Source: api.php:354-356 — HOOK_RENDER_ARTICLE_API fires per article
        for result in pm.hook.hook_render_article_api(headline_row={"article": article}):
            if result and isinstance(result, dict) and "article" in result:
                article = result["article"]

        articles.append(article)

    return _ok(seq, articles)


# ---------------------------------------------------------------------------
# Batch 3 handlers
# ---------------------------------------------------------------------------


def _handle_updateArticle(data: dict, seq: int):
    """
    Update boolean flags or note for a set of articles.

    Source: ttrss/classes/api.php:API.updateArticle (lines 233-308)
    field: 0=marked, 1=published, 2=unread, 3=note
    mode:  0=false, 1=true, 2=toggle
    data["data"]: used only when field==3 (note text; PHP does NOT strip_tags — Python strips
    HTML as a security improvement to prevent stored XSS in note field)
    ccache_update fires per distinct feed_id ONLY when field==2 (unread) AND num_updated>0.
    """
    from datetime import datetime, timezone

    from sqlalchemy import case, update as sa_update

    article_id_raw: str = str(
        data.get("article_ids") or request.args.get("article_ids", "")
    ).strip()
    if not article_id_raw:
        return _err(seq, "INCORRECT_USAGE")

    # Source: api.php:236 — array_filter(..., is_numeric)
    article_ids = [
        int(x.strip()) for x in article_id_raw.split(",") if x.strip().lstrip("-").isdigit()
    ]
    if not article_ids:
        return _err(seq, "INCORRECT_USAGE")

    mode_raw = data.get("mode") or request.args.get("mode", 0)
    field_raw: int = int(data.get("field") or request.args.get("field", 0))
    mode: int = int(mode_raw)

    # Source: api.php:248-259 — FIELD_MAP; note field uses article["note"] text, mode ignored
    FIELD_MAP = {
        0: ("marked", "last_marked"),
        1: ("published", "last_published"),
        2: ("unread", "last_read"),
        3: ("note", None),
    }
    if field_raw not in FIELD_MAP:
        return _err(seq, "INCORRECT_USAGE")

    col_name, ts_col_name = FIELD_MAP[field_raw]
    now = datetime.now(tz=timezone.utc)

    if field_raw == 3:
        # Source: api.php:271 — note content from request param "data"; PHP stores raw (no strip_tags)
        # New: Python strips HTML tags from note to prevent stored XSS (improvement over PHP)
        import re as _re

        _raw_note = str(data.get("data") or request.args.get("data", ""))
        note_text: str = _re.sub(r"<[^>]*>", "", _raw_note)
        stmt = (
            sa_update(TtRssUserEntry)
            .where(TtRssUserEntry.ref_id.in_(article_ids))
            .where(TtRssUserEntry.owner_uid == current_user.id)
            .values(note=note_text)
        )
    elif mode == 0:
        # Source: api.php:265 — mode==0 → false
        values = {col_name: False}
        if ts_col_name:
            values[ts_col_name] = now
        stmt = (
            sa_update(TtRssUserEntry)
            .where(TtRssUserEntry.ref_id.in_(article_ids))
            .where(TtRssUserEntry.owner_uid == current_user.id)
            .values(**values)
        )
    elif mode == 1:
        # Source: api.php:263 — mode==1 → true
        values = {col_name: True}
        if ts_col_name:
            values[ts_col_name] = now
        stmt = (
            sa_update(TtRssUserEntry)
            .where(TtRssUserEntry.ref_id.in_(article_ids))
            .where(TtRssUserEntry.owner_uid == current_user.id)
            .values(**values)
        )
    else:
        # Source: api.php:267-273 — mode==2 → toggle per article
        col = getattr(TtRssUserEntry, col_name)
        values = {col_name: case((col == False, True), else_=False)}  # noqa: E712
        if ts_col_name:
            values[ts_col_name] = now
        stmt = (
            sa_update(TtRssUserEntry)
            .where(TtRssUserEntry.ref_id.in_(article_ids))
            .where(TtRssUserEntry.owner_uid == current_user.id)
            .values(**values)
        )

    result = db.session.execute(stmt)
    num_updated: int = result.rowcount
    db.session.commit()

    # Source: api.php:285-305 — ccache_update per distinct feed_id ONLY when field==2 AND num_updated>0
    if field_raw == 2 and num_updated > 0:
        affected_feed_rows = db.session.execute(
            select(TtRssUserEntry.feed_id)
            .where(TtRssUserEntry.ref_id.in_(article_ids))
            .where(TtRssUserEntry.owner_uid == current_user.id)
            .distinct()
        ).all()
        for row in affected_feed_rows:
            if row.feed_id is not None:
                ccache_update(db.session, row.feed_id, current_user.id)

    return _ok(seq, {"status": "OK", "updated": num_updated})


def _handle_catchupFeed(data: dict, seq: int):
    """
    Mark all articles in a feed (or category) as read.

    Source: ttrss/classes/api.php:API.catchupFeed (lines 369-407)
    is_cat=true → feed_id is treated as a category ID.
    """
    feed_id_raw = data.get("feed_id") or request.args.get("feed_id", "0")
    is_cat = _truthy(data.get("is_cat") or request.args.get("is_cat", ""))

    feed_id: int = int(feed_id_raw)

    # Source: ttrss/include/functions.php:catchup_feed (lines 1094-1237)
    catchup_feed(db.session, feed_id, is_cat, current_user.id)
    db.session.commit()

    return _ok(seq, {"status": "OK"})


def _handle_setArticleLabel(data: dict, seq: int):
    """
    Add or remove a label from one or more articles.

    Source: ttrss/classes/api.php:API.setArticleLabel (lines 449-477)
    label_id: virtual feed ID (e.g. -1001); assign: true=add, false=remove.
    label_add_article / label_remove_article operate by caption (Source: labels.php).
    """
    label_id_raw = data.get("label_id") or request.args.get("label_id", "0")
    label_id: int = int(label_id_raw)
    assign = _truthy(data.get("assign") or request.args.get("assign", ""))
    article_id_raw: str = str(
        data.get("article_ids") or request.args.get("article_ids", "")
    ).strip()

    article_ids = [
        int(x.strip()) for x in article_id_raw.split(",") if x.strip().lstrip("-").isdigit()
    ]
    if not article_ids:
        return _err(seq, "INCORRECT_USAGE")

    # Source: api.php:461 — label_to_feed_id($label_id) converts virtual feed ID → DB label id
    from ttrss.utils.feeds import feed_to_label_id as _feed_to_label_id

    real_label_id = _feed_to_label_id(label_id)
    # Source: api.php:462 — SELECT caption FROM ttrss_labels2 WHERE id = real_label_id AND owner_uid
    caption = label_find_caption(db.session, real_label_id, current_user.id)
    # Source: api.php:462-474 — PHP silently returns OK when label not found; no error
    if not caption:
        return _ok(seq, {"status": "OK"})

    # Source: api.php:467-473 — foreach article_id: label_add_article or label_remove_article
    for article_id in article_ids:
        if assign:
            label_add_article(db.session, article_id, caption, current_user.id)
        else:
            label_remove_article(db.session, article_id, caption, current_user.id)

    db.session.commit()
    return _ok(seq, {"status": "OK"})


def _handle_updateFeed(data: dict, seq: int):
    """
    Schedule an immediate background update for a feed the user owns.

    Source: ttrss/classes/api.php:API.updateFeed (lines 387-395)
    Adapted (ADR-0011): update_rss_feed() → update_feed.delay() (Celery task).
    Returns {"status":"OK"} regardless of whether broker is reachable (PHP parity).
    """
    feed_id_raw = data.get("feed_id") or request.args.get("feed_id", "0")
    feed_id: int = int(feed_id_raw)

    # Source: api.php:389 — ownership check before scheduling
    owner_row = db.session.execute(
        select(TtRssFeed.owner_uid).where(TtRssFeed.id == feed_id)
    ).scalar_one_or_none()

    if owner_row == current_user.id:
        # Source: api.php:392 — update_rss_feed($feed_id) → Celery .delay() (ADR-0011)
        from ttrss.tasks.feed_tasks import update_feed  # lazy import: avoids circular

        update_feed.delay(feed_id)

    return _ok(seq, {"status": "OK"})


# ---------------------------------------------------------------------------
# Batch 4 handlers
# ---------------------------------------------------------------------------


def _handle_getHeadlines(data: dict, seq: int):
    """
    Return headlines for a feed, category, or virtual feed.

    Source: ttrss/classes/api.php:API.getHeadlines (lines 542-627)
    queryFeedHeadlines returns list[Row] with full entry + user_entry fields.
    HOOK_RENDER_ARTICLE_API fires per headline row (api.php:617-621).
    Attachments included if include_attachments=true.
    """
    import re as _re

    # Source: api.php:543-545 — feed_id is required; absent/empty → INCORRECT_USAGE
    feed_id_raw = data.get("feed_id") or request.args.get("feed_id", "")
    if not feed_id_raw:
        return _err(seq, "INCORRECT_USAGE")
    feed_id: int = int(feed_id_raw)
    # Source: api.php:548 — limit=0 means "use max" (200); cap at 200 to match PHP behaviour
    _limit_raw: int = int(data.get("limit") or request.args.get("limit", 30) or 30)
    limit: int = 200 if (_limit_raw == 0 or _limit_raw >= 200) else _limit_raw
    offset: int = int(data.get("skip") or request.args.get("skip", 0) or 0)
    is_cat = _truthy(data.get("is_cat") or request.args.get("is_cat", ""))
    show_excerpt = _truthy(data.get("show_excerpt") or request.args.get("show_excerpt", ""))
    show_content = _truthy(data.get("show_content") or request.args.get("show_content", ""))
    view_mode: str = (
        data.get("view_mode") or request.args.get("view_mode", "all_articles") or "all_articles"
    )
    since_id: int = int(data.get("since_id") or request.args.get("since_id", 0) or 0)
    include_attachments = _truthy(
        data.get("include_attachments") or request.args.get("include_attachments", "")
    )
    order_by: str = data.get("order_by") or request.args.get("order_by", "") or ""
    search: str = data.get("search") or request.args.get("search", "") or ""
    search_mode: str = data.get("search_mode") or request.args.get("search_mode", "") or ""
    include_nested = _truthy(
        data.get("include_nested") or request.args.get("include_nested", "")
    )
    # Source: ttrss/classes/api.php:API.getHeadlines (line 201-202) —
    # sanitize_content defaults True; pass sanitize=false to disable
    sanitize_content = _truthy(
        data.get("sanitize", "1") or request.args.get("sanitize", "1") or "1"
    )

    from ttrss.articles.sanitize import sanitize as _sanitize

    # Source: ttrss/include/functions2.php:queryFeedHeadlines (lines 392-841)
    rows = queryFeedHeadlines(
        session=db.session,
        feed=feed_id,
        limit=limit,
        view_mode=view_mode,
        cat_view=is_cat,
        search=search,
        search_mode=search_mode,
        override_order=order_by or None,
        offset=offset,
        owner_uid=current_user.id,
        since_id=since_id,
        include_children=include_nested,
    )

    pm = get_plugin_manager()
    headlines = []

    for row in rows:
        # Source: api.php:582 — is_updated = last_read empty AND not currently unread
        # PHP: $is_updated = ($line["last_read"] == "" && !$line["unread"])
        # Means: article is read (unread=false) but last_read was cleared (= updated since read)
        is_updated = row.last_read is None and not bool(row.unread)

        # Source: api.php:591 — excerpt = first 100 chars of stripped content
        if show_excerpt:
            raw = _re.sub(r"<[^>]*>", "", row.content or "")
            excerpt = raw[:100].replace("\n", " ")
        else:
            excerpt = ""

        # Source: api.php:594-596 — tags from tag_cache, comma-separated
        tags: list[str] = [
            t.strip() for t in (row.tag_cache or "").split(",") if t.strip()
        ]

        # Source: api.php:598-600 — attachments when requested
        attachments = (
            get_article_enclosures(db.session, row.id) if include_attachments else []
        )

        # Source: api.php:602-605 — labels from get_article_labels
        labels = get_article_labels(db.session, row.id, current_user.id)

        # Source: api.php:567 — feed_title: available only when include_feed_title=True in QFH
        feed_title = getattr(row, "feed_title", "") or ""

        headline = {
            "id": row.id,
            "unread": bool(row.unread),
            "marked": bool(row.marked),
            "published": bool(row.published),
            # Source: api.php:576 — same truncation as getArticle (SUBSTRING_FOR_DATE to minute)
            "updated": (
                int(row.updated.replace(second=0, microsecond=0).timestamp())
                if row.updated
                else 0
            ),
            "is_updated": is_updated,
            "title": row.title or "",
            "link": row.link or "",
            "feed_id": row.feed_id,
            "tags": tags,
            "attachments": attachments,
            "score": int(row.score or 0),
            "feed_title": feed_title,
            "comments_count": int(row.num_comments or 0),
            "comments_link": row.comments or "",
            # Source: api.php — PHP key is always_display_attachments
            "always_display_attachments": bool(
                getattr(row, "always_display_enclosures", False)
            ),
            # Source: api.php:681-690 — sanitize_content=true calls sanitize() before returning
            "content": (
                _sanitize(
                    row.content or "",
                    owner_uid=current_user.id,
                    site_url=getattr(row, "site_url", None),
                    highlight_words=rows.search_words or None,
                    article_id=row.id,
                )
                if show_content and sanitize_content
                else (row.content or "") if show_content else ""
            ),
            "excerpt": excerpt,
            "author": row.author or "",
            "note": row.note or "",
            "lang": row.lang or "",
            "labels": labels,
        }

        # Source: api.php:617-621 — HOOK_RENDER_ARTICLE_API per headline
        for result in pm.hook.hook_render_article_api(headline_row={"article": headline}):
            if result and isinstance(result, dict) and "article" in result:
                headline = result["article"]

        headlines.append(headline)

    return _ok(seq, headlines)


def _handle_subscribeToFeed(data: dict, seq: int):
    """
    Subscribe the current user to a feed URL.

    Source: ttrss/classes/api.php:API.subscribeToFeed (lines 629-638)
    Delegates to subscribe_to_feed() (functions.php:subscribe_to_feed).
    Response wraps result dict under "status" key.
    """
    feed_url: str = data.get("feed_url") or request.args.get("feed_url", "")
    category_id: int = int(data.get("category_id") or request.args.get("category_id", 0) or 0)
    login: str = data.get("login") or request.args.get("login", "") or ""
    password: str = data.get("password") or request.args.get("password", "") or ""

    # Source: api.php:629 — feed_url is required
    if not feed_url:
        return _err(seq, "INCORRECT_USAGE")

    # Source: ttrss/include/functions.php:subscribe_to_feed (lines 1672-1754)
    result = subscribe_to_feed(
        db.session,
        feed_url,
        current_user.id,
        cat_id=category_id,
        auth_login=login,
        auth_pass=password,
    )
    db.session.commit()

    # Source: api.php:637 — return {"status": result}
    return _ok(seq, {"status": result})


def _handle_unsubscribeFeed(data: dict, seq: int):
    """
    Unsubscribe the current user from a feed, deleting all related data.

    Source: ttrss/classes/api.php:API.unsubscribeFeed (lines 640-652)
            + ttrss/include/functions.php:remove_feed (lines 1756-1810)
    Cascade order: delete orphaned ttrss_entries → ttrss_user_entries → ttrss_feeds.
    """
    from sqlalchemy import delete as sa_delete, or_, update as sa_update

    feed_id_raw = data.get("feed_id") or request.args.get("feed_id", "0")
    feed_id: int = int(feed_id_raw)

    # Source: api.php:642 — ownership check
    owner_uid = db.session.execute(
        select(TtRssFeed.owner_uid).where(TtRssFeed.id == feed_id)
    ).scalar_one_or_none()

    if owner_uid != current_user.id:
        return _err(seq, "FEED_NOT_FOUND")

    # Source: functions.php:remove_feed — archive starred articles before deletion
    # Starred (marked=true) articles are moved to ttrss_archived_feeds to prevent data loss.
    starred_entry_ids = db.session.scalars(
        select(TtRssUserEntry.ref_id)
        .where(TtRssUserEntry.feed_id == feed_id)
        .where(TtRssUserEntry.owner_uid == current_user.id)
        .where(TtRssUserEntry.marked == True)  # noqa: E712
    ).all()
    if starred_entry_ids:
        # Source: functions.php:archive_feed — TtRssArchivedFeed PK = original feed_id
        archived_feed = db.session.get(TtRssArchivedFeed, feed_id)
        if archived_feed is None:
            feed_row = db.session.get(TtRssFeed, feed_id)
            archived_feed = TtRssArchivedFeed(
                id=feed_id,  # PK is the original feed id (not serial)
                owner_uid=current_user.id,
                title=feed_row.title if feed_row else "",
                feed_url=feed_row.feed_url if feed_row else "",
                site_url=feed_row.site_url if feed_row else "",
            )
            db.session.add(archived_feed)
            db.session.flush()
        db.session.execute(
            sa_update(TtRssUserEntry)
            .where(TtRssUserEntry.ref_id.in_(starred_entry_ids))
            .where(TtRssUserEntry.owner_uid == current_user.id)
            .where(TtRssUserEntry.feed_id == feed_id)
            .values(feed_id=None, orig_feed_id=archived_feed.id)
        )

    # Source: functions.php:remove_feed — delete orphaned entries first
    # Orphaned = referenced only by this user's subscription (no other user_entry row)
    # feed_id IS NULL rows are shared/archived entries — exclude them from "still referenced"
    candidate_ids = (
        select(TtRssUserEntry.ref_id)
        .where(TtRssUserEntry.feed_id == feed_id)
        .where(TtRssUserEntry.owner_uid == current_user.id)
    )
    still_referenced = (
        select(TtRssUserEntry.ref_id)
        .where(TtRssUserEntry.feed_id.isnot(None))
        .where(
            or_(
                TtRssUserEntry.feed_id != feed_id,
                TtRssUserEntry.owner_uid != current_user.id,
            )
        )
    )
    db.session.execute(
        sa_delete(TtRssEntry)
        .where(TtRssEntry.id.in_(candidate_ids))
        .where(TtRssEntry.id.not_in(still_referenced))
    )

    # Source: functions.php:remove_feed — delete non-starred user entries for this feed
    db.session.execute(
        sa_delete(TtRssUserEntry)
        .where(TtRssUserEntry.feed_id == feed_id)
        .where(TtRssUserEntry.owner_uid == current_user.id)
    )

    # Source: functions.php:remove_feed — delete the feed record itself
    db.session.execute(
        sa_delete(TtRssFeed)
        .where(TtRssFeed.id == feed_id)
        .where(TtRssFeed.owner_uid == current_user.id)
    )
    db.session.commit()

    return _ok(seq, {"status": "OK"})


def _handle_shareToPublished(data: dict, seq: int):
    """
    Create a manually shared article in the Published virtual feed.

    Source: ttrss/classes/api.php:API::shareToPublished (lines 492-502)
    Source: ttrss/classes/article.php:share_to_published (lines 129-134, 155-159)
    guid = "SHA1:" + url (literal prefix, not computed hash — matches PHP convention).
    TtRssUserEntry.feed_id = None (NOT -2) — shared articles have no feed row (R16).
    """
    import hashlib as _hashlib
    import uuid as _uuid

    from datetime import datetime, timezone

    from sqlalchemy import update as sa_update

    import re as _re

    def _strip_tags(s: str) -> str:
        """Source: api.php:shareToPublished — strip_tags() on input before INSERT."""
        return _re.sub(r"<[^>]+>", "", s)

    title: str = _strip_tags(str(data.get("title") or request.args.get("title", "")))
    url: str = _strip_tags(str(data.get("url") or request.args.get("url", "")))
    content: str = _strip_tags(str(data.get("content") or request.args.get("content", "")))

    # Source: api.php — url is required
    if not url:
        return _err(seq, "INCORRECT_USAGE")

    # Source: article.php — title fallback to url when empty
    if not title:
        title = url

    now = datetime.now(tz=timezone.utc)

    # Source: article.php:131 — guid = "SHA1:" . sha1("ttshared:" . $url . $owner_uid)
    guid = "SHA1:" + _hashlib.sha1(
        f"ttshared:{url}{current_user.id}".encode()
    ).hexdigest()

    # Source: article.php:132-134 — INSERT INTO ttrss_entries if guid not found
    existing_id = db.session.execute(
        select(TtRssEntry.id).where(TtRssEntry.guid == guid)
    ).scalar_one_or_none()

    content_hash = _hashlib.sha1(content.encode()).hexdigest()
    if existing_id is None:
        entry = TtRssEntry(
            title=title,
            guid=guid,
            link=url,
            updated=now,
            content=content,
            content_hash=content_hash,
            date_updated=now,
            date_entered=now,
            author="",
            no_orig_date=False,
            num_comments=0,
            lang="",
        )
        db.session.add(entry)
        db.session.flush()
        entry_id: int = entry.id
    else:
        entry_id = existing_id

    # Source: article.php:155-159 — INSERT INTO ttrss_user_entries if not already present
    # feed_id = None (NOT -2) — R16 invariant: manually shared articles have no feed
    existing_ue = db.session.execute(
        select(TtRssUserEntry.int_id).where(
            TtRssUserEntry.ref_id == entry_id,
            TtRssUserEntry.owner_uid == current_user.id,
            TtRssUserEntry.feed_id.is_(None),
        )
    ).scalar_one_or_none()

    if existing_ue is None:
        user_entry = TtRssUserEntry(
            ref_id=entry_id,
            owner_uid=current_user.id,
            published=True,
            feed_id=None,
            unread=False,
            tag_cache="",
            label_cache="",
            marked=False,
            score=0,
            uuid=str(_uuid.uuid4()),
        )
        db.session.add(user_entry)
    else:
        # Source: article.php:155-159 — UPDATE existing entry content + re-publish user_entry
        db.session.execute(
            sa_update(TtRssEntry)
            .where(TtRssEntry.id == entry_id)
            .values(content=content, content_hash=content_hash, date_updated=now)
        )
        db.session.execute(
            sa_update(TtRssUserEntry)
            .where(TtRssUserEntry.int_id == existing_ue)
            .values(published=True)
        )
    db.session.commit()

    return _ok(seq, {"status": "OK"})


# ---------------------------------------------------------------------------
# Batch 5 handler
# ---------------------------------------------------------------------------


def _handle_getFeedTree(data: dict, seq: int):
    """
    Return the full feed/category tree for the current user.

    Source: ttrss/classes/api.php:API.getFeedTree (lines 722-730)
            + ttrss/classes/pref/feeds.php:Pref_Feeds::makefeedtree (lines 123-292)
    Output: {"categories": {"identifier":"id","label":"name","items":[...]}}
    IDs:    categories prefixed "CAT:{id}", feeds prefixed "FEED:{id}".
    Virtual feeds in order: [-4,-3,-1,-2,0,-6] under Special (CAT:-1).
    BFS with MAX_CATEGORY_DEPTH=20 and visited set for cycle detection (AR9).
    """
    include_empty = _truthy(
        data.get("include_empty") or request.args.get("include_empty", "")
    )
    icons_dir: str = current_app.config.get("ICONS_DIR", "")

    # ---------------------------------------------------------------------------
    # Inner helpers (closures use db.session and current_user via Flask context)
    # ---------------------------------------------------------------------------

    def _make_feed_node(feed_id: int, title: str) -> dict:
        """Source: pref/feeds.php — feed entry in tree."""
        unread = _count_feed_articles(db.session, feed_id, current_user.id, unread_only=True)
        has_icon = feed_has_icon(feed_id, icons_dir=icons_dir)
        return {
            "id": f"FEED:{feed_id}",
            "bare_id": int(feed_id),
            "name": title or "",
            "unread": int(unread),
            "auxcounter": 0,
            "type": "feed",
            "error": "",
            "icon": has_icon,
        }

    def _make_real_feed_node(row) -> dict:
        """Source: pref/feeds.php:get_category_items — real feed; PHP hardcodes unread=0 here."""
        has_icon = feed_has_icon(row.id, icons_dir=icons_dir)
        return {
            "id": f"FEED:{row.id}",
            "bare_id": int(row.id),
            "name": row.title or "",
            # Source: pref/feeds.php:get_category_items line ~85 — $feed['unread'] = 0 (hardcoded)
            "unread": 0,
            "auxcounter": 0,
            "type": "feed",
            "error": "",
            "icon": has_icon,
        }

    def _cat_node(cat_id: int, title: str, child_items: list, unread: int = -1) -> dict:
        """Source: pref/feeds.php — category node in tree.

        unread: if -1 (default), computed as sum of child unreads (correct for CAT:-2 / CAT:0).
        PHP feedlist_init_cat(-1) → uninitialized → 0; real cats hardcode unread=0.
        Pass unread=0 explicitly for CAT:-1 and real category nodes to match PHP.
        """
        effective_unread = sum(item["unread"] for item in child_items) if unread == -1 else unread
        return {
            "id": f"CAT:{cat_id}",
            "bare_id": int(cat_id),
            "name": title,
            "items": child_items,
            "unread": effective_unread,
            "auxcounter": 0,
            "child_unread": 0,
            "type": "category",
        }

    def _build_real_cat(cat_id: int, title: str, depth: int, visited: set) -> Optional[dict]:
        """Recursively build category node; BFS-safe via depth guard + visited set (AR9)."""
        # Source: pref/feeds.php:MAX_CATEGORY_DEPTH guard
        if depth >= MAX_CATEGORY_DEPTH or cat_id in visited:
            return None
        visited = visited | {cat_id}  # immutable update — each path has its own set

        child_items: list = []

        # Child categories first
        child_cats = db.session.execute(
            select(
                TtRssFeedCategory.id,
                TtRssFeedCategory.title,
                TtRssFeedCategory.order_id,
            )
            .where(TtRssFeedCategory.parent_cat == cat_id)
            .where(TtRssFeedCategory.owner_uid == current_user.id)
            .order_by(TtRssFeedCategory.order_id, TtRssFeedCategory.title)
        ).all()

        for child in child_cats:
            child_node = _build_real_cat(child.id, child.title, depth + 1, visited)
            if child_node is not None and (include_empty or child_node["items"]):
                child_items.append(child_node)

        # Feeds in this category
        feed_rows = db.session.execute(
            select(TtRssFeed.id, TtRssFeed.title, TtRssFeed.order_id)
            .where(TtRssFeed.cat_id == cat_id)
            .where(TtRssFeed.owner_uid == current_user.id)
            .order_by(TtRssFeed.order_id, TtRssFeed.title)
        ).all()

        for feed in feed_rows:
            child_items.append(_make_real_feed_node(feed))

        # Source: pref/feeds.php:get_category_items — real cat unread hardcoded to 0
        return _cat_node(cat_id, title, child_items, unread=0)

    # ---------------------------------------------------------------------------
    # Build root items
    # ---------------------------------------------------------------------------

    root_items: list = []

    # Source: pref/feeds.php — Special category (CAT:-1) contains virtual feeds
    # Virtual feeds in exact order: [-4,-3,-1,-2,0,-6] (Source: pref/feeds.php)
    virtual_items = [
        _make_feed_node(vfid, getFeedTitle(db.session, vfid))
        for vfid in [-4, -3, -1, -2, 0, -6]
    ]
    # Source: pref/feeds.php:feedlist_init_cat(-1) — unread uninitialized → 0 in PHP
    root_items.append(
        _cat_node(-1, getCategoryTitle(db.session, -1), virtual_items, unread=0)
    )

    # Source: pref/feeds.php — Labels category (CAT:-2) contains label feeds
    label_rows = db.session.execute(
        select(TtRssLabel2.id, TtRssLabel2.caption)
        .where(TtRssLabel2.owner_uid == current_user.id)
        .order_by(TtRssLabel2.caption)
    ).all()
    label_items = [
        _make_feed_node(label_to_feed_id(lr.id), lr.caption)
        for lr in label_rows
    ]
    if include_empty or label_items:
        root_items.append(
            _cat_node(-2, getCategoryTitle(db.session, -2), label_items)
        )

    # Source: pref/feeds.php — real categories (root: parent_cat IS NULL)
    root_cat_rows = db.session.execute(
        select(
            TtRssFeedCategory.id,
            TtRssFeedCategory.title,
            TtRssFeedCategory.order_id,
        )
        .where(TtRssFeedCategory.owner_uid == current_user.id)
        .where(TtRssFeedCategory.parent_cat.is_(None))
        .order_by(TtRssFeedCategory.order_id, TtRssFeedCategory.title)
    ).all()

    for rc in root_cat_rows:
        cat_node = _build_real_cat(rc.id, rc.title, depth=0, visited=set())
        if cat_node is not None and (include_empty or cat_node["items"]):
            root_items.append(cat_node)

    # Source: pref/feeds.php — Uncategorized (CAT:0): feeds with cat_id IS NULL
    uncat_rows = db.session.execute(
        select(TtRssFeed.id, TtRssFeed.title, TtRssFeed.order_id)
        .where(TtRssFeed.cat_id.is_(None))
        .where(TtRssFeed.owner_uid == current_user.id)
        .order_by(TtRssFeed.order_id, TtRssFeed.title)
    ).all()
    uncat_items = [_make_real_feed_node(r) for r in uncat_rows]

    if include_empty or uncat_items:
        root_items.append(
            _cat_node(0, getCategoryTitle(db.session, 0), uncat_items)
        )

    # Source: api.php:728 — return {"categories": makefeedtree()}
    return _ok(seq, {
        "categories": {
            "identifier": "id",
            "label": "name",
            "items": root_items,
        }
    })


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _truthy(val) -> bool:
    """Convert API string/bool param to Python bool.

    Inferred from: ttrss/include/db-prefs.php:sql_bool_to_bool and PHP truthy semantics.
    "true", "1", True → True; "false", "0", "", None, False → False.
    """
    if isinstance(val, bool):
        return val
    if isinstance(val, int):
        return val != 0
    if isinstance(val, str):
        return val.lower() not in {"false", "0", ""}
    return False
