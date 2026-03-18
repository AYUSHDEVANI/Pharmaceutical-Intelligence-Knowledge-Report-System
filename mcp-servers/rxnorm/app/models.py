"""
RxNorm MCP Server — Source-Specific Models
=============================================
Pydantic models describing the data extracted from RxNorm.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RxNormResult(BaseModel):
    """Structured result for a drug resolved via RxNorm."""

    rxnorm_cui: str = Field(..., description="RxNorm Concept Unique Identifier (RxCUI)")
    ingredient_name: Optional[str] = Field(None, description="Active ingredient extracted from concepts")
    brand_names: list[str] = Field(default_factory=list, description="Associated brand names")
    synonyms: list[str] = Field(default_factory=list, description="Drug synonyms and alternative names")
