"""Data preparation and keyword intent classification."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

INTENTS = ("informational", "commercial", "transactional", "navigational", "unknown")
DEFAULT_NOISE = {"free", "torrent", "crack", "jobs", "salary", "pdf"}


def load_keywords(path: str | Path) -> pd.DataFrame:
    """Load CSV or Excel data and normalize common column names."""
    path = Path(path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    elif path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    else:
        raise ValueError("Input must be a .csv, .xlsx, or .xls file")
    if df.empty:
        raise ValueError("Input file has no rows")

    normalized = {str(c).strip().lower().replace(" ", "_"): c for c in df.columns}
    keyword_col = next((normalized[k] for k in ("keyword", "query", "search_term", "term") if k in normalized), None)
    if keyword_col is None:
        raise ValueError("Input needs a keyword column (e.g. keyword, query, or search_term)")
    volume_col = next((normalized[k] for k in ("volume", "search_volume", "monthly_searches") if k in normalized), None)
    result = pd.DataFrame({"keyword": df[keyword_col]})
    result["volume"] = pd.to_numeric(df[volume_col], errors="coerce") if volume_col else np.nan
    result["keyword"] = result["keyword"].astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
    result = result.dropna(subset=["keyword"])
    result = result[result["keyword"].str.len() > 0]
    result["keyword"] = result["keyword"].str.lower()
    result["volume"] = result["volume"].fillna(0).clip(lower=0).astype(int)
    result = result.drop_duplicates(subset=["keyword"], keep="first").reset_index(drop=True)
    return result


def rule_intent(keyword: str) -> tuple[str, float]:
    """Fast explainable baseline classifier; confidence is heuristic, not accuracy."""
    text = keyword.lower()
    groups = {
        "transactional": (r"\b(buy|order|purchase|discount|coupon|deal|price|pricing|book|hire|subscribe|near me)\b",),
        "commercial": (r"\b(best|top|review|reviews|vs|versus| 비교|alternative|alternatives|comparison|cheap)\b",),
        "informational": (r"\b(how|what|why|when|where|who|guide|tutorial|meaning|examples?|ideas?|tips?)\b",),
        "navigational": (r"\b(login|sign in|website|official site|contact|support)\b",),
    }
    for intent in ("transactional", "commercial", "informational", "navigational"):
        if any(re.search(pattern, text) for pattern in groups[intent]):
            return intent, 0.72
    return "unknown", 0.45


def classify_keywords(df: pd.DataFrame, use_llm: bool = False) -> pd.DataFrame:
    """Add intent and source columns. LLM classification is optional and batched."""
    result = df.copy()
    if not use_llm:
        labels = result["keyword"].map(rule_intent)
        result["intent"] = labels.map(lambda item: item[0])
        result["confidence"] = labels.map(lambda item: item[1])
        result["classification_source"] = "rules"
        return result

    import os
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise RuntimeError("Install the optional dependency with: pip install -e '.[claude]'") from exc
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("Set ANTHROPIC_API_KEY before using --llm")
    client = Anthropic()
    model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
    intents: list[str] = []
    confidences: list[float] = []
    sources: list[str] = []
    for start in range(0, len(result), 40):
        batch = result["keyword"].iloc[start:start + 40].tolist()
        numbered = "\n".join(f"{i + 1}. {kw}" for i, kw in enumerate(batch))
        response = client.messages.create(
            model=model,
            max_tokens=700,
            system=("Classify each search query by dominant intent: informational, commercial, "
                    "transactional, navigational, or unknown. Return exactly one label per line, in order."),
            messages=[{"role": "user", "content": numbered}],
        )
        raw_lines = response.content[0].text.splitlines()
        for index, keyword in enumerate(batch):
            raw = raw_lines[index].strip().lower() if index < len(raw_lines) else ""
            match = re.fullmatch(r"(?:\d+[.)]\s*)?(informational|commercial|transactional|navigational|unknown)[.! ]*", raw)
            if match:
                label = match.group(1)
                intents.append(label)
                confidences.append(0.45 if label == "unknown" else 0.80)
                sources.append("claude")
            else:
                label, confidence = rule_intent(keyword)
                intents.append(label)
                confidences.append(confidence)
                sources.append("rules-fallback")
    result["intent"] = intents
    result["confidence"] = confidences
    result["classification_source"] = sources
    return result


def filter_keywords(
    df: pd.DataFrame,
    min_volume: int = 0,
    max_volume: int | None = None,
    intents: Iterable[str] | None = None,
    exclude_terms: Iterable[str] = (),
) -> pd.DataFrame:
    """Filter by volume, selected intent, and excluded terms."""
    if min_volume < 0 or (max_volume is not None and max_volume < min_volume):
        raise ValueError("Volume bounds must be non-negative and max must be >= min")
    mask = df["volume"].ge(min_volume)
    if max_volume is not None:
        mask &= df["volume"].le(max_volume)
    if intents:
        chosen = {value.lower() for value in intents}
        invalid = chosen - set(INTENTS)
        if invalid:
            raise ValueError(f"Unknown intents: {', '.join(sorted(invalid))}")
        mask &= df["intent"].isin(chosen)
    terms = [term.strip().lower() for term in exclude_terms if term.strip()]
    if terms:
        pattern = "|".join(re.escape(term) for term in terms)
        mask &= ~df["keyword"].str.contains(pattern, regex=True, na=False)
    return df.loc[mask].copy().reset_index(drop=True)


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    """Return keyword counts and volume totals by intent."""
    return (df.groupby("intent", dropna=False)
            .agg(keywords=("keyword", "count"), total_volume=("volume", "sum"), mean_volume=("volume", "mean"))
            .reset_index().sort_values("total_volume", ascending=False))
