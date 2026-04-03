"""
HTTP error handlers — JSON for /api/, plain text elsewhere.

Source: ttrss/errors.php (PHP error page handler)
        + ttrss/classes/api.php:API.wrap (STATUS_ERR responses, lines 33-37)
        Adapted for Flask error handler registration pattern.
New: register_error_handlers() factory (no direct PHP equivalent)

Note on API error responses:
  The PHP API always includes seq in responses (api.php:API.wrap).
  Flask error handlers do NOT have access to the request's seq value by default
  because the error may be raised outside the dispatch() function.
  API errors return seq=0 as a safe default — the client should match by error type,
  not by seq, for error responses (consistent with PHP behavior when seq is missing).
"""
from flask import Flask, jsonify, request


# Inferred from: ttrss/errors.php + ttrss/classes/api.php:API.wrap (error response format)
def register_error_handlers(app: Flask) -> None:

    # Source: ttrss/classes/api.php:API.wrap — STATUS_ERR=1 for all error responses
    @app.errorhandler(400)
    def bad_request(e):
        # New: no direct PHP equivalent (PHP returns 200 with status=1 for API errors)
        if request.path.startswith("/api/"):
            return jsonify({"seq": 0, "status": 1, "content": {"error": str(e)}}), 400
        return str(e), 400

    @app.errorhandler(401)
    def unauthorized(e):
        # Source: ttrss/classes/api.php:API.before (line 17 — NOT_LOGGED_IN check)
        if request.path.startswith("/api/"):
            return jsonify({"seq": 0, "status": 1, "content": {"error": "NOT_LOGGED_IN"}}), 401
        return str(e), 401

    @app.errorhandler(403)
    def forbidden(e):
        # New: PHP API does not return 403 — it uses status=1 with error string.
        if request.path.startswith("/api/"):
            return jsonify({"seq": 0, "status": 1, "content": {"error": "FORBIDDEN"}}), 403
        return str(e), 403

    @app.errorhandler(404)
    def not_found(e):
        # New: PHP API does not return 404 — unknown methods return UNKNOWN_METHOD via dispatch.
        if request.path.startswith("/api/"):
            return jsonify({"seq": 0, "status": 1, "content": {"error": "NOT_FOUND"}}), 404
        return str(e), 404

    @app.errorhandler(500)
    def server_error(e):
        # New: PHP API returns 200 with status=1 for server errors.
        if request.path.startswith("/api/"):
            return jsonify({"seq": 0, "status": 1, "content": {"error": "INTERNAL_ERROR"}}), 500
        return str(e), 500
