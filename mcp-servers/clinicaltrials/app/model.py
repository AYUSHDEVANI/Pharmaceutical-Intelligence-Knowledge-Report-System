from pydantic import BaseModel
from typing import Optional, List


class ClinicalTrial(BaseModel):

    title: Optional[str]
    status: Optional[str]
    phase: Optional[List[str]]
    conditions: Optional[List[str]]