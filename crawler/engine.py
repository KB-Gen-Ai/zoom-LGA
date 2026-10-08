import asyncio
import re
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

from services.llm import enrich_opportunity
from services.scoring import score_opportunity

KEY_TERMS = [
    "mep", "hvac", "vrf", "chiller", "chilled water", "firefighting",
    "fire pump", "plumbing", "drainage", "electrical", "low current",
    "infrastructure", "industrial piping", "mechanical", "maintenance",
    "subcontract", "subcontractor", "epc", "cement", "power plant",
    "hotel", "airport", "metro", "university", "hospital"
]

def _candidate(text: str) -> bool:
    t = text.lower()
    return sum(1 for k in KEY_TERMS if k in t) >= 2

async def _crawl(urls, crawler_cfg):
    browser = BrowserConfig(headless=True, verbose=False)
    run_cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        word_count_threshold=crawler_cfg.get("word_count_threshold", 80),
        page_timeout=crawler_cfg.get("page_timeout_ms", 30000),
    )
    rows = []
    async with AsyncWebCrawler(config=browser) as crawler:
        for source_name, source_url, url in urls:
            try:
                result = await crawler.arun(url=url, config=run_cfg)
                text = result.markdown or result.cleaned_html or ""
                if _candidate(text):
                    rows.append({
                        "source_name": source_name,
                        "source_url": url,
                        "raw_text": text[:30000],
                    })
            except Exception as exc:
                rows.append({
                    "source_name": source_name,
                    "source_url": url,
                    "raw_text": "",
                    "error": str(exc),
                })
    return rows

def _build_urls(cfg):
    urls = []
    for s in cfg["sources"]:
        for u in s.get("discovery_urls", []):
            urls.append((s["name"], s["url"], u))
    return urls

async def run_scan(cfg, max_results=15, use_llm=True):
    raw = await _crawl(_build_urls(cfg), cfg["settings"]["crawler"])
    leads = []
    for item in raw:
        if not item.get("raw_text"):
            continue
        if use_llm:
            lead = await enrich_opportunity(item, cfg)
        else:
            lead = enrich_opportunity(item, cfg, force_no_llm=True)
        if not lead:
            continue
        scored = score_opportunity(lead, cfg)
        if scored["score"] >= cfg["thresholds"]["include_from"]:
            leads.append(scored)

    leads.sort(key=lambda x: x.get("score", 0), reverse=True)
    return leads[:max_results]
