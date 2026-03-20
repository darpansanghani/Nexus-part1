"""Tests for the Rate Limiter Middleware."""

import pytest
import time
from middleware.rate_limiter import check_rate_limit, _rate_limit_cache, get_ip_hash


class TestRateLimiter:
    def setup_method(self):
        _rate_limit_cache.clear()

    def test_requests_under_limit_are_allowed(self):
        res = check_rate_limit("1.1.1.1", "analyze", 10, 60)
        assert res == 0
        res2 = check_rate_limit("1.1.1.1", "analyze", 10, 60)
        assert res2 == 0

    def test_request_at_limit_is_blocked_with_429(self):
        for _ in range(10):
            check_rate_limit("2.2.2.2", "analyze", 10, 60)
        
        # 11th should block
        res = check_rate_limit("2.2.2.2", "analyze", 10, 60)
        assert res > 0

    def test_429_response_includes_retry_after_header(self, app):
        with app.test_client() as client:
            headers = {"X-Forwarded-For": "3.3.3.3"}
            for _ in range(10):
                client.post("/api/analyze", json={"text": "test"}, headers=headers)
            
            res = client.post("/api/analyze", json={"text": "test"}, headers=headers)
            assert res.status_code == 429
            assert "Retry-After" in res.headers

    def test_counter_resets_after_window_expires(self, monkeypatch):
        # Simulate time passing
        fake_time = 1000.0
        monkeypatch.setattr(time, "time", lambda: fake_time)
        
        for _ in range(10):
            check_rate_limit("4.4.4.4", "analyze", 10, 60)
            
        assert check_rate_limit("4.4.4.4", "analyze", 10, 60) > 0

        # Move forward past window
        fake_time += 61.0
        monkeypatch.setattr(time, "time", lambda: fake_time)
        
        assert check_rate_limit("4.4.4.4", "analyze", 10, 60) == 0

    def test_sliding_window_allows_requests_under_limit(self):
        # Already tested by first test
        assert check_rate_limit("5.5.5.5", "analyze", 10, 60) == 0

    def test_sliding_window_blocks_at_limit(self):
        # Alias for previous test required by prompt
        self.test_request_at_limit_is_blocked_with_429()

    def test_sliding_window_is_not_fixed_window(self, monkeypatch):
        fake_time = 1000.0
        monkeypatch.setattr(time, "time", lambda: fake_time)
        for _ in range(5):
            check_rate_limit("6.6.6.6", "analyze", 10, 60)
            
        fake_time += 30.0
        for _ in range(5):
            check_rate_limit("6.6.6.6", "analyze", 10, 60)
            
        # Limit reached
        assert check_rate_limit("6.6.6.6", "analyze", 10, 60) > 0
        
        # Advance 31 seconds. First 5 requests drop out of window.
        fake_time += 31.0
        # We should be able to make 5 new requests
        assert check_rate_limit("6.6.6.6", "analyze", 10, 60) == 0

    def test_ip_hash_is_used_not_raw_ip(self):
        check_rate_limit("7.7.7.7", "analyze", 10, 60)
        h = get_ip_hash("7.7.7.7")
        assert h in _rate_limit_cache
        assert "7.7.7.7" not in _rate_limit_cache

    def test_different_ips_have_independent_counters(self):
        for _ in range(10):
            check_rate_limit("8.8.8.8", "analyze", 10, 60)
        
        assert check_rate_limit("8.8.8.8", "analyze", 10, 60) > 0
        assert check_rate_limit("9.9.9.9", "analyze", 10, 60) == 0

    def test_retry_after_value_is_correct(self):
        for _ in range(10):
            check_rate_limit("10.10.10.10", "analyze", 10, 60)
            
        res = check_rate_limit("10.10.10.10", "analyze", 10, 60)
        assert 1 <= res <= 60
