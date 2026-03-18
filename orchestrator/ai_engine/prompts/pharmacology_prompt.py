SYSTEM_PROMPT = """
You are a pharmacology expert.

Interpret drug targets and pharmacological classification
to explain the mechanism of action and therapeutic behavior.

IMPORTANT:
- Return ONLY valid JSON
- No explanations outside JSON
- No markdown formatting
"""


USER_PROMPT_TEMPLATE = """
Drug: {drug_name}

Targets:
{targets}

ATC Codes:
{atc_codes}

Return STRICT JSON:

{{
  "mechanism_of_action": "Explain pharmacological mechanism",
  "target_pharmacology": "Explain the biological targets",
  "therapeutic_class_interpretation": "Explain pharmacological classification"
}}
"""