"""Google Cloud Secret Manager service for NEXUS."""

import os

from flask import Flask
from google.api_core.exceptions import GoogleAPIError
from google.cloud import secretmanager

from logger import get_logger

logger = get_logger(__name__)


class SecretService:
    """Manages retrieving and caching secrets."""

    def __init__(self) -> None:
        """Initialize the SecretService instance."""
        self._client: secretmanager.SecretManagerServiceClient | None = None
        self._project_id: str = ""
        self._use_sm: bool = False
        self._cache: dict[str, str] = {}

    def init_app(self, app: Flask) -> None:
        """Initialize the Secret Manager client.

        Args:
            app: The Flask application instance.
        """
        self._project_id = app.config.get("GCP_PROJECT_ID", "")
        self._use_sm = app.config.get("USE_SECRET_MANAGER", False)

        if self._use_sm and not app.config.get("TESTING"):
            try:
                self._client = secretmanager.SecretManagerServiceClient()
                logger.info("Secret Manager client initialized successfully.")
            except Exception:
                logger.exception("Failed to initialize Secret Manager client")
                self._use_sm = False
        else:
            logger.info("Using local environment variables for secrets.")

    def get_secret(self, secret_id: str) -> str:
        """Get a secret, caching it in memory.

        Args:
            secret_id: The ID of the secret (e.g., 'nexus-gemini-api-key').

        Returns:
            The secret payload as a string.
        """
        # Check cache first
        if secret_id in self._cache:
            return self._cache[secret_id]

        # Use local environment variable if not configured for Secret Manager
        if not self._use_sm or self._client is None or not self._project_id:
            # Map known secret IDs to environment variable names
            env_map = {
                "nexus-gemini-api-key": "GEMINI_API_KEY",
                "nexus-maps-api-key": "MAPS_API_KEY",
            }
            env_var = env_map.get(secret_id, secret_id.upper().replace("-", "_"))
            val = os.environ.get(env_var, "")
            if val:
                self._cache[secret_id] = val
            return val

        # Fetch from Secret Manager
        try:
            name = f"projects/{self._project_id}/secrets/{secret_id}/versions/latest"
            response = self._client.access_secret_version(request={"name": name})
            payload: str = response.payload.data.decode("UTF-8")
            self._cache[secret_id] = payload
            return payload
        except GoogleAPIError as e:
            logger.exception("Failed to fetch secret", extra={"secret_id": secret_id})
            return ""

    def clear_cache(self) -> None:
        """Clear the secret cache (e.g., on authentication error)."""
        self._cache.clear()
        logger.info("Secret cache cleared.")


# Singleton instance
secret_service = SecretService()


def init_app(app: Flask) -> None:
    """Initialize the global SecretService instance.

    Args:
        app: The Flask app instance.
    """
    secret_service.init_app(app)
