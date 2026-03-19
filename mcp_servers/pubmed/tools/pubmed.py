"""PubMed MCP Tools."""
import logging
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("mcp_servers.pubmed.tools")


def register_tools(mcp: FastMCP, client):
    @mcp.tool()
    async def pubmed_search(drug_name: str) -> dict:
        """Search recent research papers about a drug from PubMed (title, journal, year).

        Args:
            drug_name: Name of the drug
        """
        logger.info(f"pubmed_search: '{drug_name}'")
        return await client.search_papers(drug_name)

    @mcp.tool()
    async def health_check() -> str:
        """Check if the PubMed upstream API is responsive."""
        ok = await client.check_health()
        return "Healthy" if ok else "Degraded"
