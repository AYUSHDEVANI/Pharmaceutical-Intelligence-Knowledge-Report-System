"""ChEMBL API Client — Final Production Version (fully normalized)."""

import httpx
import logging
from typing import Any, Dict, List
from datetime import datetime

logger = logging.getLogger("mcp_servers.chembl.client")


class ChemblAPIClient:
    def __init__(self, base_url: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # -------------------------------
    # Smart molecule selection (CRITICAL)
    # -------------------------------
    def _select_best_molecule(self, molecules: List[Dict[str, Any]]) -> Dict[str, Any]:
        def score(m):
            return (
                (2 if m.get("pref_name") else 0) +
                (3 if str(m.get("max_phase")) == "4.0" else 0) +
                (3 if m.get("therapeutic_flag") else 0) +
                (2 if m.get("dosed_ingredient") else 0)
            )

        return sorted(molecules, key=score, reverse=True)[0]

    async def search_molecule(self, drug_name: str) -> Dict[str, Any]:
        url = f"{self.base_url}/molecule/search?q={drug_name}&format=json"

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=self.timeout)
            resp.raise_for_status()
            raw = resp.json()

        molecules = raw.get("molecules", [])
        if not molecules:
            raise ValueError(f"No ChEMBL data found for '{drug_name}'")

        # ✅ Correct molecule selection
        mol = self._select_best_molecule(molecules)

        chembl_id = mol.get("molecule_chembl_id")
        pref_name = (mol.get("pref_name") or drug_name).lower()

        props = mol.get("molecule_properties", {})

        # -------------------------------
        # Naming (CLEANED)
        # -------------------------------
        synonyms_raw = mol.get("molecule_synonyms", [])

        brand_names = set()
        aliases = set()

        for s in synonyms_raw:
            name = s.get("molecule_synonym")
            syn_type = s.get("syn_type")

            if not name:
                continue

            name_clean = name.strip()

            # Brand names
            if syn_type == "TRADE_NAME" and name_clean.lower() != pref_name:
                brand_names.add(name_clean)

            # Everything else → aliases
            else:
                if name_clean.lower() != pref_name:
                    aliases.add(name_clean)

        # Deduplicate against generic name
        brand_names.discard(pref_name)
        aliases.discard(pref_name)

        # -------------------------------
        # Structure
        # -------------------------------
        structures = mol.get("molecule_structures", {})
        structure = {
            "smiles": structures.get("canonical_smiles"),
            "inchi": structures.get("standard_inchi"),
            "inchi_key": structures.get("standard_inchi_key"),
        }

        # -------------------------------
        # Safe float conversion
        # -------------------------------
        def to_float(val):
            try:
                return float(val) if val is not None else None
            except:
                return None

        # -------------------------------
        # Chemical properties
        # -------------------------------
        chemical = {
            "molecular_formula": props.get("full_molformula"),
            "molecular_weight": to_float(props.get("full_mwt")),
            "logp": to_float(props.get("alogp")),
            "polar_surface_area": to_float(props.get("psa")),
            "hbond_donors": props.get("hbd"),
            "hbond_acceptors": props.get("hba"),
        }

        complexity = {
            "aromatic_rings": props.get("aromatic_rings"),
            "heavy_atoms": props.get("heavy_atoms"),
            "rotatable_bonds": props.get("rtb"),
        }

        # -------------------------------
        # Classification & approval
        # -------------------------------
        classification = {
            "drug_type": mol.get("molecule_type"),
            "atc_codes": mol.get("atc_classifications", []),
        }

        approval = {
            "first_approved_year": mol.get("first_approval"),
            "clinical_phase": int(float(mol.get("max_phase"))) if mol.get("max_phase") else None,
        }

        pharmacologic_class = {
            "usan_stem": mol.get("usan_stem"),
            "usan_stem_definition": mol.get("usan_stem_definition"),
        }

        safety = {
            "black_box_warning": bool(mol.get("black_box_warning"))
        }

        # -------------------------------
        # Routes
        # -------------------------------
        routes: List[str] = []
        if mol.get("oral"):
            routes.append("oral")
        if mol.get("parenteral"):
            routes.append("parenteral")
        if mol.get("topical"):
            routes.append("topical")

        # -------------------------------
        # Targets (FIXED fallback)
        # -------------------------------
        targets = []

        if chembl_id:
            try:
                mech_url = f"{self.base_url}/mechanism.json?molecule_chembl_id={chembl_id}"
                async with httpx.AsyncClient() as c2:
                    resp2 = await c2.get(mech_url, timeout=self.timeout)

                    if resp2.status_code == 200:
                        for mech in resp2.json().get("mechanisms", []):
                            targets.append({
                                "target": {
                                    "name": mech.get("target_pref_name") or mech.get("target_chembl_id"),
                                    "chembl_id": mech.get("target_chembl_id"),
                                    "organism": mech.get("organism"),
                                },
                                "mechanism_of_action": mech.get("mechanism_of_action"),
                            })
            except Exception as e:
                logger.warning(f"Mechanism fetch failed: {e}")

        # -------------------------------
        # Final Output
        # -------------------------------
        result = {
            "drug": {
                "name": pref_name,
                "description": pref_name,
                "naming": {
                    "generic_name": pref_name,
                    "brand_names": sorted(list(brand_names)),
                    "aliases": sorted(list(aliases))[:20],
                },
            },
            "identifiers": {
                "chembl_id": chembl_id,
                "inchi_key": structure.get("inchi_key"),
            },
            "chemical": chemical,
            "structure": structure,
            "classification": classification,
            "approval": approval,
            "pharmacology": {
                "targets": targets,
                "usan_stem": pharmacologic_class,
            },
            "safety": safety,
            "administration": {
                "routes": routes
            },
            "complexity": complexity,
        }

        return {
            "source": {
                "name": "ChEMBL",
                "url": "https://www.ebi.ac.uk/chembl",
            },
            "query": drug_name,
            "count": 1,
            "results": [result],
            "meta": {
                "timestamp": datetime.utcnow().isoformat(),
                "version": "chembl-v3.0-final",
            },
        }

    async def check_health(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/status", timeout=5.0)
                return resp.status_code == 200
        except Exception:
            return False