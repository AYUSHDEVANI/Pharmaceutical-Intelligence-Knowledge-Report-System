"""ChEMBL MCP Tools."""
import logging
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("mcp_servers.chembl.tools")


def register_tools(mcp: FastMCP, client):
    @mcp.tool()
    async def chembl_search(drug_name: str) -> dict:
        """Search drug information from ChEMBL (classification, approval, pharmacology, safety, targets, molecular properties).

        Args:
            drug_name: Name of the drug
        """
        logger.info(f"chembl_search: '{drug_name}'")
        return await client.search_molecule(drug_name)

    @mcp.tool()
    async def chembl_targets(drug_name: str) -> list:
        """Retrieve specific mechanism-of-action targets for a drug from ChEMBL.

        Args:
            drug_name: Name of the drug
        """
        logger.info(f"chembl_targets: '{drug_name}'")
        data = await client.search_molecule(drug_name)
        return data.get("results", {}).get("targets", [])

    @mcp.tool()
    async def health_check() -> str:
        """Check if the ChEMBL upstream API is responsive."""
        ok = await client.check_health()
        return "Healthy" if ok else "Degraded"
