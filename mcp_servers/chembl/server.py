import logging
from mcp.server.fastmcp import FastMCP
from .config import settings
from .client.chembl_api import ChemblAPIClient
from .tools.chembl import register_tools

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
                    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")

mcp = FastMCP("chembl")
client = ChemblAPIClient(base_url=settings.CHEMBL_BASE_URL, timeout=settings.REQUEST_TIMEOUT)
register_tools(mcp, client)
