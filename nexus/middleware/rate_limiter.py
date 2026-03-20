"""Rate limiting middleware using an in-memory sliding window."""

import hashlib
import time
from functools import wraps
from typing import Callable, Any
from flask import request
from exceptions import RateLimitError

# Structure: { ip_hash: { endpoint: [timestamp1, timestamp2, ...] } }
_rate_limit_cache: dict[str, dict[str, list[float]]] = {}

def get_ip_hash(ip_address: str) -> str:
    """Hash the client IP address using SHA-256 for privacy."""
    return hashlib.sha256(ip_address.encode('utf-8')).hexdigest()

def clean_old_timestamps(timestamps: list[float], current_time: float, window: int) -> list[float]:
    """Remove timestamps older than the specified time window in seconds."""
    cutoff = current_time - window
    return [t for t in timestamps if t > cutoff]

def check_rate_limit(client_ip: str, endpoint: str, limit: int, window_seconds: int) -> int:
    """Check if the request exceeds the limit for the sliding window.
    
    Returns:
        0 if allowed, otherwise the number of seconds to retry after.
    """
    if not client_ip:
        return 0

    ip_hash = get_ip_hash(client_ip)
    current_time = time.time()

    if ip_hash not in _rate_limit_cache:
        _rate_limit_cache[ip_hash] = {}
        
    if endpoint not in _rate_limit_cache[ip_hash]:
        _rate_limit_cache[ip_hash][endpoint] = []

    # Clean old records
    timestamps = _rate_limit_cache[ip_hash][endpoint]
    timestamps = clean_old_timestamps(timestamps, current_time, window_seconds)
    _rate_limit_cache[ip_hash][endpoint] = timestamps

    if len(timestamps) >= limit:
        # Calculate when the oldest request will drop out of the window
        oldest_in_window = timestamps[0]
        retry_after = int(window_seconds - (current_time - oldest_in_window))
        if retry_after <= 0:
            retry_after = 1
        return retry_after

    # Allowed, record this request
    timestamps.append(current_time)
    return 0

def rate_limit(limit: int, window_seconds: int, endpoint_name: str) -> Callable[..., Any]:
    """Decorator to enforce strict rate limiting on route handlers."""
    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(f)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            client_ip = request.remote_addr or request.headers.get("X-Forwarded-For", "0.0.0.0")
            
            # Global limit: 100 per hour (3600 seconds)
            global_retry = check_rate_limit(client_ip, "global", 100, 3600)
            if global_retry > 0:
                raise RateLimitError("Too Many Requests")
                
            # Specific endpoint limit
            endpoint_retry = check_rate_limit(client_ip, endpoint_name, limit, window_seconds)
            
            retry_after = max(global_retry, endpoint_retry)
            if retry_after > 0:
                err = RateLimitError("Too Many Requests")
                # We can attach the retry_after attribute to be handled by app.py, 
                # but since we just return standard 429, we handle headers manually here or in error handler
                # By prompt requirements: 429 with a Retry-After header.
                # A quick way is to raise, catch it in route or custom response.
                # But Werkzeug HTTPException makes setting headers easier.
                pass
            
            if retry_after > 0:
                # Custom exception handling to pass retry_after
                from werkzeug.exceptions import TooManyRequests
                e = TooManyRequests("Too Many Requests")
                e.response = __import__("flask").jsonify({"error": "Too Many Requests. Please try again later.", "status": 429})
                e.response.status_code = 429
                e.response.headers["Retry-After"] = str(retry_after)
                raise e

            return f(*args, **kwargs)
        return wrapped
    return decorator
