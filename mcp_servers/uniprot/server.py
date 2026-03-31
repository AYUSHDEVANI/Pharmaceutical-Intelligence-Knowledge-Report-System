import logging
from mcp.server.fastmcp import FastMCP
from .config import settings
from .client.uniprot_api import UniProtAPIClient
from .tools.uniprot import register_tools


logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)

mcp = FastMCP("uniprot")

client = UniProtAPIClient(
    base_url = settings.UNIPROT_BASE_URL,
    timeout = settings.REQUEST_TIMEOUT
)

register_tools(mcp, client = client)