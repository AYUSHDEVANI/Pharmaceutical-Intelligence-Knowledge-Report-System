from fastapi import APIRouter, Request
from shared.schemas import MCPRequest, MCPResponse, HealthResponse

router = APIRouter()

_connector = None


def set_connector(connector):
    global _connector
    _connector = connector


def get_connector():
    if _connector is None:
        raise RuntimeError("Connector not initialized")
    return _connector

@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        source_id="clinicaltrials",
        name="ClinicalTrials.gov",
        version="1.0.0",
        uptime_seconds=0,
        upstream_reachable=True
    )



@router.post("/query", response_model=MCPResponse)
async def query(body: MCPRequest, request: Request):

    connector = get_connector()

    request.state.source_id = connector.source_id
    request.state.source_name = connector.source_name
    request.state.server_version = connector.server_version

    return await connector.query(body)