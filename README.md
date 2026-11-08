# Keyword Intent Toolkit

A small Python CLI that turns a keyword export into clean, deduplicated, intent-labeled files and a volume summary. It supports CSV and Excel input, practical volume and intent filters, exclusion terms, and optional Claude-based classification.

## What it does

- Normalizes keyword text and common input column names; removes blank rows and duplicate keywords.
- Reads search volume when present and safely treats missing or invalid values as zero.
- Labels intent with a fast, explainable rules baseline, or optionally sends batches to Claude.
- Filters by volume range, intent, and unwanted words; writes classified, filtered, and summary CSV files.

The rule-based confidence values are rough indicators, not measured model accuracy. Claude output is also not guaranteed to be 99% accurate: evaluate it against a manually labeled sample before making performance claims. API use can incur provider charges and sends keyword text to Anthropic.

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

## CV wording

Keep claims tied to what you have actually built and measured. A defensible starting point:

> Built a Python keyword research pipeline with Pandas and NumPy to clean, deduplicate, classify, and filter search queries by intent and volume; added optional Claude API classification and CSV reporting.

After benchmarking on a labeled dataset, you can add measured accuracy and time savings with the sample size and evaluation method.

## License

Add a license before public reuse (for example, MIT if that matches your intent).
