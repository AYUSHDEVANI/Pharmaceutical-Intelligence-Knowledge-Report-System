def analyze_drug_likeness(properties: dict) -> dict:

    try:
        mw = float(properties.get("molecular_weight", 0))
        logp = float(properties.get("logp", 0))
        hbd = int(properties.get("hbond_donors", 0))
        hba = int(properties.get("hbond_acceptors", 0))

        violations = 0

        if mw > 500:
            violations += 1
        if logp > 5:
            violations += 1
        if hbd > 5:
            violations += 1
        if hba > 10:
            violations += 1

        return {
            "lipinski_violations": violations,
            "likely_orally_active": violations <= 1,
            "molecular_weight": mw,
            "logp": logp,
            "hbond_donors": hbd,
            "hbond_acceptors": hba
        }

    except Exception:
        return {}