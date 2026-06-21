"""Token-bucket rate limiter for async operations.

Use ``RateLimiter`` to throttle plugin requests and avoid hitting API
rate limits.  The limiter is async-native and uses ``asyncio.sleep``.
"""
from __future__ import annotations

import asyncio
import time


class RateLimiter:
    """Async token-bucket rate limiter.

    Parameters
    ----------
    max_requests:
        Maximum number of requests allowed in the time window.
    per_seconds:
        Duration of the sliding window in seconds.
    """

    def __init__(self, max_requests: int = 5, per_seconds: float = 1.0) -> None:
        self._max_requests = max_requests
        self._per_seconds = per_seconds
        self._tokens = float(max_requests)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            float(self._max_requests),
            self._tokens + elapsed * (self._max_requests / self._per_seconds),
        )
        self._last_refill = now

    async def acquire(self) -> None:
        """Wait until a token is available, then consume one."""
        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
            # Not enough tokens — sleep briefly and retry
            await asyncio.sleep(0.05)
