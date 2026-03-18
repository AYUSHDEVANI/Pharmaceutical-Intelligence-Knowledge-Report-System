from typing import Optional
from pydantic import BaseModel


class KeggDrug(BaseModel):

    kegg_id: Optional[str]
    description: Optional[str]