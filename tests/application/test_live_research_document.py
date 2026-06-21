from __future__ import annotations

from unittest.mock import MagicMock

from app.modules.system.services.ui.live_research_document_service import (
    LiveResearchDocumentService,
)
from app.domain.enums import MarketCode


def test_apply_lights_from_resonance_and_debate() -> None:
    svc = LiveResearchDocumentService()
    doc = {
        "traffic_lights": {
            "data_truth": {"color": "green", "label": "数据真值", "status": "verified", "detail": ""},
            "technical": {"color": "yellow", "label": "技术共振", "status": "", "detail": ""},
            "agent_debate": {"color": "yellow", "label": "Agent 辩论", "status": "", "detail": ""},
        },
        "resonance": {"ok": True, "signal": "strong_buy", "signal_label": "强烈买入", "resonance_score": 82},
        "debate": {"verdict": "bullish", "confidence": 0.78, "rounds": []},
    }
    out = svc.apply_lights_from_payload(doc)
    assert out["traffic_lights"]["technical"]["color"] == "green"
    assert out["traffic_lights"]["agent_debate"]["color"] == "green"


def test_build_document_minimal() -> None:
    svc = LiveResearchDocumentService()
    doc = svc.build_document("600519", MarketCode.CN, stock_service=None)
    assert doc["ok"] is True
    assert "traffic_lights" in doc
    assert doc["live"] is True
