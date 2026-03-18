"""
OpenFDA MCP Server — Connector
================================
Implements the OpenFDA REST API connector.

Retrieves:
- Indications and Usage
- Dosage and Administration
- Warnings
- Contraindications
- Adverse Reactions
- Drug Interactions
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from shared.base_connector import BaseConnector
from shared.exceptions import DrugNotFoundError
from shared.schemas import MCPRequest

logger = logging.getLogger("mcp.openfda.connector")


class OpenFDAConnector(BaseConnector):
    """Connector for the OpenFDA REST API."""

    source_id = "openfda"
    source_name = "OpenFDA"
    source_url = "https://api.fda.gov"

    def __init__(self, base_url: str, **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip("/")

    async def build_request_url(self, request: MCPRequest) -> str:
        """Construct the OpenFDA drug label search URL."""
        # Querying by generic name, limiting to 1 result for the most relevant label
        encoded_name = quote(request.drug_name, safe="")
        endpoint = f"{self.base_url}/label.json?search=openfda.generic_name:{encoded_name}&limit=1"
        return endpoint

    async def parse_response(
        self,
        raw: dict[str, Any],
        request: MCPRequest,
    ) -> dict[str, Any]:
        """
        Extract required FDA label sections from the raw JSON response.
        """
        error = raw.get("error")
        if error:
            code = error.get("code")
            if code == "NOT_FOUND":
                raise DrugNotFoundError(f"No OpenFDA labels found for '{request.drug_name}'")
            # Other errors will be caught upstream or as general upstream errors

        results = raw.get("results", [])
        if not results:
            raise DrugNotFoundError(f"No OpenFDA labels found for '{request.drug_name}'")

        # Take the best matching label
        label = results[0]

        # Helper to neatly extract the first string from FDA's list format
        def extract_first(field_name: str) -> str | None:
            items = label.get(field_name, [])
            if items and isinstance(items, list) and len(items) > 0:
                first_item = items[0]
                # Sometimes FDA data includes the section title inside the text.
                # Just return raw text for now, can be cleaned if needed.
                return str(first_item).strip()
            return None

        # Build the structured result
        indications = extract_first("indications_and_usage")
        dosage = extract_first("dosage_and_administration")
        
        # Prefer boxed warning if available, otherwise general warnings
        warnings = extract_first("boxed_warning")
        if not warnings:
            warnings = extract_first("warnings")
            
        contraindications = extract_first("contraindications")
        adverse_reactions = extract_first("adverse_reactions")
        drug_interactions = extract_first("drug_interactions")

        return {
            "drug_name": request.drug_name,
            "identifiers": {},
            "results": {
                "indications": indications,
                "dosage": dosage,
                "warnings": warnings,
                "contraindications": contraindications,
                "adverse_reactions": adverse_reactions,
                "drug_interactions": drug_interactions,
            },
        }

    async def check_upstream_health(self) -> bool:
        """Check OpenFDA API health by doing a minimal search."""
        try:
            if self._client is None:
                return False
            # Search for aspirin, limit 1. Should return 200.
            resp = await self._client.get(
                f"{self.base_url}/label.json?search=openfda.generic_name:aspirin&limit=1",
                timeout=5.0,
            )
            return resp.status_code == 200
        except Exception:
            return False
