"""
TT-RSS REST API (/api/ — equivalent to PHP api/index.php).

Protocol (spec/03-api-routing.md, R08, R09):
  POST or GET /api/ with JSON body (or query params for GET).
  Response envelope: {"seq": N, "status": 0|1, "content": {...}}
  seq MUST be echoed from the request in every response (CG-04).
  API level: 8.

Auth (ADR-0007, ADR-0008, R07, AR05):
  Login stores user_id in Redis session only — never pwd_hash (AR05).
  Legacy SHA1 hashes are upgraded to argon2id on first successful login (ADR-0008).
"""
from flask import Blueprint, jsonify, session
from flask_login import current_user, login_user, logout_user

from ttrss.auth.password import hash_password, needs_upgrade, verify_password
from ttrss.extensions import db
from ttrss.models.user import TtRssUser

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _seq(data: dict) -> int:
    """Extract seq from request data — echoed in every response (CG-04, R08)."""
    from flask import request

    return int(data.get("seq", request.args.get("seq", 0)))


def _ok(seq: int, content: dict):
    return jsonify({"seq": seq, "status": 0, "content": content})


def _err(seq: int, error: str):
    return jsonify({"seq": seq, "status": 1, "content": {"error": error}})


@api_bp.route("/", methods=["GET", "POST"])
def dispatch():
    """Single dispatch endpoint for all API operations (spec/03-api-routing.md)."""
    from flask import request

    data = request.get_json(silent=True) or {}
    op = data.get("op") or request.args.get("op", "")
    seq = _seq(data)

    if op == "login":
        return _handle_login(data, seq)
    if op == "logout":
        logout_user()
        session.clear()
        return _ok(seq, {"status": "OK"})
    if op == "isLoggedIn":
        # R09: content.status 1=logged in, 0=not logged in
        return _ok(seq, {"status": 1 if current_user.is_authenticated else 0})
    if op == "getVersion":
        return _ok(seq, {"version": "1.12.0-python"})
    if op == "getApiLevel":
        return _ok(seq, {"level": 8})

    return _err(seq, "UNKNOWN_METHOD")


def _handle_login(data: dict, seq: int):
    """
    Authenticate user and create session.
    Upgrades legacy SHA1 hash to argon2id on successful login (ADR-0008, R10).
    Session stores user_id only — never pwd_hash (ADR-0007, R07, AR05).
    Response includes session_id and api_level=8 (R08, spec/03-api-routing.md).
    """
    username = data.get("user", "")
    password = data.get("password", "")

    user: TtRssUser | None = db.session.scalars(
        db.select(TtRssUser).where(TtRssUser.login == username)
    ).first()

    if not user or not verify_password(user.pwd_hash, password):
        return _err(seq, "LOGIN_ERROR")

    # Upgrade legacy SHA1 hash to argon2id on first successful login (ADR-0008)
    if needs_upgrade(user.pwd_hash):
        user.pwd_hash = hash_password(password)
        db.session.commit()

    login_user(user)
    # AR05: store only user_id — pwd_hash MUST NOT be stored in session
    session["user_id"] = user.id

    return _ok(
        seq,
        {
            "session_id": getattr(session, "sid", ""),  # Flask-Session sets .sid
            "api_level": 8,
        },
    )
