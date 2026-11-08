# Keyword Intent Toolkit

A Python command-line tool for cleaning, classifying, and filtering keyword research exports. It reads CSV and Excel files and writes classified keywords, filtered results, and an intent summary.

## What it does

- Normalizes keyword text and common input column names; removes blank rows and duplicate keywords.
- Reads search volume when present and safely treats missing or invalid values as zero.
- Labels intent with a fast, explainable rules baseline, or optionally sends batches to Claude.
- Filters by volume range, intent, and unwanted words; writes classified, filtered, and summary CSV files.

Intent rules and confidence values are heuristic estimates. Review labels before using them in a campaign. Optional Claude classification sends keyword text to Anthropic and may incur API charges.

## Quick start

Requires Python 3.10 or later.

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e .
keyword-tool examples/sample_keywords.csv --min-volume 100
```

Results appear in `output/`:

- `classified_keywords.csv` — all cleaned keywords with intent labels.
- `filtered_keywords.csv` — rows after selected filters.
- `intent_summary.csv` — counts and volume totals by intent.

Example with custom filters:

```bash
keyword-tool keywords.csv --min-volume 200 --max-volume 10000 --intent commercial transactional --exclude free jobs
```

Input needs a column named `keyword`, `query`, `search_term`, or `term`. A volume column is optional; recognized names include `volume`, `search_volume`, and `monthly_searches`.

## Optional Claude classification

Install the extra and set your key in the environment (do not commit secrets):

```bash
python -m pip install -e ".[claude]"
# macOS/Linux
export ANTHROPIC_API_KEY="your-key"
# Windows PowerShell
$env:ANTHROPIC_API_KEY = "your-key"
keyword-tool keywords.csv --llm
```

The default model is Claude Haiku 4.5. You can set `ANTHROPIC_MODEL` to another model available to your account. Review labels before relying on them: model output can be wrong, and usage may incur provider charges.

## Development checks

```bash
python -m pip install -e ".[dev]"
pytest
```

## Project structure

```text
src/keyword_toolkit/   pipeline and CLI
examples/              small demo input
tests/                 focused behavior checks
```

