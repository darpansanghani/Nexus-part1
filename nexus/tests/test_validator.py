"""Tests for the input validator."""

import pytest
import base64
from exceptions import ValidationError
from middleware.input_validator import sanitize_text, validate_image


class TestInputValidator:
    def test_valid_text_input_passes(self):
        result = sanitize_text("This is a safe emergency message.")
        assert "safe emergency message" in result

    def test_empty_text_raises_validation_error(self):
        with pytest.raises(ValidationError):
            sanitize_text("")

    def test_text_over_10000_chars_raises_validation_error(self):
        with pytest.raises(ValidationError):
            sanitize_text("A" * 10001)

    def test_sql_injection_string_raises_validation_error(self):
        with pytest.raises(ValidationError):
            sanitize_text("admin' OR 1=1 --")
        with pytest.raises(ValidationError):
            sanitize_text("UNION SELECT * FROM users")
        with pytest.raises(ValidationError):
            sanitize_text("DROP TABLE incidents")

    def test_script_tag_string_raises_validation_error(self):
        with pytest.raises(ValidationError):
            sanitize_text("<script>alert(1)</script>")

    def test_null_byte_string_raises_validation_error(self):
        with pytest.raises(ValidationError):
            sanitize_text("Message with \x00 null byte")

    def test_javascript_uri_raises_validation_error(self):
        with pytest.raises(ValidationError):
            sanitize_text("javascript:alert(1)")

    def test_valid_jpeg_base64_passes(self, sample_image_b64):
        # sample_image_b64 is defined in conftest and passed via injection or setup
        # For this to work, we verify the decode step
        b = validate_image(sample_image_b64)
        assert len(b) > 0

    def test_invalid_mime_type_raises_validation_error(self):
        invalid_b64 = "data:image/gif;base64,R0lGODlh"
        with pytest.raises(ValidationError, match="Invalid image format"):
            validate_image(invalid_b64)

    def test_image_over_5mb_raises_validation_error(self):
        # Generate dummy base64 larger than 5MB
        # 5MB in bytes is 5242880, base64 expands by 4/3 => ~7MB length
        huge_str = "A" * 7000000
        with pytest.raises(ValidationError, match="exceeds maximum"):
            validate_image(huge_str)

    def test_malformed_base64_raises_validation_error(self):
        with pytest.raises(ValidationError, match="Could not decode"):
            validate_image("data:image/jpeg;base64,this_is_not_b64@@@")
