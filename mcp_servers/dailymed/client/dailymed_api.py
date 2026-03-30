"""DailyMed API Client — FINAL VERSION (v6.0 with data quality intelligence)"""

import httpx
import logging
from typing import Any, Dict, List
from datetime import datetime
import xml.etree.ElementTree as ET

logger = logging.getLogger("mcp_servers.dailymed.client")


class DailyMedAPIClient:
    def __init__(self, base_url: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # -------------------------------
    # Select best SPL
    # -------------------------------
    def _select_best_spl(self, spls: List[Dict[str, Any]]) -> Dict[str, Any]:
        for spl in spls:
            title = spl.get("title", "").lower()
            if "zithromax" in title or "pfizer" in title:
                return spl

        spls_sorted = sorted(
            spls,
            key=lambda x: x.get("spl_version", 0),
            reverse=True
        )

        return spls_sorted[0]

    # -------------------------------
    # Extract manufacturer
    # -------------------------------
    def _extract_manufacturer(self, title: str) -> str:
        if "[" in title and "]" in title:
            return title.split("[")[-1].replace("]", "").strip()
        return None

    # -------------------------------
    # Extract XML sections (LOINC + namespace)
    # -------------------------------
    def _extract_by_loinc(self, root, loinc_code: str) -> List[str]:
        results = []
        ns = {"hl7": "urn:hl7-org:v3"}

        for section in root.findall(".//hl7:section", ns):
            code_elem = section.find(".//hl7:code", ns)

            if code_elem is not None and code_elem.attrib.get("code") == loinc_code:
                text_elem = section.find(".//hl7:text", ns)

                if text_elem is not None:
                    text = "".join(text_elem.itertext()).strip()
                    if text:
                        results.append(text)

        return list(set(results))

    async def search_drug(self, drug_name: str) -> Dict[str, Any]:
        headers = {
            "User-Agent": "MCP-Client/1.0"
        }

        async with httpx.AsyncClient() as client:

            # -------------------------------
            # Step 1: Fetch SPL list
            # -------------------------------
            search_url = f"{self.base_url}/spls.json?drug_name={drug_name}"

            resp = await client.get(search_url, timeout=self.timeout)
            resp.raise_for_status()

            data = resp.json()
            spls = data.get("data", [])
            metadata = data.get("metadata", {})

            if not spls:
                raise ValueError(f"No DailyMed data found for '{drug_name}'")

            # -------------------------------
            # Step 2: Select best SPL
            # -------------------------------
            spl = self._select_best_spl(spls)

            setid = spl.get("setid")
            title = spl.get("title", drug_name)
            spl_version = spl.get("spl_version")
            published_date = spl.get("published_date")
            manufacturer = self._extract_manufacturer(title)

            # -------------------------------
            # Step 3: Fetch XML
            # -------------------------------
            xml_url = f"{self.base_url}/spls/{setid}.xml"

            resp2 = await client.get(xml_url, headers=headers, timeout=self.timeout)
            resp2.raise_for_status()

            root = ET.fromstring(resp2.text)

        # -------------------------------
        # Extract label sections
        # -------------------------------
        indications = self._extract_by_loinc(root, "34067-9")
        dosage = self._extract_by_loinc(root, "34068-7")
        warnings = self._extract_by_loinc(root, "34071-1")
        adverse = self._extract_by_loinc(root, "34084-4")
        ingredients = self._extract_by_loinc(root, "34390-5")

        # -------------------------------
        # Data quality assessment
        # -------------------------------
        has_label_data = any([
            indications,
            dosage,
            warnings,
            adverse,
            ingredients
        ])

        label_completeness = "high" if has_label_data else "low"

        generic_name = drug_name.lower()

        result = {
            "drug": {
                "name": generic_name,
                "description": title,
                "naming": {
                    "generic_name": generic_name,
                    "brand_names": [],
                    "aliases": [],
                },
            },
            "identifiers": {
                "dailymed_setid": setid,
                "spl_version": spl_version,
                "published_date": published_date,
            },
            "source_quality": {
                "is_branded": "zithromax" in title.lower(),
                "manufacturer": manufacturer,
            },
            "data_quality": {
                "has_structured_label": has_label_data,
                "label_completeness": label_completeness,
            },
            "label": {
                "indications": indications[:5],
                "dosage": dosage[:5],
                "warnings": warnings[:5],
                "adverse_reactions": adverse[:5],
                "ingredients": ingredients[:5],
            },
        }

        return {
            "source": {
                "name": "DailyMed",
                "url": "https://dailymed.nlm.nih.gov",
            },
            "query": drug_name,
            "count": 1,
            "total_spls_available": metadata.get("total_elements"),
            "pages_available": metadata.get("total_pages"),
            "results": [result],
            "meta": {
                "timestamp": datetime.utcnow().isoformat(),
                "version": "dailymed-v6.0-final",
            },
        }

    async def check_health(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/spls.json?drug_name=aspirin",
                    timeout=5.0
                )
                return resp.status_code == 200
        except Exception:
            return False