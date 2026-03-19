"""RxNorm API Client — Ported from RxNormConnector (two-step resolution)."""
import httpx
import logging
from typing import Any, Dict, List
from urllib.parse import quote

logger = logging.getLogger("mcp_servers.rxnorm.client")


class RxNormAPIClient:
    def __init__(self, base_url: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def search_drug(self, drug_name: str) -> Dict[str, Any]:
        """Two-step: resolve name → RxCUI, then fetch related concepts."""
        async with httpx.AsyncClient() as client:
            # Step 1: Resolve RxCUI
            encoded = quote(drug_name, safe="")
            url1 = f"{self.base_url}/rxcui.json?name={encoded}"
            resp1 = await client.get(url1, timeout=self.timeout)
            resp1.raise_for_status()
            raw1 = resp1.json()

            rxcui = None
            id_group = raw1.get("idGroup", {})
            rxnorm_ids = id_group.get("rxnormId", [])
            if rxnorm_ids:
                rxcui = rxnorm_ids[0]

            if not rxcui:
                raise ValueError(f"Drug '{drug_name}' could not be resolved to an RxCUI")

            # Step 2: Fetch all related concepts
            url2 = f"{self.base_url}/rxcui/{rxcui}/allrelated.json"
            resp2 = await client.get(url2, timeout=self.timeout)
            resp2.raise_for_status()
            raw2 = resp2.json()

        # Parse
        ingredient_name = None
        brand_names: set = set()
        synonyms: set = set()

        concept_groups = raw2.get("allRelatedGroup", {}).get("conceptGroup", [])
        for group in concept_groups:
            tty = group.get("tty", "")
            concepts = group.get("conceptProperties", [])
            for concept in concepts:
                name = concept.get("name", "").strip()
                if not name:
                    continue
                if tty in ["IN", "MIN", "PIN"]:
                    ingredient_name = name
                elif tty == "BN":
                    brand_names.add(name)
                elif tty == "SY":
                    synonyms.add(name)

        return {
            "drug_name": drug_name,
            "identifiers": {"rxnorm_cui": rxcui},
            "results": {
                "ingredient_name": ingredient_name,
                "brand_names": sorted(list(brand_names)),
                "synonyms": sorted(list(synonyms)),
            },
        }

    async def check_health(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/version.json", timeout=5.0)
                return resp.status_code == 200
        except Exception:
            return False
