import os
import json
import logging
from groq import Groq

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
You are a lead analyst for a Saudi MEP and infrastructure subcontractor.
Your job: read one news item or tender listing, decide whether it is a
COMMERCIALLY ACTIONABLE LEAD, and score it 1-5.

ACTIONABLE means: this is a signal the company can act on in the next
1-30 days — a live tender, a fresh award to a main contractor, or an
RFQ that will generate MEP subcontracting packages.

STEP 1 — CLASSIFY the item into exactly ONE category:

A. LIVE_TENDER         — open tender or RFQ with a stated closing date
B. FRESH_AWARD         — main contractor just WON a project (within 60 days)
C. PRE_TENDER_SIGNAL   — project announced, prequalification or EOI stage
D. PRODUCT_DEAL        — sale, supply, or distribution of equipment/products
E. COMPLETED_NEWS      — article about something already built or finished
F. OUT_OF_SCOPE        — work that is not MEP / infrastructure (see scope below)
G. OPINION_OR_MARKET   — market commentary, interview, forecast, ranking

STEP 2 — APPLY the score by category:

A. LIVE_TENDER         → 5 if scope matches, else 2
B. FRESH_AWARD         → 5 if MEP subpackages likely, 3 if unclear
C. PRE_TENDER_SIGNAL   → 4 if scope matches, else 2
D. PRODUCT_DEAL        → 1 (never a lead for a subcontractor)
E. COMPLETED_NEWS      → 1 (already done, cannot bid)
F. OUT_OF_SCOPE        → 1
G. OPINION_OR_MARKET   → 1

STEP 3 — SCOPE check (applies to A, B, C only):
IN SCOPE = MEP, HVAC, VRF, chillers, chilled water, firefighting,
fire pumps, plumbing, drainage, electrical distribution, low current,
infrastructure utilities, industrial piping, water networks.
OUT OF SCOPE = facade, structural steel, civil earthworks, piling,
roads (as prime scope), architecture, fit-out joinery, landscaping,
solar panels (as sole scope), general real estate.

STEP 4 — GEOGRAPHY filter:
Saudi Arabia only. If project is outside KSA, set score to 1.

STEP 5 — OUTPUT strict JSON with these exact keys:

{
  "category": "A" | "B" | "C" | "D" | "E" | "F" | "G",
  "score": 1-5,
  "title": "clean headline, max 90 chars",
  "principal": "client name or 'Not disclosed'",
  "main_contractor": "name or 'Not disclosed'",
  "location": "city, Saudi Arabia or 'Not disclosed'",
  "value_display": "SAR X mn / $X mn / Not disclosed",
  "deadline": "YYYY-MM-DD or 'Not stated'",
  "scope": ["list", "of", "in-scope", "trades"],
  "why_zoom": "one sentence, evidence-based, no fluff",
  "lead_type": "TENDER" | "AWARD" | "PRE_TENDER" | "OTHER",
  "confidence": "high" | "medium" | "low"
}

RULES:
- Never invent a value, deadline, principal, or contractor. Use "Not disclosed".
- Never output a score higher than the category allows.
- Every "why_zoom" must cite a specific fact from the text, not generic praise.
- Return ONLY valid JSON. No prose. No markdown fences.
"""


def _client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("GROQ_API_KEY")
        except Exception:
            pass
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not configured")
    return Groq(api_key=api_key)


def _empty_score(lead):
    """Fallback when the LLM fails — never let a lead crash the scan."""
    return {
        "category": "G",
        "score": 0,
        "title": (lead.get("raw_text") or "")[:90],
        "principal": "Not disclosed",
        "main_contractor": "Not disclosed",
        "location": "Not disclosed",
        "value_display": "Not disclosed",
        "deadline": "Not stated",
        "scope": [],
        "why_zoom": "Scoring failed — LLM error.",
        "lead_type": "OTHER",
        "confidence": "low",
        "source_url": lead.get("source_url", ""),
        "source_name": lead.get("source_name", ""),
        "publisher": lead.get("source_name", ""),
    }


def score_opportunity(lead, cfg):
    """
    Takes an enriched lead dict, asks Groq to classify + score it,
    returns a flat dict with all fields merged.
    """
    text = lead.get("raw_text") or lead.get("title") or ""
    if not text:
        return _empty_score(lead)

    model = cfg.get("settings", {}).get("llm", {}).get(
        "model", "openai/gpt-oss-120b"
    )

    user_payload = (
        f"SOURCE: {lead.get('source_name','')}\n"
        f"URL: {lead.get('source_url','')}\n"
        f"PUBLISHED: {lead.get('published','')}\n\n"
        f"ITEM TEXT:\n{text[:6000]}"
    )

    try:
        client = _client()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_payload},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=800,
        )
        raw = response.choices[0].message.content or "{}"
        parsed = json.loads(raw)
    except Exception as e:
        logger.warning(f"score_opportunity LLM failed: {type(e).__name__}: {e}")
        return _empty_score(lead)

    # Ensure required keys exist
    parsed.setdefault("category", "G")
    parsed.setdefault("score", 0)
    parsed.setdefault("title", "")
    parsed.setdefault("principal", "Not disclosed")
    parsed.setdefault("main_contractor", "Not disclosed")
    parsed.setdefault("location", "Not disclosed")
    parsed.setdefault("value_display", "Not disclosed")
    parsed.setdefault("deadline", "Not stated")
    parsed.setdefault("scope", [])
    parsed.setdefault("why_zoom", "")
    parsed.setdefault("lead_type", "OTHER")
    parsed.setdefault("confidence", "low")

    # Attach source metadata — never trust the LLM to preserve it
    parsed["source_url"] = lead.get("source_url", "")
    parsed["source_name"] = lead.get("source_name", "")
    parsed["publisher"] = lead.get("source_name", "")

    return parsed
