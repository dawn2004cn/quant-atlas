"""Regression: market panorama must not use inline onclick (blocked by CSP script-src nonce)."""

from __future__ import annotations

from pathlib import Path

TEMPLATE = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "presentation"
    / "web"
    / "templates"
    / "market_panorama.html"
)


SELF_STOCKS = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "presentation"
    / "web"
    / "templates"
    / "self_stocks.html"
)


def test_market_panorama_avoids_inline_onclick_handlers() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "onclick=" not in text, "use delegated listeners instead of inline onclick"
    assert 'data-page="' in text
    assert "addEventListener('click'" in text or 'addEventListener("click"' in text


def test_market_panorama_quotes_fetch_times_out_and_retries() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "AbortController" in text
    assert "schedulePanoRetry" in text
    assert "后台同步中" in text


def test_self_stocks_avoids_inline_onclick_handlers() -> None:
    text = SELF_STOCKS.read_text(encoding="utf-8")
    assert "onclick=" not in text
    assert 'data-watch-action="shadow-details"' in text
    assert "bindWatchPageActions" in text
