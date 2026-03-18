"""
MCP Standard Exceptions
========================
Custom exception hierarchy mapped to HTTP status codes and MCP error codes.
Includes a `register_exception_handlers` function to install all handlers
on any FastAPI application.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .schemas import ErrorDetail, MCPErrorResponse, ResponseMetadata, SourceInfo

logger = logging.getLogger("mcp.exceptions")


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

class MCPBaseError(Exception):
    """Base class for all MCP errors."""

    http_status: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        retry_after: float | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.retry_after = retry_after


class DrugNotFoundError(MCPBaseError):
    http_status = 404
    error_code = "DRUG_NOT_FOUND"


class UpstreamAPIError(MCPBaseError):
    http_status = 502
    error_code = "UPSTREAM_ERROR"


class UpstreamTimeoutError(MCPBaseError):
    http_status = 504
    error_code = "UPSTREAM_TIMEOUT"


class RateLimitedError(MCPBaseError):
    http_status = 429
    error_code = "RATE_LIMITED"

    def __init__(self, message: str = "Rate limit exceeded", retry_after: float = 1.0, **kwargs):
        super().__init__(message, retry_after=retry_after, **kwargs)


class InputValidationError(MCPBaseError):
    http_status = 422
    error_code = "VALIDATION_ERROR"


class MCPInternalError(MCPBaseError):
    http_status = 500
    error_code = "INTERNAL_ERROR"


# ---------------------------------------------------------------------------
# FastAPI exception handlers
# ---------------------------------------------------------------------------

def _build_error_response(
    exc: MCPBaseError,
    request: Request,
    start_time: float | None = None,
) -> JSONResponse:
    """Build a standardised MCPErrorResponse from an MCP exception."""

    request_id = getattr(request.state, "request_id", None) or "unknown"
    source_id = getattr(request.state, "source_id", None)
    source_name = getattr(request.state, "source_name", None)
    server_version = getattr(request.state, "server_version", "1.0.0")

    elapsed = (time.perf_counter() - start_time) * 1000 if start_time else 0.0

    source = None
    if source_id and source_name:
        source = SourceInfo(source_id=source_id, name=source_name, url="")

    error_resp = MCPErrorResponse(
        source=source,
        error=ErrorDetail(
            code=exc.error_code,
            message=exc.message,
            details=exc.details,
            retry_after=exc.retry_after,
        ),
        metadata=ResponseMetadata(
            request_id=request_id,
            response_time_ms=round(elapsed, 2),
            server_version=server_version,
        ),
    )

    logger.warning(
        "MCP error: %s | code=%s | request_id=%s",
        exc.message,
        exc.error_code,
        request_id,
    )

    return JSONResponse(
        status_code=exc.http_status,
        content=error_resp.model_dump(mode="json"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Install MCP exception handlers on *app*."""

    @app.exception_handler(MCPBaseError)
    async def _mcp_error_handler(request: Request, exc: MCPBaseError) -> JSONResponse:
        start_time = getattr(request.state, "start_time", None)
        return _build_error_response(exc, request, start_time)

    @app.exception_handler(Exception)
    async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        mcp_exc = MCPInternalError(message="An unexpected internal error occurred")
        start_time = getattr(request.state, "start_time", None)
        return _build_error_response(mcp_exc, request, start_time)
