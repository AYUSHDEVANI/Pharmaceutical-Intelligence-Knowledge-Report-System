"""
PIKRS Orchestrator — Main API Entrypoint
==========================================
The central FastAPI service that exposes the Orchestrator
and AI Insight Engine to front-end clients.
"""

from fastapi import FastAPI
from pydantic import BaseModel
import logging

from .service import generate_drug_profile
from .ai_engine.service import generate_drug_intelligence
from .models import DrugProfile

# Set up root logger
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="PIKRS Orchestrator API",
    version="1.0.0",
    description="Central orchestration layer for the PIKRS platform."
)


@app.get("/health")
async def health_check():
    """Verify the Orchestrator container is running."""
    return {"status": "healthy"}


class QueryRequest(BaseModel):
    drug_name: str


@app.post("/profile", response_model=DrugProfile)
async def fetch_profile(request: QueryRequest):
    """Retrieve raw structured data from backend MCP servers."""
    return await generate_drug_profile(request.drug_name)


@app.post("/intelligence")
async def fetch_intelligence(request: QueryRequest):
    """
    Generate a synthesized AI Intelligence Report.

    AI receives only selected fields (chemical + pharmacology)
    but the final API response still includes full scientific data
    such as clinical trials and research papers.
    """

    # Step 1: Retrieve full drug profile
    profile = await generate_drug_profile(request.drug_name)

    # Autofill canonical_smiles from ChEMBL if missing
    try:
        if (
            profile.chemical_properties
            and profile.chembl
            and not profile.chemical_properties.get("canonical_smiles")
        ):
            profile.chemical_properties["canonical_smiles"] = \
                profile.chembl.get("structure", {}).get("smiles")
    except Exception:
        pass

    # Step 2: Generate AI report
    report = await generate_drug_intelligence(profile)

    # If AI failed, return profile directly
    if isinstance(report, DrugProfile):
        return report

    # Step 3: Merge AI insights + raw scientific data
    return {
    "drug_name": profile.drug_name,

    # 🧠 AI insights
    "overview": report["overview"],
    "chemical_intelligence": report["chemical_intelligence"],
    "pharmacology": report["pharmacology"],
    "safety_profile": report["safety_profile"],

    # 🔥 NEW: INTELLIGENCE LAYER
    "intelligence": profile.intelligence,

    # 📊 Raw scientific data
    "chemical_properties": profile.chemical_properties,
    "chembl": profile.chembl,
    "regulatory_information": profile.regulatory_information,

    "clinical_trials": profile.clinical_trials,
    "research_papers": profile.research_papers,

    "brand_names": profile.brand_names,
    "synonyms": profile.synonyms,
    "sources": profile.sources,
}