import logging
from mcp.server.fastmcp import FastMCP
from .config import settings
from .client.rxnorm_api import RxNormAPIClient
from .tools.rxnorm import register_tools

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
                    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")

mcp = FastMCP("rxnorm")
client = RxNormAPIClient(base_url=settings.RXNORM_BASE_URL, timeout=settings.REQUEST_TIMEOUT)
register_tools(mcp, client)
