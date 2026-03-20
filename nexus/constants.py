"""Centralized constants for the NEXUS application to eliminate magic values."""

# Validation Constants
MAX_TEXT_LENGTH: int = 10000
MAX_IMAGE_SIZE_MB: int = 5
MAX_IMAGE_SIZE_BYTES: int = MAX_IMAGE_SIZE_MB * 1024 * 1024
ALLOWED_IMAGE_MIME_TYPES: set[str] = {"image/jpeg", "image/png", "image/webp"}

# Security & Sanitization
# Using (?i) at the beginning of the regex for Python 3.11 compatibility
SQL_INJECTION_PATTERNS: list[str] = [
    r"(?i)\bUNION\b\s+SELECT",
    r"(?i)\bDROP\b\s+TABLE",
    r"(?i)OR\s+1\s*=\s*1",
    r"(?i)OR\s+'1'\s*=\s*'1'",
    r"(?i)--$"
]

# Rate Limiting
RATE_LIMIT_GLOBAL_REQUESTS: int = 100
RATE_LIMIT_GLOBAL_WINDOW: int = 3600
RATE_LIMIT_FALLBACK_RETRY_AFTER: int = 1

# API / Gemini Configuration
GEMINI_API_TIMEOUT_SECONDS: int = 30
GEMINI_MAX_RETRIES: int = 3
GEMINI_RETRY_DELAY_SECONDS: int = 2
GEMINI_RETRY_BACKOFF: int = 2

# HTTP Status Codes
HTTP_200_OK: int = 200
HTTP_204_NO_CONTENT: int = 204
HTTP_400_BAD_REQUEST: int = 400
HTTP_404_NOT_FOUND: int = 404
HTTP_413_PAYLOAD_TOO_LARGE: int = 413
HTTP_429_TOO_MANY_REQUESTS: int = 429
HTTP_500_INTERNAL_SERVER_ERROR: int = 500
HTTP_503_SERVICE_UNAVAILABLE: int = 503
