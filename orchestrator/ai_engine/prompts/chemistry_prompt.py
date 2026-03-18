SYSTEM_PROMPT = """
You are a medicinal chemistry expert.

Analyze the chemical and molecular properties of a drug
and provide scientific interpretation useful for researchers.

IMPORTANT:
- Return ONLY valid JSON
- Do NOT include explanations outside JSON
- Do NOT include markdown or code blocks
"""


USER_PROMPT_TEMPLATE = """
Drug: {drug_name}

Chemical Properties:
{chemical_properties}

ChEMBL Structure:
{chembl_structure}

Molecular Properties:
{chembl_properties}

Drug Likeness Analysis:
{drug_likeness}

Return STRICT JSON with this schema:

{{
  "physicochemical_profile": "Explain the meaning of molecular weight, logP, polar surface area, and hydrogen bonding properties.",
  "drug_likeness_interpretation": "Explain Lipinski rule implications and oral bioavailability.",
  "structural_features": "Explain important functional groups and scaffold features.",
  "medicinal_chemistry_insight": "Explain how structure influences pharmacological behavior."
}}
"""