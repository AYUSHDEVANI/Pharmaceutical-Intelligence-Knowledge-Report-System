"""
RxNorm MCP Server — Router
=============================
Defines the API endpoints:
  POST /query   — query RxNorm for drug information
  GET  /health  — server and upstream health status
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from shared.schemas import MCPRequest, MCPResponse, HealthResponse

from .connector import RxNormConnector

logger = logging.getLogger("mcp.rxnorm.router")

router = APIRouter()

# The connector instance is attached at app startup (see main.py)
_connector: RxNormConnector | None = None


def set_connector(connector: RxNormConnector) -> None:
    """Called by main.py during startup to inject the connector."""
    global _connector
    _connector = connector


def get_connector() -> RxNormConnector:
    """Retrieve the connector; raise if not initialized."""
    if _connector is None:
        raise RuntimeError("Connector not initialized")
    return _connector


# ---------------------------------------------------------------------------
# POST /query
# ---------------------------------------------------------------------------

@router.post(
    "/query",
    response_model=MCPResponse,
    summary="Query RxNorm for drug information",
    description=(
        "Accepts a drug name (and optional identifiers) and returns "
        "RxCUI, ingredient name, brand names, and synonyms from RxNorm."
    ),
)
async def query_drug(body: MCPRequest, request: Request) -> MCPResponse:
    """Query RxNorm and return results in the standard MCP envelope."""
    connector = get_connector()

    # Attach source info to request state for exception handlers
    request.state.source_id = connector.source_id
    request.state.source_name = connector.source_name
    request.state.server_version = connector.server_version

    result = await connector.query(body)
    return result


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns server status, uptime, and upstream connectivity.",
)
async def health_check() -> HealthResponse:
    """Return server health including RxNorm upstream reachability."""
    connector = get_connector()
    upstream_ok = await connector.check_upstream_health()

    return HealthResponse(
        status="healthy" if upstream_ok else "degraded",
        source_id=connector.source_id,
        name=connector.source_name,
        version=connector.server_version,
        uptime_seconds=connector.uptime_seconds,
        upstream_reachable=upstream_ok,
    )
