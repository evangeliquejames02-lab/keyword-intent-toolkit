from __future__ import annotations

import re
from urllib.parse import unquote, urlsplit

import numpy as np
import pandas as pd

from keyword_toolkit.pipeline import INTENTS, rule_intent


class DataValidationError(ValueError):
    pass


def normalize_header(value: object) -> str:
    text = str(value).strip().lower()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def normalize_page_url(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if not text:
        return ""
    parsed = urlsplit(text if "://" in text else f"https://placeholder.local/{text.lstrip('/')}")
    path = unquote(parsed.path or "/")
    path = re.sub(r"/{2,}", "/", path)
    if path != "/":
        path = path.rstrip("/")
    return path.casefold()


def _columns(frame: pd.DataFrame) -> dict[str, str]:
    return {normalize_header(column): str(column) for column in frame.columns}


def _find_column(columns: dict[str, str], choices: tuple[str, ...], label: str, required: bool = True) -> str | None:
    for choice in choices:
        if choice in columns:
            return columns[choice]
    if required:
        names = ", ".join(choices[:4])
        raise DataValidationError(f"Could not find the {label} column. Expected a heading such as {names}.")
    return None


def _numeric(series: pd.Series | None, index: pd.Index) -> pd.Series:
    if series is None:
        return pd.Series(0.0, index=index, dtype="float64")
    values = series.astype("string").str.replace(",", "", regex=False).str.replace("%", "", regex=False)
    return pd.to_numeric(values, errors="coerce").fillna(0).astype("float64")


def load_search_console(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        raise DataValidationError("The Search Console file has no rows.")
    columns = _columns(frame)
    page_col = _find_column(columns, ("page", "top_pages", "page_url", "url", "landing_page"), "page URL")
    query_col = _find_column(columns, ("query", "top_queries", "search_query"), "query")
    clicks_col = _find_column(columns, ("clicks",), "clicks")
    impressions_col = _find_column(columns, ("impressions",), "impressions")
    position_col = _find_column(columns, ("position", "average_position", "avg_position"), "average position", required=False)
    title_col = _find_column(columns, ("page_title", "title", "page_name"), "page title", required=False)

    raw = pd.DataFrame(index=frame.index)
    raw["page_url"] = frame[page_col].astype("string").str.strip()
    raw["page_key"] = raw["page_url"].map(normalize_page_url)
    raw["query"] = frame[query_col].astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
    raw["page_title"] = frame[title_col].astype("string").str.strip() if title_col else ""
    raw["clicks"] = _numeric(frame[clicks_col], frame.index)
    raw["impressions"] = _numeric(frame[impressions_col], frame.index)
    raw["position"] = _numeric(frame[position_col], frame.index) if position_col else np.nan
    raw = raw.dropna(subset=["query", "page_url"])
    raw = raw[(raw["query"].str.len() > 0) & (raw["page_key"].str.len() > 0)]
    if raw.empty:
        raise DataValidationError("No rows with both a page URL and query were found.")

    raw["weighted_position"] = raw["position"] * raw["impressions"]
    raw["position_weight"] = raw["impressions"].where(raw["position"].notna(), 0)
    result = (raw.groupby(["page_key", "query"], as_index=False, dropna=False)
              .agg(page_url=("page_url", "first"), page_title=("page_title", "first"),
                   clicks=("clicks", "sum"), impressions=("impressions", "sum"),
                   weighted_position=("weighted_position", "sum"), position_weight=("position_weight", "sum")))
    result["position"] = result["weighted_position"].div(result["position_weight"].replace(0, np.nan))
    result["ctr"] = result["clicks"].div(result["impressions"].replace(0, np.nan)).fillna(0)
    result["intent"] = result["query"].map(lambda query: rule_intent(query)[0])
    return result.drop(columns=["weighted_position", "position_weight"])


def load_analytics(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        raise DataValidationError("The Analytics file has no rows.")
    columns = _columns(frame)
    page_col = _find_column(
        columns,
        ("landing_page_plus_query_string", "landing_page_and_query_string", "landing_page", "landing_page_path", "page_path_plus_query_string", "page_location"),
        "landing page",
    )
    sessions_col = _find_column(columns, ("sessions",), "sessions", required=False)
    events_col = _find_column(columns, ("key_events", "conversions", "event_count"), "key events", required=False)
    revenue_col = _find_column(columns, ("total_revenue", "purchase_revenue", "revenue"), "revenue", required=False)
    title_col = _find_column(columns, ("page_title", "title", "page_name"), "page title", required=False)
    channel_col = _find_column(
        columns,
        ("session_default_channel_group", "default_channel_group", "session_channel_group", "channel"),
        "channel group",
        required=False,
    )

    source = frame.copy()
    if channel_col:
        organic = source[channel_col].astype("string").str.casefold().str.contains("organic search", na=False)
        source = source.loc[organic].copy()
        if source.empty:
            raise DataValidationError("No Organic Search rows were found. Upload a GA4 export filtered to Organic Search.")

    result = pd.DataFrame(index=source.index)
    result["page_url"] = source[page_col].astype("string").str.strip()
    result["page_key"] = result["page_url"].map(normalize_page_url)
    result["page_title"] = source[title_col].astype("string").str.strip() if title_col else ""
    result["sessions"] = _numeric(source[sessions_col], source.index) if sessions_col else 0.0
    result["key_events"] = _numeric(source[events_col], source.index) if events_col else 0.0
    result["revenue"] = _numeric(source[revenue_col], source.index) if revenue_col else 0.0
    result = result.dropna(subset=["page_url"])
    result = result[result["page_key"].str.len() > 0]
    if result.empty:
        raise DataValidationError("No valid landing pages were found in the Analytics file.")
    return (result.groupby("page_key", as_index=False, dropna=False)
            .agg(page_url=("page_url", "first"), page_title=("page_title", "first"),
                 sessions=("sessions", "sum"), key_events=("key_events", "sum"), revenue=("revenue", "sum")))


def build_page_summary(
    search_console: pd.DataFrame,
    analytics_current: pd.DataFrame,
    analytics_previous: pd.DataFrame | None = None,
) -> pd.DataFrame:
    pages = (search_console.groupby("page_key", as_index=False, dropna=False)
             .agg(page_url=("page_url", "first"), page_title=("page_title", "first"),
                  clicks=("clicks", "sum"), impressions=("impressions", "sum")))
    position_rows = search_console.assign(
        weighted_position=search_console["position"] * search_console["impressions"],
        position_weight=search_console["impressions"].where(search_console["position"].notna(), 0),
    )
    positions = position_rows.groupby("page_key").agg(
        weighted_position=("weighted_position", "sum"), position_weight=("position_weight", "sum")
    )
    pages = pages.merge(positions, on="page_key", how="left")
    pages["position"] = pages["weighted_position"].div(pages["position_weight"].replace(0, np.nan))
    pages = pages.drop(columns=["weighted_position", "position_weight"])
    pages["ctr"] = pages["clicks"].div(pages["impressions"].replace(0, np.nan)).fillna(0)

    current = analytics_current.rename(columns={
        "sessions": "sessions_current", "key_events": "key_events_current", "revenue": "revenue_current",
        "page_url": "analytics_page_url", "page_title": "analytics_page_title",
    })
    pages = pages.merge(current, on="page_key", how="outer")
    if analytics_previous is not None:
        previous = analytics_previous.rename(columns={
            "sessions": "sessions_previous", "key_events": "key_events_previous", "revenue": "revenue_previous",
            "page_url": "previous_page_url", "page_title": "previous_page_title",
        })
        pages = pages.merge(previous[["page_key", "sessions_previous", "key_events_previous", "revenue_previous"]],
                            on="page_key", how="outer")
    else:
        pages["sessions_previous"] = np.nan
        pages["key_events_previous"] = np.nan
        pages["revenue_previous"] = np.nan

    pages["page_url"] = pages["page_url"].fillna(pages["analytics_page_url"])
    pages["page_title"] = pages["page_title"].fillna(pages["analytics_page_title"])
    if "previous_page_url" in pages:
        pages["page_url"] = pages["page_url"].fillna(pages["previous_page_url"])
        pages["page_title"] = pages["page_title"].fillna(pages["previous_page_title"])
    for column in ("clicks", "impressions", "sessions_current", "key_events_current", "revenue_current"):
        pages[column] = pages[column].fillna(0)
    pages["revenue_change_pct"] = np.where(
        pages["revenue_previous"].gt(0),
        (pages["revenue_current"] - pages["revenue_previous"]) / pages["revenue_previous"],
        np.nan,
    )
    return pages.sort_values("impressions", ascending=False, na_position="last").reset_index(drop=True)
