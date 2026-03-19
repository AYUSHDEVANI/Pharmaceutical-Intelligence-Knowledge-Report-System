"""RxNorm MCP Tools."""
import logging
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("mcp_servers.rxnorm.tools")


def register_tools(mcp: FastMCP, client):
    @mcp.tool()
    async def rxnorm_search(drug_name: str) -> dict:
        """Search drug normalization data from RxNorm (RxCUI, ingredients, brand names, synonyms).

        Args:
            drug_name: Name of the drug
        """
        logger.info(f"rxnorm_search: '{drug_name}'")
        return await client.search_drug(drug_name)

    @mcp.tool()
    async def health_check() -> str:
        """Check if the RxNorm upstream API is responsive."""
        ok = await client.check_health()
        return "Healthy" if ok else "Degraded"
