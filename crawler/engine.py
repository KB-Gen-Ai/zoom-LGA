import asyncio
import traceback
import httpx
import feedparser

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

from services.llm import enrich_opportunity
from services.scoring import score_opportunity


KEY_TERMS = [
    "mep", "hvac", "vrf", "chiller", "chilled water", "firefighting",
    "fire pump", "plumbing", "drainage", "electrical", "low current",
    "infrastructure", "industrial piping", "mechanical", "maintenance",
    "subcontract", "subcontractor", "epc", "cement", "power plant",
    "hotel", "airport", "metro", "university", "hospital",
]


def _candidate(text: str) -> bool:
    t = (text or "").lower()
    return sum(1 for k in KEY_TERMS if k in t) >= 2


# ---------------- RSS path ----------------

def _fetch_rss(source):
    """Return list of items from a feed URL using feedparser."""
    print(f"[rss] fetching: {source['name']} -> {source['url']}")
    try:
        feed = feedparser.parse(source["url"])
        entries = feed.entries or []
        print(f"[rss] {source['name']}: {len(entries)} entries")
        items = []
        for entry in entries:
            title = entry.get("title", "")
            summary = entry.get("summary", "") or entry.get("description", "")
            link = entry.get("link", "")
            published = entry.get("published", "") or entry.get("updated", "")
            blob = f"{title}\n{summary}"
            if not _candidate(blob):
                continue
            items.append({
                "source_name": source["name"],
                "source_url": link,
                "raw_text": blob[:5000],
                "published": published,
            })
        print(f"[rss] {source['name']}: {len(items)} after keyword filter")
        return items
    except Exception as e:
        print(f"[rss] {source['name']} FAILED: {type(e).__name__}: {e}")
        traceback.print_exc()
        return []


# ---------------- HTML path (Playwright via crawl4ai) ----------------

async def _crawl_html(urls, crawler_cfg):
    browser = BrowserConfig(headless=True, verbose=False)
    run_cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        word_count_threshold=crawler_cfg.get("word_count_threshold", 80),
        page_timeout=crawler_cfg.get("page_timeout_ms", 30000),
    )
    rows = []
    async with AsyncWebCrawler(config=browser) as crawler:
        for source_name, source_url, url in urls:
            print(f"[html] crawling: {source_name} -> {url}")
            try:
                result = await crawler.arun(url=url, config=run_cfg)
                text = result.markdown or result.cleaned_html or ""
                if _candidate(text):
                    rows.append({
                        "source_name": source_name,
                        "source_url": url,
                        "raw_text": text[:20000],
                    })
                    print(f"[html] {source_name}: MATCH")
                else:
                    print(f"[html] {source_name}: no keyword match")
            except Exception as exc:
                print(f"[html] {source_name} FAILED: {exc}")
                rows.append({
                    "source_name": source_name,
                    "source_url": url,
                    "raw_text": "",
                    "error": str(exc),
                })
    return rows


# ---------------- Dispatcher ----------------

async def run_scan(cfg, max_results=15, use_llm=True):
    print("=" * 60)
    print(f"[scan] START — {len(cfg.get('sources', []))} sources configured")

    all_raw = []
    html_urls = []

    for source in cfg.get("sources", []):
        stype = source.get("type", "html").lower()
        if stype == "rss":
            all_raw.extend(_fetch_rss(source))
        elif stype in ("html", "playwright"):
            html_urls.append((source["name"], source["url"], source["url"]))
        else:
            print(f"[scan] unknown source type: {stype} ({source.get('name')})")

    if html_urls:
        try:
            all_raw.extend(await _crawl_html(html_urls, cfg["settings"]["crawler"]))
        except Exception as e:
            print(f"[scan] HTML crawl failed: {type(e).__name__}: {e}")

    print(f"[scan] raw items collected: {len(all_raw)}")

    leads = []
    for item in all_raw:
        if not item.get("raw_text"):
            continue
        try:
            if use_llm:
                lead = await enrich_opportunity(item, cfg)
            else:
                lead = enrich_opportunity(item, cfg, force_no_llm=True)
        except Exception as e:
            print(f"[scan] enrich FAILED for {item.get('source_url')}: {type(e).__name__}: {e}")
            continue
        if not lead:
            continue
        try:
            scored = score_opportunity(lead, cfg)
        except Exception as e:
            print(f"[scan] score FAILED: {type(e).__name__}: {e}")
            continue
        if scored["score"] >= cfg["thresholds"]["include_from"]:
            leads.append(scored)

    leads.sort(key=lambda x: x.get("score", 0), reverse=True)
    print(f"[scan] DONE — {len(leads)} leads above threshold")
    print("=" * 60)
    return leads[:max_results]
