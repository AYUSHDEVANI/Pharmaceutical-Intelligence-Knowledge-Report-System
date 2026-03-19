"""PubChem API Client — Ported from PubChemConnector."""
import httpx
import logging
from typing import Any, Dict
from urllib.parse import quote

logger = logging.getLogger("mcp_servers.pubchem.client")

PROPERTIES = [
    "MolecularFormula", "MolecularWeight", "IUPACName",
    "CanonicalSMILES", "InChI", "InChIKey",
]


class PubChemAPIClient:
    def __init__(self, base_url: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def search_compound(self, drug_name: str) -> Dict[str, Any]:
        props_csv = ",".join(PROPERTIES)
        encoded = quote(drug_name, safe="")
        url = f"{self.base_url}/compound/name/{encoded}/property/{props_csv}/JSON"

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=self.timeout)
            resp.raise_for_status()
            raw = resp.json()

        try:
            props_list = raw["PropertyTable"]["Properties"]
        except (KeyError, TypeError):
            raise ValueError(f"Drug '{drug_name}' was not found in PubChem")

        if not props_list:
            raise ValueError(f"No compound data returned for '{drug_name}'")

        props = props_list[0]
        return {
            "drug_name": drug_name,
            "identifiers": {"pubchem_cid": props.get("CID")},
            "results": {
                "molecular_formula": props.get("MolecularFormula"),
                "molecular_weight": props.get("MolecularWeight"),
                "iupac_name": props.get("IUPACName"),
                "canonical_smiles": props.get("CanonicalSMILES"),
                "inchi": props.get("InChI"),
                "inchi_key": props.get("InChIKey"),
            },
        }

    async def check_health(self) -> bool:
        try:
            url = f"{self.base_url}/compound/name/aspirin/property/MolecularFormula/JSON"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=5.0)
                return resp.status_code == 200
        except Exception:
            return False
