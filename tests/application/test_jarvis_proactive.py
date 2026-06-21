from __future__ import annotations

from unittest.mock import MagicMock

from app.modules.ai_agent.services.jarvis_proactive_service import JarvisProactiveService


def test_scan_finds_elastic_mover() -> None:
    watchlist = MagicMock()
    watchlist.list_symbols.return_value = ["600519"]
    market = MagicMock()
    market.list_quotes.return_value = [
        {"symbol": "sh600519", "name": "贵州茅台", "change_pct": 6.2, "price": 1800},
    ]
    knowledge = MagicMock()
    knowledge.get_profile.return_value = {
        "factor_attention": {"momentum": 3, "高弹性": 2},
        "interaction_events": [],
        "decision_patterns": [],
    }
    svc = JarvisProactiveService(
        watchlist_service=watchlist,
        market_service=market,
        user_knowledge_service=knowledge,
    )
    out = svc.scan(user_id=1)
    assert out["ok"] is True
    assert len(out["signals"]) == 1
    assert out["signals"][0]["jarvis_command"]
