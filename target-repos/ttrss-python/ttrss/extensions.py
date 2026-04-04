"""
Flask extension objects (ADR-0002, ADR-0007, R01, AR02).
Defined without an app; init_app() called in create_app().

Source: ttrss/classes/db.php:Db (singleton DB pattern)
        + ttrss/include/sessions.php (PHP native sessions)
        + ttrss/include/functions.php:authenticate_user / login_sequence (auth flow)
        Adapted for Flask extension pattern — init_app() replaces PHP global singletons.
New: LoginManager, Session, CSRFProtect, Talisman (no direct PHP equivalents)
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_talisman import Talisman
from flask_wtf.csrf import CSRFProtect

from ttrss.models.base import Base

# Source: ttrss/classes/db.php:Db (singleton pattern)
# Python equivalent: Flask-SQLAlchemy extension; model_class=Base ensures single metadata
# so Alembic sees all tables (A-NC-02/03)
db = SQLAlchemy(model_class=Base)

# Inferred from: ttrss/include/sessions.php:validate_session + ttrss/include/functions.php:login_sequence
# Flask-Login replaces PHP $_SESSION["uid"] + validate_session() pattern (ADR-0007)
login_manager = LoginManager()

# Inferred from: ttrss/include/sessions.php (PHP native sessions replaced by Redis, ADR-0007)
sess = Session()

# New: CSRF protection — replaces PHP custom uniqid() tokens (spec/06-security.md F6, R13)
csrf = CSRFProtect()

# New: security headers — no PHP equivalent (spec/06-security.md F7: missing security headers)
# Adds HSTS, X-Content-Type-Options, X-Frame-Options per ADR-0002 security requirements.
talisman = Talisman()

# New: API rate limiting — no PHP equivalent (spec/06-security.md: API abuse prevention).
# key_func=get_remote_address: limits per client IP.
# Disabled in tests via RATELIMIT_ENABLED=False config key (prevents 537 existing tests breaking).
limiter = Limiter(key_func=get_remote_address)

# New: Flask-Login login_view — redirects unauthenticated users to public index.
# PHP equivalent: login_sequence() in functions.php redirects to public.php.
login_manager.login_view = "public.index"  # type: ignore[assignment]


# Inferred from: ttrss/include/sessions.php:validate_session (user lookup by session uid)
# Source: ttrss/include/sessions.php (lines 77-92 — uid-based session validation)
@login_manager.user_loader
def load_user(user_id: str):
    # Lazy import prevents circular import: extensions → models.user → models.base (AR02)
    from ttrss.models.user import TtRssUser

    return db.session.get(TtRssUser, int(user_id))
