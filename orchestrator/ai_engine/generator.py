import asyncio

from orchestrator.models import DrugProfile
from .providers.groq_provider import GroqProvider

from .analyzers.chemistry import analyze_chemistry
from .analyzers.pharmacology import analyze_pharmacology
from .analyzers.safety import analyze_safety

from .merger.report_merger import merge_results


async def generate_report(profile: DrugProfile):

    provider = GroqProvider()

    tasks = [
        analyze_chemistry(profile, provider),
        analyze_pharmacology(profile, provider),
        analyze_safety(profile, provider)
    ]

    chemistry, pharmacology, safety = await asyncio.gather(*tasks)

    report = merge_results(profile, chemistry, pharmacology, safety)

    return report