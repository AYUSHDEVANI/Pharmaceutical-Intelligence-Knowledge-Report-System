"""
Retry Logic
============
Async retry decorator with exponential backoff and jitter.
Retries only on transient errors (5xx, timeouts, connection errors).
"""

from __future__ import annotations

import asyncio
import functools
import logging
import random
from typing import Any, Callable, Type

import httpx

logger = logging.getLogger("mcp.retry")

# Exception types that warrant an automatic retry
TRANSIENT_EXCEPTIONS: tuple[Type[BaseException], ...] = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.ReadError,
    httpx.WriteError,
    httpx.PoolTimeout,
    ConnectionError,
    TimeoutError,
)


def is_transient_http_status(status_code: int) -> bool:
    """Return True if the HTTP status code is transiently retriable."""
    return status_code in {429, 500, 502, 503, 504}


class RetryConfig:
    """Configuration for the retry decorator."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 0.5,
        max_delay: float = 10.0,
        jitter: bool = True,
        retryable_exceptions: tuple[Type[BaseException], ...] = TRANSIENT_EXCEPTIONS,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions


def _compute_delay(attempt: int, config: RetryConfig) -> float:
    """Exponential backoff with optional jitter."""
    delay = min(config.base_delay * (2 ** attempt), config.max_delay)
    if config.jitter:
        delay = delay * (0.5 + random.random())  # noqa: S311
    return delay


def with_retry(config: RetryConfig | None = None) -> Callable:
    """
    Async retry decorator.

    Usage::

        @with_retry(RetryConfig(max_retries=3))
        async def fetch_data(url: str) -> dict:
            ...
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: BaseException | None = None

            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except config.retryable_exceptions as exc:
                    last_exception = exc
                    if attempt < config.max_retries:
                        delay = _compute_delay(attempt, config)
                        logger.warning(
                            "Retry %d/%d for %s after %.2fs — %s: %s",
                            attempt + 1,
                            config.max_retries,
                            func.__qualname__,
                            delay,
                            type(exc).__name__,
                            exc,
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "All %d retries exhausted for %s — %s: %s",
                            config.max_retries,
                            func.__qualname__,
                            type(exc).__name__,
                            exc,
                        )

            raise last_exception  # type: ignore[misc]

        return wrapper

    return decorator
