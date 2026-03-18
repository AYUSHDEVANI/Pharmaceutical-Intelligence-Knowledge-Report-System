"""
RxNorm MCP Server — Connector
================================
Implements the NLM RxNorm REST API connector.

Retrieves:
- RxCUI
- Ingredient name
- Brand names
- Synonyms

Orchestrates a two-step fetch:
1. Resolve drug name -> RxCUI
2. Fetch related concepts for the RxCUI -> extract ingredients, brands, synonyms
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from shared.base_connector import BaseConnector
from shared.exceptions import DrugNotFoundError
from shared.schemas import (
    MCPRequest,
    MCPResponse,
    MCPResponseData,
    ResponseMetadata,
    SourceInfo,
)

logger = logging.getLogger("mcp.rxnorm.connector")


class RxNormConnector(BaseConnector):
    """Connector for the NLM RxNav REST API."""

    source_id = "rxnorm"
    source_name = "RxNorm"
    source_url = "https://rxnav.nlm.nih.gov"

    def __init__(self, base_url: str, **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------
    # Query Orchestration (Overrides BaseConnector to support 2-step)
    # ------------------------------------------------------------------

    async def query(self, request: MCPRequest) -> MCPResponse:
        """
        Overrides the single-fetch `query()` from BaseConnector to orchestrate
        the two-step RxNorm resolution process.
        """
        start = time.perf_counter()
        request_id = request.effective_request_id()

        # Step 1: Resolve RxCUI
        rxcui = None
        if request.identifiers and request.identifiers.rxnorm_cui:
            rxcui = str(request.identifiers.rxnorm_cui)
        
        step1_url = ""
        if not rxcui:
            encoded_name = quote(request.drug_name, safe="")
            step1_url = f"{self.base_url}/rxcui.json?name={encoded_name}"
            logger.info("Resolving RxCUI | url=%s | request_id=%s", step1_url, request_id)
            
            raw_rxcui_resp = await self._fetch(step1_url, timeout=request.options.timeout)
            
            try:
                id_group = raw_rxcui_resp.get("idGroup", {})
                rxnorm_id = id_group.get("rxnormId")
                if rxnorm_id and len(rxnorm_id) > 0:
                    rxcui = rxnorm_id[0]
            except Exception as exc:
                logger.error("Failed to parse RxCUI response: %s", exc)
                
            if not rxcui:
                raise DrugNotFoundError(
                    message=f"Drug '{request.drug_name}' could not be resolved to an RxCUI",
                    details={"url": step1_url}
                )

        # Step 2: Fetch related concepts
        step2_url = f"{self.base_url}/rxcui/{rxcui}/allrelated.json"
        logger.info("Fetching concepts | url=%s | request_id=%s", step2_url, request_id)
        
        raw_related_resp = await self._fetch(step2_url, timeout=request.options.timeout)
        
        # Step 3: Parse the related concepts
        parsed = await self.parse_response(raw_related_resp, request)
        parsed["identifiers"]["rxnorm_cui"] = rxcui
        
        drug_name = parsed.get("drug_name", request.drug_name)
        identifiers = parsed.get("identifiers", {})
        results = parsed.get("results", {})

        # Apply field filtering if requested
        if request.fields:
            results = {k: v for k, v in results.items() if k in request.fields}

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        raw_payload = None
        if request.options.include_raw:
            raw_payload = {
                "step1_rxcui": raw_rxcui_resp if not (request.identifiers and request.identifiers.rxnorm_cui) else None,
                "step2_allrelated": raw_related_resp
            }

        return MCPResponse(
            source=SourceInfo(
                source_id=self.source_id,
                name=self.source_name,
                url=self.source_url,
                query_url=step2_url,
                accessed_at=datetime.now(timezone.utc),
            ),
            data=MCPResponseData(
                drug_name=drug_name,
                identifiers=identifiers,
                results=results,
            ),
            metadata=ResponseMetadata(
                request_id=request_id,
                response_time_ms=elapsed_ms,
                server_version=self.server_version,
                result_count=len(results),
                cached=False,
            ),
            raw=raw_payload,
        )

    # ------------------------------------------------------------------
    # Abstract hooks (required but bypassed by our custom query())
    # ------------------------------------------------------------------

    async def build_request_url(self, request: MCPRequest) -> str:
        # Not used because we override query(), but required by BaseConnector
        return ""

    async def parse_response(
        self,
        raw: dict[str, Any],
        request: MCPRequest,
    ) -> dict[str, Any]:
        """
        Extract ingredient, brand names, and synonyms from allrelated.json.
        """
        ingredient_name = None
        brand_names = set()
        synonyms = set()

        try:
            concept_groups = raw.get("allRelatedGroup", {}).get("conceptGroup", [])
            
            for group in concept_groups:
                tty = group.get("tty", "")
                concepts = group.get("conceptProperties", [])
                
                if not concepts:
                    continue
                    
                for concept in concepts:
                    name = concept.get("name", "").strip()
                    if not name:
                        continue
                        
                    # IN = Ingredient, MIN = Multiple Ingredients, PIN = Precise Ingredient
                    if tty in ["IN", "MIN", "PIN"]:
                        ingredient_name = name
                    
                    # BN = Brand Name
                    elif tty == "BN":
                        brand_names.add(name)
                        
                    # SY = Synonym
                    elif tty == "SY":
                        synonyms.add(name)
                        
        except Exception as exc:
            logger.error("Error parsing related concepts: %s", exc)

        # Ensure lists are returned
        return {
            "drug_name": request.drug_name,
            "identifiers": {},  # Will be merged in query()
            "results": {
                "ingredient_name": ingredient_name,
                "brand_names": sorted(list(brand_names)),
                "synonyms": sorted(list(synonyms)),
            },
        }

    async def check_upstream_health(self) -> bool:
        """Ping RxNav version endpoint."""
        try:
            if self._client is None:
                return False
            resp = await self._client.get(
                f"{self.base_url}/version.json",
                timeout=5.0,
            )
            return resp.status_code == 200
        except Exception:
            return False
