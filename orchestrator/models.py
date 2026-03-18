"""
PIKRS Orchestrator — Unified Data Models
==========================================
Pydantic schemas describing the final, unified intelligence
profile after aggregating responses from multiple MCP servers.
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class DrugIdentifiers(BaseModel):
    """Normalized cross-references to key databases."""
    rxnorm_cui: str | None = None
    pubchem_cid: int | None = None
    chembl_id: Optional[str] = None
    # Support for extensibility
    other_identifiers: dict[str, Any] = Field(default_factory=dict)


class ChemicalProperties(BaseModel):
    """Properties derived primarily from PubChem or similar structural databases."""
    molecular_formula: str | None = None
    molecular_weight: float | None = None
    iupac_name: str | None = None
    canonical_smiles: str | None = None


class RegulatoryInformation(BaseModel):
    """Clinical, dosage, and safety data derived primarily from OpenFDA or DailyMed."""
    indications: str | None = None
    dosage: str | None = None
    warnings: str | None = None
    contraindications: str | None = None
    adverse_reactions: str | None = None
    drug_interactions: str | None = None


class ChemblData(BaseModel):
    chembl_id: str | None = None
    classification: dict | None = None
    structure: dict | None = None
    molecular_properties: dict | None = None
    targets: list[dict] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)


class DrugProfile(BaseModel):

    drug_name: str
    identifiers: DrugIdentifiers = Field(default_factory=DrugIdentifiers)
    chemical_properties: ChemicalProperties = Field(default_factory=ChemicalProperties)
    regulatory_information: RegulatoryInformation = Field(default_factory=RegulatoryInformation)

    chembl: ChemblData | None = None

    clinical_trials: list[dict[str, Any]] = Field(default_factory=list)

    research_papers: list[dict] = Field(default_factory=list)

    synonyms: list[str] = Field(default_factory=list)
    brand_names: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)