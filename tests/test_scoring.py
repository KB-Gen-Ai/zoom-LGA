from config.loader import load_config
from services.scoring import score_opportunity

def test_hvac_hotel_should_score():
    cfg = load_config()
    lead = {
        "title": "HVAC and MEP subcontract package for hotel",
        "description": "Chillers, chilled water, VRF and firefighting package in Jeddah.",
        "publisher": "Main Contractor",
        "main_contractor": "Example Contractor",
        "location": "Jeddah",
        "opportunity_type": "subcontract",
        "lead_type": "INDIRECT",
        "scope": ["HVAC", "MEP", "chillers", "firefighting"],
        "source_name": "test",
        "source_url": "https://example.com",
    }
    scored = score_opportunity(lead, cfg)
    assert scored["score"] >= 4
