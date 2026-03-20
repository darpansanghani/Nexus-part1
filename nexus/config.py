"""Configuration settings for NEXUS application."""

import os


class Config:
    """Base configuration."""

    SECRET_KEY: str = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-in-prod")
    GCP_PROJECT_ID: str = os.environ.get("GCP_PROJECT_ID", "")
    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
    MAPS_API_KEY: str = os.environ.get("MAPS_API_KEY", "")
    GCS_BUCKET_NAME: str = os.environ.get("GCS_BUCKET_NAME", "nexus-uploads")
    USE_SECRET_MANAGER: bool = os.environ.get("USE_SECRET_MANAGER", "false").lower() == "true"
    TESTING: bool = False
    DEBUG: bool = False


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG: bool = True


class TestingConfig(Config):
    """Testing configuration."""

    TESTING: bool = True
    DEBUG: bool = True
    # For testing, we mock everything
    GCP_PROJECT_ID: str = "test-project"
    GEMINI_API_KEY: str = "test-gemini-key"
    MAPS_API_KEY: str = "test-maps-key"
    GCS_BUCKET_NAME: str = "test-bucket"
    USE_SECRET_MANAGER: bool = False


class ProductionConfig(Config):
    """Production configuration."""

    # In production (Cloud Run), always use Secret Manager
    USE_SECRET_MANAGER: bool = True


config: dict[str, type[Config]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
