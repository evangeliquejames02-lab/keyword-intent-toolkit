"""Command line entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from .pipeline import DEFAULT_NOISE, classify_keywords, filter_keywords, load_keywords, summarize


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean and classify a keyword research export.")
    parser.add_argument("input", help="Input CSV or Excel file")
    parser.add_argument("--output", default="output", help="Output directory (default: output)")
    parser.add_argument("--min-volume", type=int, default=0)
    parser.add_argument("--max-volume", type=int)
    parser.add_argument("--intent", nargs="+", choices=["informational", "commercial", "transactional", "navigational", "unknown"])
    parser.add_argument("--exclude", nargs="*", default=sorted(DEFAULT_NOISE), help="Terms to exclude")
    parser.add_argument("--llm", action="store_true", help="Use optional Claude API for intent classification")
    args = parser.parse_args()

    data = load_keywords(args.input)
    classified = classify_keywords(data, use_llm=args.llm)
    filtered = filter_keywords(classified, args.min_volume, args.max_volume, args.intent, args.exclude)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    classified.to_csv(output / "classified_keywords.csv", index=False)
    filtered.to_csv(output / "filtered_keywords.csv", index=False)
    summarize(classified).to_csv(output / "intent_summary.csv", index=False)
    print(f"Processed {len(data):,} unique keywords; retained {len(filtered):,}. Results: {output.resolve()}")


if __name__ == "__main__":
    main()
