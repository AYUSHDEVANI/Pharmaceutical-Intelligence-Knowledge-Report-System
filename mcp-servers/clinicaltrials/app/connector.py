import logging
from typing import Any

from shared.base_connector import BaseConnector
from shared.schemas import MCPRequest
from shared.exceptions import DrugNotFoundError

logger = logging.getLogger("mcp.clinicaltrials.connector")


class ClinicalTrialsConnector(BaseConnector):

    source_id = "clinicaltrials"
    source_name = "ClinicalTrials.gov"
    source_url = "https://clinicaltrials.gov"

    def __init__(self, base_url: str, **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------
    # Initial request
    # ------------------------------------------------------------------

    async def build_request_url(self, request: MCPRequest) -> str:
        return (
            f"{self.base_url}/studies"
            f"?query.term={request.drug_name}"
            f"&pageSize=100"
        )

    # ------------------------------------------------------------------
    # Parse response + pagination
    # ------------------------------------------------------------------

    async def parse_response(
            self,
            raw: dict[str, Any],
            request: MCPRequest
        ) -> dict[str, Any]:

            all_studies = raw.get("studies", [])[:100]

            if not all_studies:
                raise DrugNotFoundError(
                    message=f"No clinical trials found for '{request.drug_name}'"
                )

            trials = []

            for s in all_studies:

                protocol = s.get("protocolSection", {})

                identification = protocol.get("identificationModule", {})
                status = protocol.get("statusModule", {})
                design = protocol.get("designModule", {})
                conditions = protocol.get("conditionsModule", {})

                trials.append({
                    "title": identification.get("briefTitle"),
                    "status": status.get("overallStatus"),
                    "phase": design.get("phases"),
                    "conditions": conditions.get("conditions"),
                })

            logger.info(
                "Retrieved %d clinical trials for %s",
                len(trials),
                request.drug_name
            )

            return {
                "drug_name": request.drug_name,
                "results": {
                    "clinical_trials": trials,
                    "total_trials": len(trials)
                }
            }

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def check_upstream_health(self) -> bool:
        try:
            resp = await self._client.get(
                f"{self.base_url}/studies?query.term=aspirin&pageSize=1"
            )
            return resp.status_code == 200
        except Exception:
            return False