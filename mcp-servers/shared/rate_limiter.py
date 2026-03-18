"""
Token-Bucket Rate Limiter
==========================
Async-safe rate limiter that enforces a maximum requests-per-second
against upstream APIs. Raises `RateLimitedError` when the bucket is empty.
"""

from __future__ import annotations

import asyncio
import time

from .exceptions import RateLimitedError


class TokenBucketRateLimiter:
    """
    An async token-bucket rate limiter.

    Parameters
    ----------
    rate : float
        Maximum sustained requests per second.
    burst : int | None
        Maximum burst size.  Defaults to ``int(rate)``.
    """

    def __init__(self, rate: float, burst: int | None = None):
        self.rate = rate
        self.burst = burst if burst is not None else max(1, int(rate))
        self._tokens: float = float(self.burst)
        self._last_refill: float = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """
        Acquire a token.  Raises ``RateLimitedError`` if no tokens
        are available after refilling.
        """
        async with self._lock:
            self._refill()
            if self._tokens >= 1.0:
                self._tokens -= 1.0
            else:
                retry_after = (1.0 - self._tokens) / self.rate
                raise RateLimitedError(
                    message=f"Rate limit exceeded ({self.rate} req/s). Try again in {retry_after:.1f}s.",
                    retry_after=round(retry_after, 2),
                )

    def _refill(self) -> None:
        """Add tokens based on elapsed time since last refill."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(float(self.burst), self._tokens + elapsed * self.rate)
        self._last_refill = now
