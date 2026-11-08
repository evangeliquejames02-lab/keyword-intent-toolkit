from __future__ import annotations

import re

import numpy as np
import pandas as pd


def _terms(value: object) -> set[str]:
    words = re.findall(r"[a-z0-9]+", str(value).casefold())
    stop = {"the", "and", "for", "with", "from", "how", "what", "best", "to", "in", "of", "a", "an"}
    return {word for word in words if len(word) > 2 and word not in stop}


def build_opportunities(search_console: pd.DataFrame, pages: pd.DataFrame, min_impressions: int = 100) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    positioned = pages.dropna(subset=["position"])
    if not positioned.empty:
        positioned = positioned.copy()
        positioned["position_band"] = pd.cut(
            positioned["position"], [0, 3, 10, 20, np.inf], labels=["1–3", "4–10", "11–20", "21+"]
        )
        benchmarks = positioned.groupby("position_band", observed=True)["ctr"].agg(["median", "count"]).to_dict("index")
        for page in positioned.itertuples(index=False):
            cohort = benchmarks.get(page.position_band, {})
            benchmark = cohort.get("median")
            if cohort.get("count", 0) >= 2 and page.impressions >= min_impressions and benchmark and page.ctr < benchmark * 0.7:
                rows.append({
                    "type": "Low click-through rate", "priority": "High" if page.impressions >= min_impressions * 5 else "Medium",
                    "page": page.page_url, "query": "", "detail": f"CTR {page.ctr:.1%}; median for position {page.position_band}: {benchmark:.1%}",
                    "estimated_click_gap": round(max(0, (benchmark - page.ctr) * page.impressions)),
                    "revenue_change_pct": np.nan,
                })

    for page in pages.itertuples(index=False):
        change = getattr(page, "revenue_change_pct", np.nan)
        if pd.notna(change) and change <= -0.2 and getattr(page, "revenue_previous", 0) > 0:
            rows.append({
                "type": "Revenue decline", "priority": "High" if change <= -0.4 else "Medium",
                "page": page.page_url, "query": "", "detail": f"Organic revenue changed {change:.1%} vs. previous period",
                "estimated_click_gap": np.nan, "revenue_change_pct": change,
            })

    if not search_console.empty:
        pages_lookup = pages.set_index("page_key", drop=False)
        for item in search_console.itertuples(index=False):
            if item.impressions < min_impressions:
                continue
            match = pages_lookup.loc[item.page_key] if item.page_key in pages_lookup.index else None
            if isinstance(match, pd.DataFrame):
                match = match.iloc[0]
            title = match["page_title"] if match is not None else item.page_url
            query_terms = _terms(item.query)
            target_terms = _terms(f"{title} {item.page_url}")
            overlap = len(query_terms & target_terms) / len(query_terms) if query_terms else 1
            if overlap < 0.25:
                rows.append({
                    "type": "Query-to-page relevance review", "priority": "High" if item.impressions >= min_impressions * 5 else "Medium",
                    "page": item.page_url, "query": item.query,
                    "detail": f"{item.impressions:,.0f} impressions; limited query/title/URL word overlap ({overlap:.0%})",
                    "estimated_click_gap": np.nan, "revenue_change_pct": np.nan,
                })

    columns = ["type", "priority", "page", "query", "detail", "estimated_click_gap", "revenue_change_pct"]
    result = pd.DataFrame(rows, columns=columns)
    if not result.empty:
        result["_rank"] = result["priority"].map({"High": 0, "Medium": 1, "Low": 2})
        result = result.sort_values(["_rank", "estimated_click_gap"], ascending=[True, False], na_position="last").drop(columns="_rank")
    return result.reset_index(drop=True)
