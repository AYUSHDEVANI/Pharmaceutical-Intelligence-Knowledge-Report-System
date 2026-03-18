"""
OpenFDA MCP Server — Router
=============================
Defines the API endpoints:
  POST /query   — query OpenFDA for drug labels
  GET  /health  — server and upstream health status
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from shared.schemas import MCPRequest, MCPResponse, HealthResponse

from .connector import OpenFDAConnector

logger = logging.getLogger("mcp.openfda.router")

router = APIRouter()

# The connector instance is attached at app startup (see main.py)
_connector: OpenFDAConnector | None = None


def set_connector(connector: OpenFDAConnector) -> None:
    """Called by main.py during startup to inject the connector."""
    global _connector
    _connector = connector


def get_connector() -> OpenFDAConnector:
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
    summary="Query OpenFDA for drug label information",
    description=(
        "Accepts a drug name and returns FDA label sections including "
        "indications, dosage, warnings, and adverse reactions."
    ),
)
async def query_drug(body: MCPRequest, request: Request) -> MCPResponse:
    """Query OpenFDA and return results in the standard MCP envelope."""
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
    """Return server health including OpenFDA upstream reachability."""
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
