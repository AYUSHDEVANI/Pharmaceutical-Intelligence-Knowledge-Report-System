from __future__ import annotations

from typing import Any, Dict, List
from .models import ChemblData, DrugProfile


# ---------------------------------------------------------
# 🧠 EVIDENCE SCORING
# ---------------------------------------------------------
def _compute_evidence_score(relevance: str, interaction: list, source_count: int) -> float:
    score = 0.0

    if relevance == "high":
        score += 0.5
    elif relevance == "medium":
        score += 0.3

    interaction_types = [i.get("type") for i in interaction if isinstance(i, dict)]

    if "inhibitor" in interaction_types or "agonist" in interaction_types:
        score += 0.3
    elif interaction:
        score += 0.1

    if source_count >= 8:
        score += 0.2
    elif source_count >= 5:
        score += 0.1

    return round(min(score, 1.0), 3)


# ---------------------------------------------------------
# 🧬 TARGET CLASSIFICATION
# ---------------------------------------------------------
def _classify_target(gene: str, interaction: list) -> str:
    interaction_types = [i.get("type") for i in interaction if isinstance(i, dict)]

    if "inhibitor" in interaction_types or "agonist" in interaction_types:
        return "primary_targets"

    if gene.startswith(("CYP", "UGT", "CES")):
        return "metabolic_enzymes"

    if gene.startswith(("SLC", "ABC")):
        return "transporters"

    if interaction:
        return "secondary_targets"

    return "other_proteins"


# ---------------------------------------------------------
# 🧬 TARGET EXTRACTION
# ---------------------------------------------------------
def _extract_targets(profile: DrugProfile) -> Dict[str, List[Dict[str, Any]]]:

    categorized = {
        "primary_targets": [],
        "secondary_targets": [],
        "metabolic_enzymes": [],
        "transporters": [],
        "other_proteins": []
    }

    if not profile.uniprot:
        return categorized

    source_count = len(profile.sources)

    for p in profile.uniprot.get("results", {}).get("proteins", []):
        relevance = p.get("confidence", {}).get("target_relevance")

        if relevance not in ["high", "medium"]:
            continue

        genes = p.get("identifiers", {}).get("gene_symbols", [])
        interaction = p.get("drug_interaction", [])

        for g in genes:
            category = _classify_target(g, interaction)

            score = _compute_evidence_score(relevance, interaction, source_count)

            categorized[category].append({
                "gene": g,
                "confidence": relevance,
                "evidence_score": score,
                "interaction": interaction
            })

    # Deduplicate
    for key in categorized:
        seen = set()
        unique = []

        for t in categorized[key]:
            if t["gene"] not in seen:
                seen.add(t["gene"])
                unique.append(t)

        categorized[key] = unique

    return categorized


# ---------------------------------------------------------
# 🧪 CHemBL BIOACTIVITY
# ---------------------------------------------------------
def _extract_bioactivity(profile: DrugProfile) -> Dict[str, Any]:

    raw_activities = getattr(profile.chembl, "activities", []) if profile.chembl else []

    activities = []

    for a in raw_activities:
        try:
            value = float(a.get("value"))
        except:
            continue

        activities.append({
            "target": a.get("target_gene"),
            "type": a.get("type"),
            "value": value,
            "unit": a.get("unit")
        })

    activities = sorted(activities, key=lambda x: x["value"])

    top = activities[:5]

    return {
        "top_activities": top,
        "activity_count": len(activities),
        "summary": f"Top activity: {top[0]['target']}" if top else "No activity data"
    }


# ---------------------------------------------------------
# 📚 PUBMED
# ---------------------------------------------------------
def _extract_pubmed(profile: DrugProfile) -> Dict[str, Any]:

    papers = profile.research_papers or []

    ranked = sorted(
        papers,
        key=lambda x: len(x.get("abstract", "") or ""),
        reverse=True
    )

    top = ranked[:5]

    titles = [p.get("title", "") for p in top if p.get("title")]

    return {
        "top_papers": top,
        "paper_count": len(papers),
        "summary": " | ".join(titles[:3]) if titles else "No research data"
    }


# ---------------------------------------------------------
# ⚠️ FAERS
# ---------------------------------------------------------
def _extract_faers(profile: DrugProfile) -> List[Dict[str, Any]]:
    reactions = []

    if profile.faers:
        for r in profile.faers.get("results", {}).get("summary", {}).get("top_reactions", []):
            reactions.append({
                "name": r.get("reaction"),
                "frequency": r.get("count")
            })

    return reactions


# ---------------------------------------------------------
# 🏥 REGULATORY PARSING
# ---------------------------------------------------------
def _extract_regulatory(profile: DrugProfile) -> Dict[str, Any]:

    reg = profile.regulatory_information

    return {
        "indications": reg.indications,
        "dosage": reg.dosage,
        "warnings": reg.warnings,
        "contraindications": reg.contraindications,
        "adverse_reactions": reg.adverse_reactions,
        "drug_interactions": reg.drug_interactions
    }


# ---------------------------------------------------------
# 🧪 CLINICAL TRIALS PARSING
# ---------------------------------------------------------
def _extract_clinical(profile: DrugProfile) -> Dict[str, Any]:

    trials = profile.clinical_trials or []

    # Normalize
    normalized = []

    for t in trials:
        normalized.append({
            "title": t.get("title") or t.get("brief_title"),
            "phase": t.get("phase"),
            "status": t.get("status"),
            "condition": t.get("condition")
        })

    top = normalized[:5]

    summary = (
        f"{len(trials)} trials found. Top study: {top[0]['title']}"
        if top else "No clinical trials available"
    )

    return {
        "trial_count": len(trials),
        "top_trials": top,
        "summary": summary
    }


# ---------------------------------------------------------
# 🧠 INTELLIGENCE BUILDER
# ---------------------------------------------------------
def _build_intelligence(profile, targets, reactions, evidence, bioactivity, clinical, regulatory):

    return {
        "targets": targets,
        "bioactivity": bioactivity,
        "evidence": evidence,
        "adverse_events": reactions,
        "clinical": clinical,
        "regulatory": regulatory,
        "sources": profile.sources
    }


# ---------------------------------------------------------
# 🚀 MAIN AGGREGATOR
# ---------------------------------------------------------
def aggregate_mcp_responses(drug_name: str, mcp_results: dict[str, Any]) -> DrugProfile:

    profile = DrugProfile(drug_name=drug_name)

    for source_id, envelope in mcp_results.items():
        profile.sources.append(source_id)

        data = envelope.get("data") or envelope
        identifiers = data.get("identifiers", {})
        raw_results = data.get("results", {})

        if isinstance(raw_results, list):
            results = raw_results[0] if raw_results else {}
        elif isinstance(raw_results, dict):
            results = raw_results
        else:
            results = {}

        if source_id == "chembl":
            profile.chembl = ChemblData(
                chembl_id=identifiers.get("chembl_id"),
                classification=results.get("classification"),
                structure=results.get("structure"),
                molecular_properties=results.get("molecular_properties"),
                targets=results.get("targets", []),
                synonyms=results.get("synonyms", [])
            )
            if profile.chembl:
                activities = results.get("activities", [])

                if isinstance(activities, list):
                    profile.chembl.activities = activities

        elif source_id == "pubmed":
            papers = results.get("research_papers") or results.get("articles")
            if isinstance(papers, list):
                profile.research_papers.extend(papers)

        elif source_id == "clinicaltrials":
            trials = results.get("clinical_trials") or results.get("studies")
            if isinstance(trials, list):
                profile.clinical_trials.extend(trials)

        elif source_id == "openfda":
            profile.regulatory_information.indications = (
                results.get("indications")
                or results.get("indications_and_usage")
            )
            profile.regulatory_information.dosage = results.get("dosage")
            profile.regulatory_information.warnings = results.get("warnings")
            profile.regulatory_information.contraindications = results.get("contraindications")
            profile.regulatory_information.adverse_reactions = results.get("adverse_reactions")
            profile.regulatory_information.drug_interactions = results.get("drug_interactions")

        elif source_id == "uniprot":
            profile.uniprot = data

        elif source_id == "faers":
            profile.faers = data

    targets = _extract_targets(profile)
    reactions = _extract_faers(profile)
    evidence = _extract_pubmed(profile)
    bioactivity = _extract_bioactivity(profile)
    clinical = _extract_clinical(profile)
    regulatory = _extract_regulatory(profile)

    profile.intelligence = _build_intelligence(
        profile, targets, reactions, evidence, bioactivity, clinical, regulatory
    )

    return profile