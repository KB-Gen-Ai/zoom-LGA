from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent

def _load(name):
    with open(ROOT / name, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_config():
    profile = _load("profile.yaml")
    sources_doc = _load("sources.yaml")
    rubric_doc = _load("rubric.yaml")
    recipients_doc = _load("recipients.yaml")
    settings = _load("settings.yaml")
    return {
        "profile": profile,
        "sources": [x for x in sources_doc["sources"] if x.get("enabled", True)],
        "rubric": rubric_doc["rubric"],
        "thresholds": rubric_doc["thresholds"],
        "recipients": recipients_doc["recipients"],
        "settings": settings,
    }
