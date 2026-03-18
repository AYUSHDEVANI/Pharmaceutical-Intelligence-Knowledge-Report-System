from __future__ import annotations

import logging
from typing import Any

from shared.base_connector import BaseConnector
from shared.schemas import MCPRequest

logger = logging.getLogger("mcp.chembl.connector")


class ChemblConnector(BaseConnector):

    source_id = "chembl"
    source_name = "ChEMBL"
    source_url = "https://www.ebi.ac.uk/chembl"

    def __init__(self, base_url: str, **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip("/")

    async def build_request_url(self, request: MCPRequest) -> str:
        """
        First request searches for the molecule using the drug name.
        """
        return f"{self.base_url}/molecule/search?q={request.drug_name}&format=json"

    async def parse_response(
        self,
        raw: Dict[str, Any],
        request: MCPRequest
    ) -> Dict[str, Any]:

        molecules = raw.get("molecules", [])

        if not molecules:
            raise DrugNotFoundError(
                message=f"No ChEMBL data found for '{request.drug_name}'"
            )

        mol = molecules[0]

        chembl_id = mol.get("molecule_chembl_id")

        # -------------------------
        # Molecular Properties
        # -------------------------
        props = mol.get("molecule_properties", {})

        molecular_properties = {
            "molecular_formula": props.get("full_molformula"),
            "molecular_weight": props.get("full_mwt"),
            "logp": props.get("alogp"),
            "polar_surface_area": props.get("psa"),
            "hbond_donors": props.get("hbd"),
            "hbond_acceptors": props.get("hba"),
        }

        # -------------------------
        # Chemical Complexity
        # -------------------------
        chemical_complexity = {
            "aromatic_rings": props.get("aromatic_rings"),
            "heavy_atoms": props.get("heavy_atoms"),
            "rotatable_bonds": props.get("rtb"),
        }

        # -------------------------
        # Structure
        # -------------------------
        structures = mol.get("molecule_structures", {})

        structure = {
            "smiles": structures.get("canonical_smiles"),
            "inchi": structures.get("standard_inchi"),
            "inchi_key": structures.get("standard_inchi_key"),
        }

        # -------------------------
        # Drug Classification
        # -------------------------
        classification = {
            "drug_type": mol.get("molecule_type"),
            "atc_codes": mol.get("atc_classifications", []),
        }

        # -------------------------
        # Approval Info
        # -------------------------
        approval = {
            "first_approved_year": mol.get("first_approval"),
            "clinical_phase": mol.get("max_phase"),
        }

        # -------------------------
        # Pharmacologic Class
        # -------------------------
        pharmacologic_class = {
            "usan_stem": mol.get("usan_stem"),
            "usan_stem_definition": mol.get("usan_stem_definition"),
        }

        # -------------------------
        # Safety
        # -------------------------
        safety = {
            "black_box_warning": bool(mol.get("black_box_warning")),
        }

        # -------------------------
        # Administration Routes
        # -------------------------
        routes: List[str] = []

        if mol.get("oral"):
            routes.append("oral")

        if mol.get("parenteral"):
            routes.append("parenteral")

        if mol.get("topical"):
            routes.append("topical")

        # -------------------------
        # Synonyms
        # -------------------------
        synonyms_raw = mol.get("molecule_synonyms", [])

        synonyms: List[str] = []

        for syn in synonyms_raw[:25]:
            name = syn.get("molecule_synonym")
            if name:
                synonyms.append(name)

        # -------------------------
        # Mechanism / Targets
        # -------------------------
        targets = []

        if chembl_id:

            mech_url = (
                f"{self.base_url}/mechanism.json"
                f"?molecule_chembl_id={chembl_id}"
            )

            try:
                resp = await self._client.get(mech_url)

                if resp.status_code == 200:

                    mech_data = resp.json()

                    for mech in mech_data.get("mechanisms", []):

                        targets.append(
                            {
                                "target_name": mech.get("target_pref_name"),
                                "target_chembl_id": mech.get("target_chembl_id"),
                                "organism": mech.get("organism"),
                                "mechanism": mech.get("mechanism_of_action"),
                            }
                        )

            except Exception as e:
                logger.warning("Failed to retrieve mechanism data: %s", e)

        return {
            "drug_name": request.drug_name,
            "identifiers": {
                "chembl_id": chembl_id
            },
            "results": {
                "classification": classification,
                "approval": approval,
                "pharmacologic_class": pharmacologic_class,
                "safety": safety,
                "administration_routes": routes,
                "molecular_properties": molecular_properties,
                "chemical_complexity": chemical_complexity,
                "structure": structure,
                "synonyms": synonyms,
                "targets": targets
            }
        }

    async def check_upstream_health(self) -> bool:

        try:
            if self._client is None:
                return False

            resp = await self._client.get(
                f"{self.base_url}/status",
                timeout=5.0,
            )

            return resp.status_code == 200

        except Exception:
            return False