from __future__ import annotations

from unittest.mock import MagicMock

from app.modules.strategy.services.analytics.smart_briefing_service import SmartDailyBriefingService
from app.domain.enums import MarketCode


def test_generate_briefing_attaches_narrative() -> None:
    strategy = MagicMock()
    strategy.select_stocks.return_value = {
        "ok": True,
        "candidates": [
            {
                "symbol": "sz000001",
                "name": "平安银行",
                "change_pct": -4.2,
                "rsi": 28,
                "volume_ratio": 1.8,
            }
        ],
        "effective_strategy_group": "reversal",
        "sentiment_analysis": {"market_regime": "sideways", "recommended_categories": ["reversal"]},
    }
    narrative = MagicMock()
    narrative.synthesize_daily_briefing.return_value = {
        "mode": "template",
        "opening": "早安，个性化简报",
        "personalized_closing": "关注反转机会",
        "recommendation_narratives": [
            {"symbol": "sz000001", "narrative": "检测到与您历史抄底模式相似的背离信号。"}
        ],
    }
    svc = SmartDailyBriefingService(
        strategy,
        narrative_synthesis_service=narrative,
        user_knowledge_service=MagicMock(),
    )
    out = svc.generate_briefing(MarketCode.CN, top_n=1, user_id=42, use_narrative=True)
    assert out["ok"] is True
    assert out["narrative_mode"] == "template"
    assert out["recommendations"][0].get("narrative")
    narrative.synthesize_daily_briefing.assert_called_once()
