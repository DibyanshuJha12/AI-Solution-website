from __future__ import annotations

from flask import Flask, jsonify, render_template, request


def register_error_handlers(app: Flask) -> None:
    def wants_json_response() -> bool:
        return request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json"

    def render_error(status_code: int, title: str, message: str):
        if wants_json_response():
            return jsonify({"error": message, "status": status_code}), status_code
        return (
            render_template("errors/error.html", status_code=status_code, title=title, message=message),
            status_code,
        )

    @app.errorhandler(404)
    def not_found(error):
        return render_error(404, "Page not found", "The page you requested could not be found.")

    @app.errorhandler(413)
    def too_large(error):
        return render_error(413, "Upload too large", "The uploaded file is larger than the allowed limit.")

    @app.errorhandler(429)
    def rate_limited(error):
        return render_error(429, "Too many requests", "Please wait a moment and try again.")

    @app.errorhandler(500)
    def server_error(error):
        app.logger.error("Unhandled server error: %s", error, exc_info=True)
        return render_error(500, "Server error", "Something unexpected happened. Please try again shortly.")
