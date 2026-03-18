from pydantic import BaseModel, Field
from typing import List, Dict, Any


class DrugTarget(BaseModel):
    target_name: str | None = None
    target_chembl_id: str | None = None
    organism: str | None = None
    mechanism: str | None = None


class PhysicochemicalProfile(BaseModel):
    lipophilicity: str | None = None
    absorption_implications: str | None = None
    distribution_characteristics: str | None = None
    metabolism_implications: str | None = None


class MedicinalChemistryInsight(BaseModel):
    scaffold: str | None = None
    functional_groups: List[str] = Field(default_factory=list)
    design_significance: str | None = None


class Pharmacokinetics(BaseModel):
    absorption: str | None = None
    distribution: str | None = None
    metabolism: str | None = None
    excretion: str | None = None


class SafetyProfile(BaseModel):
    major_risks: List[str] = Field(default_factory=list)
    risk_populations: List[str] = Field(default_factory=list)


class ClinicalEvidenceSummary(BaseModel):
    trial_count: int | None = None
    common_indications: List[str] = Field(default_factory=list)


class DrugIntelligenceReport(BaseModel):

    drug_name: str

    overview: str | None = None

    chemical_summary: str | None = None

    physicochemical_profile: PhysicochemicalProfile | None = None

    medicinal_chemistry_insight: MedicinalChemistryInsight | None = None

    mechanism_of_action: str | None = None

    drug_targets: List[DrugTarget] = Field(default_factory=list)

    pharmacokinetics: Pharmacokinetics | None = None

    therapeutic_indications: str | None = None

    safety_profile: SafetyProfile | None = None

    clinical_evidence_summary: ClinicalEvidenceSummary | None = None

    brand_names: List[str] = Field(default_factory=list)

    sources: List[str] = Field(default_factory=list)

    clinical_trials: List[Dict[str, Any]] = Field(default_factory=list)

    research_papers: List[Dict[str, Any]] = Field(default_factory=list)