from typing import Any, Dict
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from shared.schemas import MCPRequest, MCPResponse, HealthResponse

from .connector import ChemblConnector

router = APIRouter()

_connector: ChemblConnector | None = None


def set_connector(connector: ChemblConnector):
    global _connector
    _connector = connector


def get_connector() -> ChemblConnector:
    if _connector is None:
        raise RuntimeError("Connector not initialized")
    return _connector


class ToolCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]



from fastapi import Body

@router.post("/")
async def mcp_rpc(body: dict = Body(...)):

    method = body.get("method")
    params = body.get("params", {})
    request_id = body.get("id")
    if request_id is None:
        request_id = 0

    connector = get_connector()

    # ---- initialize ----
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2025-06-18",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "chembl-mcp",
                    "version": "1.0.0"
                }
            }
        }

    # ---- tools/list ----
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {
                        "name": "chembl_search",
                        "description": "Search drug information from ChEMBL",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "drug_name": {"type": "string"}
                            },
                            "required": ["drug_name"]
                        }
                    }
                ]
            }
        }

    # ---- tools/call ----
    elif method == "tools/call":

        name = params.get("name")
        arguments = params.get("arguments", {})

        if name != "chembl_search":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Unknown tool: {name}"}
            }

        mcp_request = MCPRequest(**arguments)
        result = await connector.query(mcp_request)

        if isinstance(result, dict) and "data" in result:
            clean_result = result["data"]
        else:
            clean_result = result

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {
                        "type": "json",
                        "json": clean_result
                    }
                ]
            }
        }

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": -32601,
            "message": f"Unknown method: {method}"}
    }

@router.get("/tools/list")
@router.post("/tools/list")
async def list_tools():
    return {
        "tools": [
            {
                "name": "chembl_search",
                "description": "Search drug information from ChEMBL",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "drug_name": {
                            "type": "string",
                            "description": "Name of the drug"
                        }
                    },
                    "required": ["drug_name"]
                }
            }
        ]
    }


@router.post("/tools/call")
async def call_tool(body: ToolCallRequest, request: Request):
    if body.name != "chembl_search":
        raise HTTPException(status_code=400, detail=f"Unknown tool: {body.name}")

    if "drug_name" not in body.arguments:
        raise HTTPException(status_code=400, detail="Missing required argument 'drug_name'")

    connector = get_connector()

    # Pass the identifiers from connector to state if they expect it in middleware
    request.state.source_id = connector.source_id
    request.state.source_name = connector.source_name
    request.state.server_version = connector.server_version

    # Convert arguments -> MCPRequest
    mcp_request = MCPRequest(drug_name=body.arguments["drug_name"])
    
    # Call connector.query()
    result = await connector.query(mcp_request)
    
    # Safely retrieve the serialization method via getattr to prevent static type 
    # checkers from reporting "object has no attribute" regardless of Pydantic version.
    dump_method = getattr(result, "model_dump", getattr(result, "dict", None))
    data = dump_method() if dump_method else {}

    # 🔥 unwrap MCP if already wrapped
    if isinstance(data, dict) and "content" in data:
        inner = data["content"][0]

        if isinstance(inner, dict) and "json" in inner:
            clean_data = inner["json"]
        else:
            clean_data = data
    else:
        clean_data = data

    return {
        "content": [
            {
                "type": "json",
                "json": clean_data
            }
        ]
    }


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