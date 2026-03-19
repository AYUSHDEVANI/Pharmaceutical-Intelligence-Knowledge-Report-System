"""ClinicalTrials MCP Tools."""
import logging
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("mcp_servers.clinicaltrials.tools")


def register_tools(mcp: FastMCP, client):
    @mcp.tool()
    async def clinicaltrials_search(drug_name: str) -> dict:
        """Search active clinical trials for a drug from ClinicalTrials.gov (title, status, phase, conditions).

        Args:
            drug_name: Name of the drug
        """
        logger.info(f"clinicaltrials_search: '{drug_name}'")
        return await client.search_trials(drug_name)

    @mcp.tool()
    async def health_check() -> str:
        """Check if the ClinicalTrials.gov upstream API is responsive."""
        ok = await client.check_health()
        return "Healthy" if ok else "Degraded"
