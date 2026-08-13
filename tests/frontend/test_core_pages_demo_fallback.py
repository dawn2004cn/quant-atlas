"""Core SPA pages must fall back to labeled demo rows when live lists are empty."""

from __future__ import annotations

from pathlib import Path

FE = Path(__file__).resolve().parents[2] / "frontend" / "src"


def test_demo_catalog_exports_core_lists() -> None:
    text = (FE / "lib" / "demoCatalog.ts").read_text(encoding="utf-8")
    for token in ("DEMO_STOCKS", "DEMO_SECTORS", "DEMO_PORTFOLIO", "DEMO_SELECTOR", "DEMO_PANORAMA_ROWS"):
        assert token in text, token
    assert "600519" in text


def test_core_pages_use_demo_fallback() -> None:
    pages = (
        "SelfStocks.tsx",
        "HotSectors.tsx",
        "Portfolio.tsx",
        "StockSelector.tsx",
        "MarketPanorama.tsx",
    )
    for name in pages:
        text = (FE / "pages" / name).read_text(encoding="utf-8")
        assert "DemoBanner" in text, name
        assert "demoCatalog" in text or "DEMO_" in text, name
        assert "window.location" not in text, name
