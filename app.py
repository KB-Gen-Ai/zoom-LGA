import asyncio
import os
import subprocess
from pathlib import Path

import streamlit as st


@st.cache_resource
def ensure_playwright_browser():
    marker = Path.home() / ".cache" / "ms-playwright" / ".installed"
    if marker.exists():
        return True
    result = subprocess.run(
        ["bash", "setup.sh"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Playwright browser installation failed:\n" + result.stderr
        )
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.touch()
    return True


ensure_playwright_browser()

import streamlit as st

from config.loader import load_config
from crawler.engine import run_scan
from services.digest import build_digest_markdown, send_digest_email


st.set_page_config(
    page_title="Zoom Al Arab — Opportunity Intelligence",
    page_icon="🔎",
    layout="wide",
)


@st.cache_resource
def get_config():
    return load_config()


cfg = get_config()

st.title("Zoom Al Arab — KSA Opportunity Intelligence")
st.caption("Procurement, project and subcontracting lead intelligence")

st.sidebar.header("Scan settings")

max_results = st.sidebar.number_input(
    "Maximum results",
    min_value=1,
    max_value=50,
    value=15,
    step=1,
)

use_llm = st.sidebar.checkbox(
    "Use Groq enrichment",
    value=True,
)

st.sidebar.markdown("---")
st.sidebar.write("Configured sources")

for source in cfg["sources"]:
    st.sidebar.write(f"• {source['name']}")

if st.button("Run opportunity scan", type="primary"):
    with st.spinner("Scanning configured sources..."):
        try:
            results = asyncio.run(
                run_scan(
                    cfg,
                    max_results=max_results,
                    use_llm=use_llm,
                )
            )
        except Exception as exc:
            st.error(f"Scan failed: {exc}")
            st.stop()

    st.session_state["results"] = results


results = st.session_state.get("results", [])

if results:
    st.subheader(f"Opportunities found: {len(results)}")

    for i, result in enumerate(results, 1):
        with st.expander(
            f"{i}. {result.get('title', 'Untitled')} — "
            f"{result.get('score', 0)}/5"
        ):
            st.write(f"**Type:** {result.get('lead_type', 'UNKNOWN')}")
            st.write(f"**Location:** {result.get('location', 'Saudi Arabia')}")
            st.write(f"**Publisher:** {result.get('publisher', 'Unknown')}")
            st.write(
                f"**Main contractor:** "
                f"{result.get('main_contractor') or 'Not identified'}"
            )
            st.write(
                f"**Scope:** "
                f"{', '.join(result.get('scope', [])) or 'See source'}"
            )
            st.write(
                f"**Value:** "
                f"{result.get('value_display', 'Unknown')}"
            )
            st.write(
                f"**Deadline:** "
                f"{result.get('deadline') or 'Not stated'}"
            )
            st.write(
                f"**Why Zoom:** "
                f"{result.get('why_zoom', '')}"
            )
            st.write(
                f"**Confidence:** "
                f"{result.get('confidence', 'Unknown')}"
            )

            source_url = result.get("source_url", "")
            if source_url:
                st.markdown(f"[Open source]({source_url})")

    st.download_button(
        "Download digest",
        data=build_digest_markdown(results),
        file_name="zoom_al_arab_opportunity_digest.md",
        mime="text/markdown",
    )

    recipients = cfg["recipients"].get("default", "")

    if st.button("Email digest"):
        if not recipients:
            st.warning(
                "No recipients configured in config/recipients.yaml."
            )
        else:
            try:
                message = send_digest_email(
                    build_digest_markdown(results),
                    recipients,
                )
                st.success(message)
            except Exception as exc:
                st.error(f"Email failed: {exc}")

else:
    st.info(
        "No scan results yet. Click 'Run opportunity scan' to start."
    )
