"""
OpenFDA MCP Server — Source-Specific Models
=============================================
Pydantic models describing the data extracted from OpenFDA.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class OpenFDAResult(BaseModel):
    """Structured result for an OpenFDA drug label."""

    indications: Optional[str] = Field(None, description="Indications and usage")
    dosage: Optional[str] = Field(None, description="Dosage and administration")
    warnings: Optional[str] = Field(None, description="Boxed warnings or general warnings")
    contraindications: Optional[str] = Field(None, description="Contraindications")
    adverse_reactions: Optional[str] = Field(None, description="Adverse reactions")
    drug_interactions: Optional[str] = Field(None, description="Drug interactions")
