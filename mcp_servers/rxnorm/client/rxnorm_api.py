"""RxNorm API Client — Advanced (KG-ready + structured parsing)."""

import httpx
import logging
import re
from typing import Any, Dict
from urllib.parse import quote
from datetime import datetime

logger = logging.getLogger("mcp_servers.rxnorm.client")


class RxNormAPIClient:
    def __init__(self, base_url: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # -------------------------------
    # Helper: Parse dosage string
    # -------------------------------
    def _parse_clinical_drug(self, name: str) -> Dict[str, str]:
        """
        Example:
        'azithromycin 500 MG Oral Tablet'
        """
        pattern = r"^(.*?)\s+([\d\.]+\s*MG\/ML|[\d\.]+\s*MG)\s+(.*)$"
        match = re.match(pattern, name, re.IGNORECASE)

        if match:
            return {
                "ingredient": match.group(1),
                "strength": match.group(2),
                "form": match.group(3),
                "raw": name,
            }

        return {"raw": name}

    async def search_drug(self, drug_name: str) -> Dict[str, Any]:
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
                raise ValueError(f"Drug '{drug_name}' could not be resolved to RxCUI")

            # Step 2: Fetch related concepts
            url2 = f"{self.base_url}/rxcui/{rxcui}/allrelated.json"
            resp2 = await client.get(url2, timeout=self.timeout)
            resp2.raise_for_status()
            raw2 = resp2.json()

        # -------------------------------
        # Parsing
        # -------------------------------

        ingredient_name = None

        brand_names = set()
        synonyms = set()
        ingredient_variants = set()

        clinical_drugs = []
        branded_drugs = []

        dose_forms = set()
        packs = []
        pack_synonyms = set()

        clinical_groups = set()   # SCDG
        branded_groups = set()    # SBDG

        concept_groups = raw2.get("allRelatedGroup", {}).get("conceptGroup", [])

        for group in concept_groups:
            tty = group.get("tty", "")
            concepts = group.get("conceptProperties", [])

            for concept in concepts:
                name = concept.get("name", "").strip()
                synonym = concept.get("synonym", "").strip()

                if tty == "IN":
                    ingredient_name = name

                elif tty == "PIN":
                    ingredient_variants.add(name)

                elif tty == "BN":
                    brand_names.add(name)

                elif tty == "SY":
                    synonyms.add(name)

                elif tty == "SCD":
                    clinical_drugs.append(self._parse_clinical_drug(name))

                elif tty == "SBD":
                    branded_drugs.append(self._parse_clinical_drug(name))

                elif tty == "DF":
                    dose_forms.add(name)

                elif tty in ["BPCK", "GPCK"]:
                    packs.append({
                        "name": name,
                        "alias": synonym if synonym else None
                    })
                    if synonym:
                        pack_synonyms.add(synonym)

                elif tty == "SCDG":
                    clinical_groups.add(name)

                elif tty == "SBDG":
                    branded_groups.add(name)

        aliases = synonyms.union(ingredient_variants)

        # -------------------------------
        # Final Output
        # -------------------------------

        result = {
            "drug": {
                "name": ingredient_name or drug_name,
                "description": ingredient_name or drug_name,
                "naming": {
                    "generic_name": ingredient_name or drug_name,
                    "brand_names": sorted(brand_names),
                    "aliases": sorted(aliases),
                },
            },
            "identifiers": {
                "rxnorm_cui": rxcui,
            },
            "clinical": {
                "dose_forms": sorted(dose_forms),
                "clinical_drugs": clinical_drugs,
                "branded_drugs": branded_drugs,
                "packs": packs,
                "pack_aliases": sorted(pack_synonyms),
            },
            "knowledge_graph": {
                "clinical_groups": sorted(clinical_groups),
                "branded_groups": sorted(branded_groups),
            },
        }

        return {
            "source": {
                "name": "RxNorm",
                "url": "https://rxnav.nlm.nih.gov",
            },
            "query": drug_name,
            "count": 1,
            "results": [result],
            "meta": {
                "timestamp": datetime.utcnow().isoformat(),
                "version": "rxnorm-v2.0-kg",
            },
        }

    async def check_health(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/version.json", timeout=5.0
                )
                return resp.status_code == 200
        except Exception:
            return False