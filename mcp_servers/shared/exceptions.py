"""
PIKRS MCP Servers — Shared Exceptions
========================================
Unified exception classes for all MCP server API clients.
"""


class DrugNotFoundError(Exception):
    """Raised when a drug cannot be found in an upstream API."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.details = details or {}


class UpstreamError(Exception):
    """Raised when an upstream API returns an unexpected error."""

    def __init__(self, source: str, message: str):
        super().__init__(f"[{source}] {message}")
        self.source = source
