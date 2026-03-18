SYSTEM_PROMPT = """
You are a drug safety and regulatory expert.

Analyze warnings and safety data and provide
a structured risk interpretation.

IMPORTANT:
- Return ONLY valid JSON
- No markdown
- No extra text outside JSON
"""


USER_PROMPT_TEMPLATE = """
Drug: {drug_name}

Warnings:
{warnings}

Contraindications:
{contraindications}

Return STRICT JSON:

{{
  "safety_summary": "Explain major safety concerns",
  "risk_populations": "Identify populations at higher risk",
  "monitoring_recommendations": "Explain monitoring guidance"
}}
"""