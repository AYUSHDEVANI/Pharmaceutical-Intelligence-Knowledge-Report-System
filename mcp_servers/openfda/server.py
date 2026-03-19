import logging
from mcp.server.fastmcp import FastMCP
from .config import settings
from .client.openfda_api import OpenFDAAPIClient
from .tools.openfda import register_tools

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
                    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")

mcp = FastMCP("openfda")
client = OpenFDAAPIClient(base_url=settings.OPENFDA_BASE_URL, timeout=settings.REQUEST_TIMEOUT)
register_tools(mcp, client)
