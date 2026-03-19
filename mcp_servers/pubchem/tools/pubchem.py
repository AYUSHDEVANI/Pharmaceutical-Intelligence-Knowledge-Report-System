"""PubChem MCP Tools."""
import logging
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("mcp_servers.pubchem.tools")


def register_tools(mcp: FastMCP, client):
    @mcp.tool()
    async def pubchem_search(drug_name: str) -> dict:
        """Search compound properties from PubChem (formula, weight, SMILES, InChI).

        Args:
            drug_name: Name of the drug compound
        """
        logger.info(f"pubchem_search: '{drug_name}'")
        return await client.search_compound(drug_name)

    @mcp.tool()
    async def health_check() -> str:
        """Check if PubChem upstream API is responsive."""
        ok = await client.check_health()
        return "Healthy" if ok else "Degraded"
