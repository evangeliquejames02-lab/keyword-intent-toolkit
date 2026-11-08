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
    st.set_page_config(page_title="Organic Search Opportunity Engine", page_icon="↗", layout="wide", initial_sidebar_state="expanded")
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
    :root { --ink:#172b3a; --muted:#637586; --line:#e3eaf0; --green:#13866b; --pale:#edf7f3; }
    html, body, [class*="css"] { font-family:'DM Sans',sans-serif; color:var(--ink); }
    .stApp { background:linear-gradient(180deg,#f4f8fa 0,#f8fafb 230px,#f7f9fb 100%); }
    [data-testid="stHeader"] { background:transparent; }
    .block-container { max-width:1440px; padding-top:2.1rem; padding-bottom:3rem; }
    h1,h2,h3 { font-family:'Manrope',sans-serif !important; letter-spacing:-.035em; color:var(--ink); }
    h2 { font-size:1.35rem !important; margin-bottom:.25rem !important; }
    [data-testid="stSidebar"] { background:#102b38; }
    [data-testid="stSidebar"] * { color:#eef6f5 !important; }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section { border-color:#52707b; }
    [data-testid="stSidebar"] [data-testid="stRadio"] label { color:#e7f0ef !important; }
    .hero { padding:1.6rem 1.8rem 1.5rem; border-radius:20px; color:#f7fbfb; background:linear-gradient(112deg,#102b38 0%,#164c4d 62%,#16775f 100%); box-shadow:0 14px 34px rgba(21,55,66,.13); margin-bottom:1.15rem; }
    .hero-eyebrow { text-transform:uppercase; letter-spacing:.14em; font-size:.72rem; font-weight:700; color:#a9d9ca; margin-bottom:.6rem; }
    .hero-title { font:800 clamp(1.7rem,3vw,2.5rem)/1.13 'Manrope',sans-serif; letter-spacing:-.05em; margin:0 0 .55rem; color:#fff; }
    .hero-copy { color:#d5e8e4; font-size:1rem; max-width:760px; margin:0; }
    .hero-tag { display:inline-block; margin-top:1.15rem; padding:.38rem .68rem; border:1px solid rgba(226,246,239,.3); border-radius:99px; color:#e8f5ef; font-size:.76rem; }
    [data-testid="stMetric"] { background:#fff; border:1px solid var(--line); padding:1rem 1.05rem .85rem; border-radius:15px; box-shadow:0 3px 12px rgba(23,43,58,.035); }
    [data-testid="stMetricLabel"] p { color:var(--muted); font-weight:600; font-size:.78rem; }
    [data-testid="stMetricValue"] { color:var(--ink); font:700 1.7rem 'Manrope',sans-serif; }
    [data-testid="stVerticalBlockBorderWrapper"] { border-color:var(--line) !important; border-radius:15px !important; background:#fff; }
    [data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:12px; overflow:hidden; }
    .section-note { color:var(--muted); font-size:.88rem; margin:.1rem 0 .85rem; }
    div.stButton > button, div.stDownloadButton > button { border-radius:9px; font-weight:600; }
    div.stDownloadButton > button { background:#13866b; color:#fff; border:0; }
    div.stDownloadButton > button:hover { background:#0f7059; color:#fff; border:0; }
    [data-testid="stTabs"] button { font-weight:600; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="hero">
      <div class="hero-eyebrow">Organic growth intelligence</div>
      <div class="hero-title">Organic Search-to-Revenue<br>Opportunity Engine</div>
      <p class="hero-copy">Find the search visibility, landing-page, and revenue signals that deserve your attention next.</p>
      <span class="hero-tag">Search Console + GA4 · One prioritized view</span>
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.header("Workspace")
        mode = st.radio("Choose data", ["Interactive demo", "Upload CSV exports"], index=0, key="data_mode")
        st.divider()
        min_impressions = st.number_input("Minimum impressions", min_value=1, value=100, step=50)
        st.caption("Set the impression threshold to focus the opportunity review.")
        if mode == "Upload CSV exports":
            gsc_file = st.file_uploader("Search Console query and page export", type="csv")
            current_file = st.file_uploader("GA4 current period export", type="csv", key="current")
            previous_file = st.file_uploader("GA4 comparison period export", type="csv", key="previous")
        else:
            gsc_file = current_file = previous_file = None

    if mode == "Upload CSV exports" and (gsc_file is None or current_file is None):
        st.info("Upload the Search Console export and current-period GA4 export to build your report. The comparison-period GA4 export is optional.")
        return

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
    b.metric("Search impressions", f"{total_impressions:,.0f}")
    c.metric("Average CTR", f"{ctr:.1%}")
    d.metric("Key events", f"{total_events:,.0f}")
    e.metric("Organic revenue", f"${total_revenue:,.0f}")

    st.markdown("<div style='height:1.1rem'></div>", unsafe_allow_html=True)
    opportunity_tab, landing_tab, guide_tab = st.tabs(["Opportunity queue", "Landing pages", "Method & data"])
    with opportunity_tab:
        st.subheader("Prioritized review")
        st.markdown(f"<p class='section-note'>{len(opportunities)} signals across {len(pages):,} landing pages · Focus on the strongest evidence first.</p>", unsafe_allow_html=True)
        if opportunities.empty:
            st.success("No opportunities meet this threshold. Lower minimum impressions to review more pages and queries.")
        else:
            types = st.multiselect("Filter signals", opportunities["type"].unique().tolist(), default=opportunities["type"].unique().tolist(), label_visibility="collapsed", placeholder="Filter signal types")
            visible = opportunities[opportunities["type"].isin(types)].copy()
            visible["revenue_change_pct"] = visible["revenue_change_pct"].map(lambda value: f"{value:.1%}" if pd.notna(value) else "")
            visible = visible.rename(columns={"type":"Opportunity", "priority":"Priority", "page":"Landing page", "query":"Search query", "detail":"Why it surfaced", "estimated_click_gap":"Potential clicks*", "revenue_change_pct":"Revenue change"})
            st.dataframe(visible, width="stretch", hide_index=True, height=min(480, 90 + 42 * len(visible)))
            st.download_button("Export opportunity queue", opportunities.to_csv(index=False), "organic_opportunities.csv", "text/csv")
            st.caption("*Potential clicks are a directional estimate against the site's median CTR for the same position band.")
        left, right = st.columns(2)
        with left, st.container(border=True):
            st.markdown("#### Revenue by landing page")
            chart = pages.nlargest(8, "revenue_current").set_index("page_url")["revenue_current"]
            st.bar_chart(chart, y_label="Revenue", color="#13866b")
        with right, st.container(border=True):
            st.markdown("#### Search visibility")
            chart = pages.nlargest(8, "impressions").set_index("page_url")[["clicks", "impressions"]]
            st.bar_chart(chart, y_label="Clicks and impressions", color=["#13866b", "#b8d9ce"])
    with landing_tab:
        st.subheader("Landing-page performance")
        st.markdown("<p class='section-note'>Explore search, engagement, and revenue metrics side by side.</p>", unsafe_allow_html=True)
        page_view = pages[["page_url", "clicks", "impressions", "ctr", "position", "sessions_current", "key_events_current", "revenue_current", "revenue_previous", "revenue_change_pct"]].copy()
        page_view["ctr"] = page_view["ctr"].map(lambda value: f"{value:.1%}")
        page_view["revenue_change_pct"] = page_view["revenue_change_pct"].map(lambda value: f"{value:.1%}" if pd.notna(value) else "")
        page_view = page_view.rename(columns={"page_url":"Landing page", "clicks":"Clicks", "impressions":"Impressions", "ctr":"CTR", "position":"Avg. position", "sessions_current":"Organic sessions", "key_events_current":"Key events", "revenue_current":"Revenue (current)", "revenue_previous":"Revenue (previous)", "revenue_change_pct":"Revenue change"})
        st.dataframe(page_view, width="stretch", hide_index=True, height=520)
    with guide_tab:
        st.subheader("How to read this dashboard")
        st.markdown("""
        **Low click-through rate** compares each page with the median CTR of pages in the same average-position band. A potential click gap is an estimate, not a forecast.

        **Revenue decline** highlights landing pages with at least a 20% decline against the uploaded comparison period. Use equal-length periods.

        **Query-to-page relevance review** finds high-impression queries with little word overlap against the page title and URL. It is a prompt for human review, not a semantic relevance score.

        **Data handling:** page records join by landing-page path. Confirm that the Search Console property and GA4 property, currency, channel, date range, and attribution settings match. The demo uses fictional values. Uploads are processed by this local app; there is no direct Google account connection.
        """)
    st.markdown("<div style='height:1rem'></div><div style='border-top:1px solid #e3eaf0;padding-top:.8rem;color:#71818d;font-size:.78rem'>Organic Search Opportunity Engine&nbsp;&nbsp;·&nbsp;&nbsp;Analysis workspace</div>", unsafe_allow_html=True)
