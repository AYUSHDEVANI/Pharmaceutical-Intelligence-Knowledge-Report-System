from mcp.server.fastmcp import FastMCP

def register_tools(mcp: FastMCP, client):

    @mcp.tool()
    async def faers_search(drug_name: str):
        """
        Get Adverse event reports for a given drug from FAERS.
        """

        return await client.faers_search(drug_name)
    

    @mcp.tool()
    async def faers_check_health():
        """
        Check FAERS API Availability.
        """
        return {"healthy": await client.check_health()}