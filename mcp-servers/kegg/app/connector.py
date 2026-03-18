from __future__ import annotations

import logging
from typing import Any, Dict, List

from shared.base_connector import BaseConnector
from shared.schemas import MCPRequest
from shared.exceptions import DrugNotFoundError

logger = logging.getLogger("mcp.kegg.connector")


class KeggConnector(BaseConnector):

    source_id = "kegg"
    source_name = "KEGG Drug"
    source_url = "https://www.kegg.jp"

    def __init__(self, base_url: str, **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip("/")

    async def build_request_url(self, request: MCPRequest) -> str:
        return f"{self.base_url}/find/drug/{request.drug_name}"

    async def parse_response(
        self,
        raw: str,
        request: MCPRequest
    ) -> Dict[str, Any]:

        if not raw:
            raise DrugNotFoundError(
                message=f"No KEGG data found for '{request.drug_name}'"
            )

        lines = raw.strip().split("\n")

        drugs: List[Dict[str, str]] = []

        for line in lines[:10]:

            parts = line.split("\t")

            if len(parts) >= 2:
                drugs.append({
                    "kegg_id": parts[0].replace("dr:", ""),
                    "description": parts[1]
                })

        return {
            "drug_name": request.drug_name,
            "identifiers": {},
            "results": {
                "kegg_drugs": drugs
            }
        }

    async def check_upstream_health(self) -> bool:

        try:
            resp = await self._client.get(
                f"{self.base_url}/list/drug",
                timeout=5.0
            )

            return resp.status_code == 200

        except Exception:
            return False