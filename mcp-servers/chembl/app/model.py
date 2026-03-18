from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class ChemblTarget(BaseModel):

    target_name: Optional[str]
    gene_symbol: Optional[str]
    organism: Optional[str]