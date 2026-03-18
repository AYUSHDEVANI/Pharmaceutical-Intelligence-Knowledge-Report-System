from __future__ import annotations

import logging
from typing import Any

from shared.base_connector import BaseConnector
from shared.exceptions import DrugNotFoundError
from shared.schemas import MCPRequest

logger = logging.getLogger("mcp.pubmed.connector")


class PubMedConnector(BaseConnector):

    source_id = "pubmed"
    source_name = "PubMed"
    source_url = "https://pubmed.ncbi.nlm.nih.gov"

    MAX_PAPERS = 100
    PAGE_SIZE = 100
    BATCH_SIZE = 100

    def __init__(self, base_url: str, **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip("/")

    async def build_request_url(self, request: MCPRequest) -> str:

        return (
            f"{self.base_url}/esearch.fcgi"
            f"?db=pubmed"
            f"&term={request.drug_name}"
            f"&retmode=json"
            f"&retmax={self.PAGE_SIZE}"
            f"&retstart=0"
        )

    async def parse_response(
        self,
        raw: dict[str, Any],
        request: MCPRequest,
    ) -> dict[str, Any]:

        esearch = raw.get("esearchresult", {})
        ids = esearch.get("idlist", [])
        total_count = int(esearch.get("count", 0))

        if not ids:
            raise DrugNotFoundError(
                f"No PubMed papers found for '{request.drug_name}'"
            )

        logger.info("PubMed total results: %s", total_count)

        max_records = min(total_count, self.MAX_PAPERS)

        # -------- Pagination --------
        for start in range(self.PAGE_SIZE, max_records, self.PAGE_SIZE):

            url = (
                f"{self.base_url}/esearch.fcgi"
                f"?db=pubmed"
                f"&term={request.drug_name}"
                f"&retmode=json"
                f"&retmax={self.PAGE_SIZE}"
                f"&retstart={start}"
            )

            try:
                resp = await self._client.get(url)

                if resp.status_code != 200 or not resp.content:
                    logger.warning("PubMed pagination request failed")
                    continue

                page = resp.json()

            except Exception:
                logger.warning("PubMed pagination JSON error")
                continue

            page_ids = page.get("esearchresult", {}).get("idlist", [])
            ids.extend(page_ids)

        ids = ids[:max_records]

        papers = []

        # -------- Fetch summaries in batches --------
        for i in range(0, len(ids), self.BATCH_SIZE):

            batch_ids = ids[i:i + self.BATCH_SIZE]
            id_string = ",".join(batch_ids)

            summary_url = (
                f"{self.base_url}/esummary.fcgi"
                f"?db=pubmed&id={id_string}&retmode=json"
            )

            try:
                resp = await self._client.get(summary_url)

                if resp.status_code != 200 or not resp.content:
                    logger.warning("PubMed summary request failed")
                    continue

                summary_data = resp.json()

            except Exception:
                logger.warning("PubMed summary JSON error")
                continue

            result = summary_data.get("result", {})

            for pid in batch_ids:

                paper = result.get(pid, {})

                papers.append({
                    "pubmed_id": pid,
                    "title": paper.get("title"),
                    "journal": paper.get("fulljournalname"),
                    "year": paper.get("pubdate"),
                })

        return {
            "drug_name": request.drug_name,
            "identifiers": {},
            "results": {
                "research_papers": papers
            },
        }

    async def check_upstream_health(self) -> bool:

        try:
            if self._client is None:
                return False

            resp = await self._client.get(
                f"{self.base_url}/esearch.fcgi?db=pubmed&term=aspirin&retmode=json&retmax=1",
                timeout=5.0,
            )

            return resp.status_code == 200

        except Exception:
            return False