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
from flask import Blueprint, jsonify, request, session
from flask_login import current_user, login_user, logout_user

from ttrss.auth.password import hash_password, needs_upgrade, verify_password
from ttrss.extensions import csrf, db
from ttrss.models.user import TtRssUser

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


# Source: ttrss/api/index.php (method dispatch via $handler->$method())
#         + ttrss/classes/api.php:API (method routing)
@api_bp.route("/", methods=["GET", "POST"])
def dispatch():
    """Single dispatch endpoint for all API operations (spec/03-api-routing.md)."""
    data = request.get_json(silent=True) or {}
    op = data.get("op") or request.args.get("op", "")
    seq = _seq()

    if op == "login":
        return _handle_login(data, seq)
    if op == "logout":
        # Source: ttrss/classes/api.php:API.logout (lines 89-92)
        logout_user()
        session.clear()
        return _ok(seq, {"status": "OK"})
    if op == "isLoggedIn":
        # Source: ttrss/classes/api.php:API.isLoggedIn (lines 94-95)
        # PHP returns {"status":true/false} as boolean — preserved here.
        return _ok(seq, {"status": current_user.is_authenticated})
    if op == "getVersion":
        # Source: ttrss/classes/api.php:API.getVersion (lines 39-42)
        return _ok(seq, {"version": "1.12.0-python"})
    if op == "getApiLevel":
        # Source: ttrss/classes/api.php:API.getApiLevel (lines 44-47)
        return _ok(seq, {"level": 8})

    # Source: ttrss/classes/api.php:API.__call (line 488 — UNKNOWN_METHOD error)
    return _err(seq, "UNKNOWN_METHOD")


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
    username = data.get("user", "")
    password = data.get("password", "")

    # Source: ttrss/plugins/auth_internal/init.php:authenticate — SELECT login, pwd_hash, salt
    user: TtRssUser | None = db.session.scalars(
        db.select(TtRssUser).where(TtRssUser.login == username)
    ).first()

    if not user or not verify_password(
        user.pwd_hash,
        password,
        salt=user.salt or "",
        login=user.login,
    ):
        # Source: ttrss/classes/api.php:API.login (line 68 — "LOGIN_ERROR")
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
