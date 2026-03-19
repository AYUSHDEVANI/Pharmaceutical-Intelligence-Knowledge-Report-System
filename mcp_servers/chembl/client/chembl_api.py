"""ChEMBL API Client — Ported from ChemblConnector."""
import httpx
import logging
from typing import Any, Dict, List

logger = logging.getLogger("mcp_servers.chembl.client")


class ChemblAPIClient:
    def __init__(self, base_url: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def search_molecule(self, drug_name: str) -> Dict[str, Any]:
        url = f"{self.base_url}/molecule/search?q={drug_name}&format=json"

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=self.timeout)
            resp.raise_for_status()
            raw = resp.json()

        molecules = raw.get("molecules", [])
        if not molecules:
            raise ValueError(f"No ChEMBL data found for '{drug_name}'")

        mol = molecules[0]
        chembl_id = mol.get("molecule_chembl_id")

        props = mol.get("molecule_properties", {})
        molecular_properties = {
            "molecular_formula": props.get("full_molformula"),
            "molecular_weight": props.get("full_mwt"),
            "logp": props.get("alogp"),
            "polar_surface_area": props.get("psa"),
            "hbond_donors": props.get("hbd"),
            "hbond_acceptors": props.get("hba"),
        }
        chemical_complexity = {
            "aromatic_rings": props.get("aromatic_rings"),
            "heavy_atoms": props.get("heavy_atoms"),
            "rotatable_bonds": props.get("rtb"),
        }

        structures = mol.get("molecule_structures", {})
        structure = {
            "smiles": structures.get("canonical_smiles"),
            "inchi": structures.get("standard_inchi"),
            "inchi_key": structures.get("standard_inchi_key"),
        }
        classification = {
            "drug_type": mol.get("molecule_type"),
            "atc_codes": mol.get("atc_classifications", []),
        }
        approval = {
            "first_approved_year": mol.get("first_approval"),
            "clinical_phase": mol.get("max_phase"),
        }
        pharmacologic_class = {
            "usan_stem": mol.get("usan_stem"),
            "usan_stem_definition": mol.get("usan_stem_definition"),
        }
        safety = {"black_box_warning": bool(mol.get("black_box_warning"))}

        routes: List[str] = []
        if mol.get("oral"): routes.append("oral")
        if mol.get("parenteral"): routes.append("parenteral")
        if mol.get("topical"): routes.append("topical")

        synonyms_raw = mol.get("molecule_synonyms", [])
        synonyms = [s.get("molecule_synonym") for s in synonyms_raw[:25] if s.get("molecule_synonym")]

        # Mechanism targets
        targets = []
        if chembl_id:
            try:
                mech_url = f"{self.base_url}/mechanism.json?molecule_chembl_id={chembl_id}"
                async with httpx.AsyncClient() as c2:
                    resp2 = await c2.get(mech_url, timeout=self.timeout)
                    if resp2.status_code == 200:
                        for mech in resp2.json().get("mechanisms", []):
                            targets.append({
                                "target_name": mech.get("target_pref_name"),
                                "target_chembl_id": mech.get("target_chembl_id"),
                                "organism": mech.get("organism"),
                                "mechanism": mech.get("mechanism_of_action"),
                            })
            except Exception as e:
                logger.warning(f"Failed to retrieve mechanism data: {e}")

        return {
            "drug_name": drug_name,
            "identifiers": {"chembl_id": chembl_id},
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
                "targets": targets,
            },
        }

    async def check_health(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/status", timeout=5.0)
                return resp.status_code == 200
        except Exception:
            return False
