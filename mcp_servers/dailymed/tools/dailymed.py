"""DailyMed MCP Tools"""
import logging
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("mcp_servers.dailymed.tools")


def register_tools(mcp: FastMCP, client):
    
    @mcp.tool()
    async def dailymed_search(drug_name: str) -> dict:
        """Fetch FDA drug label data from DailyMed.

        Args:
            drug_name: Name of the drug
        """
        logger.info(f"dailymed_search: '{drug_name}'")
        return await client.search_drug(drug_name)

    @mcp.tool()
    async def health_check() -> str:
        """Check if DailyMed API is responsive."""
        ok = await client.check_health()
        return "Healthy" if ok else "Degraded"