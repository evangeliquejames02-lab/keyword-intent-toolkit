from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from seo_opportunity_engine.data import DataValidationError, build_page_summary, load_analytics, load_search_console
from seo_opportunity_engine.opportunities import build_opportunities


ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "sample_data"


def _read_csv(upload, sample: str) -> pd.DataFrame:
    if upload is not None:
        return pd.read_csv(upload)
    return pd.read_csv(SAMPLES / sample)


def run() -> None:
    st.set_page_config(page_title="Organic Search Opportunity Engine", page_icon="↗", layout="wide")
    st.title("Organic Search-to-Revenue Opportunity Engine")
    st.caption("Turn Search Console and GA4 exports into a prioritized organic growth review.")

    with st.sidebar:
        st.header("Data source")
        mode = st.radio("Choose data", ["Interactive demo", "Upload CSV exports"], index=0)
        st.divider()
        min_impressions = st.number_input("Minimum impressions", min_value=1, value=100, step=50)
        st.caption("Opportunity signals use transparent heuristics. Review findings before acting.")
        if mode == "Upload CSV exports":
            gsc_file = st.file_uploader("Search Console query and page export", type="csv")
            current_file = st.file_uploader("GA4 current period export", type="csv", key="current")
            previous_file = st.file_uploader("GA4 comparison period export", type="csv", key="previous")
        else:
            gsc_file = current_file = previous_file = None

    try:
        search_console = load_search_console(_read_csv(gsc_file, "gsc_queries.csv"))
        current = load_analytics(_read_csv(current_file, "ga4_current.csv"))
        previous = load_analytics(_read_csv(previous_file, "ga4_previous.csv")) if previous_file is not None or mode == "Interactive demo" else None
        pages = build_page_summary(search_console, current, previous)
        opportunities = build_opportunities(search_console, pages, int(min_impressions))
    except (DataValidationError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        st.error(str(exc))
        st.info("Use CSV exports with page and query, clicks, impressions, and GA4 landing page, sessions, key events, and revenue columns.")
        return

    total_revenue = pages["revenue_current"].sum()
    total_events = pages["key_events_current"].sum()
    total_clicks = pages["clicks"].sum()
    total_impressions = pages["impressions"].sum()
    ctr = total_clicks / total_impressions if total_impressions else 0
    a, b, c, d, e = st.columns(5)
    a.metric("Organic clicks", f"{total_clicks:,.0f}")
    b.metric("Impressions", f"{total_impressions:,.0f}")
    c.metric("Average CTR", f"{ctr:.1%}")
    d.metric("Key events", f"{total_events:,.0f}")
    e.metric("Organic revenue", f"${total_revenue:,.0f}")

    st.subheader("Opportunity queue")
    st.caption(f"{len(opportunities)} review signals across {len(pages):,} landing pages. Click gaps are estimates based on position-band median CTR, not forecasts.")
    if opportunities.empty:
        st.success("No opportunities match the current threshold. Lower minimum impressions to review more rows.")
    else:
        types = st.multiselect("Opportunity type", opportunities["type"].unique().tolist(), default=opportunities["type"].unique().tolist())
        visible = opportunities[opportunities["type"].isin(types)].copy()
        visible["revenue_change_pct"] = visible["revenue_change_pct"].map(lambda value: f"{value:.1%}" if pd.notna(value) else "")
        st.dataframe(visible, use_container_width=True, hide_index=True)
        st.download_button("Download opportunity queue", opportunities.to_csv(index=False), "organic_opportunities.csv", "text/csv")

    left, right = st.columns(2)
    with left:
        st.subheader("Organic revenue by landing page")
        chart = pages.nlargest(10, "revenue_current").set_index("page_url")["revenue_current"]
        st.bar_chart(chart, y_label="Revenue")
    with right:
        st.subheader("Search visibility by page")
        chart = pages.nlargest(10, "impressions").set_index("page_url")[["clicks", "impressions"]]
        st.bar_chart(chart, y_label="Search Console activity")

    st.subheader("Page performance")
    page_view = pages[["page_url", "clicks", "impressions", "ctr", "position", "sessions_current", "key_events_current", "revenue_current", "revenue_previous", "revenue_change_pct"]].copy()
    page_view["ctr"] = page_view["ctr"].map(lambda value: f"{value:.1%}")
    page_view["revenue_change_pct"] = page_view["revenue_change_pct"].map(lambda value: f"{value:.1%}" if pd.notna(value) else "")
    st.dataframe(page_view, use_container_width=True, hide_index=True)
    st.caption("Query-to-page relevance is a word-overlap review signal. CTR benchmarks use the uploaded site's position-band median. GA4 and Search Console data are joined by landing-page path; check property, date range, currency, and attribution settings before interpreting results.")
