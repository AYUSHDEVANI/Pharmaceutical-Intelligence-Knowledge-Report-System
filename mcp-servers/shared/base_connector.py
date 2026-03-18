"""
Base Connector
===============
Abstract base class for all MCP data-source connectors.

Provides:
- ``httpx.AsyncClient`` lifecycle management with connection pooling
- Built-in retry via ``retry.py`` and rate-limiting via ``rate_limiter.py``
- A standard ``query()`` orchestration method
- Abstract hooks for subclass customisation
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from .exceptions import DrugNotFoundError, UpstreamAPIError, UpstreamTimeoutError
from .rate_limiter import TokenBucketRateLimiter
from .retry import RetryConfig, with_retry
from .schemas import (
    MCPRequest,
    MCPResponse,
    MCPResponseData,
    ResponseMetadata,
    SourceInfo,
)

logger = logging.getLogger("mcp.connector")


class BaseConnector(ABC):
    """
    Abstract connector all MCP servers inherit from.

    Subclasses **must** implement:
    - ``build_request_url(request)`` → str
    - ``parse_response(raw, request)`` → dict containing ``drug_name``,
      ``identifiers``, and ``results`` keys.

    Subclasses **may** override:
    - ``check_upstream_health()`` for the ``/health`` endpoint.
    """

    source_id: str = "unknown"
    source_name: str = "Unknown"
    source_url: str = ""

    def __init__(
        self,
        *,
        timeout: float = 15.0,
        max_retries: int = 3,
        rate_limit: float = 5.0,
        server_version: str = "1.0.0",
    ):
        self.timeout = timeout
        self.server_version = server_version
        self._client: Optional[httpx.AsyncClient] = None
        self._started_at: float = time.monotonic()

        # Retry configuration
        self._retry_config = RetryConfig(
            max_retries=max_retries,
            base_delay=0.5,
            max_delay=10.0,
        )

        # Rate limiter (per-source)
        self._rate_limiter = TokenBucketRateLimiter(rate=rate_limit)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def startup(self) -> None:
        """Create the shared ``httpx.AsyncClient`` with connection pooling."""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout, connect=5.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            follow_redirects=True,
            headers={"Accept": "application/json"},
        )
        self._started_at = time.monotonic()
        logger.info("Connector started: %s", self.source_name)

    async def shutdown(self) -> None:
        """Close the HTTP client and release resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.info("Connector shutdown: %s", self.source_name)

    @property
    def uptime_seconds(self) -> float:
        return round(time.monotonic() - self._started_at, 1)

    # ------------------------------------------------------------------
    # Abstract hooks for subclasses
    # ------------------------------------------------------------------

    @abstractmethod
    async def build_request_url(self, request: MCPRequest) -> str:
        """Return the upstream URL to query for the given request."""

    @abstractmethod
    async def parse_response(
        self,
        raw: dict[str, Any],
        request: MCPRequest,
    ) -> dict[str, Any]:
        """
        Parse the raw upstream JSON into a dict with keys:
        ``drug_name``, ``identifiers``, ``results``.
        """

    # ------------------------------------------------------------------
    # Core query orchestration
    # ------------------------------------------------------------------

    async def query(self, request: MCPRequest) -> MCPResponse:
        """
        Full query lifecycle:
        1. Build upstream URL
        2. Fetch (with retry + rate-limit)
        3. Parse response
        4. Wrap in standard MCPResponse envelope
        """
        start = time.perf_counter()
        request_id = request.effective_request_id()

        url = await self.build_request_url(request)
        logger.info(
            "Querying %s | url=%s | request_id=%s",
            self.source_name,
            url,
            request_id,
        )

        raw = await self._fetch(url, timeout=request.options.timeout)

        parsed = await self.parse_response(raw, request)
        drug_name = parsed.get("drug_name", request.drug_name)
        identifiers = parsed.get("identifiers", {})
        results = parsed.get("results", {})

        # Apply field filtering if requested
        if request.fields:
            results = {k: v for k, v in results.items() if k in request.fields}

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        return MCPResponse(
            source=SourceInfo(
                source_id=self.source_id,
                name=self.source_name,
                url=self.source_url,
                query_url=url,
                accessed_at=datetime.now(timezone.utc),
            ),
            data=MCPResponseData(
                drug_name=drug_name,
                identifiers=identifiers,
                results=results,
            ),
            metadata=ResponseMetadata(
                request_id=request_id,
                response_time_ms=elapsed_ms,
                server_version=self.server_version,
                result_count=len(results),
                cached=False,
            ),
            raw=raw if request.options.include_raw else None,
        )

    # ------------------------------------------------------------------
    # Internal HTTP fetch with retry + rate-limit
    # ------------------------------------------------------------------

    async def _fetch(self, url: str, timeout: float | None = None) -> dict[str, Any]:
        """
        GET *url* via the shared httpx client.
        Applies rate-limiting, retries on transient errors, and raises
        appropriate MCP exceptions on failure.
        """
        if self._client is None:
            raise RuntimeError("Connector not started. Call startup() first.")

        # Rate-limit check
        await self._rate_limiter.acquire()

        effective_timeout = timeout or self.timeout

        @with_retry(self._retry_config)
        async def _do_fetch() -> dict[str, Any]:
            try:
                resp = await self._client.get(url, timeout=effective_timeout)
            except httpx.TimeoutException as exc:
                raise UpstreamTimeoutError(
                    message=f"Upstream {self.source_name} timed out after {effective_timeout}s",
                    details={"url": url},
                ) from exc
            except httpx.HTTPError as exc:
                raise UpstreamAPIError(
                    message=f"HTTP error from {self.source_name}: {exc}",
                    details={"url": url},
                ) from exc

            if resp.status_code == 404:
                raise DrugNotFoundError(
                    message=f"Resource not found at {self.source_name}",
                    details={"url": url, "status_code": 404},
                )

            if resp.status_code >= 400:
                raise UpstreamAPIError(
                    message=f"{self.source_name} returned HTTP {resp.status_code}",
                    details={"url": url, "status_code": resp.status_code},
                )

            return resp.json() if "application/json" in resp.headers.get("content-type", "") else resp.text

        return await _do_fetch()

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def check_upstream_health(self) -> bool:
        """
        Return True if the upstream API is reachable.
        Override in subclasses for source-specific health checks.
        """
        try:
            if self._client is None:
                return False
            resp = await self._client.get(self.source_url, timeout=5.0)
            return resp.status_code < 500
        except Exception:
            return False
