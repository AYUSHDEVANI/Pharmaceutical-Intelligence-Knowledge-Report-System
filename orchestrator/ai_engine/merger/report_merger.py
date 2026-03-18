from orchestrator.models import DrugProfile


def merge_results(profile: DrugProfile, chemistry, pharmacology, safety):

    return {
        "drug_name": profile.drug_name,

        "overview": pharmacology.get("mechanism_of_action"),

        "chemical_intelligence": chemistry,

        "pharmacology": pharmacology,

        "safety_profile": safety,

        "chemical_properties": profile.chemical_properties,

        "chembl": profile.chembl,

        "regulatory_information": profile.regulatory_information,

        "clinical_trials": profile.clinical_trials,

        "research_papers": profile.research_papers,

        "sources": profile.sources
    }