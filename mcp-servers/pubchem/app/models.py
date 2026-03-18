"""
PubChem MCP Server — Source-Specific Models
=============================================
Pydantic models describing the data extracted from PubChem.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class PubChemCompound(BaseModel):
    """Structured result for a single PubChem compound."""

    pubchem_cid: int = Field(..., description="PubChem Compound Identifier")
    molecular_formula: Optional[str] = Field(None, description="e.g. C9H8O4")
    molecular_weight: Optional[float] = Field(None, description="g/mol")
    iupac_name: Optional[str] = Field(None, description="IUPAC systematic name")
    canonical_smiles: Optional[str] = Field(None, description="Canonical SMILES string")
    inchi: Optional[str] = Field(None, description="InChI identifier")
    inchi_key: Optional[str] = Field(None, description="InChIKey hash")
