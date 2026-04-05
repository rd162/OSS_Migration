"""
Public endpoints (/public.php equivalent — no auth required).

Source: ttrss/public.php (entry point) + ttrss/classes/handler/public.php:Handler_Public
        (OPML, RSS output, shared articles, login form — all Phase 1b+)
Phase 1a: index health-check stub only.
Full implementation: RSS feed output, registration, image proxy, login, forgotpass, etc.
"""
from __future__ import annotations

import os

import structlog
from flask import (
    Blueprint, abort, current_app, jsonify, redirect,
    request, send_file, session, url_for,
)
from flask_login import current_user, login_user, logout_user

# DB table coverage — handler/public.php uses these models for RSS/OPML/shared feeds
# Source: ttrss/classes/handler/public.php:Handler_Public
from ttrss.models.access_key import TtRssAccessKey  # noqa: F401
from ttrss.models.feed import TtRssFeed  # noqa: F401
from ttrss.models.pref import TtRssSettingsProfile  # noqa: F401
from ttrss.models.user import TtRssUser  # noqa: F401
from ttrss.models.user_entry import TtRssUserEntry  # noqa: F401

# Source: ttrss/public.php + ttrss/classes/handler/public.php:Handler_Public
public_bp = Blueprint("public", __name__)

logger = structlog.get_logger(__name__)


# Source: ttrss/index.php (app root entry point) — Phase 1a health check stub
@public_bp.get("/")
def index():
    """Health-check / app root. Phase 1a stub."""
    return jsonify({"status": "ok", "app": "ttrss-python", "phase": "1a"})


# Source: ttrss/image.php (lines 23-53 — cached image proxy endpoint)
@public_bp.get("/image")
def image_proxy():
    """
    Serve cached feed images by hash.
    Source: ttrss/image.php (lines 23-53)
    Note: X-Sendfile support not reproduced — Python uses send_file() instead.
    """
    hash_val = request.args.get("hash", "")
    if not hash_val:
        abort(404)
    hash_val = os.path.basename(hash_val)
    cache_dir = current_app.config.get("CACHE_DIR", "cache")
    filepath = os.path.join(cache_dir, "images", f"{hash_val}.png")
    if not os.path.isfile(filepath):
        abort(404)
    return send_file(filepath, mimetype="image/png")


# Source: ttrss/register.php (lines 1-368 — user self-registration entry point)
@public_bp.route("/register", methods=["GET", "POST"])
def register():
    """
    User self-registration page.
    Source: ttrss/register.php (full file)
    """
    from ttrss.extensions import db
    from ttrss.auth.register import (
        register_user, check_username_available,
        cleanup_stale_registrations, registration_slots_feed,
    )

    enable_reg = current_app.config.get("ENABLE_REGISTRATION", False)
    max_users = current_app.config.get("REG_MAX_USERS", 0)
    self_url = current_app.config.get("SELF_URL_PATH", "")

    # Source: register.php lines 60-68 — cleanup stale registrations on every visit
    cleanup_stale_registrations(db.session)

    # Source: register.php lines 24-57 — Atom feed format
    if request.args.get("format") == "feed":
        from flask import Response
        xml = registration_slots_feed(
            db.session, enable_registration=enable_reg,
            reg_max_users=max_users, self_url=self_url,
        )
        return Response(xml, mimetype="text/xml")

    # Source: register.php line 74-91 — AJAX username check
    if request.args.get("action") == "check":
        from flask import Response
        login_name = request.args.get("login", "")
        available = check_username_available(db.session, login_name)
        return Response(
            f"<result>{0 if available else 1}</result>",
            mimetype="application/xml",
        )

    if not enable_reg:
        return jsonify({"error": "registration_disabled"}), 403

    if request.method == "POST":
        login_name = request.form.get("login", "")
        email = request.form.get("email", "")
        captcha = request.form.get("turing_test", "")

        # Source: register.php line 260 — captcha check
        if captcha.strip().lower() not in ("4", "four"):
            return jsonify({"error": "captcha_failed"}), 400

        result = register_user(
            db.session, login_name, email,
            reg_max_users=max_users, enable_registration=enable_reg,
        )

        if result["success"]:
            # Source: register.php lines 297-314 — send login/password to new user by email
            # Source: register.php lines 321-331 — send admin notification email
            try:
                from ttrss.utils.mail import send_mail
                _login = result.get("login", login_name)
                _temp_pw = result.get("temp_password", "")
                _user_msg = (
                    "Hi!\n\n"
                    "You are receiving this message because you (or someone else) have opened\n"
                    "an account at Tiny Tiny RSS.\n\n"
                    "Your login information:\n\n"
                    f"Login:    {_login}\n"
                    f"Password: {_temp_pw}\n\n"
                    "Please login at least once within 24 hours or your account will be removed.\n"
                )
                if email:
                    send_mail(email, "", "Registration information for Tiny Tiny RSS", _user_msg)
                # Source: register.php:321 — REG_NOTIFY_ADDRESS admin notification
                _admin_addr = current_app.config.get("REG_NOTIFY_ADDRESS", "")
                if _admin_addr:
                    _admin_msg = (
                        f"New user registered at Tiny Tiny RSS.\n\n"
                        f"Login: {_login}\nEmail: {email}\n"
                    )
                    send_mail(_admin_addr, "", "Registration notice for Tiny Tiny RSS", _admin_msg)
            except Exception:
                pass  # Email failure is non-fatal — registration still succeeded
            return jsonify({"status": "ok", "message": "Account created successfully"})
        else:
            return jsonify({"error": result["error"]}), 400

    return jsonify({"registration": "enabled" if enable_reg else "disabled"})


# Source: ttrss/classes/handler/public.php:login (lines 545-592)
@public_bp.route("/login", methods=["POST"])
def login():
    """
    Login endpoint — authenticate user and create session.
    Source: ttrss/classes/handler/public.php:login (lines 545-592)
    Note: ttrss/include/login_form.php HTML rendering not reproduced — JSON API only.
    """
    from ttrss.extensions import db
    from ttrss.auth.authenticate import authenticate_user

    login_name = request.form.get("login", "")
    password = request.form.get("password", "")
    remember_me = bool(request.form.get("remember_me"))

    # Source: handler/public.php lines 560-561 — authenticate_user($login, $password)
    user = authenticate_user(login_name, password)

    if user:
        login_user(user, remember=remember_me)

        # Source: handler/public.php lines 570-579 — profile selection
        profile_id = request.form.get("profile")
        if profile_id:
            from ttrss.models.pref import TtRssSettingsProfile
            profile = db.session.query(TtRssSettingsProfile).filter_by(
                id=int(profile_id), owner_uid=user.id
            ).first()
            if profile:
                session["profile"] = profile.id

        # Source: handler/public.php lines 586-590 — redirect to return URL or home
        return_url = request.args.get("return") or url_for("public.index")
        return redirect(return_url)
    else:
        return jsonify({"error": "incorrect_credentials"}), 401


# Source: ttrss/classes/handler/public.php:logout (lines 343-346)
@public_bp.get("/logout")
def logout():
    """Source: ttrss/classes/handler/public.php:logout (lines 343-346)"""
    logout_user()
    return redirect(url_for("public.index"))


# Source: ttrss/classes/handler/public.php:getUnread (lines 236-256)
@public_bp.get("/getUnread")
def get_unread():
    """
    Public unread count by login name.
    Source: ttrss/classes/handler/public.php:getUnread (lines 236-256)
    """
    from ttrss.extensions import db
    from ttrss.models.user import TtRssUser
    from ttrss.feeds.counters import get_global_unread

    login_name = request.args.get("login", "")
    fresh = request.args.get("fresh") == "1"

    user = db.session.query(TtRssUser).filter_by(login=login_name).first()
    if not user:
        return "-1;User not found", 200

    unread = get_global_unread(user.id)
    result = str(unread)

    if fresh:
        from ttrss.feeds.counters import get_feed_articles
        fresh_count = get_feed_articles(-3, False, True, user.id)
        result += f";{fresh_count}"

    return result, 200


# Source: ttrss/classes/handler/public.php:getProfiles (lines 258-276)
@public_bp.get("/getProfiles")
def get_profiles():
    """
    Return profile list for a login as JSON.
    Source: ttrss/classes/handler/public.php:getProfiles (lines 258-276)
    Adapted: PHP returns HTML <select>; Python returns JSON list.
    """
    from ttrss.extensions import db
    from ttrss.models.user import TtRssUser
    from ttrss.models.pref import TtRssSettingsProfile

    login_name = request.args.get("login", "")
    user = db.session.query(TtRssUser).filter_by(login=login_name).first()
    if not user:
        return jsonify([])

    profiles = db.session.query(TtRssSettingsProfile).filter_by(
        owner_uid=user.id
    ).order_by(TtRssSettingsProfile.title).all()

    return jsonify([{"id": p.id, "title": p.title} for p in profiles])


# Source: ttrss/classes/handler/public.php:pubsub (lines 278-341)
@public_bp.route("/pubsub", methods=["GET", "POST"])
def pubsub():
    """
    PubSubHubbub callback handler.
    Source: ttrss/classes/handler/public.php:pubsub (lines 278-341)
    """
    from ttrss.extensions import db
    from sqlalchemy import text

    if not current_app.config.get("PUBSUBHUBBUB_ENABLED", False):
        return "404 Not found (Disabled by server)", 404

    mode = request.args.get("hub_mode") or request.args.get("hub.mode", "")
    feed_id = int(request.args.get("id", 0))

    feed_row = db.session.execute(
        text("SELECT feed_url FROM ttrss_feeds WHERE id = :id"), {"id": feed_id}
    ).fetchone()

    if not feed_row:
        return "404 Not found (Feed not found)", 404

    if mode == "subscribe":
        db.session.execute(
            text("UPDATE ttrss_feeds SET pubsub_state = 2 WHERE id = :id"), {"id": feed_id}
        )
        db.session.commit()
        return request.args.get("hub_challenge", ""), 200
    elif mode == "unsubscribe":
        db.session.execute(
            text("UPDATE ttrss_feeds SET pubsub_state = 0 WHERE id = :id"), {"id": feed_id}
        )
        db.session.commit()
        return request.args.get("hub_challenge", ""), 200
    else:
        # Source: handler/public.php lines 326-330 — update ping: reset timestamps
        db.session.execute(
            text("UPDATE ttrss_feeds SET last_update_started = '1970-01-01', last_updated = '1970-01-01' WHERE id = :id"),
            {"id": feed_id}
        )
        db.session.commit()
        return "", 200


# Source: ttrss/classes/handler/public.php:share (lines 348-368)
@public_bp.get("/share")
def share():
    """
    View shared article by UUID.
    Source: ttrss/classes/handler/public.php:share (lines 348-368)
    """
    from ttrss.extensions import db
    from ttrss.models.user_entry import TtRssUserEntry
    from ttrss.articles.ops import format_article

    uuid = request.args.get("key", "")
    entry = db.session.query(TtRssUserEntry).filter_by(uuid=uuid).first()
    if not entry:
        return jsonify({"error": "Article not found"}), 404

    article = format_article(entry.ref_id, False, True, entry.owner_uid)
    return jsonify(article)


# Source: ttrss/classes/handler/public.php:sharepopup (lines 424-543)
@public_bp.route("/sharepopup", methods=["GET", "POST"])
def sharepopup():
    """
    Share article popup — create published article.
    Source: ttrss/classes/handler/public.php:sharepopup (lines 424-543)
    Adapted: HTML popup replaced by JSON API.
    """
    from ttrss.extensions import db

    if not current_user.is_authenticated:
        return jsonify({"error": "not_authenticated"}), 401

    action = request.form.get("action") or request.args.get("action", "")

    if action == "share":
        # Source: handler/public.php lines 447-453 — create_published_article
        title = request.form.get("title", "")
        url_val = request.form.get("url", "")
        content = request.form.get("content", "")
        labels = request.form.get("labels", "")

        from ttrss.articles.ops import create_published_article
        create_published_article(title, url_val, content, labels, current_user.id)
        return jsonify({"status": "ok"})
    else:
        title = request.args.get("title", "")
        url_val = request.args.get("url", "")
        return jsonify({"title": title, "url": url_val})


# Source: ttrss/classes/handler/public.php:subscribe (lines 606-706)
@public_bp.route("/subscribe", methods=["GET", "POST"])
def subscribe():
    """
    Public feed subscription.
    Source: ttrss/classes/handler/public.php:subscribe (lines 606-706)
    """
    if not current_user.is_authenticated:
        return jsonify({"error": "not_authenticated"}), 401

    feed_url = (request.form.get("feed_url") or request.args.get("feed_url", "")).strip()
    if not feed_url:
        return jsonify({"error": "feed_url required"}), 400

    from ttrss.feeds.ops import subscribe_to_feed
    from ttrss.extensions import db

    rc = subscribe_to_feed(db.session, feed_url, current_user.id)
    return jsonify(rc)


# Source: ttrss/classes/handler/public.php:forgotpass (lines 713-887)
@public_bp.route("/forgotpass", methods=["GET", "POST"])
def forgotpass():
    """
    Password reset flow (three phases).
    Source: ttrss/classes/handler/public.php:forgotpass (lines 713-887)
    Adapted: HTML form replaced by JSON API.
    """
    import secrets as _secrets
    from ttrss.extensions import db
    from ttrss.models.user import TtRssUser
    from sqlalchemy import text
    import time

    hash_val = request.args.get("hash", "")
    login_name = request.args.get("login", "") or request.form.get("login", "")

    if hash_val:
        # Source: handler/public.php lines 738-756 — validate reset token
        if not login_name:
            return jsonify({"error": "missing_login"}), 400

        user = db.session.query(TtRssUser).filter_by(login=login_name).first()
        if not user or not user.resetpass_token:
            return jsonify({"error": "invalid_reset_link"}), 400

        parts = user.resetpass_token.split(":", 1)
        if len(parts) != 2:
            return jsonify({"error": "invalid_reset_link"}), 400

        timestamp, token = parts
        if not (int(timestamp) >= time.time() - 15 * 60 * 60 and token == hash_val):
            return jsonify({"error": "expired_or_invalid_token"}), 400

        # Source: handler/public.php line 754 — Pref_Users::resetUserPassword($id, true)
        # Generates a new random password, clears token, and emails the new credentials.
        db.session.execute(
            text("UPDATE ttrss_users SET resetpass_token = NULL WHERE id = :id"),
            {"id": user.id}
        )
        # Source: pref/users.php:resetUserPassword — generate temp password and update hash
        from ttrss.prefs.users_crud import reset_user_password
        result = reset_user_password(user.id)

        # Source: handler/public.php:forgotpass lines 870-876 — send new password by email
        if result and user.email:
            try:
                from ttrss.utils.mail import send_mail
                _msg = (
                    f"Hi!\n\n"
                    f"Your password for Tiny Tiny RSS has been reset.\n\n"
                    f"New temporary password: {result.get('tmp_password', '')}\n\n"
                    f"Please change it after logging in."
                )
                send_mail(user.email, "", "[tt-rss] Password reset", _msg)
            except Exception:
                pass  # Non-fatal — password was reset, email failed
        return jsonify({"status": "ok", "message": "Password reset completed"})

    method = request.form.get("method", "")
    if method == "do":
        # Source: handler/public.php lines 800-879 — process reset request
        email = request.form.get("email", "")
        test = request.form.get("test", "")

        if test.strip().lower() not in ("4", "four") or not email or not login_name:
            return jsonify({"error": "invalid_form_data"}), 400

        user = db.session.query(TtRssUser).filter_by(
            login=login_name, email=email
        ).first()
        if not user:
            return jsonify({"error": "login_email_not_found"}), 404

        reset_token = _secrets.token_hex(20)
        token_full = f"{int(time.time())}:{reset_token}"
        db.session.execute(
            text("UPDATE ttrss_users SET resetpass_token = :token WHERE id = :id"),
            {"token": token_full, "id": user.id}
        )
        db.session.commit()

        # Source: handler/public.php lines 839-877 — send reset link email
        self_url = current_app.config.get("SELF_URL_PATH", request.host_url.rstrip("/"))
        reset_link = f"{self_url}/forgotpass?login={login_name}&hash={reset_token}"
        try:
            from ttrss.utils.mail import send_mail
            _msg = (
                f"Hi!\n\n"
                f"Someone (hopefully you) requested a password reset for your Tiny Tiny RSS account.\n\n"
                f"To reset your password, please click the following link:\n\n"
                f"{reset_link}\n\n"
                f"This link expires in 15 hours. If you did not request this, ignore this message."
            )
            send_mail(email, "", "[tt-rss] Password reset request", _msg)
        except Exception:
            pass  # Non-fatal — token stored; user can manually use the link if known

        logger.info("forgotpass: reset token issued for user %s", login_name)
        return jsonify({"status": "ok", "message": "Reset instructions sent"})

    # GET — return form info
    return jsonify({"op": "forgotpass"})


# Source: ttrss/classes/handler/public.php:dbupdate (lines 889-1003)
@public_bp.route("/dbupdate", methods=["GET", "POST"])
def dbupdate():
    """
    Database schema update (admin only).
    Source: ttrss/classes/handler/public.php:dbupdate (lines 889-1003)
    Adapted: PHP DbUpdater → Alembic migration.
    """
    if not current_user.is_authenticated or getattr(current_user, "access_level", 0) < 10:
        return jsonify({"error": "insufficient_access"}), 403

    subop = request.form.get("subop") or request.args.get("subop", "")
    if subop == "performupdate":
        try:
            import subprocess
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                capture_output=True, text=True, cwd=current_app.root_path + "/.."
            )
            if result.returncode == 0:
                return jsonify({"status": "ok", "output": result.stdout})
            else:
                return jsonify({"status": "error", "output": result.stderr}), 500
        except Exception as exc:
            return jsonify({"status": "error", "message": str(exc)}), 500

    return jsonify({"status": "ready", "op": "dbupdate"})


# Source: ttrss/classes/handler/public.php:rss (lines 370-408)
# Source: ttrss/classes/handler/public.php:generate_syndicated_feed (lines 4-234)
@public_bp.get("/rss")
def rss():
    """
    Public RSS/Atom/JSON feed output via access key.
    Source: ttrss/classes/handler/public.php:rss (lines 370-408)
            ttrss/classes/handler/public.php:generate_syndicated_feed (lines 4-234)
    Adapted: Atom XML template generation deferred; JSON Feed format returned.
    """
    from ttrss.extensions import db
    from ttrss.models.access_key import TtRssAccessKey
    from ttrss.articles.search import query_feed_headlines

    feed_id = request.args.get("id", "")
    key = request.args.get("key", "")
    is_cat = request.args.get("is_cat") == "1"
    limit = int(request.args.get("limit", 60))
    offset = int(request.args.get("offset", 0))
    fmt = request.args.get("format", "json")

    # Source: handler/public.php lines 394-400 — validate access key
    if not key:
        return jsonify({"error": "access_key required"}), 403

    access_key = db.session.query(TtRssAccessKey).filter_by(
        access_key=key, feed_id=feed_id
    ).first()
    if not access_key:
        return jsonify({"error": "forbidden"}), 403

    owner_uid = access_key.owner_uid

    # Source: handler/public.php lines 403-407 — generate_syndicated_feed
    headlines = query_feed_headlines(
        db.session,
        feed=int(feed_id) if str(feed_id).lstrip("-").isdigit() else 0,
        limit=limit,
        owner_uid=owner_uid,
        is_cat=is_cat,
        offset=offset,
    )

    return jsonify({
        "feed_id": feed_id,
        "owner_uid": owner_uid,
        "articles": headlines,
        "format": fmt,
    })


# Source: ttrss/opml.php (lines 17-32) + ttrss/classes/opml.php:Opml::export
# PHP: public.php?op=opml&key=... → validates key → opml_export("", $owner_uid, true, false)
@public_bp.get("/opml")
def opml_export():
    """
    Public OPML export via access key.
    Source: ttrss/opml.php (lines 17-32) — key-authenticated OPML subscription export.
    Adapted: PHP sent HTTP headers inline; Python returns Flask Response.
             hide_private_feeds=True, include_settings=False (public subscription view).
    """
    from flask import Response

    from ttrss.extensions import db
    from ttrss.feeds.opml import opml_export_full
    from ttrss.models.access_key import TtRssAccessKey

    key = request.args.get("key", "")
    if not key:
        return jsonify({"error": "access_key required"}), 403

    # Source: ttrss/opml.php lines 17-26 — validate access key for feed_id = -3 (OPML virtual feed)
    access_key_row = db.session.query(TtRssAccessKey).filter_by(
        access_key=key,
        feed_id="-3",
    ).first()
    if not access_key_row:
        return jsonify({"error": "forbidden"}), 403

    owner_uid = access_key_row.owner_uid

    # Source: ttrss/opml.php line 30 — opml_export("", $owner_uid, hide_private_feeds=true, include_settings=false)
    xml_content = opml_export_full(
        db.session,
        owner_uid,
        hide_private_feeds=True,
        include_settings=False,
    )

    return Response(
        xml_content,
        mimetype="application/xml+opml",
        headers={"Content-Disposition": "attachment; filename=tt-rss-subscriptions.opml"},
    )
