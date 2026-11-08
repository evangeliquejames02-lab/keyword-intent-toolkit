import pandas as pd

from seo_opportunity_engine.data import build_page_summary, load_analytics, load_search_console
from seo_opportunity_engine.opportunities import build_opportunities


def test_exports_join_by_path_and_filter_organic_channel():
    gsc = load_search_console(pd.DataFrame({
        "Page": ["https://shop.test/products/shoe/"], "Query": ["buy running shoe"],
        "Clicks": [10], "Impressions": [200], "Position": [5],
    }))
    analytics = load_analytics(pd.DataFrame({
        "Landing page": ["/products/shoe"], "Default channel group": ["Organic Search"],
        "Sessions": [100], "Key events": [7], "Revenue": [250],
    }))
    pages = build_page_summary(gsc, analytics)
    assert len(pages) == 1
    assert pages.iloc[0].revenue_current == 250
    assert pages.iloc[0].ctr == 0.05


def test_identifies_low_ctr_and_declining_revenue():
    gsc = load_search_console(pd.DataFrame({
        "Page": ["https://shop.test/guides/shoes", "https://shop.test/guides/shoes", "https://shop.test/products/boots"],
        "Query": ["running shoe guide", "shoe sizing guide", "best hiking boots"], "Clicks": [10, 80, 500],
        "Impressions": [1000, 1000, 1000], "Position": [5, 5, 5],
    }))
    current = load_analytics(pd.DataFrame({"Landing page": ["/guides/shoes"], "Revenue": [60]}))
    previous = load_analytics(pd.DataFrame({"Landing page": ["/guides/shoes"], "Revenue": [100]}))
    pages = build_page_summary(gsc, current, previous)
    opportunities = build_opportunities(gsc, pages, 100)
    assert "Revenue decline" in opportunities["type"].tolist()
    assert "Low click-through rate" in opportunities["type"].tolist()


def test_bad_headers_raise_helpful_validation_error():
    import pytest
    from seo_opportunity_engine.data import DataValidationError

    with pytest.raises(DataValidationError, match="page URL"):
        load_search_console(pd.DataFrame({"term": ["shoes"]}))
