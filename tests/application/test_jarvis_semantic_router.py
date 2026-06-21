from __future__ import annotations

from unittest.mock import MagicMock

from app.modules.ai_agent.services.jarvis_semantic_router_service import JarvisSemanticRouterService


def test_voice_briefing_intent() -> None:
    svc = JarvisSemanticRouterService()
    out = svc.route(1, "播放晨间语音简报")
    assert out.input_snapshot["ok"] is True
    assert out.input_snapshot["intent"] == "voice_briefing"
    assert out.input_snapshot["url"] == "/voice-briefing"
    assert out.decision_id.startswith("jarvis_")


def test_winning_pattern_match() -> None:
    knowledge = MagicMock()
    knowledge.get_profile.return_value = {
        "decision_patterns": [
            {
                "outcome": "win",
                "sectors": ["auto", "科技"],
                "factors": ["reversal"],
                "symbols": ["sz000625"],
            },
            {"outcome": "loss", "sectors": ["bank"], "factors": [], "symbols": []},
        ],
    }
    strategy = MagicMock()
    strategy.select_stocks.return_value = {
        "ok": True,
        "candidates": [
            {"symbol": "sz000625", "name": "长安汽车", "sector": "auto", "strategy": "reversal"},
            {"symbol": "sz000001", "name": "平安银行", "sector": "bank"},
        ],
    }
    svc = JarvisSemanticRouterService(
        user_knowledge_service=knowledge,
        strategy_service=strategy,
    )
    out = svc.route(42, "帮我找找符合我去年赚钱风格的票")
    assert out.input_snapshot["ok"] is True
    assert out.input_snapshot["intent"] == "pattern_stock_pick"
    assert out.input_snapshot["candidates"]
    assert out.input_snapshot["candidates"][0]["symbol"] == "sz000625"
    assert "winning_style" in out.input_snapshot["url"]
    assert out.decision_id.startswith("jarvis_")


def test_match_winning_patterns_summary() -> None:
    knowledge = MagicMock()
    knowledge.get_profile.return_value = {
        "decision_patterns": [
            {"outcome": "profit", "sectors": ["消费"], "factors": ["momentum"], "symbols": ["sz000001"]},
        ],
    }
    svc = JarvisSemanticRouterService(user_knowledge_service=knowledge)
    ctx = svc.match_winning_patterns(1)
    assert ctx.input_snapshot["ok"] is True
    assert ctx.input_snapshot["pattern_count"] == 1
    assert "消费" in ctx.input_snapshot["top_sectors"]
    assert ctx.decision_id.startswith("jarvis_")
