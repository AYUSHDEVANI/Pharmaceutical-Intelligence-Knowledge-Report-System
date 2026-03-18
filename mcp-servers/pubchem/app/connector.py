"""
PubChem MCP Server — Connector
================================
Implements the PubChem REST (PUG) API connector.

Retrieves:
- Molecular formula
- Molecular weight
- IUPAC name
- Canonical SMILES
- InChI / InChIKey
- PubChem CID
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import sys
import os

# Add parent directory so shared library is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from shared.base_connector import BaseConnector
from shared.exceptions import DrugNotFoundError
from shared.schemas import MCPRequest

logger = logging.getLogger("mcp.pubchem.connector")


class PubChemConnector(BaseConnector):
    """Connector for the PubChem PUG REST API."""

    source_id = "pubchem"
    source_name = "PubChem"
    source_url = "https://pubchem.ncbi.nlm.nih.gov"

    # PubChem property keys we request in a single call
    PROPERTIES = [
        "MolecularFormula",
        "MolecularWeight",
        "IUPACName",
        "CanonicalSMILES",
        "InChI",
        "InChIKey",
    ]

    def __init__(self, base_url: str, **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------
    # Abstract hook implementations
    # ------------------------------------------------------------------

    async def build_request_url(self, request: MCPRequest) -> str:
        """
        Construct the PUG REST URL.

        If a PubChem CID is supplied in ``identifiers``, query by CID.
        Otherwise, query by compound name.
        """
        properties_csv = ",".join(self.PROPERTIES)

        cid = None
        if request.identifiers:
            cid = request.identifiers.pubchem_cid

        if cid:
            return (
                f"{self.base_url}/compound/cid/{cid}"
                f"/property/{properties_csv}/JSON"
            )

        encoded_name = quote(request.drug_name, safe="")
        return (
            f"{self.base_url}/compound/name/{encoded_name}"
            f"/property/{properties_csv}/JSON"
        )

    async def parse_response(
        self,
        raw: dict[str, Any],
        request: MCPRequest,
    ) -> dict[str, Any]:
        """
        Extract compound properties from PubChem's JSON response.

        Expected raw shape::

            {
              "PropertyTable": {
                "Properties": [
                  {
                    "CID": 2244,
                    "MolecularFormula": "C9H8O4",
                    "MolecularWeight": 180.16,
                    ...
                  }
                ]
              }
            }
        """
        try:
            props_list = raw["PropertyTable"]["Properties"]
        except (KeyError, TypeError) as exc:
            raise DrugNotFoundError(
                message=f"Drug '{request.drug_name}' was not found in PubChem",
                details={"raw_keys": list(raw.keys()) if isinstance(raw, dict) else []},
            ) from exc

        if not props_list:
            raise DrugNotFoundError(
                message=f"No compound data returned for '{request.drug_name}'",
            )

        props = props_list[0]

        return {
            "drug_name": request.drug_name,
            "identifiers": {
                "pubchem_cid": props.get("CID"),
            },
            "results": {
                "molecular_formula": props.get("MolecularFormula"),
                "molecular_weight": props.get("MolecularWeight"),
                "iupac_name": props.get("IUPACName"),
                "canonical_smiles": props.get("CanonicalSMILES"),
                "inchi": props.get("InChI"),
                "inchi_key": props.get("InChIKey"),
            },
        }

    async def check_upstream_health(self) -> bool:
        """Ping PubChem status endpoint."""
        try:
            if self._client is None:
                return False
            resp = await self._client.get(
                f"{self.base_url}/compound/name/aspirin/property/MolecularFormula/JSON",
                timeout=5.0,
            )
            return resp.status_code == 200
        except Exception:
            return False
