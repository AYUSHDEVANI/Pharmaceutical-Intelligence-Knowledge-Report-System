"""
PIKRS AI Engine — Service Wrapper
===================================
Executes the AI synthesis stage using an already generated DrugProfile.
"""

import logging

from orchestrator.models import DrugProfile
from orchestrator.ai_engine.models import DrugIntelligenceReport
from orchestrator.ai_engine.generator import generate_report

logger = logging.getLogger("pikrs.pipeline")


async def generate_drug_intelligence(
    profile: DrugProfile
) -> DrugIntelligenceReport | DrugProfile:
    """
    AI synthesis stage.

    Input:
        DrugProfile (already aggregated by orchestrator)

    Output:
        DrugIntelligenceReport if AI succeeds
        DrugProfile fallback if AI fails
    """

    logger.info(f"AI synthesis started for: {profile.drug_name}")

    if not profile.sources:
        logger.warning(
            f"No sources returned any data for '{profile.drug_name}'. Returning raw profile."
        )
        return profile

    try:
        logger.info("Structured data aggregated. Commencing AI synthesis.")
        report: DrugIntelligenceReport = await generate_report(profile)

        logger.info(
            f"Successfully generated Drug Intelligence Report for '{profile.drug_name}'"
        )

        return report

    except Exception as e:
        logger.error(
            f"AI synthesis failed: {str(e)}. Falling back to structured DrugProfile."
        )

        profile.regulatory_information.warnings = (
            profile.regulatory_information.warnings or ""
        ) + "\n[AI_ENGINE_ERROR] Inference failed."

        return profile