import json
import os
from groq import Groq

SYSTEM = """You are the opportunity intelligence analyst for Zoom Al Arab General Contracting Company in Saudi Arabia.

Classify only commercially plausible opportunities. Zoom is primarily an MEP/mechanical/infrastructure contractor and often works as a subcontractor or JV partner.

Return JSON only with:
title, description, publisher, main_contractor, location, opportunity_type,
lead_type, scope, deadline, dates, value, value_type, contact, summary,
why_zoom, evidence, confidence.

lead_type must be DIRECT, INDIRECT, MARKET_INTELLIGENCE, or UNKNOWN.
value_type must be OFFICIAL, CONVERTED, ESTIMATED, or UNKNOWN.
Do not invent facts. If absent, use empty string/array.
For indirect leads, explain why a main contractor/project award could create a subcontracting opportunity for Zoom.
"""

async def enrich_opportunity(item, cfg, force_no_llm=False):
    if force_no_llm:
        return {
            "title": item["source_url"],
            "description": item["raw_text"][:1000],
            "publisher": item["source_name"],
            "location": "Saudi Arabia",
            "lead_type": "UNKNOWN",
            "scope": [],
            "source_name": item["source_name"],
            "source_url": item["source_url"],
            "evidence": [item["source_url"]],
            "confidence": "Low",
        }

    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    client = Groq(api_key=key)
    profile = cfg["profile"]
    prompt = f"""Zoom profile:
{json.dumps(profile, ensure_ascii=False)}

Source:
{item['source_name']} — {item['source_url']}

Page content:
{item['raw_text'][:24000]}
"""
    response = client.chat.completions.create(
        model=cfg["settings"]["llm"]["model"],
        temperature=cfg["settings"]["llm"]["temperature"],
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
    )
    data = json.loads(response.choices[0].message.content)
    data["source_name"] = item["source_name"]
    data["source_url"] = item["source_url"]
    data["raw_text"] = item["raw_text"][:5000]
    return data
