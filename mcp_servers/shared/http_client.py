"""
PIKRS MCP Servers — Shared HTTP Client
=========================================
Reusable async httpx wrapper for all MCP server API clients.
"""

import httpx
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("mcp_servers.shared.http_client")


class AsyncAPIClient:
    """Lightweight async HTTP client with timeout and error logging."""

    def __init__(self, base_url: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def get(self, url: str, timeout: Optional[float] = None) -> httpx.Response:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=timeout or self.timeout)
            resp.raise_for_status()
            return resp

    async def get_json(self, url: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        resp = await self.get(url, timeout)
        return resp.json()

    async def get_text(self, url: str, timeout: Optional[float] = None) -> str:
        resp = await self.get(url, timeout)
        return resp.text

    async def check_health(self, path: str) -> bool:
        try:
            url = f"{self.base_url}/{path.lstrip('/')}"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=5.0)
                return resp.status_code == 200
        except Exception:
            return False
