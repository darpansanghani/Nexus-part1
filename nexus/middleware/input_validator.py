"""Input validation and sanitization for NEXUS."""

import base64
import re
from typing import Any

import bleach

from constants import (
    ALLOWED_IMAGE_MIME_TYPES,
    MAX_IMAGE_SIZE_BYTES,
    MAX_TEXT_LENGTH,
    SQL_INJECTION_PATTERNS,
)
from exceptions import ValidationError
from logger import get_logger

logger = get_logger(__name__)


def sanitize_text(text: str) -> str:
    """Sanitize and validate text input to ensure safety.

    Args:
        text: The raw input string.

    Returns:
        The cleaned, safe string.

    Raises:
        ValidationError: If the text violates security constraints.
    """
    if not text:
        return ""

    if len(text) > MAX_TEXT_LENGTH:
        raise ValidationError("Text input exceeds maximum allowed length.")

    # Reject null bytes
    if "\x00" in text:
        raise ValidationError("Input contains null bytes and is rejected.")

    # Reject blatant Script or JS URIs explicitly
    lower_text = text.lower()
    if "<script>" in lower_text or "javascript:" in lower_text:
        raise ValidationError("Input contains script tags or javascript URIs and is rejected.")

    # Check for SQL injection patterns
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, text):
            logger.warning("SQL injection pattern detected", extra={"pattern": pattern})
            raise ValidationError("Input matches signature of SQL injection and is rejected.")

    # Use bleach to strip any tags completely
    cleaned: str = bleach.clean(text, tags=[], attributes={}, protocols=[], strip=True)
    return cleaned


def validate_image(image_b64: str) -> bytes:
    """Validate and decode a base64 image string.

    Args:
        image_b64: The base64 encoded image string.

    Returns:
        The raw bytes of the image.

    Raises:
        ValidationError: If the image is invalid, too large, or wrong format.
    """
    if not image_b64:
        raise ValidationError("Image data is missing.")

    mime_type = "image/jpeg"
    data_str = image_b64

    if image_b64.startswith("data:"):
        parts = image_b64.split(",", 1)
        if len(parts) == 2:
            schema, data_str = parts
            mime_match = re.search(r"data:(image/\w+);", schema)
            if mime_match:
                mime_type = mime_match.group(1).lower()

    if mime_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise ValidationError(f"Invalid image format '{mime_type}'.")

    try:
        image_bytes: bytes = base64.b64decode(data_str, validate=True)
    except Exception as e:
        logger.exception("Failed to decode base64 image data")
        raise ValidationError("Could not decode base64 image data.") from e

    # Validate size
    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise ValidationError("Image exceeds maximum allowed size.")

    return image_bytes
