from __future__ import annotations

from unittest.mock import MagicMock

from app.modules.strategy.services.strategy.strategy_copilot_service import (
    StrategyCoPilotService,
)
from app.domain.enums import MarketCode


def test_handover_eligible_when_shadow_beats_active() -> None:
    use_case = MagicMock()
    use_case.execute.return_value = {
        "recommendations": [
            {"strategy": "momentum", "score": 0.9, "reason": "上升趋势"},
            {"strategy": "grid_trading", "score": 0.7, "reason": "高波动"},
        ],
        "trend": "uptrend",
        "volatility": 3.0,
        "regime": "medium_volatility_bullish",
    }
    arbiter = MagicMock()
    arbiter.synthesize.return_value = {
        "ok": True,
        "verdict": "bullish",
        "confidence": 0.85,
        "provenance_id": "prov-test",
    }
    stock = MagicMock()
    stock.get_history.return_value = [
        {"close": 10.0},
        {"close": 10.2},
        {"close": 10.8},
        {"close": 11.2},
    ]
    svc = StrategyCoPilotService(
        copilot_use_case=use_case,
        debate_arbiter_service=arbiter,
        stock_service=stock,
    )
    svc.set_active_strategy("600519", "mean_reversion", "CN")
    out = svc.evaluate("600519", MarketCode.CN)
    assert out["ok"] is True
    handover = out.get("handover") or {}
    assert handover.get("eligible") is True
    assert handover.get("to_strategy")
