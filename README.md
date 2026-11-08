# Organic Search-to-Revenue Opportunity Engine

A local dashboard that combines Google Search Console query/page exports with Google Analytics 4 landing-page data to help prioritize organic search work. It also includes a reusable keyword cleaning and intent-classification CLI.

## Try the dashboard

The dashboard opens with fictional sample data, so it can be explored without Google credentials or API keys.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e .
streamlit run app.py
```

Open the local address Streamlit prints (usually `http://localhost:8501`). Choose **Interactive demo** to inspect the sample opportunity queue, charts, and downloadable CSV.

## Publish a live demo

The repository includes Streamlit Cloud dependency and theme settings. To create a shareable app link, sign in at [Streamlit Community Cloud](https://share.streamlit.io/), connect your GitHub account, choose this repository and the `main` branch, and set the app file to `app.py`. Deploy with the default settings. The interactive demo uses fictional sample data and needs no secrets.

Share the resulting Streamlit app URL with an interviewer alongside the GitHub repository. The repository itself is public, but its GitHub page does not host the interactive dashboard.

## Use your own exports

In the sidebar, choose **Upload CSV exports** and upload:

1. Search Console data exported with **Page** and **Query** dimensions and **Clicks**, **Impressions**, and optionally **Position** metrics.
2. A GA4 current-period landing-page export with **Sessions**, **Key events**, and/or **Total revenue**. If the export includes a channel dimension, rows are limited to **Organic Search**.
3. Optionally, a matching GA4 prior-period export to identify revenue declines. Use equal-length date ranges and consistent property, currency, channel, and attribution settings.

Common Search Console and GA4 column names are recognized. Page URLs are joined by path, so confirm that both exports describe the same site and that any subdomain/path differences are accounted for. A missing metric is treated as zero. Exports should be CSV files.

## Opportunity signals

- **Low click-through rate:** pages above the impression threshold with CTR below 70% of the uploaded site's median CTR for the same average-position band. The click gap is an estimate, not a forecast.
- **Revenue decline:** pages with a revenue decrease of at least 20% against the uploaded prior period.
- **Query-to-page relevance review:** high-impression queries with little word overlap against a matching page title and URL. This is a review prompt, not a semantic relevance judgment.

The dashboard does not connect directly to Google accounts. Download CSV exports from Search Console and GA4, then upload them locally. Google APIs can be added later with OAuth and the appropriate account permissions.

## Keyword CLI

The command-line tool cleans CSV/Excel keyword lists, applies explainable intent rules, and filters results by volume, intent, or excluded words.

```bash
keyword-tool examples/sample_keywords.csv --min-volume 100
```

Output files are written to `output/`. For optional Claude classification, install `python -m pip install -e ".[claude]"` and set `ANTHROPIC_API_KEY` in your shell. API classification is optional; rule-based classification works offline.

## Development

```bash
python -m pip install -e ".[dev]"
pytest
```

## Project layout

```text
app.py                         Streamlit dashboard entry point
src/seo_opportunity_engine/    export preparation and opportunity signals
src/keyword_toolkit/           keyword cleaning, intent rules, and CLI
sample_data/                   fictional demo exports
tests/                         automated checks
```

## Data and privacy

Demo values are fictional. Uploaded files are read by the local app process and are not sent to a third-party service by this dashboard. Optional Claude classification in the separate CLI sends keyword text to Anthropic when explicitly enabled. Do not commit private exports, API keys, or credentials.
