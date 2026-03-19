import logging
from mcp.server.fastmcp import FastMCP
from .config import settings
from .client.kegg_api import KeggAPIClient
from .tools.kegg import register_tools

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
                    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")

mcp = FastMCP("kegg")
client = KeggAPIClient(base_url=settings.KEGG_BASE_URL, timeout=settings.REQUEST_TIMEOUT)
register_tools(mcp, client)
