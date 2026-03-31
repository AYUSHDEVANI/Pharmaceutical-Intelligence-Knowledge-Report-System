import httpx
import logging
from typing import Dict, Any, List
import urllib.parse
import re

logger = logging.getLogger("mcp_server.uniprot.client")


# 🔥 Drug synonym intelligence
DRUG_SYNONYMS = {
    "aspirin": [
        "aspirin",
        "acetylsalicylic acid",
        "nsaid",
        "nonsteroidal anti-inflammatory",
        "non-steroidal anti-inflammatory"
    ]
}


class UniProtAPIClient:

    def __init__(self, base_url: str, timeout: float = 15.0):
        self.base_url = base_url
        self.timeout = timeout

    async def _fetch(self, url: str) -> Dict[str, Any]:
        for attempt in range(3):
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, timeout=self.timeout)
                    resp.raise_for_status()
                    return resp.json()
            except Exception as e:
                logger.warning(f"Attempt {attempt+1} failed: {e}")
                if attempt == 2:
                    raise

    # ---------------------------------------------------------
    # 🧠 HELPERS
    # ---------------------------------------------------------
    def _extract_evidence(self, evidences: List[Dict]) -> Dict[str, Any]:
        eco, pubmed = [], []

        for e in evidences or []:
            if e.get("evidenceCode"):
                eco.append(e["evidenceCode"])
            if e.get("source") == "PubMed":
                pubmed.append(e.get("id"))

        return {
            "eco_codes": list(set(eco)),
            "pubmed_ids": list(set(pubmed))
        }

    def _split_function(self, texts):
        sentences = []
        for t in texts:
            parts = re.split(r'(?<=[.!?])\s+', t)
            sentences.extend([p.strip() for p in parts if len(p.strip()) > 20])
        return sentences

    def _detect_drug_interaction(self, text: str, drug: str):
        text_l = text.lower()

        synonyms = DRUG_SYNONYMS.get(drug.lower(), [drug.lower()])

        if not any(s in text_l for s in synonyms):
            return None

        if "inhibit" in text_l:
            return "inhibitor"
        if "activate" in text_l:
            return "activator"
        if "substrate" in text_l:
            return "substrate"

        return "associated"

    def _classify_target(self, name: str, catalytic: List):
        if catalytic:
            return "enzyme"

        if name:
            n = name.lower()
            if "receptor" in n:
                return "receptor"
            if "transcription factor" in n:
                return "transcription_factor"

        return "other"

    # ---------------------------------------------------------
    # 🔥 MAIN PARSER
    # ---------------------------------------------------------
    def _extract_protein(self, entry: Dict[str, Any], drug_name: str):

        accession = entry.get("primaryAccession")

        protein_desc = entry.get("proteinDescription", {})
        protein_name = protein_desc.get("recommendedName", {}) \
            .get("fullName", {}).get("value")

        alt_names = [
            n.get("fullName", {}).get("value")
            for n in protein_desc.get("alternativeNames", [])
            if n.get("fullName")
        ]

        genes = [
            g.get("geneName", {}).get("value")
            for g in entry.get("genes", [])
            if g.get("geneName")
        ]

        organism = entry.get("organism", {}).get("scientificName")

        secondary_accessions = entry.get("secondaryAccessions", [])

        comments = entry.get("comments", []) or []

        function_data = []
        pathways = []
        diseases = []

        catalytic = []
        cofactors = []
        interactions = []
        subcell = []
        tissue = []
        induction = []
        ptms = []
        regulation = []
        drug_interactions = []

        for c in comments:
            ctype = c.get("commentType")
            texts = c.get("texts", [])

            raw_texts = [t.get("value") for t in texts if t.get("value")]

            evidence = self._extract_evidence(
                [ev for t in texts for ev in t.get("evidences", [])]
            )

            # ---------------- FUNCTION ----------------
            if ctype == "FUNCTION":
                for t in self._split_function(raw_texts):
                    function_data.append({
                        "text": t,
                        "evidence": evidence
                    })

                    interaction = self._detect_drug_interaction(t, drug_name)
                    if interaction:
                        drug_interactions.append({
                            "type": interaction,
                            "evidence": evidence
                        })

            elif ctype == "PATHWAY":
                pathways.extend(raw_texts)

            elif ctype == "DISEASE":
                diseases.extend(raw_texts)

            elif ctype == "CATALYTIC ACTIVITY":
                r = c.get("reaction", {})
                catalytic.append({
                    "reaction": r.get("name"),
                    "ec_number": r.get("ecNumber"),
                    "rhea_id": next(
                        (x.get("id") for x in r.get("reactionCrossReferences", [])
                         if x.get("database") == "Rhea"), None
                    ),
                    "chebi_ids": [
                        x.get("id") for x in r.get("reactionCrossReferences", [])
                        if x.get("database") == "ChEBI"
                    ],
                    "evidence": self._extract_evidence(r.get("evidences", []))
                })

            elif ctype == "COFACTOR":
                cofactors.extend([cf.get("name") for cf in c.get("cofactors", [])])

            elif ctype == "INTERACTION":
                for i in c.get("interactions", []):
                    interactions.append({
                        "uniprot_id": i.get("interactantTwo", {}).get("uniProtKBAccession"),
                        "gene": i.get("interactantTwo", {}).get("geneName"),
                        "intact_id": i.get("interactantTwo", {}).get("intActId"),
                        "experiments": i.get("numberOfExperiments")
                    })

            elif ctype == "SUBCELLULAR LOCATION":
                subcell.extend([
                    l.get("location", {}).get("value")
                    for l in c.get("subcellularLocations", [])
                ])

            elif ctype == "TISSUE SPECIFICITY":
                tissue.extend(raw_texts)

            elif ctype == "INDUCTION":
                induction.extend(raw_texts)

            elif ctype == "PTM":
                ptms.extend(raw_texts)

            elif ctype == "ACTIVITY REGULATION":
                regulation.extend(raw_texts)

                # 🔥 Detect drug interaction from regulation too
                for t in raw_texts:
                    interaction = self._detect_drug_interaction(t, drug_name)
                    if interaction:
                        drug_interactions.append({
                            "type": interaction,
                            "evidence": evidence
                        })

        # ---------------- FEATURES ----------------
        domains, motifs, binding_sites = [], [], []

        for f in entry.get("features", []):
            if f.get("type") == "Domain":
                domains.append(f.get("description"))

            elif f.get("type") == "Motif":
                motifs.append(f.get("description"))

            elif f.get("type") == "Binding site":
                ligand = f.get("ligand", {}).get("name")
                role = "cofactor_binding" if ligand and "heme" in ligand.lower() else "active_site"

                binding_sites.append({
                    "ligand": ligand,
                    "position": f.get("location", {}).get("start", {}).get("value"),
                    "role": role
                })

        # ---------------- CROSS REFS ----------------
        kegg_ids, pdb_ids = [], []

        for ref in entry.get("uniProtKBCrossReferences", []):
            if ref.get("database") == "KEGG":
                kegg_ids.append(ref.get("id"))
            elif ref.get("database") == "PDB":
                pdb_ids.append(ref.get("id"))

        # ---------------- CLEAN REACTIONS ----------------
        seen = set()
        catalytic = [r for r in catalytic if not (r["reaction"] in seen or seen.add(r["reaction"]))][:5]

        # ---------------- CLASSIFICATION ----------------
        target_type = self._classify_target(protein_name, catalytic)

        # ---------------- CONFIDENCE ----------------
        pubmed_count = sum(len(f["evidence"]["pubmed_ids"]) for f in function_data)

        if drug_interactions:
            relevance = "high"
        elif catalytic:
            relevance = "medium"
        else:
            relevance = "low"

        confidence = {
            "target_relevance": relevance,
            "evidence_strength": pubmed_count
        }

        # ---------------- FINAL ----------------
        return {
            "entity_type": "protein",

            "source": {
                "name": "uniprot",
                "url": f"https://www.uniprot.org/uniprotkb/{accession}"
            },

            "identifiers": {
                "uniprot_id": accession,
                "secondary_accessions": secondary_accessions,
                "gene_symbols": genes,
                "alternative_names": alt_names
            },

            "classification": {
                "target_type": target_type
            },

            "confidence": confidence,

            "biological": {
                "protein_name": protein_name,
                "organism": organism,
                "function": function_data,
                "pathways": {
                    "text": pathways,
                    "kegg_ids": kegg_ids
                },
                "disease_associations": diseases,
                "subcellular_location": subcell,
                "tissue_specificity": tissue
            },

            "mechanistic": {
                "catalytic_activity": catalytic,
                "cofactors": list(set(cofactors)),
                "binding_sites": binding_sites,
                "regulation": regulation,
                "induction": induction
            },

            "drug_interaction": drug_interactions,

            "interaction": {
                "protein_interactions": interactions
            },

            "structure": {
                "domains": domains,
                "motifs": motifs
            },

            "clinical": {
                "ptms": ptms
            },

            "cross_references": {
                "pdb": pdb_ids
            },

            "metadata": {
                "annotation_score": entry.get("annotationScore"),
                "protein_existence": entry.get("proteinExistence")
            }
        }

    # ---------------------------------------------------------
    async def search_proteins(self, drug_name: str, limit: int = 20):

        query = f"{drug_name} AND organism_id:9606 AND reviewed:true"
        url = f"{self.base_url}/uniprotkb/search?query={urllib.parse.quote(query)}&format=json&size={limit}"

        raw = await self._fetch(url)

        proteins = [
            self._extract_protein(e, drug_name)
            for e in raw.get("results", [])
        ]

        return {
            "drug_name": drug_name,
            "results": {
                "total_proteins": len(proteins),
                "proteins": proteins
            }
        }

    async def check_health(self):
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{self.base_url}/uniprotkb/search?query=aspirin&size=1")
                return r.status_code == 200
        except:
            return False