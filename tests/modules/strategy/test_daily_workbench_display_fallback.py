"""Empty market sources still yield a displayable workbench snapshot."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[3]


def _load_fallback():
    path = ROOT / "app/modules/strategy/services/analytics/workbench_display_fallback.py"
    spec = importlib.util.spec_from_file_location("workbench_display_fallback", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_apply_display_fallback_fills_empty_payload() -> None:
    mod = _load_fallback()
    snap = mod.apply_display_fallback(
        {
            "watchlist_health": {"items": []},
            "macro_indices": [],
            "market_panorama": {"up": 0, "down": 0, "flat": 0},
            "headlines": [],
            "recommendations_preview": {"items": []},
        },
        "CN",
    )
    assert snap["data_mode"] == "demo"
    assert len(snap["watchlist_health"]["items"]) >= 3
    assert len(snap["macro_indices"]) >= 3
    assert int(snap["market_panorama"]["up"]) + int(snap["market_panorama"]["down"]) > 0
    assert snap["headlines"]
    assert snap["recommendations_preview"]["items"]


def test_apply_display_fallback_keeps_live_watchlist() -> None:
    mod = _load_fallback()
    snap = mod.apply_display_fallback(
        {
            "watchlist_health": {
                "items": [{"code": "600519", "name": "贵州茅台", "price": 1700, "change_pct": 1.2}]
            },
            "macro_indices": [{"label": "上证指数", "code": "SH000001", "price": 3200, "change_pct": 0.4}],
            "market_panorama": {"up": 1200, "down": 800, "flat": 300, "total": 2300},
            "headlines": [{"title": "live"}],
            "recommendations_preview": {"items": [{"code": "600519"}]},
        },
        "CN",
    )
    assert snap["data_mode"] == "live"
    assert snap["watchlist_health"]["items"][0]["code"] == "600519"


def test_workbench_empty_sources_still_has_display_rows() -> None:
    pytest.importorskip("pydantic")
    from app.domain.enums import MarketCode
    from app.modules.strategy.services.analytics.daily_workbench_service import DailyWorkbenchService

    market = MagicMock()
    market.get_panorama.side_effect = RuntimeError("unavailable")
    market.get_sentiment.side_effect = RuntimeError("unavailable")
    market.list_quotes.return_value = []
    watchlist = MagicMock()
    watchlist.list_symbols.return_value = []

    svc = DailyWorkbenchService(market_service=market, watchlist_service=watchlist)
    snap = svc.build_snapshot(1, market=MarketCode.CN)

    assert snap["data_mode"] == "demo"
    assert len(snap["watchlist_health"]["items"]) >= 3
    assert len(snap["macro_indices"]) >= 3
    breadth = snap["market_panorama"]
    assert int(breadth.get("up") or 0) + int(breadth.get("down") or 0) > 0
    assert snap["headlines"]
    rec_items = (snap.get("recommendations_preview") or {}).get("items") or []
    assert rec_items


def test_workbench_live_quotes_are_not_replaced_by_demo() -> None:
    pytest.importorskip("pydantic")
    from app.domain.enums import MarketCode
    from app.modules.strategy.services.analytics.daily_workbench_service import DailyWorkbenchService

    market = MagicMock()
    market.get_panorama.return_value = {"up": 1200, "down": 800, "flat": 300, "total": 2300}
    market.get_sentiment.return_value = {
        "score": 58,
        "level": "中性",
        "stats": {"gainers": 1200, "losers": 800, "neutral": 300, "total": 2300},
    }
    market.list_quotes.return_value = [
        {"code": "600519", "name": "贵州茅台", "price": 1700, "change_pct": 1.2}
    ]
    watchlist = MagicMock()
    watchlist.list_symbols.return_value = ["600519"]

    svc = DailyWorkbenchService(market_service=market, watchlist_service=watchlist)
    snap = svc.build_snapshot(1, market=MarketCode.CN)

    codes = [str(item.get("code")) for item in snap["watchlist_health"]["items"]]
    assert "600519" in codes
    assert snap["data_mode"] in ("live", "mixed")
