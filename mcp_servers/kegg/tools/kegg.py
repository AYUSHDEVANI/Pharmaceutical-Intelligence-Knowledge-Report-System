"""KEGG MCP Tools."""
import logging
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("mcp_servers.kegg.tools")


def register_tools(mcp: FastMCP, client):
    @mcp.tool()
    async def kegg_search(drug_name: str) -> dict:
        """Search drug entries from the KEGG (Kyoto Encyclopedia of Genes and Genomes) drug database.

        Args:
            drug_name: Name of the drug
        """
        logger.info(f"kegg_search: '{drug_name}'")
        return await client.search_drug(drug_name)

    @mcp.tool()
    async def health_check() -> str:
        """Check if the KEGG upstream API is responsive."""
        ok = await client.check_health()
        return "Healthy" if ok else "Degraded"
