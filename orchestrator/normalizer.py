"""
PIKRS Orchestrator — Normalizer
=================================
Cleans, deduplicates, and standardizes text fields
across the aggregated DrugProfile.
"""

from __future__ import annotations

from .models import DrugProfile

def normalize_text_list(items: list[str]) -> list[str]:
    """
    Lowercase text, strip whitespace, and remove duplicates.
    Preserves the casing of the first occurrence of a word.
    Example: ["Advil", "advil", "ADVIL"] -> ["Advil"]
    """
    seen_lower = set()
    result = []
    
    for item in items:
        if not item or not isinstance(item, str):
            continue
            
        cleaned = item.strip()
        if not cleaned:
            continue
            
        lower_cleaned = cleaned.lower()
        if lower_cleaned not in seen_lower:
            seen_lower.add(lower_cleaned)
            result.append(cleaned)
            
    return result


def normalize_drug_profile(profile: DrugProfile) -> DrugProfile:
    """
    Apply global normalization rules to the assembled profile.
    """
    # Normalize base drug name to lowercase
    if profile.drug_name:
        profile.drug_name = profile.drug_name.strip().lower()
        
    # Deduplicate lists
    profile.brand_names = normalize_text_list(profile.brand_names)
    profile.synonyms = normalize_text_list(profile.synonyms)
    
    # Ensure missing strings are cleanly handled
    if profile.regulatory_information.indications:
        profile.regulatory_information.indications = profile.regulatory_information.indications.strip()
        
    return profile
