"""
PubChem MCP Server — Application Entry Point
===============================================
FastAPI app factory with lifespan events, middleware, and exception handlers.

Run locally::

    uvicorn app.main:app --host 0.0.0.0 --port 8100 --reload
"""

from __future__ import annotations

import logging
import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure the shared library is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from shared.exceptions import register_exception_handlers
from shared.middleware import register_middleware

from .config import settings
from .connector import PubChemConnector
from .router import router, set_connector

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("mcp.pubchem")

# ---------------------------------------------------------------------------
# Connector singleton
# ---------------------------------------------------------------------------

connector = PubChemConnector(
    base_url=settings.PUBCHEM_BASE_URL,
    timeout=settings.REQUEST_TIMEOUT,
    max_retries=settings.MAX_RETRIES,
    rate_limit=settings.RATE_LIMIT_PER_SECOND,
    server_version=settings.SERVER_VERSION,
)

# ---------------------------------------------------------------------------
# Lifespan context manager
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle for the FastAPI app."""
    logger.info(
        "Starting PubChem MCP Server v%s on %s:%s",
        settings.SERVER_VERSION,
        settings.HOST,
        settings.PORT,
    )
    await connector.startup()
    set_connector(connector)
    yield
    logger.info("Shutting down PubChem MCP Server")
    await connector.shutdown()

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="PubChem MCP Server",
    description=(
        "PIKRS MCP server for PubChem.  Retrieves molecular formula, "
        "molecular weight, IUPAC name, SMILES, InChI, and InChIKey "
        "for pharmaceutical compounds."
    ),
    version=settings.SERVER_VERSION,
    lifespan=lifespan,
)

# CORS (allow all origins for development; restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Standard MCP middleware (request-ID, timing, body-size limit)
register_middleware(app, max_body_bytes=settings.MAX_BODY_BYTES)

# Standard MCP exception handlers
register_exception_handlers(app)

# Mount router
app.include_router(router)


# ---------------------------------------------------------------------------
# Direct execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )
