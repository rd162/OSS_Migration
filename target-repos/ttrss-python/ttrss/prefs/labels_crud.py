"""DB service layer for label preferences CRUD operations.

Source: ttrss/classes/pref/labels.php (Pref_Labels handler, 331 lines)
Adapted: All db.session calls extracted from the pref/labels blueprint
         so that blueprint files remain free of direct DB access (AR-2).
"""
from __future__ import annotations

from sqlalchemy import select, update

from ttrss.extensions import db
from ttrss.models.filter import TtRssFilter2, TtRssFilter2Action
from ttrss.models.label import TtRssLabel2
from ttrss.models.user_entry import TtRssUserEntry


# ---------------------------------------------------------------------------
# Label tree
# ---------------------------------------------------------------------------


def fetch_labels(owner_uid: int) -> list:
    """Return all TtRssLabel2 rows for *owner_uid*, ordered by caption.

    Source: ttrss/classes/pref/labels.php:getlabeltree (line 93-96)
    """
    return db.session.execute(
        select(TtRssLabel2)
        .where(TtRssLabel2.owner_uid == owner_uid)
        .order_by(TtRssLabel2.caption)
    ).scalars().all()


# ---------------------------------------------------------------------------
# Create label
# ---------------------------------------------------------------------------


def create_label(caption: str, owner_uid: int) -> bool:
    """Create a label if it doesn't already exist; commit and return True if created.

    Source: ttrss/classes/pref/labels.php:add (line 224) — delegates to label_create.
    Commits the transaction.
    """
    from ttrss.labels import label_create
    created = label_create(db.session, caption, owner_uid=owner_uid)
    db.session.commit()
    return created


# ---------------------------------------------------------------------------
# Save label (rename + colors)
# ---------------------------------------------------------------------------


def fetch_label_caption(label_id: int, owner_uid: int) -> str | None:
    """Return the current caption of a label, or None if not found.

    Source: ttrss/classes/pref/labels.php:save (line 176-177)
    """
    return db.session.execute(
        select(TtRssLabel2.caption)
        .where(TtRssLabel2.id == label_id, TtRssLabel2.owner_uid == owner_uid)
    ).scalar_one_or_none()


def check_caption_taken(caption: str, owner_uid: int) -> bool:
    """Return True if *caption* is already used by another label for this user.

    Source: ttrss/classes/pref/labels.php:save (line 182-185)
    """
    existing = db.session.execute(
        select(TtRssLabel2.id)
        .where(TtRssLabel2.caption == caption, TtRssLabel2.owner_uid == owner_uid)
    ).scalar_one_or_none()
    return existing is not None


def rename_label(label_id: int, owner_uid: int, old_caption: str, new_caption: str) -> None:
    """Rename a label and update any filter actions that referenced the old caption.

    Source: ttrss/classes/pref/labels.php:save (line 187-198)
    Does NOT commit — caller is responsible.
    """
    # Source: ttrss/classes/pref/labels.php:187-189 — rename
    db.session.execute(
        update(TtRssLabel2)
        .where(TtRssLabel2.id == label_id, TtRssLabel2.owner_uid == owner_uid)
        .values(caption=new_caption)
    )

    # Source: ttrss/classes/pref/labels.php:193-198 — update filter actions referencing old name
    db.session.execute(
        update(TtRssFilter2Action)
        .where(
            TtRssFilter2Action.action_param == old_caption,
            TtRssFilter2Action.action_id == 7,
            TtRssFilter2Action.filter_id.in_(
                select(TtRssFilter2.id).where(TtRssFilter2.owner_uid == owner_uid)
            ),
        )
        .values(action_param=new_caption)
    )


def update_label_colors(label_id: int, owner_uid: int, **color_fields: str) -> None:
    """Update fg_color and/or bg_color columns for a label.

    Source: ttrss/classes/pref/labels.php:save — color update block.
    Does NOT commit — caller is responsible.
    Pass keyword args: fg_color="...", bg_color="...".
    """
    if color_fields:
        db.session.execute(
            update(TtRssLabel2)
            .where(TtRssLabel2.id == label_id, TtRssLabel2.owner_uid == owner_uid)
            .values(**color_fields)
        )


def commit_label() -> None:
    """Commit the current DB transaction."""
    db.session.commit()


# ---------------------------------------------------------------------------
# Delete label
# ---------------------------------------------------------------------------


def delete_label(label_id: int, owner_uid: int) -> None:
    """Delete a label and clean up caches, then commit.

    Source: ttrss/classes/pref/labels.php:remove (line 214)
    """
    from ttrss.labels import label_remove
    label_remove(db.session, label_id, owner_uid)
    db.session.commit()


# ---------------------------------------------------------------------------
# Color set / reset
# ---------------------------------------------------------------------------


def set_label_color(
    label_id: int,
    owner_uid: int,
    *,
    kind: str,
    color: str,
    fg: str,
    bg: str,
) -> None:
    """Set foreground and/or background color for a label, invalidate label_cache.

    Source: ttrss/classes/pref/labels.php:colorset (line 128-143)
    Commits the transaction.
    """
    # Source: ttrss/classes/pref/labels.php:128-138
    if kind in ("fg", "bg"):
        db.session.execute(
            update(TtRssLabel2)
            .where(TtRssLabel2.id == label_id, TtRssLabel2.owner_uid == owner_uid)
            .values(**{f"{kind}_color": color})
        )
    else:
        db.session.execute(
            update(TtRssLabel2)
            .where(TtRssLabel2.id == label_id, TtRssLabel2.owner_uid == owner_uid)
            .values(fg_color=fg, bg_color=bg)
        )

    # Source: ttrss/classes/pref/labels.php:139-143 — invalidate label_cache
    from ttrss.labels import label_find_caption
    caption = label_find_caption(db.session, label_id, owner_uid)
    if caption:
        db.session.execute(
            update(TtRssUserEntry)
            .where(TtRssUserEntry.label_cache.like(f"%{caption}%"),
                   TtRssUserEntry.owner_uid == owner_uid)
            .values(label_cache="")
        )

    db.session.commit()


def reset_label_color(label_id: int, owner_uid: int) -> None:
    """Reset label colors to empty strings and invalidate label_cache.

    Source: ttrss/classes/pref/labels.php:colorreset (line 155-164)
    Commits the transaction.
    """
    # Source: ttrss/classes/pref/labels.php:155-157
    db.session.execute(
        update(TtRssLabel2)
        .where(TtRssLabel2.id == label_id, TtRssLabel2.owner_uid == owner_uid)
        .values(fg_color="", bg_color="")
    )

    # Source: ttrss/classes/pref/labels.php:159-164 — invalidate label_cache
    from ttrss.labels import label_find_caption
    caption = label_find_caption(db.session, label_id, owner_uid)
    if caption:
        db.session.execute(
            update(TtRssUserEntry)
            .where(TtRssUserEntry.label_cache.like(f"%{caption}%"),
                   TtRssUserEntry.owner_uid == owner_uid)
            .values(label_cache="")
        )

    db.session.commit()
