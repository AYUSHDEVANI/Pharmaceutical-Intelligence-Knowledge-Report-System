import logging
from mcp.server.fastmcp import FastMCP
from .config import settings
from .client.pubchem_api import PubChemAPIClient
from .tools.pubchem import register_tools

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
                    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")

mcp = FastMCP("pubchem")
client = PubChemAPIClient(base_url=settings.PUBCHEM_BASE_URL, timeout=settings.REQUEST_TIMEOUT)
register_tools(mcp, client)
