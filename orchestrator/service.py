"""
PIKRS Orchestrator — Service Layer
====================================
The main orchestration entrypoint.
Orchestrates the client calls, aggregation, and normalization.
"""

from __future__ import annotations

import logging

from .models import DrugProfile
from .mcp_client import query_all_mcp_servers
from .aggregator import aggregate_mcp_responses
from .normalizer import normalize_drug_profile

logger = logging.getLogger("pikrs.orchestrator.service")

async def generate_drug_profile(drug_name: str) -> DrugProfile:
    """
    Generate a unified drug intelligence profile by querying all
    registered MCP servers in parallel.
    
    1. Call the MCP client to execute parallel async requests
    2. Pass successful results to the aggregator
    3. Normalize the final assembled payload
    4. Return the pydantic DrugProfile object
    """
    logger.info(f"Starting orchestration for drug: '{drug_name}'")
    
    # 1. Parallel execution
    mcp_results = await query_all_mcp_servers(drug_name)
    
    # 2. Aggregation
    profile = aggregate_mcp_responses(drug_name, mcp_results)
    
    # 3. Normalization
    profile = normalize_drug_profile(profile)
    
    logger.info(f"Successfully generated profile for '{profile.drug_name}' consisting of {len(profile.sources)} sources.")
    return profile
