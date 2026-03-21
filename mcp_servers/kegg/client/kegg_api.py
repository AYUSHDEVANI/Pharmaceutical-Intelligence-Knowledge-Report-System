"""KEGG API Client — Cleaned Production Version (multi-result + normalized)."""

import httpx
import logging
import re
from typing import Any, Dict, List
from datetime import datetime

logger = logging.getLogger("mcp_servers.kegg.client")


class KeggAPIClient:
    def __init__(self, base_url: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # -------------------------------
    # Clean generic name
    # -------------------------------
    def _clean_generic(self, name: str) -> str:
        # Remove tags like (INN), (USP), (JP18)
        name = re.sub(r"\(.*?\)", "", name)

        # Remove salt/hydrate terms
        name = re.sub(
            r"\b(hydrate|dihydrate|monohydrate)\b",
            "",
            name,
            flags=re.IGNORECASE
        )

        return name.strip().lower()

    # -------------------------------
    # Variant classification
    # -------------------------------
    def _classify_variant(self, desc: str) -> str:
        d = desc.lower()

        if "hydrate" in d or "dihydrate" in d:
            return "salt/formulation"
        elif "(usp)" in d:
            return "standard_variant"
        elif "(inn)" in d:
            return "canonical"
        return "other"

    # -------------------------------
    # Parse names
    # -------------------------------
    def _parse_names(self, description: str):
        names = description.split(";")

        generic_name = None
        brand_names = []
        aliases = []

        for n in names:
            n = n.strip()
            lower = n.lower()

            if "(inn)" in lower:
                generic_name = n.replace("(INN)", "").strip()

            elif "(tn)" in lower:
                brand_names.append(n.replace("(TN)", "").strip())

            elif "(usp)" in lower:
                if not generic_name:
                    generic_name = n.replace("(USP)", "").strip()

            else:
                aliases.append(n)

        if not generic_name:
            generic_name = names[0].strip()

        # Clean generic name
        generic_name = self._clean_generic(generic_name)

        # Remove duplicates from aliases
        aliases = [a for a in aliases if a.lower() != generic_name]

        return generic_name, brand_names, aliases

    # -------------------------------
    # Fetch biology
    # -------------------------------
    async def _fetch_biology(self, client, kegg_id: str):
        pathways = []
        enzymes = []

        # Pathways
        p_url = f"{self.base_url}/link/pathway/dr:{kegg_id}"
        p_resp = await client.get(p_url, timeout=self.timeout)

        if p_resp.status_code == 200 and p_resp.text.strip():
            for line in p_resp.text.strip().split("\n"):
                parts = line.split("\t")
                if len(parts) == 2:
                    pathways.append(parts[1].replace("path:", ""))

        # Enzymes
        e_url = f"{self.base_url}/link/enzyme/dr:{kegg_id}"
        e_resp = await client.get(e_url, timeout=self.timeout)

        if e_resp.status_code == 200 and e_resp.text.strip():
            for line in e_resp.text.strip().split("\n"):
                parts = line.split("\t")
                if len(parts) == 2:
                    enzymes.append(parts[1])

        return pathways, enzymes

    async def search_drug(self, drug_name: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:

            # -------------------------------
            # Step 1: Search
            # -------------------------------
            search_url = f"{self.base_url}/find/drug/{drug_name}"
            resp = await client.get(search_url, timeout=self.timeout)
            resp.raise_for_status()

            lines = resp.text.strip().split("\n")

            if not lines or not lines[0]:
                raise ValueError(f"No KEGG data found for '{drug_name}'")

            results = []

            # -------------------------------
            # Step 2: Process all entries
            # -------------------------------
            for line in lines:
                parts = line.split("\t")
                if len(parts) < 2:
                    continue

                kegg_id = parts[0].replace("dr:", "")
                description = parts[1]

                # Parse names
                generic_name, brand_names, aliases = self._parse_names(description)

                # Fetch biology
                pathways, enzymes = await self._fetch_biology(client, kegg_id)

                # Variant classification
                variant_type = self._classify_variant(description)

                result = {
                    "drug": {
                        "name": generic_name,
                        "description": generic_name,
                        "naming": {
                            "generic_name": generic_name,
                            "brand_names": sorted(set(brand_names)),
                            "aliases": sorted(set(aliases))[:10],
                        },
                    },
                    "identifiers": {
                        "kegg_id": kegg_id,
                    },
                    "variant_type": variant_type,
                    "biology": {
                        "pathways": sorted(set(pathways)),
                        "enzymes": sorted(set(enzymes)),
                    },
                }

                results.append(result)

        return {
            "source": {
                "name": "KEGG",
                "url": "https://rest.kegg.jp",
            },
            "query": drug_name,
            "count": len(results),
            "results": results,
            "meta": {
                "timestamp": datetime.utcnow().isoformat(),
                "version": "kegg-v6.0-clean",
            },
        }

    async def check_health(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/list/drug", timeout=5.0)
                return resp.status_code == 200
        except Exception:
            return False