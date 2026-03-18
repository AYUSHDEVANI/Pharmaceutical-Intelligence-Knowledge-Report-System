import json
import logging

from orchestrator.models import DrugProfile
from ..providers.base_provider import LLMProvider
from ..prompts.pharmacology_prompt import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


async def analyze_pharmacology(profile: DrugProfile, provider: LLMProvider):

    chembl = profile.chembl

    targets = chembl.targets if chembl else []
    atc_codes = chembl.classification.get("atc_codes") if chembl else []

    user_prompt = USER_PROMPT_TEMPLATE.format(
        drug_name=profile.drug_name,
        targets=json.dumps(targets, indent=2),
        atc_codes=json.dumps(atc_codes, indent=2)
    )

    logger = logging.getLogger("pikrs.pipeline")

    response = await provider.generate(SYSTEM_PROMPT, user_prompt)

    if not response or not response.strip():
        raise ValueError("LLM returned empty response")

    response = response.strip()

    # remove markdown code blocks
    if response.startswith("```"):
        response = response.split("```")[1]

    # remove leading "json"
    if response.lower().startswith("json"):
        response = response[4:]

    response = response.strip()

    return json.loads(response)