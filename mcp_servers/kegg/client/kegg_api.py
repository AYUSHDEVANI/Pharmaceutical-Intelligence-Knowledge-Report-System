"""KEGG API Client — Ported from KeggConnector. Note: KEGG returns tab-delimited text, not JSON."""
import httpx
import logging
from typing import Any, Dict, List

logger = logging.getLogger("mcp_servers.kegg.client")


class KeggAPIClient:
    def __init__(self, base_url: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def search_drug(self, drug_name: str) -> Dict[str, Any]:
        url = f"{self.base_url}/find/drug/{drug_name}"

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=self.timeout)
            resp.raise_for_status()
            raw = resp.text

        if not raw or not raw.strip():
            raise ValueError(f"No KEGG data found for '{drug_name}'")

        lines = raw.strip().split("\n")
        drugs: List[Dict[str, str]] = []

        for line in lines[:10]:
            parts = line.split("\t")
            if len(parts) >= 2:
                drugs.append({
                    "kegg_id": parts[0].replace("dr:", ""),
                    "description": parts[1],
                })

        return {
            "drug_name": drug_name,
            "identifiers": {},
            "results": {"kegg_drugs": drugs},
        }

    async def check_health(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/list/drug", timeout=5.0)
                return resp.status_code == 200
        except Exception:
            return False
