import pandas as pd
import pytest

from keyword_toolkit.pipeline import classify_keywords, filter_keywords, load_keywords, rule_intent, summarize


def test_load_keywords_normalizes_and_deduplicates(tmp_path):
    source = tmp_path / "keywords.csv"
    source.write_text(
        "Query,Search Volume\n  How  to bake bread , 100\nhow to bake bread,250\nBuy bread,20\n",
        encoding="utf-8",
    )

    result = load_keywords(source)

    assert result.to_dict("records") == [
        {"keyword": "how to bake bread", "volume": 100},
        {"keyword": "buy bread", "volume": 20},
    ]


@pytest.mark.parametrize(
    ("keyword", "expected"),
    [
        ("how to repair a bike", "informational"),
        ("best road bikes", "commercial"),
        ("buy a road bike", "transactional"),
        ("brand homepage", "unknown"),
    ],
)
def test_rule_intent(keyword, expected):
    assert rule_intent(keyword)[0] == expected


def test_filter_by_volume_intent_and_exclusions():
    data = pd.DataFrame(
        {
            "keyword": ["how to run", "buy shoes", "best shoes", "free shoes"],
            "volume": [300, 500, 100, 50],
        }
    )

    classified = classify_keywords(data)
    result = filter_keywords(
        classified,
        min_volume=100,
        intents=["transactional", "commercial"],
        exclude_terms=["free"],
    )

    assert result["keyword"].tolist() == ["buy shoes", "best shoes"]


def test_summary_groups_keyword_counts_and_volumes():
    data = classify_keywords(
        pd.DataFrame({"keyword": ["how to run", "buy shoes"], "volume": [300, 500]})
    )

    result = summarize(data).set_index("intent")

    assert result.loc["informational", "keywords"] == 1
    assert result.loc["transactional", "total_volume"] == 500


def test_invalid_volume_bounds_raise_error():
    data = pd.DataFrame(columns=["keyword", "volume", "intent"])

    with pytest.raises(ValueError):
        filter_keywords(data, min_volume=10, max_volume=1)
