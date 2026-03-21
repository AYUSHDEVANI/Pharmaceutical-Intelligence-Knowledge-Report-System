"""PubChem API Client — v4.2 Final Production Version"""

import httpx
import logging
import asyncio
from typing import Any, Dict, List
from urllib.parse import quote
from datetime import datetime

logger = logging.getLogger("mcp_servers.pubchem.client")


class PubChemAPIClient:
    def __init__(self, base_url: str, timeout: float = 15.0, max_retries: int = 3):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )

        self.semaphore = asyncio.Semaphore(2)

    # -----------------------------
    # PUBLIC METHOD
    # -----------------------------
    async def search_compound(self, drug_name: str) -> Dict[str, Any]:
        drug_name = drug_name.strip().lower()

        try:
            results = await asyncio.gather(
                self._fetch_properties(drug_name),
                self._fetch_synonyms(drug_name),
                self._fetch_description(drug_name),
                return_exceptions=True
            )

            raw_props = results[0] if not isinstance(results[0], Exception) else {}
            synonyms = results[1] if not isinstance(results[1], Exception) else []
            description = results[2] if not isinstance(results[2], Exception) else ""

            compounds = self._extract_compounds(raw_props)

            if not compounds:
                return self._error("NOT_FOUND", f"{drug_name} not found")

            normalized = [
                self._normalize(c, drug_name, synonyms, description)
                for c in compounds
            ]

            return {
                "source": {
                    "name": "PubChem",
                    "url": "https://pubchem.ncbi.nlm.nih.gov"
                },
                "query": drug_name,
                "count": len(normalized),
                "results": normalized,
                "meta": self._meta()
            }

        except Exception as e:
            logger.exception("pubchem_search_failed")
            return self._error("INTERNAL_ERROR", str(e))

    # -----------------------------
    # FETCH METHODS
    # -----------------------------
    async def _fetch_properties(self, drug_name: str) -> Dict[str, Any]:

        base_props = [
            "MolecularFormula",
            "MolecularWeight",
            "IUPACName",
            "CanonicalSMILES",
            "InChI",
            "InChIKey",
            "IsomericSMILES"
        ]

        extra_props = [
            "XLogP",
            "TPSA",
            "ExactMass",
            "Complexity",
            "HydrogenBondDonorCount",
            "HydrogenBondAcceptorCount",
            "RotatableBondCount",
        ]

        base_url = f"{self.base_url}/compound/name/{quote(drug_name)}/property/{','.join(base_props)}/JSON"
        base_data = await self._request(base_url)

        if not base_data or "PropertyTable" not in base_data:
            return {}

        extra_url = f"{self.base_url}/compound/name/{quote(drug_name)}/property/{','.join(extra_props)}/JSON"
        extra_data = await self._request(extra_url)

        try:
            base_props_data = base_data["PropertyTable"]["Properties"][0]

            if extra_data and "PropertyTable" in extra_data:
                extra_props_data = extra_data["PropertyTable"]["Properties"][0]
                base_props_data.update(extra_props_data)

            base_data["PropertyTable"]["Properties"][0] = base_props_data
            return base_data

        except Exception:
            return base_data

    async def _fetch_synonyms(self, drug_name: str) -> List[str]:
        url = f"{self.base_url}/compound/name/{quote(drug_name)}/synonyms/JSON"
        data = await self._request(url)

        try:
            return data["InformationList"]["Information"][0]["Synonym"]
        except:
            return []

    async def _fetch_description(self, drug_name: str) -> str:
        url = f"{self.base_url}/compound/name/{quote(drug_name)}/description/JSON"
        data = await self._request(url)

        try:
            info = data["InformationList"]["Information"][0]
            return (
                info.get("Description")
                or info.get("Title")
                or f"{drug_name} is a pharmaceutical compound."
            )
        except:
            return f"{drug_name} is a pharmaceutical compound."

    # -----------------------------
    # REQUEST HANDLER
    # -----------------------------
    async def _request(self, url: str) -> Dict[str, Any]:
        for attempt in range(self.max_retries):
            try:
                async with self.semaphore:
                    resp = await self.client.get(url)

                if resp.status_code == 200:
                    return resp.json()

                if resp.status_code == 404:
                    return {}

                if resp.status_code == 429:
                    await asyncio.sleep(2 ** attempt)
                    continue

                resp.raise_for_status()

            except Exception as e:
                logger.warning("retrying_request", extra={"url": url, "error": str(e)})
                await asyncio.sleep(2 ** attempt)

        return {}

    # -----------------------------
    # NORMALIZATION
    # -----------------------------
    def _normalize(self, props, drug_name, synonyms, description):

        smiles = props.get("CanonicalSMILES") or props.get("ConnectivitySMILES")
        brand_names, aliases = self._split_synonyms(synonyms)

        mw = self._safe_float(props.get("MolecularWeight"))
        tpsa = self._safe_float(props.get("TPSA"))

        return self._clean({
            "drug": {
                "name": drug_name,
                "description": description,
                "naming": {
                    "generic_name": drug_name,
                    "brand_names": brand_names,
                    "aliases": aliases
                }
            },

            "identifiers": {
                "pubchem_cid": props.get("CID"),
                "inchi_key": props.get("InChIKey"),
            },

            "chemical": {
                "molecular_formula": props.get("MolecularFormula"),
                "molecular_weight": mw
            },

            "physicochemical": {
                "logP": self._safe_float(props.get("XLogP")),
                "tpsa": tpsa,
                "exact_mass": self._safe_float(props.get("ExactMass")),
                "complexity": props.get("Complexity"),
            },

            "structure": {
                "canonical_smiles": smiles,
                "isomeric_smiles": props.get("IsomericSMILES"),
                "inchi": props.get("InChI"),
            },

            "drug_likeness": self._lipinski(props),

            "analysis": {
                "is_large_molecule": mw > 500 if mw else None,
                "high_polarity": tpsa > 140 if tpsa else None
            }
        })

    # -----------------------------
    # HELPERS
    # -----------------------------
    def _split_synonyms(self, synonyms):
        brands, aliases = [], []

        for s in synonyms:
            s = s.strip()

            if any(char.isdigit() for char in s):
                continue
            if len(s) < 4:
                continue
            if len(s.split()) > 3:
                continue

            if s.lower() == s:
                aliases.append(s)
            else:
                brands.append(s)

        return list(dict.fromkeys(brands))[:5], list(dict.fromkeys(aliases))[:5]

    def _lipinski(self, props):
        try:
            mw = float(props.get("MolecularWeight", 0))
            donors = props.get("HydrogenBondDonorCount") or 0
            acceptors = props.get("HydrogenBondAcceptorCount") or 0

            return {
                "lipinski_rule_of_5": (
                    mw < 500 and donors <= 5 and acceptors <= 10
                )
            }
        except:
            return {}

    def _safe_float(self, value):
        try:
            return float(value) if value else None
        except:
            return None

    def _clean(self, data):
        if isinstance(data, dict):
            return {k: self._clean(v) for k, v in data.items() if v is not None}
        if isinstance(data, list):
            return [self._clean(v) for v in data if v]
        return data

    def _extract_compounds(self, raw: Dict[str, Any]) -> list:
        if not raw or "PropertyTable" not in raw:
            return []
        return raw.get("PropertyTable", {}).get("Properties", [])

    def _error(self, err_type, message):
        return {
            "source": {
                "name": "PubChem",
                "url": "https://pubchem.ncbi.nlm.nih.gov"
            },
            "error": {"type": err_type, "message": message},
            "meta": self._meta()
        }

    def _meta(self):
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "version": "4.2-final"
        }

    async def close(self):
        await self.client.aclose()