"""
MCP Middleware
===============
FastAPI middleware providing:
- Request-ID propagation (client-provided or auto-generated)
- Structured JSON logging for every request/response
- Request timing (populates ``request.state.start_time``)
- Request body size enforcement
"""

from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

logger = logging.getLogger("mcp.middleware")

# Context variable carrying the current request_id, accessible from anywhere
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")

# Default max request body size (1 MB)
DEFAULT_MAX_BODY_BYTES = 1 * 1024 * 1024


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Extracts or generates a ``request_id`` and stores it in
    ``request.state`` + the module-level ``request_id_ctx`` context var.
    Also injects the ``X-Request-ID`` response header.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # Use client-provided header, or generate a new one
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = req_id
        request_id_ctx.set(req_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """Records ``start_time`` on the request and logs elapsed duration."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        start = time.perf_counter()
        request.state.start_time = start

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "request_completed | method=%s path=%s status=%s duration_ms=%.2f request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            getattr(request.state, "request_id", "unknown"),
        )
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects requests with a body exceeding the configured limit."""

    def __init__(self, app, max_bytes: int = DEFAULT_MAX_BODY_BYTES):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_bytes:
            return JSONResponse(
                status_code=413,
                content={
                    "status": "error",
                    "error": {
                        "code": "PAYLOAD_TOO_LARGE",
                        "message": f"Request body exceeds {self.max_bytes} bytes",
                        "details": {},
                        "retry_after": None,
                    },
                    "metadata": {
                        "request_id": getattr(request.state, "request_id", "unknown"),
                        "response_time_ms": 0,
                        "server_version": "1.0.0",
                        "result_count": 0,
                        "cached": False,
                    },
                },
            )
        return await call_next(request)


def register_middleware(app: FastAPI, max_body_bytes: int = DEFAULT_MAX_BODY_BYTES) -> None:
    """Install all standard MCP middleware on *app* in correct order."""
    # Order matters: outermost middleware executes first
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=max_body_bytes)
    app.add_middleware(TimingMiddleware)
    app.add_middleware(RequestIDMiddleware)
