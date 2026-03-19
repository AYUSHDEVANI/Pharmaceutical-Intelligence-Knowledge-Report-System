import logging
from mcp.server.fastmcp import FastMCP
from .config import settings
from .client.pubmed_api import PubMedAPIClient
from .tools.pubmed import register_tools

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
                    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")

mcp = FastMCP("pubmed")
client = PubMedAPIClient(
    base_url=settings.PUBMED_BASE_URL,
    timeout=settings.REQUEST_TIMEOUT,
    max_papers=settings.MAX_PAPERS,
)
register_tools(mcp, client)
