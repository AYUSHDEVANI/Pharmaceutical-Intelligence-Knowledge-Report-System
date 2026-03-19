"""OpenFDA MCP Tools."""
import logging
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("mcp_servers.openfda.tools")


def register_tools(mcp: FastMCP, client):
    @mcp.tool()
    async def openfda_search(drug_name: str) -> dict:
        """Search FDA drug label data (indications, dosage, warnings, contraindications, adverse reactions, drug interactions).

        Args:
            drug_name: Name of the drug
        """
        logger.info(f"openfda_search: '{drug_name}'")
        return await client.search_drug_label(drug_name)

    @mcp.tool()
    async def health_check() -> str:
        """Check if the OpenFDA upstream API is responsive."""
        ok = await client.check_health()
        return "Healthy" if ok else "Degraded"
