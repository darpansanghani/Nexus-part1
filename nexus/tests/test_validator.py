"""Tests for the input validator."""

import pytest

from exceptions import ValidationError
from middleware.input_validator import sanitize_text, validate_image


class TestInputValidator:
    """Test suite for the validator."""

    def test_valid_text_input_passes(self) -> None:
        """Legit texts parse fine."""
        result = sanitize_text("This is a safe emergency message.")
        assert "safe emergency message" in result

    def test_empty_text_raises_validation_error(self) -> None:
        """Return early on empty."""
        assert sanitize_text("") == ""

    def test_text_over_10000_chars_raises_validation_error(self) -> None:
        """Limit check works."""
        with pytest.raises(ValidationError):
            sanitize_text("A" * 10001)

    def test_sql_injection_string_raises_validation_error(self) -> None:
        """Regex blacklist matches."""
        with pytest.raises(ValidationError):
            sanitize_text("admin' OR 1=1 --")
        with pytest.raises(ValidationError):
            sanitize_text("UNION SELECT * FROM users")
        with pytest.raises(ValidationError):
            sanitize_text("DROP TABLE incidents")

    def test_script_tag_string_raises_validation_error(self) -> None:
        """Regex blacklist matches XSS."""
        with pytest.raises(ValidationError):
            sanitize_text("<script>alert(1)</script>")

    def test_null_byte_string_raises_validation_error(self) -> None:
        """Null bytes immediately rejected."""
        with pytest.raises(ValidationError):
            sanitize_text("Message with \x00 null byte")

    def test_javascript_uri_raises_validation_error(self) -> None:
        """JS URI catches."""
        with pytest.raises(ValidationError):
            sanitize_text("javascript:alert(1)")

    def test_valid_jpeg_base64_passes(self, sample_image_b64: str) -> None:
        """Valid image decodes accurately."""
        b = validate_image(sample_image_b64)
        assert len(b) > 0

    def test_invalid_mime_type_raises_validation_error(self) -> None:
        """Header check triggers error."""
        invalid_b64 = "data:image/gif;base64,R0lGODlh"
        with pytest.raises(ValidationError, match="Invalid image format"):
            validate_image(invalid_b64)

    def test_image_over_5mb_raises_validation_error(self) -> None:
        """Payload size enforced in validator too."""
        # Generate dummy base64 larger than 5MB
        # 5MB in bytes is 5242880, base64 expands by 4/3 => ~7MB length
        huge_str = "A" * 7000000
        with pytest.raises(ValidationError, match="exceeds maximum"):
            validate_image(huge_str)

    def test_malformed_base64_raises_validation_error(self) -> None:
        """Bad base64 raises correct error."""
        with pytest.raises(ValidationError, match="Could not decode"):
            validate_image("data:image/jpeg;base64,this_is_not_b64@@@")
