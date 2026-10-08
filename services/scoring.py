def _text(lead):
    return " ".join([
        lead.get("title",""), lead.get("description",""),
        lead.get("summary",""), " ".join(lead.get("scope", [])),
        lead.get("opportunity_type",""), lead.get("main_contractor","")
    ]).lower()

def score_opportunity(lead, cfg):
    t = _text(lead)
    p = cfg["profile"]
    weights = cfg["rubric"]

    core = p["capabilities"]["core"]
    adjacent = p["capabilities"]["adjacent"]
    sectors = p["preferred_project_signals"]
    indirect = p["strong_indirect_signals"]
    markets = [x.lower() for x in p["geography"]["known_markets"]]

    core_hits = sum(1 for x in core if x.lower() in t)
    adj_hits = sum(1 for x in adjacent if x.lower() in t)
    sector_hits = sum(1 for x in sectors if x.lower() in t)
    indirect_hits = sum(1 for x in indirect if x.lower() in t)
    geo_hits = sum(1 for x in markets if x in t)

    capability_pct = min(100, core_hits * 22 + adj_hits * 8)
    sector_pct = min(100, sector_hits * 25)
    subcontract_pct = min(100, indirect_hits * 30 + (30 if lead.get("lead_type") == "INDIRECT" else 0))
    geography_pct = min(100, geo_hits * 35 + (25 if "saudi" in t or "ksa" in t else 0))

    # No false precision about project value. Size/complexity is a proxy until Zoom supplies thresholds.
    size_pct = 60 if any(x in t for x in ["multi-year", "major project", "large-scale", "package", "metro", "airport"]) else 40
    client_pct = 70 if lead.get("main_contractor") else 45

    weighted = (
        capability_pct * weights["capability_match"] +
        sector_pct * weights["project_sector_fit"] +
        subcontract_pct * weights["subcontract_jv_potential"] +
        geography_pct * weights["geography_fit"] +
        size_pct * weights["project_size_complexity"] +
        client_pct * weights["client_contractor_relevance"]
    ) / 10000

    score = round(max(1.0, min(5.0, 1 + weighted * 4)), 1)

    lead["score"] = score
    lead["score_breakdown"] = {
        "capability_match": round(capability_pct / 20, 1),
        "project_sector_fit": round(sector_pct / 20, 1),
        "subcontract_jv_potential": round(subcontract_pct / 20, 1),
        "geography_fit": round(geography_pct / 20, 1),
        "project_size_complexity": round(size_pct / 20, 1),
        "client_contractor_relevance": round(client_pct / 20, 1),
    }
    lead["value_display"] = f"{lead.get('value','Unknown')} ({lead.get('value_type','UNKNOWN')})"
    return lead
