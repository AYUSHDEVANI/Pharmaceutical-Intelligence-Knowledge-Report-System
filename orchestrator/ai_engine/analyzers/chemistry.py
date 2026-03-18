import json
import logging

from orchestrator.models import DrugProfile
from ..providers.base_provider import LLMProvider
from ..prompts.chemistry_prompt import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from ..utils.chemistry_utils import analyze_drug_likeness


async def analyze_chemistry(profile: DrugProfile, provider: LLMProvider):

    chembl = profile.chembl

    chembl_structure = chembl.structure if chembl else {}
    chembl_properties = chembl.molecular_properties if chembl else {}

    drug_likeness = analyze_drug_likeness(chembl_properties)

    user_prompt = USER_PROMPT_TEMPLATE.format(
        drug_name=profile.drug_name,
        chemical_properties=profile.chemical_properties.model_dump_json(),
        chembl_structure=json.dumps(chembl_structure, indent=2),
        chembl_properties=json.dumps(chembl_properties, indent=2),
        drug_likeness=json.dumps(drug_likeness, indent=2)
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