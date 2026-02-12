from __future__ import annotations

import sqlite3
import urllib.parse
from pathlib import Path

import pandas as pd
import streamlit as st


def pick_db(root: Path) -> Path:
    candidates = [
        root / "src" / "data" / "leads.sqlite",
        root / "data" / "leads.sqlite",
    ]
    existing = [p for p in candidates if p.exists()]
    if not existing:
        raise FileNotFoundError("No leads.sqlite found in src/data or data")
    return sorted(existing, key=lambda p: p.stat().st_size, reverse=True)[0]


@st.cache_data(ttl=10)
def load_data(db_path: str) -> pd.DataFrame:
    con = sqlite3.connect(db_path)

    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    has_llm = "llm_insights" in tables

    if has_llm:
        q = """
        SELECT
          d.url,
          d.discovered_from,
          d.discovered_at,
          a.final_url,
          a.status_code,
          a.https,
          a.title,
          a.has_viewport_meta,
          a.has_email,
          a.has_phone,
          a.has_address,
          a.stack_hint,
          a.score,
          a.reasons_json,
          l.bullets_json,
          l.email_opener,
          l.generated_at AS llm_generated_at
        FROM discovered_urls d
        LEFT JOIN site_analysis a ON a.url = d.url
        LEFT JOIN llm_insights l ON l.url = d.url
        """
    else:
        q = """
        SELECT
          d.url,
          d.discovered_from,
          d.discovered_at,
          a.final_url,
          a.status_code,
          a.https,
          a.title,
          a.has_viewport_meta,
          a.has_email,
          a.has_phone,
          a.has_address,
          a.stack_hint,
          a.score,
          a.reasons_json
        FROM discovered_urls d
        LEFT JOIN site_analysis a ON a.url = d.url
        """

    df = pd.read_sql_query(q, con)
    con.close()

    for col in ["https", "has_viewport_meta", "has_email", "has_phone", "has_address"]:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype(int)

    if "score" in df.columns:
        df["score"] = pd.to_numeric(df["score"], errors="coerce")

    return df


def main() -> None:
    st.set_page_config(page_title="Local Biz Lead Analytics", layout="wide")

    root = Path(__file__).resolve().parents[2]
    db = pick_db(root)

    st.title("Local Biz Lead Analytics")
    st.caption(f"Database: {db}")

    df = load_data(str(db))

    # Filters (apply BEFORE pagination)
    st.sidebar.header("Filters")

    analyzed_only = st.sidebar.checkbox("Analyzed only", value=True)
    if analyzed_only:
        df = df[df["score"].notna()]

    if df.empty:
        st.warning("No rows match your filters.")
        return

    score_min = int(df["score"].min()) if df["score"].notna().any() else 0
    score_max = int(df["score"].max()) if df["score"].notna().any() else 100
    default_hi = int(df["score"].quantile(0.5)) if df["score"].notna().any() else score_max

    score_range = st.sidebar.slider(
        "Score range (lower = worse / better opportunity)",
        min_value=score_min,
        max_value=score_max,
        value=(score_min, default_hi),
    )
    df = df[df["score"].between(score_range[0], score_range[1], inclusive="both")]

    stack_options = sorted([x for x in df["stack_hint"].dropna().unique().tolist() if x])
    stack_filter = st.sidebar.multiselect("Stack hint", options=stack_options, default=[])
    if stack_filter:
        df = df[df["stack_hint"].isin(stack_filter)]

    https_filter = st.sidebar.selectbox("HTTPS", options=["Any", "HTTPS only", "HTTP only"], index=0)
    if https_filter == "HTTPS only":
        df = df[df["https"] == 1]
    elif https_filter == "HTTP only":
        df = df[df["https"] == 0]

    search = st.sidebar.text_input("Search URL/title")
    if search.strip():
        s = search.strip().lower()
        df = df[
            df["url"].str.lower().str.contains(s, na=False)
            | df["title"].fillna("").str.lower().str.contains(s, na=False)
        ]

    sort_by = st.sidebar.selectbox(
        "Sort by",
        options=["score (worst first)", "score (best first)", "discovered_at"],
        index=0,
    )
    if sort_by == "score (worst first)":
        df = df.sort_values(["score"], ascending=True)
    elif sort_by == "score (best first)":
        df = df.sort_values(["score"], ascending=False)
    else:
        df = df.sort_values(["discovered_at"], ascending=False)

    # Add Details link column (routes via query param)
    df = df.copy()
    df["details"] = df["url"].apply(
        lambda u: f"/Details?url={urllib.parse.quote(str(u), safe='')}"
    )

    # Pagination 
    page_size = st.sidebar.selectbox("Page size", [25, 50, 100, 200], index=1)
    total_rows = len(df)
    total_pages = max(1, (total_rows + page_size - 1) // page_size)
    page = st.sidebar.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)

    start = (page - 1) * page_size
    end = start + page_size
    df_view = df.iloc[start:end].copy()

    st.caption(f"Showing {start+1}-{min(end, total_rows)} of {total_rows} (Page {page}/{total_pages})")

    # ----------------------------
    # Table
    # ----------------------------
    st.subheader("Leads")

    cols = ["score", "url", "title", "https", "has_viewport_meta", "stack_hint", "details"]
    cols = [c for c in cols if c in df_view.columns]

    st.data_editor(
        df_view[cols],
        use_container_width=True,
        height=520,
        disabled=True,
        column_config={
            "url": st.column_config.LinkColumn(
                "Website",
                display_text=None,  # shows the URL and makes it clickable
                help="Open the business website",
            ),
            "details": st.column_config.LinkColumn(
                "Details",
                display_text="View",
                help="Open details page for this lead",
            ),
            "score": st.column_config.NumberColumn("Score", format="%d"),
        },
    )

    st.info("Tip: click **View** to open the details page for a row.")


if __name__ == "__main__":
    main()