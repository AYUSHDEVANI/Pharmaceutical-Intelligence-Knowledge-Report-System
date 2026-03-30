import logging
from mcp.server.fastmcp import FastMCP
from .config import settings
from .client.dailymed_api import DailyMedAPIClient
from .tools.dailymed import register_tools

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)

mcp = FastMCP("dailymed")

client = DailyMedAPIClient(
    base_url=settings.DAILMED_BASE_URL,
    timeout=settings.REQUEST_TIMEOUT
)

register_tools(mcp, client)