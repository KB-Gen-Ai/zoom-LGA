import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone

def build_digest_markdown(results):
    lines = [
        "# ZOOM AL ARAB — KSA OPPORTUNITY INTELLIGENCE",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
    ]
    for i, x in enumerate(results, 1):
        lines += [
            f"## {i}. {x.get('title','Untitled')} — {x.get('score',0)}/5",
            f"**Type:** {x.get('lead_type','UNKNOWN')}",
            f"**Location:** {x.get('location','Saudi Arabia')}",
            f"**Publisher:** {x.get('publisher','Unknown')}",
            f"**Main contractor:** {x.get('main_contractor') or 'Not identified'}",
            f"**Scope:** {', '.join(x.get('scope',[])) or 'See source'}",
            f"**Value:** {x.get('value_display','Unknown')}",
            f"**Deadline:** {x.get('deadline') or 'Not stated'}",
            f"**Why Zoom:** {x.get('why_zoom','')}",
            f"**Confidence:** {x.get('confidence','Unknown')}",
            f"**Source:** {x.get('source_url','')}",
            "",
        ]
    return "\n".join(lines)

def send_digest_email(markdown, recipients):
    if not recipients:
        raise RuntimeError("No email recipient configured.")
    host = os.getenv("SMTP_HOST")
    user = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM", user or "")
    port = int(os.getenv("SMTP_PORT", "587"))
    if not all([host, user, password, sender]):
        raise RuntimeError("SMTP is not configured. Set SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD and SMTP_FROM in Streamlit Secrets.")

    to = [x.strip() for x in recipients.split(",") if x.strip()]
    msg = MIMEMultipart()
    msg["Subject"] = "ZOOM AL ARAB — KSA Opportunity Intelligence"
    msg["From"] = sender
    msg["To"] = ", ".join(to)
    msg.attach(MIMEText(markdown, "plain", "utf-8"))

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.sendmail(sender, to, msg.as_string())
    return f"Digest sent to {', '.join(to)}"
