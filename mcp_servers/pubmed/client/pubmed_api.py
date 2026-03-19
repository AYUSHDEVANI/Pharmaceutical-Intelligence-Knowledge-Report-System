"""PubMed API Client — Advanced Intelligence Version (final)."""
import httpx
import logging
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET

logger = logging.getLogger("mcp_servers.pubmed.client")

PAGE_SIZE = 100
BATCH_SIZE = 100


class PubMedAPIClient:
    def __init__(self, base_url: str, timeout: float = 15.0, max_papers: int = 100):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_papers = max_papers

    # -------------------------
    # Utilities
    # -------------------------

    def clean_text(self, text: Optional[str], limit: int = 1000) -> Optional[str]:
        if not text:
            return None
        text = " ".join(text.split())
        return text[:limit]

    def is_relevant(self, title: str, abstract: Optional[str], drug_name: str) -> bool:
        if not title:
            return False

        title_lower = title.lower()
        abstract_lower = (abstract or "").lower()
        drug = drug_name.lower()

        # STRICT: drug must be in TITLE (not just abstract)
        if drug not in title_lower:
            return False

        # remove animal + unrelated domains
        exclude_keywords = [
            "guinea pig", "mouse", "rat", "rabbit",
            "in vitro", "acupuncture", "herbal"
        ]

        if any(k in title_lower for k in exclude_keywords):
            return False

        return True

    def extract_doi(self, articleids: List[Dict]) -> Optional[str]:
        for aid in articleids:
            if aid.get("idtype") == "doi":
                return aid.get("value")
        return None

    def classify_study(self, pubtypes: List[str], title: str) -> str:
        text = " ".join(pubtypes).lower() + " " + (title or "").lower()

        if "meta-analysis" in text:
            return "meta_analysis"
        if "systematic review" in text:
            return "systematic_review"
        if "review" in text:
            return "review"
        if "randomized" in text:
            return "randomized_trial"
        if "clinical trial" in text:
            return "clinical_trial"

        return "observational"

    def extract_focus(self, text: Optional[str]) -> str:
        if not text:
            return "general"

        text = text.lower()

        # PRIORITIZE efficacy if both present
        if any(k in text for k in ["efficacy", "effectiveness", "treatment", "outcome"]):
            return "efficacy"

        if any(k in text for k in ["adverse", "toxicity", "safety", "risk"]):
            return "safety"

        return "general"

    def rank_papers(self, papers: List[Dict]) -> List[Dict]:
        priority = {
            "meta_analysis": 5,
            "systematic_review": 4,
            "randomized_trial": 3,
            "clinical_trial": 2,
            "observational": 1,
        }

        def score(p):
            return (
                priority.get(p.get("study_type"), 0),
                1 if p.get("focus") == "efficacy" else 0,
                int(p.get("year") or 0)
            )

        return sorted(papers, key=score, reverse=True)

    def build_summary(self, papers: List[Dict]) -> Dict:
        return {
            "total_analyzed": len(papers),

            "evidence_strength": {
                "high": sum(1 for p in papers if p["study_type"] in ["meta_analysis", "systematic_review"]),
                "moderate": sum(1 for p in papers if "trial" in p["study_type"]),
                "low": sum(1 for p in papers if p["study_type"] == "observational"),
            },

            "focus_distribution": {
                "safety": sum(1 for p in papers if p["focus"] == "safety"),
                "efficacy": sum(1 for p in papers if p["focus"] == "efficacy"),
            }
        }

    def clinical_score(self, paper: Dict) -> int:
        score = 0

        if paper["study_type"] in ["meta_analysis", "systematic_review"]:
            score += 3
        if "trial" in paper["study_type"]:
            score += 2
        if paper["focus"] == "efficacy":
            score += 2

        return score
    # -------------------------
    # Main Function
    # -------------------------

    async def search_papers(self, drug_name: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:

            # -------------------------
            # STEP 1: esearch
            # -------------------------
            search_url = (
                f"{self.base_url}/esearch.fcgi"
                f"?db=pubmed&term={drug_name}"
                f"&retmode=json&retmax={PAGE_SIZE}&retstart=0"
            )

            resp = await client.get(search_url, timeout=self.timeout)
            resp.raise_for_status()
            raw = resp.json()

            esearch = raw.get("esearchresult", {})
            ids = esearch.get("idlist", [])
            total_count = int(esearch.get("count", 0))

            if not ids:
                raise ValueError(f"No PubMed papers found for '{drug_name}'")

            max_records = min(total_count, self.max_papers)

            # pagination
            for start in range(PAGE_SIZE, max_records, PAGE_SIZE):
                url = (
                    f"{self.base_url}/esearch.fcgi"
                    f"?db=pubmed&term={drug_name}"
                    f"&retmode=json&retmax={PAGE_SIZE}&retstart={start}"
                )
                try:
                    r = await client.get(url, timeout=self.timeout)
                    if r.status_code == 200:
                        ids.extend(r.json().get("esearchresult", {}).get("idlist", []))
                except Exception:
                    logger.warning("Pagination error at start=%d", start)

            ids = ids[:max_records]

            # -------------------------
            # STEP 2: esummary
            # -------------------------
            papers_map = {}

            for i in range(0, len(ids), BATCH_SIZE):
                batch_ids = ids[i:i + BATCH_SIZE]
                id_string = ",".join(batch_ids)

                summary_url = (
                    f"{self.base_url}/esummary.fcgi"
                    f"?db=pubmed&id={id_string}&retmode=json"
                )

                try:
                    r = await client.get(summary_url, timeout=self.timeout)
                    if r.status_code != 200:
                        continue

                    data = r.json().get("result", {})

                    for pid in batch_ids:
                        paper = data.get(pid, {})
                        title = paper.get("title")

                        papers_map[pid] = {
                            "pubmed_id": pid,
                            "title": title,
                            "journal": paper.get("fulljournalname"),
                            "year": (paper.get("pubdate") or "")[:4],
                            "authors": [a.get("name") for a in paper.get("authors", [])][:5],
                            "study_type": self.classify_study(
                                paper.get("pubtype", []),
                                title,
                            ),
                            "doi": self.extract_doi(
                                paper.get("articleids", [])
                            ),
                        }

                except Exception:
                    logger.warning("Summary batch error")

            # -------------------------
            # STEP 3: efetch (abstracts + filtering)
            # -------------------------
            final_papers = []

            for i in range(0, len(papers_map), BATCH_SIZE):
                batch_ids = list(papers_map.keys())[i:i + BATCH_SIZE]
                id_string = ",".join(batch_ids)

                fetch_url = (
                    f"{self.base_url}/efetch.fcgi"
                    f"?db=pubmed&id={id_string}&retmode=xml"
                )

                try:
                    r = await client.get(fetch_url, timeout=self.timeout)
                    if r.status_code != 200:
                        continue

                    root = ET.fromstring(r.text)

                    for article in root.findall(".//PubmedArticle"):
                        pmid_elem = article.find(".//PMID")
                        if pmid_elem is None:
                            continue

                        pid = pmid_elem.text
                        base = papers_map.get(pid)

                        if not base:
                            continue

                        abstract_parts = [
                            elem.text or ""
                            for elem in article.findall(".//AbstractText")
                        ]
                        abstract = " ".join(abstract_parts)

                        # if not self.is_relevant(base["title"], abstract, drug_name):
                        #     continue

                        base["abstract"] = self.clean_text(abstract)
                        base["focus"] = self.extract_focus(abstract)

                        final_papers.append(base)

                except Exception:
                    logger.warning("Efetch batch error")

        # ranking
        final_papers = self.rank_papers(final_papers)

        return {
            "drug_name": drug_name,
            "results": {
                "total_papers": total_count,
                "returned_papers": len(final_papers),
                "summary": self.build_summary(final_papers),
                "top_insights": [p["title"] for p in final_papers[:3]],
                "research_papers": final_papers,
            },
        }

    # -------------------------
    # Health Check
    # -------------------------

    async def check_health(self) -> bool:
        try:
            url = (
                f"{self.base_url}/esearch.fcgi"
                f"?db=pubmed&term=aspirin&retmode=json&retmax=1"
            )
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=5.0)
                return resp.status_code == 200
        except Exception:
            return False