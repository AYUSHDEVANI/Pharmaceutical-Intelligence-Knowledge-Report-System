"""PubMed API Client — Ported from PubMedConnector (paginated esearch + batch esummary)."""
import httpx
import logging
from typing import Any, Dict, List

logger = logging.getLogger("mcp_servers.pubmed.client")

PAGE_SIZE = 100
BATCH_SIZE = 100


class PubMedAPIClient:
    def __init__(self, base_url: str, timeout: float = 15.0, max_papers: int = 100):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_papers = max_papers

    async def search_papers(self, drug_name: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            # Step 1: Initial esearch
            url1 = (
                f"{self.base_url}/esearch.fcgi"
                f"?db=pubmed&term={drug_name}&retmode=json&retmax={PAGE_SIZE}&retstart=0"
            )
            resp1 = await client.get(url1, timeout=self.timeout)
            resp1.raise_for_status()
            raw1 = resp1.json()

            esearch = raw1.get("esearchresult", {})
            ids = esearch.get("idlist", [])
            total_count = int(esearch.get("count", 0))

            if not ids:
                raise ValueError(f"No PubMed papers found for '{drug_name}'")

            max_records = min(total_count, self.max_papers)

            # Step 2: Paginate remaining IDs
            for start in range(PAGE_SIZE, max_records, PAGE_SIZE):
                url = (
                    f"{self.base_url}/esearch.fcgi"
                    f"?db=pubmed&term={drug_name}&retmode=json&retmax={PAGE_SIZE}&retstart={start}"
                )
                try:
                    resp = await client.get(url, timeout=self.timeout)
                    if resp.status_code == 200 and resp.content:
                        page = resp.json()
                        page_ids = page.get("esearchresult", {}).get("idlist", [])
                        ids.extend(page_ids)
                except Exception:
                    logger.warning("PubMed pagination error at start=%d", start)

            ids = ids[:max_records]

            # Step 3: Fetch summaries in batches
            papers: List[Dict[str, Any]] = []
            for i in range(0, len(ids), BATCH_SIZE):
                batch_ids = ids[i:i + BATCH_SIZE]
                id_string = ",".join(batch_ids)
                summary_url = (
                    f"{self.base_url}/esummary.fcgi"
                    f"?db=pubmed&id={id_string}&retmode=json"
                )
                try:
                    resp = await client.get(summary_url, timeout=self.timeout)
                    if resp.status_code == 200 and resp.content:
                        summary_data = resp.json()
                        result = summary_data.get("result", {})
                        for pid in batch_ids:
                            paper = result.get(pid, {})
                            papers.append({
                                "pubmed_id": pid,
                                "title": paper.get("title"),
                                "journal": paper.get("fulljournalname"),
                                "year": paper.get("pubdate"),
                            })
                except Exception:
                    logger.warning("PubMed summary batch error")

        return {
            "drug_name": drug_name,
            "identifiers": {},
            "results": {"research_papers": papers},
        }

    async def check_health(self) -> bool:
        try:
            url = f"{self.base_url}/esearch.fcgi?db=pubmed&term=aspirin&retmode=json&retmax=1"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=5.0)
                return resp.status_code == 200
        except Exception:
            return False
