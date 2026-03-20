"""Configuration settings for NEXUS application."""

import os
from typing import Dict, Type


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-in-prod")
    GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    MAPS_API_KEY = os.environ.get("MAPS_API_KEY")
    GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "nexus-uploads")
    USE_SECRET_MANAGER = os.environ.get("USE_SECRET_MANAGER", "false").lower() == "true"
    TESTING = False
    DEBUG = False


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    # For testing, we mock everything
    GCP_PROJECT_ID = "test-project"
    GEMINI_API_KEY = "test-gemini-key"
    MAPS_API_KEY = "test-maps-key"
    GCS_BUCKET_NAME = "test-bucket"
    USE_SECRET_MANAGER = False


class ProductionConfig(Config):
    """Production configuration."""
    pass


config: Dict[str, Type[Config]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
}
