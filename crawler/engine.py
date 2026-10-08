import asyncio
import sys
import re
import traceback
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import feedparser

from services.scoring import score_batch


KEY_TERMS = [
    "mep", "hvac", "vrf", "chiller", "chilled water", "firefighting",
    "fire pump", "plumbing", "drainage", "electrical", "low current",
    "infrastructure", "industrial piping", "mechanical", "maintenance",
    "subcontract", "subcontractor", "epc", "cement", "power plant",
    "hotel", "airport", "metro", "university", "hospital", "water network",
    "tender", "awarded", "rfq", "prequalification",
]

MAX_ITEMS_TO_SCORE = 25
MAX_AGE_DAYS = 21

_RELATIVE_RE = re.compile(
    r"(\d+)\s+(minute|hour|day|week)s?\s+ago", re.IGNORECASE
)


def log(msg):
    sys.stderr.write(f"{msg}\n")
    sys.stderr.flush()


def _candidate(text):
    t = (text or "").lower()
    return sum(1 for k in KEY_TERMS if k in t) >= 2


def _parse_published(entry):
    """
    Return a timezone-aware datetime or None.
    Tries feedparser parsed struct, RFC 2822 string, then relative
    time in title ('2 days ago').
    """
    for key in ("published_parsed", "updated_parsed"):
        val = entry.get(key)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc)
            except Exception:
                pass

    for key in ("published", "updated"):
        raw = entry.get(key)
        if raw:
            try:
                dt = parsedate_to_datetime(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                pass

    title = entry.get("title", "") or ""
    m = _RELATIVE_RE.search(title)
    if m:
        n = int(m.group(1))
        unit = m.group(2).lower()
        delta_map = {
            "minute": timedelta(minutes=n),
            "hour":   timedelta(hours=n),
            "day":    timedelta(days=n),
            "week":   timedelta(weeks=n),
        }
        return datetime.now(timezone.utc) - delta_map[unit]

    return None


def _is_recent(entry, max_age_days=MAX_AGE_DAYS):
    """STRICT: reject if we cannot confirm the item is recent."""
    dt = _parse_published(entry)
    if dt is None:
        return False, None
    age = datetime.now(timezone.utc) - dt
    return age <= timedelta(days=max_age_days), dt


def _fetch_rss(source):
    log(f"[rss] {source['name']}")
    try:
        feed = feedparser.parse(source["url"])
        entries = feed.entries or []
        kept = []
        dropped_old = 0
        dropped_nodate = 0
        dropped_kw = 0

        for entry in entries:
            recent, dt = _is_recent(entry)
            if dt is None:
                dropped_nodate += 1
                continue
            if not recent:
                dropped_old += 1
                continue

            title = entry.get("title", "")
            summary = entry.get("summary", "") or entry.get("description", "")
            link = entry.get("link", "")
            blob = f"{title}\n{summary}"
            if not _candidate(blob):
                dropped_kw += 1
                continue

            kept.append({
                "source_name": source["name"],
                "source_url": link,
                "raw_text": blob[:4000],
                "published": dt.strftime("%Y-%m-%d"),
                "published_dt": dt.isoformat(),
            })

        log(
            f"[rss]   {source['name']}: {len(entries)} raw "
            f"-> kept {len(kept)} "
            f"(old {dropped_old}, no-date {dropped_nodate}, kw {dropped_kw})"
        )
        return kept
    except Exception as e:
        log(f"[rss]   {source['name']} FAILED: {type(e).__name__}: {e}")
        traceback.print_exc(file=sys.stderr)
        return []


async def run_scan(cfg, max_results=15, use_llm=True):
    log("=" * 60)
    log(f"[scan] START — {len(cfg.get('sources', []))} sources")

    all_items = []
    for source in cfg.get("sources", []):
        if source.get("type", "rss").lower() == "rss":
            all_items.extend(_fetch_rss(source))

    log(f"[scan] total candidates: {len(all_items)}")

    if not all_items:
        log("[scan] no candidates — exiting")
        log("=" * 60)
        return []

    all_items = all_items[:MAX_ITEMS_TO_SCORE]
    log(f"[scan] scoring {len(all_items)} items in one batch call")

    if not use_llm:
        log("[scan] LLM disabled — returning unranked")
        log("=" * 60)
        return all_items[:max_results]

    try:
        scored = await score_batch(all_items, cfg)
    except Exception as e:
        log(f"[scan] score_batch FAILED: {type(e).__name__}: {e}")
        traceback.print_exc(file=sys.stderr)
        log("=" * 60)
        return []

    threshold = cfg.get("thresholds", {}).get("include_from", 4)
    blocked = {"D", "E", "F", "G"}

    leads = []
    for s in scored:
        if s.get("score", 0) < threshold:
            continue
        if s.get("category") in blocked:
            continue
        leads.append(s)

    leads.sort(key=lambda x: x.get("score", 0), reverse=True)
    log(f"[scan] DONE — {len(leads)} leads pass threshold {threshold}")
    log("=" * 60)
    return leads[:max_results]
