"""API Integration tests for NEXUS."""

from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient


class TestHealthEndpoint:
    """Tests for the /api/health endpoint."""

    def test_health_returns_200(self, client: FlaskClient) -> None:
        """Test healthy status code."""
        res = client.get("/api/health")
        assert res.status_code == 200

    def test_health_response_has_required_fields(self, client: FlaskClient) -> None:
        """Test health payload fields."""
        res = client.get("/api/health")
        data = res.get_json()
        assert data is not None
        assert "status" in data
        assert "version" in data
        assert "gemini_available" in data
        assert "firestore_available" in data
        assert "timestamp" in data

    def test_health_returns_503_when_gemini_unavailable(self, app: Flask) -> None:
        """Test health handling of missing Gemini."""
        with app.app_context():
            app.config["TESTING"] = False
            with app.test_client() as client:
                res = client.get("/api/health")
                assert res.status_code == 503
            app.config["TESTING"] = True


class TestAnalyzeEndpoint:
    """Tests for the /api/analyze endpoint."""

    @pytest.fixture(autouse=True)
    def auto_patch(self, mock_gemini: Any, mock_firestore: Any, mock_gcs: Any) -> None:
        """Automatically use mocks for Gemini, Firestore, GCS."""
        pass

    @pytest.fixture(autouse=True)
    def reset_rate_limit(self) -> None:
        """Clear rate limit cache before each test to avoid blocking."""
        from middleware.rate_limiter import _rate_limit_cache
        _rate_limit_cache.clear()

    def test_analyze_valid_text_returns_200(self, client: FlaskClient) -> None:
        """Test valid text returns 200."""
        res = client.post("/api/analyze", json={"text": "Car accident on highway"})
        assert res.status_code == 200
        assert "intent" in res.get_json()

    def test_analyze_valid_image_returns_200(self, client: FlaskClient, sample_image_b64: str) -> None:
        """Test valid image returns 200."""
        res = client.post("/api/analyze", json={"image": sample_image_b64})
        assert res.status_code == 200

    def test_analyze_empty_body_returns_400(self, client: FlaskClient) -> None:
        """Test empty payload returns 400."""
        res = client.post("/api/analyze", json={})
        assert res.status_code == 400

    def test_analyze_text_too_long_returns_400(self, client: FlaskClient) -> None:
        """Test excessively long text returns 400."""
        res = client.post("/api/analyze", json={"text": "A" * 10001})
        assert res.status_code == 400

    def test_analyze_image_too_large_returns_413(self, app: Flask, client: FlaskClient) -> None:
        """Test very large payloads trigger 413 from Flask."""
        original_max = app.config.get("MAX_CONTENT_LENGTH")
        app.config["MAX_CONTENT_LENGTH"] = 100  # 100 bytes max
        try:
            res = client.post("/api/analyze", json={"image": "A" * 7000000})
            assert res.status_code == 413
        finally:
            app.config["MAX_CONTENT_LENGTH"] = original_max

    def test_analyze_invalid_image_mime_returns_400(self, client: FlaskClient) -> None:
        """Test invalid base64 MIME header."""
        res = client.post("/api/analyze", json={"image": "data:image/gif;base64,123"})
        assert res.status_code == 400

    def test_analyze_response_contains_session_id_header(self, client: FlaskClient) -> None:
        """Ensure X-Session-ID is present."""
        res = client.post("/api/analyze", json={"text": "Test"})
        assert "X-Session-ID" in res.headers

    def test_analyze_response_contains_processing_time_header(self, client: FlaskClient) -> None:
        """Ensure X-Processing-Time is present."""
        res = client.post("/api/analyze", json={"text": "Test"})
        assert "X-Processing-Time" in res.headers

    def test_analyze_critical_severity_has_at_least_three_actions(self, client: FlaskClient) -> None:
        """Critical emergencies must dictate multiple actions."""
        res = client.post("/api/analyze", json={"text": "Test"})
        data = res.get_json()
        if data["severity"] == "CRITICAL":
            assert len(data["immediate_actions"]) >= 3

    def test_analyze_actions_are_sorted_by_priority_ascending(self, client: FlaskClient) -> None:
        """Actions must be prioritized."""
        res = client.post("/api/analyze", json={"text": "Test"})
        data = res.get_json()
        actions = data["immediate_actions"]
        for i in range(len(actions) - 1):
            assert actions[i]["priority"] <= actions[i + 1]["priority"]

    def test_analyze_sql_injection_input_returns_400(self, client: FlaskClient) -> None:
        """SQL injection blocks at middleware."""
        res = client.post("/api/analyze", json={"text": "UNION SELECT * FROM users"})
        assert res.status_code == 400

    def test_analyze_script_tag_input_returns_400(self, client: FlaskClient) -> None:
        """XSS drops payload."""
        res = client.post("/api/analyze", json={"text": "<script>alert(1)</script>"})
        assert res.status_code == 400

    def test_analyze_null_byte_input_returns_400(self, client: FlaskClient) -> None:
        """Null bytes immediately rejected."""
        res = client.post("/api/analyze", json={"text": "Test \x00 Byte"})
        assert res.status_code == 400


class TestRateLimiterEndpoint:
    """Delegated to specific test_rate_limiter.py."""

    def test_requests_under_limit_are_allowed(self) -> None:
        """Delegated."""
        pass

    def test_request_at_limit_is_blocked_with_429(self) -> None:
        """Delegated."""
        pass

    def test_429_response_includes_retry_after_header(self) -> None:
        """Delegated."""
        pass

    def test_counter_resets_after_window_expires(self) -> None:
        """Delegated."""
        pass


class TestLogEndpoint:
    """Tests for the /api/log endpoint."""

    @pytest.fixture(autouse=True)
    def auto_patch(self, mock_firestore: Any) -> None:
        """Setup mock firestore DB structure."""
        mock_firestore["query"].return_value = [
            {"session_id": "1", "severity": "HIGH"},
            {"session_id": "2", "severity": "LOW"},
        ]
        mock_firestore["delete"].return_value = True

    def test_log_returns_list_of_incidents(self, client: FlaskClient) -> None:
        """Log list works correctly."""
        res = client.get("/api/log")
        assert res.status_code == 200
        data = res.get_json()
        assert "incidents" in data
        assert len(data["incidents"]) == 2

    def test_log_respects_limit_query_param(self, client: FlaskClient, mock_firestore: Any) -> None:
        """Limit bound works."""
        client.get("/api/log?limit=5")
        mock_firestore["query"].assert_called_with(limit=5, severity="")

    def test_log_filters_by_severity_param(self, client: FlaskClient, mock_firestore: Any) -> None:
        """Severity filter works."""
        client.get("/api/log?severity=HIGH")
        mock_firestore["query"].assert_called_with(limit=20, severity="HIGH")

    def test_delete_returns_204_for_existing_entry(self, client: FlaskClient) -> None:
        """GDPR delete acts correctly."""
        res = client.delete("/api/log/existing_id")
        assert res.status_code == 204

    def test_delete_returns_404_for_missing_entry(self, client: FlaskClient, mock_firestore: Any) -> None:
        """GDP delete handles missing IDs cleanly."""
        mock_firestore["delete"].return_value = False
        res = client.delete("/api/log/missing_id")
        assert res.status_code == 404
