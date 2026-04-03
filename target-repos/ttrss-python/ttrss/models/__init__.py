"""
Import all 10 models to register them with Base.metadata.
Imported by ttrss/__init__.py (module level) and alembic/env.py.
AR03: sqlacodegen output is NEVER imported here — all models are hand-written.
"""
from ttrss.models.base import Base  # noqa: F401 — re-exported for alembic/env.py
from ttrss.models.category import TtRssFeedCategory  # noqa: F401
from ttrss.models.enclosure import TtRssEnclosure  # noqa: F401
from ttrss.models.entry import TtRssEntry  # noqa: F401
from ttrss.models.feed import TtRssFeed  # noqa: F401
from ttrss.models.label import TtRssLabel2, TtRssUserLabel2  # noqa: F401
from ttrss.models.tag import TtRssTag  # noqa: F401
from ttrss.models.user import TtRssUser  # noqa: F401
from ttrss.models.user_entry import TtRssUserEntry  # noqa: F401
from ttrss.models.version import TtRssVersion  # noqa: F401
