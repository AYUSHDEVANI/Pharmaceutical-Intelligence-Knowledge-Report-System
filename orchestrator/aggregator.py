"""
PIKRS Orchestrator — Aggregator
=================================
Merges raw MCP responses (from the dynamic client) into the
unified DrugProfile ontology.
"""

from __future__ import annotations

from typing import Any
from .models import ChemblData, DrugProfile

def aggregate_mcp_responses(drug_name: str, mcp_results: dict[str, Any]) -> DrugProfile:
    """
    Map independent MCP server payload schemas into the unified `DrugProfile`.
    Safely ignores missing sources or unexpected keys.
    """
    profile = DrugProfile(drug_name=drug_name)

    for source_id, envelope in mcp_results.items():
        profile.sources.append(source_id)
        
        # MCP Response Standard format:
        # { "status": "...", "data": { "identifiers": {}, "results": {} } }
        data = envelope.get("data", {})
        identifiers = data.get("identifiers", {})
        results = data.get("results", {})

        if source_id == "pubchem":
            # Map Identifiers
            if "pubchem_cid" in identifiers:
                profile.identifiers.pubchem_cid = int(identifiers["pubchem_cid"])
            
            # Map Chemical Properties
            profile.chemical_properties.molecular_formula = results.get("molecular_formula")
            if "molecular_weight" in results and results["molecular_weight"] is not None:
                profile.chemical_properties.molecular_weight = float(results["molecular_weight"])
            profile.chemical_properties.iupac_name = results.get("iupac_name")
            profile.chemical_properties.canonical_smiles = results.get("canonical_smiles")

        elif source_id == "rxnorm":
            # Map Identifiers
            if "rxnorm_cui" in identifiers:
                profile.identifiers.rxnorm_cui = str(identifiers["rxnorm_cui"])
            elif "rxnorm_cui" in results:  # fallback if mapped directly in results
                profile.identifiers.rxnorm_cui = str(results["rxnorm_cui"])
                
            # Cross-reference synonyms and naming
            if "ingredient_name" in results and results["ingredient_name"]:
                profile.synonyms.append(results["ingredient_name"])
            if "brand_names" in results and isinstance(results["brand_names"], list):
                profile.brand_names.extend(results["brand_names"])
            if "synonyms" in results and isinstance(results["synonyms"], list):
                profile.synonyms.extend(results["synonyms"])

        elif source_id == "openfda":
            # Map Regulatory Information
            profile.regulatory_information.indications = results.get("indications")
            profile.regulatory_information.dosage = results.get("dosage")
            profile.regulatory_information.warnings = results.get("warnings")
            profile.regulatory_information.contraindications = results.get("contraindications")
            profile.regulatory_information.adverse_reactions = results.get("adverse_reactions")
            profile.regulatory_information.drug_interactions = results.get("drug_interactions")

        
        elif source_id == "clinicaltrials":
            # Map Clinical Trial Data
            trials = results.get("clinical_trials")

            if isinstance(trials, list):
                profile.clinical_trials.extend(trials)


        elif source_id == "pubmed":

            papers = results.get("research_papers")

            if isinstance(papers, list):
                profile.research_papers.extend(papers)

        elif source_id == "chembl":

            profile.identifiers.chembl_id = identifiers.get("chembl_id")

            profile.chembl = ChemblData(
                chembl_id=identifiers.get("chembl_id"),
                classification=results.get("classification"),
                structure=results.get("structure"),
                molecular_properties=results.get("molecular_properties"),
                targets=results.get("targets", []),
                synonyms=results.get("synonyms", [])
            )

        elif source_id == "kegg":

            kegg_matches = results.get("kegg_drugs")

            if isinstance(kegg_matches, list):
                profile.identifiers.other_identifiers["kegg_drugs"] = kegg_matches

        else:
            # Future extensibility: Store unknown source data natively if desired,
            # or just register it as a contributor source.
            pass

    return profile
