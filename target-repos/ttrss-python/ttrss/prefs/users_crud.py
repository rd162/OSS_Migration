"""DB service layer for user management (admin) — AR-2 compliant.

All direct db.session calls for the pref/users blueprint live here.
Blueprint (ttrss/blueprints/prefs/users.py) MUST NOT import db directly.

Source: ttrss/classes/pref/users.php (Pref_Users handler, 458 lines)
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import delete as sa_delete, func, select, update

from ttrss.extensions import db
from ttrss.models.feed import TtRssFeed
from ttrss.models.tag import TtRssTag
from ttrss.models.user import TtRssUser
from ttrss.models.user_entry import TtRssUserEntry

logger = structlog.get_logger(__name__)


def list_users(search: str = "", sort: str = "login") -> list[dict]:
    """Return all non-system users matching optional search, ordered by sort column.

    Source: ttrss/classes/pref/users.php:index (line 303-453) — user listing query
    """
    if sort not in ("login", "access_level", "created", "last_login"):
        sort = "login"

    q = select(TtRssUser).where(TtRssUser.id > 0)
    if search:
        # Source: ttrss/classes/pref/users.php:363-377 — search token filter
        for token in search.split():
            token = token.strip()
            if token:
                q = q.where(func.upper(TtRssUser.login).like(func.upper(f"%{token}%")))

    q = q.order_by(getattr(TtRssUser, sort, TtRssUser.login))
    user_rows = db.session.execute(q).scalars().all()

    return [
        {
            "id": u.id,
            "login": u.login,
            "access_level": u.access_level,
            "email": u.email,
            "last_login": u.last_login.isoformat() if u.last_login else None,
            "created": u.created.isoformat() if u.created else None,
        }
        for u in user_rows
    ]


def find_user_by_login(login_name: str) -> Optional[int]:
    """Return user id if login already exists, else None.

    Source: ttrss/classes/pref/users.php:add (line 215-216) — duplicate check
    """
    return db.session.execute(
        select(TtRssUser.id).where(TtRssUser.login == login_name)
    ).scalar_one_or_none()


def create_user(login_name: str) -> dict:
    """Create a new user with a random temporary password; return id and tmp password.

    Source: ttrss/classes/pref/users.php:add (line 208-235)
    Caller must NOT wrap in a transaction — this function commits internally after
    calling initialize_user_prefs.
    """
    # Source: ttrss/classes/pref/users.php:211-213 — generate temp password
    tmp_password = secrets.token_urlsafe(8)[:8]

    from ttrss.auth.password import hash_password
    pwd_hash = hash_password(tmp_password)

    # Source: ttrss/classes/pref/users.php:220-222 — insert new user
    new_user = TtRssUser(
        login=login_name,
        pwd_hash=pwd_hash,
        access_level=0,
        salt="",
        created=datetime.now(timezone.utc),
    )
    db.session.add(new_user)
    db.session.flush()

    # Source: ttrss/classes/pref/users.php:235 — initialize_user
    from ttrss.prefs.ops import initialize_user_prefs
    initialize_user_prefs(new_user.id)

    db.session.commit()
    return {"user_id": new_user.id, "login": login_name, "tmp_password": tmp_password}


def get_user_details(user_id: int) -> Optional[dict]:
    """Return user details, feed count, article count, and feed list; None if not found.

    Source: ttrss/classes/pref/users.php:userdetails (line 20) / edit (line 101)
    """
    # Source: ttrss/classes/pref/users.php:24-31 — load user row
    user = db.session.get(TtRssUser, user_id)
    if user is None:
        return None

    # Source: ttrss/classes/pref/users.php:56-59 — feed count
    num_feeds = db.session.execute(
        select(func.count(TtRssFeed.id)).where(TtRssFeed.owner_uid == user_id)
    ).scalar() or 0

    # Source: ttrss/classes/pref/users.php:28-29 — article count
    stored_articles = db.session.execute(
        select(func.count(TtRssUserEntry.int_id)).where(TtRssUserEntry.owner_uid == user_id)
    ).scalar() or 0

    # Source: ttrss/classes/pref/users.php:67-69 — subscribed feeds
    feed_rows = db.session.execute(
        select(TtRssFeed.id, TtRssFeed.title, TtRssFeed.site_url)
        .where(TtRssFeed.owner_uid == user_id)
        .order_by(TtRssFeed.title)
    ).all()

    feeds = [
        {"id": f.id, "title": f.title, "site_url": f.site_url}
        for f in feed_rows
    ]

    return {
        "id": user.id,
        "login": user.login,
        "access_level": user.access_level,
        "email": user.email,
        "full_name": user.full_name,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "created": user.created.isoformat() if user.created else None,
        "num_feeds": num_feeds,
        "stored_articles": stored_articles,
        "feeds": feeds,
    }


def update_user(
    user_id: int,
    login_name: str,
    access_level: int,
    email: str,
    password: str = "",
) -> bool:
    """Update user fields; return False if user not found.

    Source: ttrss/classes/pref/users.php:editSave (line 175)
    """
    # Source: ttrss/classes/pref/users.php:175 — load user to get current login
    user = db.session.get(TtRssUser, user_id)
    if user is None:
        return False

    # Source: ttrss/classes/pref/users.php:190-193 — build update values
    values: dict = {
        "login": login_name or user.login,
        "access_level": access_level,
        "email": email,
        "otp_enabled": False,
    }

    # Source: ttrss/classes/pref/users.php:182-186 — optional password change
    if password:
        from ttrss.auth.password import hash_password
        values["pwd_hash"] = hash_password(password)
        values["salt"] = ""

    db.session.execute(
        update(TtRssUser).where(TtRssUser.id == user_id).values(**values)
    )
    db.session.commit()
    return True


def delete_user(user_id: int) -> None:
    """Delete a user and cascade-remove their tags, feeds, and user row.

    Source: ttrss/classes/pref/users.php:remove (line 196-203)
    Note: FK ON DELETE CASCADE handles most cleanup; PHP also explicitly deletes tags/feeds.
    """
    # Source: ttrss/classes/pref/users.php:201-203 — explicit cascade deletion
    db.session.execute(sa_delete(TtRssTag).where(TtRssTag.owner_uid == user_id))
    db.session.execute(sa_delete(TtRssFeed).where(TtRssFeed.owner_uid == user_id))
    db.session.execute(sa_delete(TtRssUser).where(TtRssUser.id == user_id))
    db.session.commit()


def reset_user_password(user_id: int) -> Optional[dict]:
    """Generate a new random password for a user; return login, tmp_password or None if not found.

    Source: ttrss/classes/pref/users.php:resetPass (line 298) / resetUserPassword (line 247)
    """
    user = db.session.get(TtRssUser, user_id)
    if user is None:
        return None

    # Source: ttrss/classes/pref/users.php:256-261 — generate and store new hash
    tmp_password = secrets.token_urlsafe(8)[:8]
    from ttrss.auth.password import hash_password
    new_hash = hash_password(tmp_password)

    user.pwd_hash = new_hash
    user.salt = ""
    user.otp_enabled = False

    db.session.commit()
    return {"login": user.login, "email": user.email, "tmp_password": tmp_password}
