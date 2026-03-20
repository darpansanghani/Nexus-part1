"""Rate limiting middleware using an in-memory sliding window."""

import hashlib
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import request
from werkzeug.exceptions import TooManyRequests

from constants import (
    HTTP_429_TOO_MANY_REQUESTS,
    RATE_LIMIT_FALLBACK_RETRY_AFTER,
    RATE_LIMIT_GLOBAL_REQUESTS,
    RATE_LIMIT_GLOBAL_WINDOW,
)
from exceptions import RateLimitError
from logger import get_logger

logger = get_logger(__name__)

# Structure: { ip_hash: { endpoint: [timestamp1, timestamp2, ...] } }
_rate_limit_cache: dict[str, dict[str, list[float]]] = {}


def get_ip_hash(ip_address: str) -> str:
    """Hash the client IP address using SHA-256 for privacy.

    Args:
        ip_address: The raw IP address string.

    Returns:
        The SHA-256 hash of the IP address.
    """
    return hashlib.sha256(ip_address.encode("utf-8")).hexdigest()


def clean_old_timestamps(timestamps: list[float], current_time: float, window: int) -> list[float]:
    """Remove timestamps older than the specified time window in seconds.

    Args:
        timestamps: The list of timestamps to check.
        current_time: The current epoch time in seconds.
        window: The time window in seconds.

    Returns:
        A list of timestamps that fall within the current window.
    """
    cutoff = current_time - window
    return [t for t in timestamps if t > cutoff]


def check_rate_limit(client_ip: str, endpoint: str, limit: int, window_seconds: int) -> int:
    """Check if the request exceeds the limit for the sliding window.

    Args:
        client_ip: The raw IP address string.
        endpoint: The name of the endpoint being accessed.
        limit: The maximum number of requests allowed.
        window_seconds: The time window in seconds.

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
            retry_after = RATE_LIMIT_FALLBACK_RETRY_AFTER
        return retry_after

    # Allowed, record this request
    timestamps.append(current_time)
    return 0


def rate_limit(limit: int, window_seconds: int, endpoint_name: str) -> Callable[..., Any]:
    """Decorator to enforce strict rate limiting on route handlers.

    Args:
        limit: The maximum number of requests allowed.
        window_seconds: The time window in seconds.
        endpoint_name: The name of the endpoint for tracking limit.

    Returns:
        The decorated function.
    """

    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(f)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            # Avoid binding warning by using loopback
            client_ip = request.remote_addr or request.headers.get("X-Forwarded-For", "127.0.0.1")

            # Global limit
            global_retry = check_rate_limit(
                str(client_ip), "global", RATE_LIMIT_GLOBAL_REQUESTS, RATE_LIMIT_GLOBAL_WINDOW
            )
            if global_retry > 0:
                logger.warning("Global rate limit exceeded", extra={"ip": client_ip})
                raise RateLimitError("Too Many Requests")

            # Specific endpoint limit
            endpoint_retry = check_rate_limit(str(client_ip), endpoint_name, limit, window_seconds)

            retry_after = max(global_retry, endpoint_retry)

            if retry_after > 0:
                logger.warning("Endpoint rate limit exceeded", extra={"endpoint": endpoint_name})
                # Custom exception handling to pass retry_after
                e = TooManyRequests("Too Many Requests")
                e.response = __import__("flask").jsonify(
                    {"error": "Too Many Requests. Please try again later.", "status": HTTP_429_TOO_MANY_REQUESTS}
                )
                e.response.status_code = HTTP_429_TOO_MANY_REQUESTS
                e.response.headers["Retry-After"] = str(retry_after)
                raise e

            return f(*args, **kwargs)

        return wrapped

    return decorator
