"""Tests for page shell CSS preload hints."""

from app.core.page_shell import page_css_preload_for_endpoint


def test_page_css_preload_known_endpoint() -> None:
    assert page_css_preload_for_endpoint("pages.backtest") == "css/pages/strategy.css"


def test_page_css_preload_data_lake() -> None:
    assert page_css_preload_for_endpoint("pages.data_lake_health") == "css/pages/data-lake.css"


def test_page_css_preload_truth_droplet() -> None:
    assert page_css_preload_for_endpoint("truth_droplet.truth_droplet_page") == "css/pages/truth.css"


def test_page_css_preload_unknown_endpoint() -> None:
    assert page_css_preload_for_endpoint("pages.unknown") is None
    assert page_css_preload_for_endpoint(None) is None
