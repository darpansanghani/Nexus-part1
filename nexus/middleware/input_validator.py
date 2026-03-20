"""Input validation and sanitization for NEXUS."""

import base64
import re
import bleach
from exceptions import ValidationError


def sanitize_text(text: str) -> str:
    """Sanitize and validate text input.
    
    Args:
        text: The raw input string
        
    Returns:
        Cleaned, safe string
        
    Raises:
        ValidationError: If the text violates security constraints
    """
    if not text:
        return ""
        
    if len(text) > 10000:
        raise ValidationError("Text input exceeds maximum allowed length of 10,000 characters.")

    # Reject null bytes
    if "\x00" in text:
        raise ValidationError("Input contains null bytes and is rejected.")

    # Reject blatant Script or JS URIs explicitly
    lower_text = text.lower()
    if "<script>" in lower_text or "javascript:" in lower_text:
        raise ValidationError("Input contains script tags or javascript URIs and is rejected.")

    # Basic SQL injection blacklist pattern detection
    sql_patterns = [
        r"(?i)\\bUNION\\b\\s+(?i)SELECT",
        r"(?i)\\bDROP\\b\\s+(?i)TABLE",
        r"(?i)OR\\s+1\\s*=\\s*1",
        r"(?i)OR\\s+'1'\\s*=\\s*'1'",
        r"(?i)--$"
    ]
    for pattern in sql_patterns:
        if re.search(pattern, text):
            raise ValidationError("Input matches signature of SQL injection and is rejected.")

    # Use bleach to strip any tags completely
    cleaned = bleach.clean(text, tags=[], attributes={}, protocols=[], strip=True)
    return cleaned


def validate_image(image_b64: str) -> bytes:
    """Validate and decode a base64 image string.
    
    Args:
        image_b64: base64 encoded image string
        
    Returns:
        Raw bytes of the image
        
    Raises:
        ValidationError: If the image is invalid, too large, or wrong format
    """
    if not image_b64:
        raise ValidationError("Image data is missing.")

    mime_type = "image/jpeg"
    data_str = image_b64
    
    if image_b64.startswith("data:"):
        parts = image_b64.split(",", 1)
        if len(parts) == 2:
            schema, data_str = parts
            mime_match = re.search(r"data:(image/\\w+);", schema)
            if mime_match:
                mime_type = mime_match.group(1).lower()

    allowed_mimes = {"image/jpeg", "image/png", "image/webp"}
    if mime_type not in allowed_mimes:
        raise ValidationError(f"Invalid image format '{mime_type}'.")

    try:
        image_bytes = base64.b64decode(data_str)
    except Exception:
        raise ValidationError("Could not decode base64 image data.")

    # Validate size: Max 5MB
    if len(image_bytes) > 5 * 1024 * 1024:
        raise ValidationError("Image exceeds maximum allowed size of 5MB.")

    return image_bytes
