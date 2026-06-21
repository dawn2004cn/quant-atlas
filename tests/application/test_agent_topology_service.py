from __future__ import annotations

from unittest.mock import MagicMock

from app.application.services.orchestration.agent_topology_service import AgentTopologyService


def test_trending_regime_boosts_technical_weight() -> None:
    stock = MagicMock()
    closes = [100 + i * 1.5 for i in range(25)]
    stock.get_history.return_value = [{"close": c, "date": f"2026-05-{i+1:02d}"} for i, c in enumerate(closes)]

    svc = AgentTopologyService(stock_service=stock)
    regime = svc._infer_regime("600519", "CN")
    weights = svc._adjust_weights(regime, {"alpha": 0.5})
    assert regime in ("trending", "mixed", "ranging", "unknown")
    assert weights["technical_analyst"] >= 1.0
