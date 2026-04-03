"""HTTP error handlers — JSON for /api/, plain text elsewhere."""
from flask import Flask, jsonify, request


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(400)
    def bad_request(e):
        if request.path.startswith("/api/"):
            return jsonify({"status": 1, "content": {"error": str(e)}}), 400
        return str(e), 400

    @app.errorhandler(401)
    def unauthorized(e):
        if request.path.startswith("/api/"):
            return jsonify({"status": 1, "content": {"error": "NOT_LOGGED_IN"}}), 401
        return str(e), 401

    @app.errorhandler(403)
    def forbidden(e):
        if request.path.startswith("/api/"):
            return jsonify({"status": 1, "content": {"error": "FORBIDDEN"}}), 403
        return str(e), 403

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"status": 1, "content": {"error": "NOT_FOUND"}}), 404
        return str(e), 404

    @app.errorhandler(500)
    def server_error(e):
        if request.path.startswith("/api/"):
            return jsonify({"status": 1, "content": {"error": "INTERNAL_ERROR"}}), 500
        return str(e), 500
