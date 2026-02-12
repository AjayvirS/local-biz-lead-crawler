import json
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


def pick_db(root: Path) -> Path:
    candidates = [root / "src" / "data" / "leads.sqlite", root / "data" / "leads.sqlite"]
    existing = [p for p in candidates if p.exists()]
    if not existing:
        raise FileNotFoundError("No leads.sqlite found")
    return sorted(existing, key=lambda p: p.stat().st_size, reverse=True)[0]


def json_list(x):
    if not x or (isinstance(x, float) and pd.isna(x)):
        return []
    try:
        v = json.loads(x)
        return v if isinstance(v, list) else []
    except Exception:
        return []


st.set_page_config(page_title="Lead Details", layout="wide")

root = Path(__file__).resolve().parents[3]  # pages/Details.py → ui → src → repo
db = pick_db(root)

params = st.query_params
url = params.get("url")

st.title("Lead details")

if not url:
    st.warning("No url provided. Go back to Home and click 'View'.")
    st.stop()

con = sqlite3.connect(db)

tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
has_llm = "llm_insights" in tables

if has_llm:
    row = con.execute(
        """
        SELECT
          d.url, d.discovered_from, d.discovered_at,
          a.final_url, a.status_code, a.https, a.title, a.has_viewport_meta,
          a.has_email, a.has_phone, a.has_address, a.stack_hint, a.score, a.reasons_json,
          l.bullets_json, l.email_opener, l.generated_at
        FROM discovered_urls d
        LEFT JOIN site_analysis a ON a.url = d.url
        LEFT JOIN llm_insights l ON l.url = d.url
        WHERE d.url = ?
        """,
        (url,),
    ).fetchone()
else:
    row = con.execute(
        """
        SELECT
          d.url, d.discovered_from, d.discovered_at,
          a.final_url, a.status_code, a.https, a.title, a.has_viewport_meta,
          a.has_email, a.has_phone, a.has_address, a.stack_hint, a.score, a.reasons_json
        FROM discovered_urls d
        LEFT JOIN site_analysis a ON a.url = d.url
        WHERE d.url = ?
        """,
        (url,),
    ).fetchone()

con.close()

if not row:
    st.error("URL not found in database.")
    st.stop()

if has_llm:
    (
        url,
        discovered_from,
        discovered_at,
        final_url,
        status_code,
        https,
        title,
        has_viewport,
        has_email,
        has_phone,
        has_address,
        stack_hint,
        score,
        reasons_json,
        bullets_json,
        email_opener,
        llm_generated_at,
    ) = row
else:
    (
        url,
        discovered_from,
        discovered_at,
        final_url,
        status_code,
        https,
        title,
        has_viewport,
        has_email,
        has_phone,
        has_address,
        stack_hint,
        score,
        reasons_json,
    ) = row
    bullets_json = None
    email_opener = None
    llm_generated_at = None

st.subheader(f"{score if score is not None else '-'} | {'HTTPS' if https else 'HTTP'} | {url}")

c1, c2 = st.columns(2)
with c1:
    st.link_button("Open website", url)
    if discovered_from:
        st.link_button("Open directory source", discovered_from)
with c2:
    st.write(f"**Title:** {title or '-'}")
    st.write(f"**Status:** {status_code or '-'}")
    st.write(f"**Stack hint:** {stack_hint or '-'}")

st.divider()
st.markdown("### Deterministic reasons")
reasons = json_list(reasons_json)
if reasons:
    for r in reasons:
        st.write(f"- {r}")
else:
    st.info("No deterministic reasons stored for this URL yet.")

st.divider()
st.markdown("### Owner-friendly bullets (LLM)")
bullets = json_list(bullets_json)
if bullets:
    for b in bullets:
        st.write(f"- {b}")
else:
    st.info("No owner-friendly bullets stored for this URL yet.")

if email_opener:
    st.divider()
    st.markdown("### Email opener (LLM)")
    st.write(email_opener)

if llm_generated_at:
    st.caption(f"LLM generated at: {llm_generated_at}")