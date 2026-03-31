"""
PIKRS Orchestrator — MCP Client (stdio transport)
====================================================
Connects to real MCP servers via stdio subprocess transport.
Replaces the old httpx-based HTTP client entirely.

Each MCP server is launched as a child process, queried via
the official MCP SDK's ClientSession, then shut down cleanly.
"""

from __future__ import annotations

import json
import logging
import asyncio
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .config import MCP_SERVERS

logger = logging.getLogger("pikrs.orchestrator.client")


async def call_mcp_server(
    source_id: str,
    config: dict[str, Any],
    drug_name: str,
) -> tuple[str, dict[str, Any] | None]:
    """
    Launch a single MCP server via stdio, call its tool, and return the result.

    Returns:
        (source_id, result_dict) on success, or (source_id, None) on failure.
        The result_dict is shaped to match the aggregator's expected format:
        { "status": "success", "data": { "drug_name": ..., "identifiers": {}, "results": {} } }
    """
    command = config["command"]
    tool_name = config["tool"]
    timeout = config.get("timeout", 20)

    logger.info(f"Connecting to MCP server '{source_id}' via stdio: {command}")

    try:
        server_params = StdioServerParameters(
            command=command[0],
            args=command[1:],
        )

        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize the MCP session handshake
                await session.initialize()

                # Call the tool with the drug_name argument
                result = await asyncio.wait_for(
                    session.call_tool(tool_name, {"drug_name": drug_name}),
                    timeout=timeout,
                )

                # Parse the MCP tool result
                # MCP SDK returns result.content as a list of content blocks
                if result.content:
                    for block in result.content:
                        # TextContent blocks contain JSON as text
                        if hasattr(block, "text"):
                            parsed = json.loads(block.text)
                            
                            # Adapt the new MCP server payloads to what aggregator.py expects
                            if source_id == "pubchem" and isinstance(parsed.get("results"), list) and parsed["results"]:
                                first = parsed["results"][0]
                                parsed["identifiers"] = first.get("identifiers", {})
                                parsed["results"] = {
                                    "molecular_formula": first.get("chemical", {}).get("molecular_formula"),
                                    "molecular_weight": first.get("chemical", {}).get("molecular_weight"),
                                    "iupac_name": first.get("drug", {}).get("naming", {}).get("generic_name"),
                                    "canonical_smiles": first.get("structure", {}).get("canonical_smiles"),
                                }
                            
                            elif source_id == "openfda":
                                drug_label = parsed.get("drug_label", {})
                                safety = parsed.get("safety", {})
                                parsed["results"] = {
                                    "indications": drug_label.get("indications"),
                                    "dosage": drug_label.get("dosage"),
                                    "warnings": safety.get("warnings") or safety.get("boxed_warning"),
                                    "contraindications": drug_label.get("contraindications"),
                                    "adverse_reactions": drug_label.get("adverse_reactions"),
                                    "drug_interactions": drug_label.get("drug_interactions"),
                                }
                                
                            elif source_id == "chembl" and isinstance(parsed.get("results"), list) and parsed["results"]:
                                first = parsed["results"][0]
                                parsed["identifiers"] = first.get("identifiers", {})
                                parsed["results"] = first
                                
                            elif source_id == "kegg" and isinstance(parsed.get("results"), list):
                                parsed["results"] = {"kegg_drugs": parsed["results"]}
                                
                            elif source_id == "rxnorm":
                                if "results" in parsed and "brands" in parsed["results"]:
                                    parsed["results"]["brand_names"] = parsed["results"]["brands"]
                            
                            # Wrap in the envelope format the aggregator expects
                            envelope = {
                                "status": "success",
                                "data": {
                                    "drug_name": parsed.get("drug_name", drug_name),
                                    "identifiers": parsed.get("identifiers", {}),
                                    "results": parsed.get("results", {}),
                                },
                            }
                            logger.info(f"MCP server '{source_id}' returned data successfully")
                            return source_id, envelope

                logger.warning(f"MCP server '{source_id}' returned empty content")
                return source_id, None

    except asyncio.TimeoutError:
        logger.warning(f"MCP server '{source_id}' timed out after {timeout}s")
    except Exception as e:
        logger.warning(f"MCP server '{source_id}' failed: {type(e).__name__}: {e}")

    return source_id, None


async def query_all_mcp_servers(drug_name: str) -> dict[str, Any]:
    """
    Dynamically read the MCP registry and query all configured servers in parallel.

    Returns:
        dict mapping source_id → aggregator-compatible envelope dict.
        Failed servers are silently omitted.
    """
    results: dict[str, Any] = {}

    if not MCP_SERVERS:
        logger.warning("No MCP servers registered in configuration!")
        return results

    # Build concurrent tasks for all registered servers
    tasks = [
        call_mcp_server(source_id, config, drug_name)
        for source_id, config in MCP_SERVERS.items()
    ]

    # Execute all in parallel; return_exceptions guards against crashes
    completed = await asyncio.gather(*tasks, return_exceptions=True)

    for task_result in completed:
        if isinstance(task_result, Exception):
            logger.error(f"Unhandled task exception: {task_result}")
            continue

        source_id, data = task_result
        if data is not None:
            results[source_id] = data

    logger.info(
        f"Retrieved data from {len(results)}/{len(MCP_SERVERS)} MCP servers for '{drug_name}'"
    )
    return results
