"""NEXUS Application Factory."""

import logging
import os
import time
import uuid

from flask import Flask, jsonify, request, g
from werkzeug.exceptions import HTTPException

from config import config
from exceptions import NexusError

# These imports will be available once created
from middleware.security_headers import add_security_headers
from routes.api import api_bp
from routes.views import views_bp
from services import gemini_service, firestore_service, storage_service, secret_service


def create_app(config_name: str = "default") -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Configure logging for structured JSON format (or standard format for dev)
    log_level_str = app.config.get("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level_str.upper(), logging.INFO),
        format='{"time": "%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'
    )
    logger = logging.getLogger("nexus-app")

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
    def apply_cors_headers(response):
        """Apply CORS headers for specific localhost domains."""
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
    def log_request_end(response):
        """Log request termination with latency and status code."""
        if hasattr(g, 'start_time'):
            duration_ms = int((time.time() - g.start_time) * 1000)
            logger.info("Request completed", extra={
                "method": request.method,
                "path": request.path,
                "duration_ms": duration_ms,
                "status_code": response.status_code,
                "session_id": getattr(g, "session_id", "unknown")
            })
        return response

    # Global Error Handlers
    @app.errorhandler(NexusError)
    def handle_nexus_error(e: NexusError) -> tuple:
        """Handle custom application errors."""
        logger.error(f"NexusError: {str(e)}", exc_info=True, extra={"request_id": getattr(g, "session_id", "unknown")})
        return jsonify({"error": str(e), "status": 500}), 500

    @app.errorhandler(400)
    def handle_bad_request(e: Exception) -> tuple:
        return jsonify({"error": "Bad Request: " + getattr(e, "description", str(e)), "status": 400}), 400

    @app.errorhandler(404)
    def handle_not_found(e: Exception) -> tuple:
        return jsonify({"error": "Not Found", "status": 404}), 404

    @app.errorhandler(413)
    def handle_payload_too_large(e: Exception) -> tuple:
        return jsonify({"error": "Payload Too Large: Maximum allowed size exceeded", "status": 413}), 413

    @app.errorhandler(429)
    def handle_too_many_requests(e: Exception) -> tuple:
        return jsonify({"error": "Too Many Requests", "status": 429}), 429

    @app.errorhandler(Exception)
    def handle_generic_error(e: Exception) -> tuple:
        if isinstance(e, HTTPException):
            return jsonify({"error": e.description, "status": e.code}), e.code
        
        logger.error(f"Unhandled Exception: {str(e)}", exc_info=True, extra={"request_id": getattr(g, "session_id", "unknown")})
        # Determine if it's a critical error where we should fallback
        return jsonify({"error": "Internal Server Error", "status": 500}), 500

    return app

if __name__ == "__main__":
    env_name = os.environ.get("FLASK_ENV", "default")
    app_instance = create_app(env_name)
    port = int(os.environ.get("PORT", 8080))
    app_instance.run(host="0.0.0.0", port=port, debug=app_instance.config.get("DEBUG", False))
