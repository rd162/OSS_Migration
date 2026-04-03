"""
TT-RSS AJAX RPC dispatcher (/backend.php — equivalent to PHP backend.php).

CSRF (R13, ADR-0002, AR06):
  Flask-WTF CSRFProtect is active globally.
  Config WTF_CSRF_HEADERS=["X-CSRFToken","X-CSRF-Token"] allows AJAX callers
  to pass the token as a header (A-NC-05, CG-05).
  JavaScript must include X-CSRFToken in all state-mutating POST requests.

Phase 1a: stub dispatcher only. Full op→handler routing in Phase 1b.
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required

backend_bp = Blueprint("backend", __name__)


@backend_bp.post("/backend.php")
@login_required
def dispatch():
    """
    Phase 1a stub. CSRF enforced globally by Flask-WTF CSRFProtect (R13).
    Full handler dispatch (op=feeds, rpc, article, pref-*, etc.) in Phase 1b.
    """
    data = request.get_json(silent=True) or {}
    op = request.form.get("op") or data.get("op", "")
    method = request.form.get("method") or data.get("method", "")
    return jsonify({"op": op, "method": method, "status": "PHASE_1A_STUB"})
