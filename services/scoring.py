import os
import sys
import json
from datetime import datetime, timezone

from groq import Groq


SYSTEM_PROMPT = """
You are a lead analyst for a Saudi MEP and infrastructure subcontractor.
You will receive a numbered list of news items and tender listings.

For EACH item, output one JSON object. Return a JSON object with a single
key "results" whose value is an array of these objects, in the same order.

For each item, output:
{
  "item_id": <int, matches input>,
  "category": "A" | "B" | "C" | "D" | "E" | "F" | "G",
  "score": 1-5,
  "title": "clean headline, max 90 chars",
  "principal": "client name or 'Not disclosed'",
  "main_contractor": "name or 'Not disclosed'",
  "location": "city or 'Not disclosed'",
  "value_display": "SAR X mn / $X mn / Not disclosed",
  "deadline": "YYYY-MM-DD or 'Not stated'",
  "scope": ["in-scope", "trades"],
  "why_zoom": "one sentence, evidence-based",
  "lead_type": "TENDER" | "AWARD" | "PRE_TENDER" | "OTHER",
  "confidence": "high" | "medium" | "low"
}

STEP 1 — CLASSIFY each item into exactly ONE category:

A. LIVE_TENDER         — open tender or RFQ with a stated closing date
B. FRESH_AWARD         — main contractor just WON a project (within 60 days)
C. PRE_TENDER_SIGNAL   — project announced, prequalification or EOI stage
D. PRODUCT_DEAL        — sale, supply, or distribution of equipment/products
E. COMPLETED_NEWS      — article about something already built or finished
F. OUT_OF_SCOPE        — non-MEP/non-infrastructure (see scope rules)
G. OPINION_OR_MARKET   — commentary, interview, forecast, ranking, list

STEP 2 — SCORE by category:

A → 5 if scope matches, else 2
B → 5 if MEP subcontract packages are likely, 3 if unclear
C → 4 if scope matches, else 2
D → 1
E → 1
F → 1
G → 1

STEP 3 — SCOPE (applies to A, B, C only):
IN: MEP, HVAC, VRF, chillers, chilled water, firefighting, fire pumps,
plumbing, drainage, electrical distribution, low current, infrastructure
utilities, industrial piping, water networks.
OUT: facade, structural steel, civil earthworks, piling, roads as prime,
architecture, fit-out joinery, landscaping, solar as sole scope, real estate.

STEP 4 — GEOGRAPHY:
Saudi Arabia only. Non-KSA project -> score 1.

RULES:
- Never invent values, deadlines, principals, or contractors.
- Every why_zoom must cite a specific fact from the item.
- Return ONLY valid JSON. No markdown fences. No prose.
"""


def _client():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("GROQ_API_KEY")
        except Exception:
            pass
    if not key:
        raise RuntimeError("GROQ_API_KEY not configured")
    return Groq(api_key=key)


def _log(msg):
    sys.stderr.write(f"{msg}\n")
    sys.stderr.flush()


def _build_batch_prompt(items):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    parts = [
        f"TODAY IS {today}. "
        f"Discard any item whose date is not clearly recent.\n"
    ]
    for i, it in enumerate(items):
        parts.append(
            f"ITEM {i}\n"
            f"SOURCE: {it.get('source_name','')}\n"
            f"URL: {it.get('source_url','')}\n"
            f"PUBLISHED: {it.get('published','')}\n"
            f"TEXT: {it.get('raw_text','')[:1500]}\n"
        )
    return "\n---\n".join(parts)


def _empty(item_id, item):
    return {
        "item_id": item_id,
        "category": "G",
        "score": 0,
        "title": (item.get("raw_text") or "")[:90],
        "principal": "Not disclosed",
        "main_contractor": "Not disclosed",
        "location": "Not disclosed",
        "value_display": "Not disclosed",
        "deadline": "Not stated",
        "scope": [],
        "why_zoom": "Scoring failed.",
        "lead_type": "OTHER",
        "confidence": "low",
        "source_url": item.get("source_url", ""),
        "source_name": item.get("source_name", ""),
        "publisher": item.get("source_name", ""),
        "published": item.get("published", ""),
    }


async def score_batch(items, cfg):
    """One Groq call, N items in, N scored dicts out."""
    if not items:
        return []

    model = cfg.get("settings", {}).get("llm", {}).get(
        "model", "openai/gpt-oss-120b"
    )

    prompt = _build_batch_prompt(items)
    _log(f"[score] batch call — {len(items)} items, prompt {len(prompt)} chars")

    try:
        client = _client()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=4000,
        )
        raw = response.choices[0].message.content or "{}"
        parsed = json.loads(raw)
    except Exception as e:
        _log(f"[score] LLM call FAILED: {type(e).__name__}: {e}")
        return [_empty(i, it) for i, it in enumerate(items)]

    results = parsed.get("results") or []
    _log(f"[score] LLM returned {len(results)} scored items")

    by_id = {}
    for r in results:
        if isinstance(r, dict) and "item_id" in r:
            by_id[r["item_id"]] = r

    final = []
    for i, it in enumerate(items):
        r = by_id.get(i)
        if not r:
            final.append(_empty(i, it))
            continue
        r["source_url"] = it.get("source_url", "")
        r["source_name"] = it.get("source_name", "")
        r["publisher"] = it.get("source_name", "")
        r["published"] = it.get("published", "")
        final.append(r)

    return final
