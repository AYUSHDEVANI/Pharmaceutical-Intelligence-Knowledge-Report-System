"""ClinicalTrials.gov API Client — Ported from ClinicalTrialsConnector."""
import httpx
import logging
from typing import Any, Dict, List

logger = logging.getLogger("mcp_servers.clinicaltrials.client")


class ClinicalTrialsAPIClient:
    def __init__(self, base_url: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def search_trials(self, drug_name: str) -> Dict[str, Any]:
        url = f"{self.base_url}/studies?query.term={drug_name}&pageSize=100&countTotal=true"

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=self.timeout)
            resp.raise_for_status()
            raw = resp.json()

        all_studies = raw.get("studies", [])
        total_count = raw.get("totalCount", len(all_studies))


        if not all_studies:
            raise ValueError(f"No clinical trials found for '{drug_name}'")

        trials: List[Dict[str, Any]] = []
        for s in all_studies:
            protocol = s.get("protocolSection", {})

            identification = protocol.get("identificationModule", {})
            status = protocol.get("statusModule", {})
            design = protocol.get("designModule", {})
            design_info = design.get("designInfo", {})
            conditions = protocol.get("conditionsModule", {})

            description = protocol.get("descriptionModule", {})
            interventions = protocol.get("armsInterventionsModule", {})
            eligibility = protocol.get("eligibilityModule", {})
            locations = protocol.get("contactsLocationsModule", {})

            outcomes = protocol.get("outcomesModule", {})
            sponsor = protocol.get("sponsorCollaboratorsModule", {})
            references = protocol.get("referencesModule", {})

            derived = s.get("derivedSection", {})
            browse = derived.get("interventionBrowseModule", {})


            trial = {
                # Source
                "source": {
                    "name": "clinicaltrials.gov",
                    "url": f"https://clinicaltrials.gov/study/{identification.get('nctId')}"
                },

                # ID Indentification
                "nct_id": identification.get("nctId"),
                "title": identification.get("briefTitle"),
                "official_title": identification.get("officialTitle"),

                # Status
                "status": status.get("overallStatus"),
                "start_date": status.get("startDateStruct", {}).get("date"),
                "completion_date": status.get("completionDateStruct", {}).get("date"),
                "last_updated": status.get("lastUpdatePostDateStruct", {}).get("date"),
                "study_first_posted": status.get("studyFirstPostDateStruct", {}).get("date"),

                # Design
                "study_design": {
                    "phase": (design.get("phases") or [None])[0],
                    "study_type": design.get("studyType"),
                    "enrollment": design.get("enrollmentInfo", {}).get("count"),
                    "allocation": design_info.get("allocation"),
                    "intervention_model": design_info.get("interventionModel"),
                    "primary_purpose": design_info.get("primaryPurpose"),
                    "masking": design_info.get("maskingInfo", {}).get("masking"),
                },

                # Conditions
                "conditions": conditions.get("conditions"),

                # Arm Groups 
                "arm_groups": [
                    {
                        "label": arm.get("label"),
                        "type": arm.get("type"),
                        "description": arm.get("description"),
                    }
                    for arm in interventions.get("armGroups", [])
                ],

                # Interventions
                "interventions": [
                    {
                        "name": i.get("name"),
                        "type": i.get("type"),
                        "description": i.get("description"),
                        "other_names": i.get("otherNames"),
                        "arm_group_labels": i.get("armGroupLabels"),
                    }
                    for i in interventions.get("interventions", [])
                ],

                # Summary
                "summary": description.get("briefSummary"),

                # Outcomes
                "outcomes": {
                    "primary": [
                        {
                        "measure": o.get("measure"),
                        "time_frame": o.get("timeFrame"),
                        }
                        for o in outcomes.get("primaryOutcomes", [])
                    ],
                    "secondary": [
                        {
                        "measure": o.get("measure"),
                        "time_frame": o.get("timeFrame"),
                        }
                        for o in outcomes.get("secondaryOutcomes", [])
                    ],
                },

                # Eligibility
                "eligibility": {
                    "criteria": eligibility.get("eligibilityCriteria"),
                    "min_age": eligibility.get("minimumAge"),
                    "max_age": eligibility.get("maximumAge") or "N/A",
                    "sex": eligibility.get("sex"),
                    "healthy_volunteers": eligibility.get("healthyVolunteers"),
                },

                # Location
                "locations": [
                    {
                        "facility": loc.get("facility"),
                        "city": loc.get("city"),
                        "country": loc.get("country"),
                        "lat": loc.get("geoPoint", {}).get("lat"),
                        "lon": loc.get("geoPoint", {}).get("lon"),
                    }
                    for loc in locations.get("locations", [])
                ],

                # Sponsore
                "sponsor": sponsor.get("leadSponsor", {}).get("name"),

                # Results + Metadata
                "has_results": s.get("hasResults"),

                # References
                "references": [
                    {
                        "pmid": ref.get("pmid"),
                        "citation": ref.get("citation"),
                    }
                    for ref in references.get("references", [])
                ],

                # MeSH Terms
                "mesh_terms": [
                    m.get("term") for m in browse.get("meshes", [])
                ],
            }

            trials.append(trial)


        return {
            "drug_name": drug_name,
            "results": {
                "total_trials": total_count,
                "returned_trials": len(trials),
                "clinical_trials": trials,
            },
        }

    async def check_health(self) -> bool:
        try:
            url = f"{self.base_url}/studies?query.term=aspirin&pageSize=1"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=5.0)
                return resp.status_code == 200
        except Exception:
            return False
