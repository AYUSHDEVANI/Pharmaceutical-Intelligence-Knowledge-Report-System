from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


class PubMedPaper(BaseModel):

    title: Optional[str]
    journal: Optional[str]
    year: Optional[str]
    pubmed_id: Optional[str]