from fastapi import APIRouter, Request
from shared.schemas import MCPRequest, MCPResponse, HealthResponse

from .connector import PubMedConnector

router = APIRouter()

_connector: PubMedConnector | None = None


def set_connector(connector: PubMedConnector):
    global _connector
    _connector = connector


def get_connector() -> PubMedConnector:
    if _connector is None:
        raise RuntimeError("Connector not initialized")
    return _connector


@router.post("/query", response_model=MCPResponse)
async def query_drug(body: MCPRequest, request: Request):

    connector = get_connector()

    request.state.source_id = connector.source_id
    request.state.source_name = connector.source_name
    request.state.server_version = connector.server_version

    return await connector.query(body)


@router.get("/health", response_model=HealthResponse)
async def health_check():

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