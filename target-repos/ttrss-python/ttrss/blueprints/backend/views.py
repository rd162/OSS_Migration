"""
TT-RSS AJAX RPC dispatcher (/backend.php — equivalent to PHP backend.php).

Source: ttrss/backend.php (entry point) + ttrss/classes/backend.php:Backend (dispatch class)
        + ttrss/classes/handler/protected.php (login_required base for all backend ops)
Phase 1a: stub dispatcher only. Full op→handler routing in Phase 1b.

CSRF (R13, ADR-0002, AR06):
  Flask-WTF CSRFProtect is active globally.
  Config WTF_CSRF_HEADERS=["X-CSRFToken","X-CSRF-Token"] allows AJAX callers
  to pass the token as a header (A-NC-05, CG-05).
  JavaScript must include X-CSRFToken in all state-mutating POST requests.
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required

# Source: ttrss/backend.php + ttrss/classes/backend.php:Backend
backend_bp = Blueprint("backend", __name__)


# Source: ttrss/backend.php (POST handler) + ttrss/classes/handler/protected.php (login guard)
@backend_bp.post("/backend.php")
@login_required
def dispatch():
    """
    Phase 1a stub. CSRF enforced globally by Flask-WTF CSRFProtect (R13).
    Full handler dispatch (op=feeds, rpc, article, pref-*, etc.) in Phase 1b.

    Source: ttrss/backend.php reads from $_REQUEST (merges GET+POST+COOKIE).
    Python: reads from form data, JSON body, AND query params to match PHP $_REQUEST.
    """
    data = request.get_json(silent=True) or {}
    # Source: ttrss/backend.php — PHP $_REQUEST merges GET, POST, COOKIE.
    # Read op/method from form, JSON, or query params to match PHP behavior.
    op = request.form.get("op") or data.get("op") or request.args.get("op", "")
    method = request.form.get("method") or data.get("method") or request.args.get("method", "")
    return jsonify({"op": op, "method": method, "status": "PHASE_1A_STUB"})
