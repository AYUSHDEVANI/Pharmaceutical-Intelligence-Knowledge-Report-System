from contextlib import asynccontextmanager
from fastapi import FastAPI

from .config import settings
from .connector import ChemblConnector
from .router import router, set_connector


connector = ChemblConnector(
    base_url=settings.CHEMBL_BASE_URL,
    timeout=settings.REQUEST_TIMEOUT,
    max_retries=settings.MAX_RETRIES,
    rate_limit=settings.RATE_LIMIT_PER_SECOND,
    server_version=settings.SERVER_VERSION,
)


@asynccontextmanager
async def lifespan(app: FastAPI):

    await connector.startup()
    set_connector(connector)

    yield

    await connector.shutdown()


app = FastAPI(
    title="ChEMBL MCP Server",
    version=settings.SERVER_VERSION,
    lifespan=lifespan,
)

app.include_router(router)