from datetime import datetime

import httpx
import logging
from typing import Any, Dict, List
from collections import Counter

logger = logging.getLogger("mcp_servers.faers.client")

# Mappings
OUTCOME_MAP = {
    "1": "Recovered",
    "2": "Recovering",
    "3": "Not Recovered",
    "4": "Recovered with Sequelae",
    "5": "Fatal",
    "6": "Unknown"
}


QUALIFICATION_MAP = {
    "1": "Physician",
    "2": "Pharmacist",
    "3": "Other Healthcare Professional",
    "4": "Consumer"
}

GENDER_MAP = {
    "1": "Male",
    "2": "Female"
}

AGE_UNIT_MAP = {
    "801": "Years",
    "802": "Months",
    "803": "Weeks",
    "804": "Days"
}

# Helpers
def parse_bool(val):
    return val == "1"


def safe_first(lst, limit=3):
    if not lst:
        return None
    return lst[:limit]


def clean_value(val):
    if val is None:
        return None
    if isinstance(val, str) and val.strip().upper() in ["UNK", "UNKNOWN", ""]:
        return None
    return val


def normalize_name(name: str):
    return name.strip().replace(".", "").upper() if name else name


def get_severity(event):
    if event["serious"]["death"]:
        return "fatal"
    if event["serious"]["is_serious"]:
        return "serious"
    return "non-serious"

class FAERSAPIClient:
    def __init__(self, base_url: str, timeout: float = 15.0):
        self.base_url = base_url
        self.timeout = timeout

    

    async def faers_search(self, drug_name: str) -> Dict[str, Any]:
        url = f"{self.base_url}?search=patient.drug.medicinalproduct:{drug_name}&limit=100"



        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout = self.timeout)
            resp.raise_for_status()
            raw = resp.json()

        results = raw.get("results", [])


        if not results:
            raise ValueError(f"No adverse events found for '{drug_name}'")
        
        events: List[Dict[str, Any]] = []

        for r in results:
            patient = r.get("patient", {})
            reactions = patient.get("reaction", [])

            relevant_drug = None
            drugs = patient.get("drug", [])
            
            for d in drugs:
                name = (d.get("medicinalproduct") or "").lower()
                role = d.get("drugcharacterization")

                if (drug_name.lower() == name or drug_name.lower() in name) and role == "1":
                    relevant_drug = d
                    break

            if not relevant_drug:
                continue

            meta = relevant_drug.get("openfda", {})

            # Combination drug detection
            drug_name_raw = relevant_drug.get("medicinalproduct", "")
            drug_name_clean = normalize_name(drug_name_raw)

            co_ingredients = []
            if "acetaminophen" in drug_name_raw.lower():
                co_ingredients.append("acetaminophen")
            if "caffeine" in drug_name_raw.lower():
                co_ingredients.append("caffeine")

            event = {
                "source": {
                    "name": "openfda-faers",
                    "url": "https://open.fda.gov/apis/drug/event/"
                },

                # Report Metadata
                "report": {
                    "id": r.get("safetyreportid"),
                    "type": r.get("reporttype"),
                    "is_duplicate": r.get("duplicate") == "1",
                    "company_id": r.get("companynumb"),
                },

                # Dates
                "dates": {
                    "received": r.get("receivedate"),
                    "receipt": r.get("receiptdate"),
                    "transmission": r.get("transmissiondate"),
                },

                # Country
                "country": {
                    "occurred": r.get("occurcountry"),
                    "reported": r.get("primarysourcecountry"),
                },

                # Reporter
                "reporter": {
                    "country": r.get("primarysource", {}).get("reportercountry"),
                    "qualification": QUALIFICATION_MAP.get(
                        r.get("primarysource", {}).get("qualification"),
                        "Unknown"
                    ),
                },

                # Patient
                "patient": {
                    "age": patient.get("patientonsetage"),
                    "age_unit": AGE_UNIT_MAP.get(
                        patient.get("patientonsetageunit")
                    ),
                    "gender": GENDER_MAP.get(
                        patient.get("patientsex"), "Unknown"
                    ),
                },


                # Drug Info
                "drug": {
                    "name": relevant_drug.get("medicinalproduct"),
                    "role": relevant_drug.get("drugcharacterization"),
                    "dosage_text": relevant_drug.get("drugdosagetext"),
                    "dosage_form": relevant_drug.get("drugdosageform"),
                    "action_taken": relevant_drug.get("actiondrug"),

                    "is_combination_drug": len(co_ingredients) > 0,
                    "co_ingredients": co_ingredients or None,

                    # OpenFDA enrichment
                    "brand_name": safe_first(meta.get("brand_name")),
                    "manufacturer": safe_first(meta.get("manufacturer_name")),
                    "generic_name": safe_first(meta.get("generic_name"), 2),
                    "route": safe_first(meta.get("route")),
                                    },

                # Reactions (Side Effects)
                "reactions": [
                    {
                        "reaction": rx.get("reactionmeddrapt"),
                        "outcome_code": rx.get("reactionoutcome"),
                        "outcome": OUTCOME_MAP.get(rx.get("reactionoutcome"), "Unknown"),
                    }
                    for rx in reactions
                ],

                # Serious Outcomes
                "serious": {
                    "is_serious": parse_bool(r.get("serious")),
                    "death": parse_bool(r.get("seriousnessdeath")),
                    "hospitalization": parse_bool(r.get("seriousnesshospitalization")),
                    "life_threatening": parse_bool(r.get("seriousnesslifethreatening")),
                    "disability": parse_bool   (r.get("seriousnessdisabling")),
                },


            }

            event["severity"] = get_severity(event)

            events.append(event)
        
        if not events:
            raise ValueError(f"No relevant adverse events found for '{drug_name}'")
        
        # Aggregation
        reaction_counter = Counter()
        serious_count = 0
        death_count = 0
        for event in events:
            for rx in event["reactions"]:
                if rx["reaction"]:
                    reaction_counter[rx["reaction"]] += 1

            if event["serious"]["is_serious"]:
                serious_count += 1

            if event["serious"]["death"]:
                death_count += 1


        # Demographics
        gender_count = {"male": 0, "female": 0, "unknown": 0}

        for e in events:
            g = e["patient"]["gender"]
            if g == "Male":
                gender_count["male"] += 1
            elif g == "Female":
                gender_count["female"] += 1
            else:
                gender_count["unknown"] += 1

        # Time Analysis
        dates = [
            datetime.strptime(e["dates"]["receipt"], "%Y%m%d")
            for e in events if e["dates"]["receipt"]
        ]

        latest = max(dates) if dates else None
        earliest = min(dates) if dates else None

        time_analysis = {
            "latest_event": latest.strftime("%Y-%m-%d") if latest else None,
            "event_span_years": round((latest - earliest).days / 365, 1)
            if latest and earliest else None,
        }

        # Summary
        summary = {
            "top_reactions": [
                {
                    "reaction": r,
                    "count": c,
                    "percentage": round((c / len(events)) * 100, 2),
                    "signal": {
                        "frequency": round(c / len(events), 2),
                        "confidence": "low" if len(events) < 20 else "medium"
                    }
                }
                for r, c in reaction_counter.most_common(10)
            ],
            "serious_cases": serious_count,
            "death_cases": death_count,
        }

        return {
            "drug_name": drug_name,
            "results": {
                "total_events": len(events),
                "summary": summary,
                "demographics": gender_count,
                "time_analysis": time_analysis,
                "adverse_events": events,
            },
        }
            

    async def check_health(self) -> bool:
        try:
            test_url = f"{self.base_url}?search=aspirin&limit=1"
            async with httpx.AsyncClient() as client:
                resp = await client.get(test_url, timeout = 5.0)
                return resp.status_code == 200  
        
        except Exception:
            return False
        