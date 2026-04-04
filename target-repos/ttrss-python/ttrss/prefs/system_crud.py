"""DB service layer for system preferences CRUD operations.

Source: ttrss/classes/pref/system.php (Pref_System handler, 91 lines)
Adapted: All db.session calls extracted from the pref/system blueprint
         so that blueprint files remain free of direct DB access (AR-2).
"""
from __future__ import annotations

from sqlalchemy import delete as sa_delete

from ttrss.extensions import db
from ttrss.models.error_log import TtRssErrorLog


def clear_error_log() -> None:
    """Delete all rows from ttrss_error_log and commit.

    Source: ttrss/classes/pref/system.php:clearLog (line 22-23)
    """
    db.session.execute(sa_delete(TtRssErrorLog))
    db.session.commit()
