"""NEXUS Application Factory."""

import os
import time
import uuid

from flask import Flask, Response, g, jsonify, request
from werkzeug.exceptions import HTTPException

from config import config
from constants import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_413_PAYLOAD_TOO_LARGE,
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from exceptions import NexusError, RateLimitError, ValidationError
from logger import get_logger
from middleware.security_headers import add_security_headers
from routes.api import api_bp
from routes.views import views_bp
from services import firestore_service, gemini_service, secret_service, storage_service

logger = get_logger(__name__)


def create_app(config_name: str = "default") -> Flask:
    """Create and configure the Flask application.

    Args:
        config_name: The configuration dictionary key.

    Returns:
        The configured Flask application.
    """
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize GCP services exactly once using singletons
    with app.app_context():
        # Secret Manager first
        secret_service.init_app(app)
        gemini_service.init_app(app)
        firestore_service.init_app(app)
        storage_service.init_app(app)

    # Register Blueprints
    app.register_blueprint(api_bp)
    app.register_blueprint(views_bp)

    # Register Global Middlewares
    app.after_request(add_security_headers)

    # CORS logic for dev environments
    @app.after_request
    def apply_cors_headers(response: Response) -> Response:
        """Apply CORS headers for specific localhost domains.

        Args:
            response: The flask response.

        Returns:
            The augmented flask response.
        """
        origin = request.headers.get("Origin")
        allowed_origins = ["http://localhost:8080", "http://localhost:5000"]
        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, DELETE"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

    @app.before_request
    def log_request_start() -> None:
        """Record start time for latency measurement and set session ID."""
        g.start_time = time.time()
        # Session ID is either provided in headers or generated
        g.session_id = request.headers.get("X-Session-ID", str(uuid.uuid4()))

    @app.after_request
    def log_request_end(response: Response) -> Response:
        """Log request termination with latency and status code.

        Args:
            response: The flask response.

        Returns:
            The original flask response.
        """
        if hasattr(g, "start_time"):
            duration_ms = int((time.time() - g.start_time) * 1000)
            logger.info(
                "Request completed",
                extra={
                    "method": request.method,
                    "path": request.path,
                    "duration_ms": duration_ms,
                    "status_code": response.status_code,
                    "session_id": getattr(g, "session_id", "unknown"),
                },
            )
        return response

    # Global Error Handlers
    @app.errorhandler(ValidationError)
    def handle_validation_error(e: ValidationError) -> tuple[Response, int]:
        """Handle validation errors.

        Args:
            e: The caught ValidationError.

        Returns:
            A JSON response and status code 400.
        """
        logger.warning("Validation error", extra={"error": str(e), "request_id": getattr(g, "session_id", "unknown")})
        return jsonify({"error": str(e), "status": HTTP_400_BAD_REQUEST}), HTTP_400_BAD_REQUEST

    @app.errorhandler(RateLimitError)
    def handle_rate_limit_error(e: RateLimitError) -> tuple[Response, int]:
        """Handle rate limit errors.

        Args:
            e: The caught RateLimitError.

        Returns:
            A JSON response and status code 429.
        """
        logger.warning("Rate limit error", extra={"error": str(e), "request_id": getattr(g, "session_id", "unknown")})
        # If headers are needed, they are usually handled by the exception or middleware,
        # but we return 429 here.
        return jsonify({"error": str(e), "status": HTTP_429_TOO_MANY_REQUESTS}), HTTP_429_TOO_MANY_REQUESTS

    @app.errorhandler(NexusError)
    def handle_nexus_error(e: NexusError) -> tuple[Response, int]:
        """Handle custom application errors.

        Args:
            e: The caught NexusError.

        Returns:
            A JSON response and status code.
        """
        logger.error(
            "NexusError",
            extra={"error": str(e), "request_id": getattr(g, "session_id", "unknown")},
            exc_info=True,
        )
        return jsonify({"error": str(e), "status": HTTP_500_INTERNAL_SERVER_ERROR}), HTTP_500_INTERNAL_SERVER_ERROR

    @app.errorhandler(400)
    def handle_bad_request(e: Exception) -> tuple[Response, int]:
        """Handle 400 Bad Request.

        Args:
            e: The caught Exception.

        Returns:
            A JSON response and status code.
        """
        return jsonify(
            {"error": "Bad Request: " + getattr(e, "description", str(e)), "status": HTTP_400_BAD_REQUEST}
        ), HTTP_400_BAD_REQUEST

    @app.errorhandler(404)
    def handle_not_found(e: Exception) -> tuple[Response, int]:
        """Handle 404 Not Found.

        Args:
            e: The caught Exception.

        Returns:
            A JSON response and status code.
        """
        return jsonify({"error": "Not Found", "status": HTTP_404_NOT_FOUND}), HTTP_404_NOT_FOUND

    @app.errorhandler(413)
    def handle_payload_too_large(e: Exception) -> tuple[Response, int]:
        """Handle 413 Payload Too Large.

        Args:
            e: The caught Exception.

        Returns:
            A JSON response and status code.
        """
        return jsonify(
            {"error": "Payload Too Large: Maximum allowed size exceeded", "status": HTTP_413_PAYLOAD_TOO_LARGE}
        ), HTTP_413_PAYLOAD_TOO_LARGE

    @app.errorhandler(429)
    def handle_too_many_requests(e: Exception) -> tuple[Response, int]:
        """Handle 429 Too Many Requests.

        Args:
            e: The caught Exception.

        Returns:
            A JSON response and status code.
        """
        # Preserve Retry-After header injected by rate_limiter decorator
        retry_after: str | None = None
        if isinstance(e, HTTPException) and e.response is not None:
            retry_after = e.response.headers.get("Retry-After")

        resp = jsonify({"error": "Too Many Requests", "status": HTTP_429_TOO_MANY_REQUESTS})
        resp.status_code = HTTP_429_TOO_MANY_REQUESTS
        if retry_after:
            resp.headers["Retry-After"] = retry_after
        return resp, HTTP_429_TOO_MANY_REQUESTS

    @app.errorhandler(Exception)
    def handle_generic_error(e: Exception) -> tuple[Response, int]:
        """Handle unhandled generic exceptions.

        Args:
            e: The caught Exception.

        Returns:
            A JSON response and status code.
        """
        if isinstance(e, HTTPException):
            code = e.code if e.code else HTTP_500_INTERNAL_SERVER_ERROR
            return jsonify({"error": e.description, "status": code}), code

        logger.error(
            "Unhandled Exception",
            extra={"error": str(e), "request_id": getattr(g, "session_id", "unknown")},
            exc_info=True,
        )
        # Determine if it's a critical error where we should fallback
        return jsonify(
            {"error": "Internal Server Error", "status": HTTP_500_INTERNAL_SERVER_ERROR}
        ), HTTP_500_INTERNAL_SERVER_ERROR

    return app


if __name__ == "__main__":
    env_name: str = os.environ.get("FLASK_ENV", "default")
    app_instance = create_app(env_name)
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 8080))
    app_instance.run(host=host, port=port, debug=app_instance.config.get("DEBUG", False))
