import json
import logging

from orchestrator.models import DrugProfile
from ..providers.base_provider import LLMProvider
from ..prompts.safety_prompt import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


async def analyze_safety(profile: DrugProfile, provider: LLMProvider):

    regulatory = profile.regulatory_information

    user_prompt = USER_PROMPT_TEMPLATE.format(
        drug_name=profile.drug_name,
        warnings=regulatory.warnings,
        contraindications=regulatory.contraindications
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