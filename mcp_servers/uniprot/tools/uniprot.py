import logging
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("mcp_servers.uniprot.tools")

def register_tools(mcp: FastMCP, client):

    @mcp.tool()
    async def uniprot_search(drug_name: str, limit: int = 20) -> dict:
        """
        Search UniProt for protein targets and biological functions related to a drug.

        Args: 
            drug_name: Name of the drug
            limit: Number of results to return (default: 20)
        """

        logger.info(f"uniprot_search: '{drug_name}' (limit={limit})")

        return await client.search_proteins(drug_name, limit = limit)
    
    @mcp.tool()
    async def health_check() -> str:
        """Check if UniProt API is responsive."""

        ok = await client.check_health()

        return "Healthy" if ok else "Degraded"