"""
PIKRS Shared MCP Library
========================
Common schemas, exceptions, middleware, and base connector used by all MCP servers.
"""

from .schemas import (
    MCPRequest,
    MCPResponse,
    MCPErrorResponse,
    SourceInfo,
    ResponseMetadata,
    QueryOptions,
    DrugIdentifiers,
)
from .exceptions import (
    MCPBaseError,
    DrugNotFoundError,
    UpstreamAPIError,
    UpstreamTimeoutError,
    RateLimitedError,
    InputValidationError,
    MCPInternalError,
    register_exception_handlers,
)
from .base_connector import BaseConnector

__all__ = [
    "MCPRequest",
    "MCPResponse",
    "MCPErrorResponse",
    "SourceInfo",
    "ResponseMetadata",
    "QueryOptions",
    "DrugIdentifiers",
    "MCPBaseError",
    "DrugNotFoundError",
    "UpstreamAPIError",
    "UpstreamTimeoutError",
    "RateLimitedError",
    "InputValidationError",
    "MCPInternalError",
    "register_exception_handlers",
    "BaseConnector",
]
