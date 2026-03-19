"""OpenFDA API Client — Robust & Adaptive Version"""
import httpx
import logging
import re
from typing import Any, Dict, Optional, List
from urllib.parse import quote

logger = logging.getLogger("mcp_servers.openfda.client")


class OpenFDAAPIClient:
    def __init__(self, base_url: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # -------------------------
    # Helpers
    # -------------------------
    def clean_text(self, text: Optional[str], limit: int = 1000) -> Optional[str]:
        if not text:
            return None

        text = " ".join(text.split())
        text = re.sub(r"\[.*?\]", "", text)
        text = re.sub(r"\b\d+(\.\d+)*\s+(?=[A-Z])", "", text)
        text = text.replace("•", "")

        return text[:limit].strip()

    def extract_first(self, label: Dict, field: str) -> Optional[str]:
        items = label.get(field, [])
        if isinstance(items, list) and items:
            return str(items[0]).strip()
        return None

    def extract_conditions(self, text: Optional[str]) -> List[str]:
        if not text:
            return []

        keywords = [
            "pneumonia", "sinusitis", "bronchitis", "otitis",
            "infection", "pharyngitis", "tonsillitis",
            "skin", "urethritis",
            "pain", "fever", "inflammation", "headache",
            "arthritis", "migraine"
        ]

        text_lower = text.lower()
        return list({k for k in keywords if k in text_lower})

    def extract_risks(self, text: Optional[str]) -> List[str]:
        if not text:
            return []

        risk_map = {
            "qt_prolongation": ["qt", "torsades"],
            "cardiovascular_risk": ["cardiovascular", "heart"],
            "hepatotoxicity": ["hepatotoxicity", "liver"],
            "allergic_reaction": ["anaphylaxis", "hypersensitivity", "allergic"],
            "cdiff_diarrhea": ["clostridioides difficile"],
            "bleeding_risk": ["bleeding"],
            "reye_syndrome": ["reye"],
            "gastrointestinal_risk": ["stomach", "ulcer"]
        }

        text_lower = text.lower()
        detected = []

        for risk, keywords in risk_map.items():
            if any(k in text_lower for k in keywords):
                detected.append(risk)

        return detected

    def extract_dosage_summary(self, text: Optional[str]) -> Dict[str, Optional[str]]:
        if not text:
            return {}

        text_lower = text.lower()

        adult_match = re.search(r"\b\d+\s?mg.*", text_lower)
        tablet_match = re.search(r"\b\d+\s+to\s+\d+\s+tablets.*", text_lower)
        pediatric_match = re.search(r"\b\d+\s?mg/kg.*", text_lower)

        return {
            "adult": (
                adult_match.group(0)[:120]
                if adult_match
                else (tablet_match.group(0)[:120] if tablet_match else None)
            ),
            "pediatric": pediatric_match.group(0)[:120] if pediatric_match else None,
        }

    def extract_otc_fields(self, label: Dict) -> Dict[str, Any]:
        def get_first(field):
            items = label.get(field, [])
            return items[0] if items else None

        return {
            "purpose": get_first("purpose"),
            "active_ingredient": get_first("active_ingredient"),
            "do_not_use": self.clean_text(get_first("do_not_use")),
            "ask_doctor": self.clean_text(get_first("ask_doctor")),
            "stop_use": self.clean_text(get_first("stop_use")),
            "pregnancy_warning": self.clean_text(get_first("pregnancy_or_breast_feeding")),
        }

    def fallback_generic_name(self, label: Dict) -> Optional[str]:
        active = label.get("active_ingredient", [])
        if active:
            return active[0]
        return None

    def is_valid_match(self, drug_name: str, openfda_meta: Dict) -> bool:
        names = []
        names.extend(openfda_meta.get("generic_name", []))
        names.extend(openfda_meta.get("brand_name", []))

        names = [n.lower() for n in names if n]

        return any(drug_name.lower() in n for n in names)

    # -------------------------
    # Main API
    # -------------------------
    async def search_drug_label(self, drug_name: str) -> Dict[str, Any]:
        encoded = quote(drug_name, safe="")

        queries = [
            f"openfda.generic_name:{encoded}",
            f"openfda.brand_name:{encoded}",
            encoded
        ]

        label = None
        openfda_meta = {}

        async with httpx.AsyncClient() as client:
            for q in queries:
                url = f"{self.base_url}/label.json?search={q}&limit=1"

                resp = await client.get(url, timeout=self.timeout)
                if resp.status_code != 200:
                    continue

                raw = resp.json()
                results = raw.get("results", [])

                if not results:
                    continue

                candidate = results[0]
                meta_candidate = candidate.get("openfda", {})

                if self.is_valid_match(drug_name, meta_candidate):
                    label = candidate
                    openfda_meta = meta_candidate
                    meta = raw.get("meta", {})
                    break

                # fallback if nothing matches strictly
                if not label:
                    label = candidate
                    openfda_meta = meta_candidate
                    meta = raw.get("meta", {})

        if not label:
            raise ValueError(f"No OpenFDA labels found for '{drug_name}'")

        # -------------------------
        # Extract
        # -------------------------
        indications_text = self.extract_first(label, "indications_and_usage")
        dosage_text = self.extract_first(label, "dosage_and_administration")

        warnings_text = (
            self.extract_first(label, "boxed_warning")
            or self.extract_first(label, "warnings")
            or self.extract_first(label, "warnings_and_cautions")
        )

        contraindications_text = self.extract_first(label, "contraindications")
        adverse_text = self.extract_first(label, "adverse_reactions")
        interactions_text = self.extract_first(label, "drug_interactions")
        boxed_warning_text = self.extract_first(label, "boxed_warning")

        # -------------------------
        # Clean
        # -------------------------
        indications = self.clean_text(indications_text)
        dosage = self.clean_text(dosage_text)
        warnings = self.clean_text(warnings_text)
        contraindications = self.clean_text(contraindications_text)
        adverse = self.clean_text(adverse_text)
        interactions = self.clean_text(interactions_text)
        boxed_warning = self.clean_text(boxed_warning_text)

        # -------------------------
        # Derived
        # -------------------------
        target_conditions = self.extract_conditions(indications_text)
        key_risks = self.extract_risks(warnings_text)
        dosage_summary = self.extract_dosage_summary(dosage_text)
        otc_fields = self.extract_otc_fields(label)

        safety_summary = {
            "has_boxed_warning": bool(boxed_warning),
            "has_warnings": bool(warnings),
            "has_contraindications": bool(contraindications),
            "has_adverse_reactions": bool(adverse),
        }

        # fallback identifiers
        if not openfda_meta.get("generic_name"):
            fallback = self.fallback_generic_name(label)
            if fallback:
                openfda_meta["generic_name"] = [fallback]

        return {
            "source": {
                "name": "openfda",
                "url": url,
                "last_updated": meta.get("last_updated"),
            },

            "drug_name": drug_name,

            "identifiers": {
                "generic_name": openfda_meta.get("generic_name", []),
                "brand_name": openfda_meta.get("brand_name", []),
                "substance_name": openfda_meta.get("substance_name", []),
                "manufacturer_name": openfda_meta.get("manufacturer_name", []),
                "product_type": openfda_meta.get("product_type", []),
                "route": openfda_meta.get("route", []),
            },

            "drug_label": {
                "indications": indications,
                "dosage": dosage,
                "warnings": warnings,
                "contraindications": contraindications,
                "adverse_reactions": adverse,
                "drug_interactions": interactions,
            },

            "safety": {
                "boxed_warning": boxed_warning,
                "summary": safety_summary,
                "key_risks": key_risks,
                "consumer_warnings": {
                    "do_not_use": otc_fields.get("do_not_use"),
                    "ask_doctor": otc_fields.get("ask_doctor"),
                    "stop_use": otc_fields.get("stop_use"),
                    "pregnancy": otc_fields.get("pregnancy_warning"),
                },
            },

            "usage": {
                "target_conditions": target_conditions,
                "dosage_summary": dosage_summary,
                "purpose": otc_fields.get("purpose"),
                "active_ingredient": otc_fields.get("active_ingredient"),
            },
        }

    # -------------------------
    # Health Check
    # -------------------------
    async def check_health(self) -> bool:
        try:
            url = f"{self.base_url}/label.json?search=openfda.generic_name:aspirin&limit=1"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=5.0)
                return resp.status_code == 200
        except Exception:
            return False