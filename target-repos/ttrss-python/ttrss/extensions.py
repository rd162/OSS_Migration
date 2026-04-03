"""
Flask extension objects (ADR-0002, ADR-0007, R01, AR02).
Defined without an app; init_app() called in create_app().
"""
from flask_login import LoginManager
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_talisman import Talisman
from flask_wtf.csrf import CSRFProtect

from ttrss.models.base import Base

# db uses our custom DeclarativeBase so all 10 models are visible to Alembic (A-NC-02/03)
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
sess = Session()
csrf = CSRFProtect()
talisman = Talisman()

login_manager.login_view = "public.index"  # type: ignore[assignment]


@login_manager.user_loader
def load_user(user_id: str):
    # Lazy import prevents circular import: extensions → models.user → models.base (AR02)
    from ttrss.models.user import TtRssUser

    return db.session.get(TtRssUser, int(user_id))
