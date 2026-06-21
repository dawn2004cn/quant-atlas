from __future__ import annotations

from types import SimpleNamespace

from app.domain.enums import MarketCode
from app.modules.ai_agent.services.ai_analysis_service import AiAnalysisService


class _StockService:
    def get_stock_detail(self, symbol: str, market: MarketCode):
        return SimpleNamespace(
            profile={"realtime": {"updated_at": "2026-06-15T00:00:00Z"}},
            indicators={"rsi": 50},
        )


class _Adapter:
    def __init__(self) -> None:
        self.calls = []

    def analyze(self, *, symbol: str, market: str, context: dict, **kwargs):
        self.calls.append({"symbol": symbol, "market": market, "context": context, **kwargs})
        return {"degraded": False, "analysis": "ok", "prompt_version": kwargs.get("prompt_version"), "prompt_hash": kwargs.get("prompt_hash")}


class _PromptService:
    def get_current_prompt_snapshot(self, prompt_id: str = "jarvis_default"):
        return {
            "prompt_id": prompt_id,
            "prompt_version": "prompt-v1",
            "prompt_hash": "0123456789abcdef",
            "prompt": "test prompt",
        }


def test_analyze_passes_prompt_metadata_to_adapter() -> None:
    adapter = _Adapter()
    service = AiAnalysisService(
        stock_service=_StockService(),
        ai_adapter=adapter,
        prompt_evolution_service=_PromptService(),
    )

    result = service.analyze("600519", MarketCode.CN)

    assert result["ai"]["prompt_version"] == "prompt-v1"
    assert result["ai"]["prompt_hash"] == "0123456789abcdef"
    assert adapter.calls[0]["prompt_version"] == "prompt-v1"
    assert adapter.calls[0]["prompt_hash"] == "0123456789abcdef"


def test_analyze_stream_yields_prompt_metadata() -> None:
    adapter = _Adapter()
    service = AiAnalysisService(
        stock_service=_StockService(),
        ai_adapter=adapter,
        prompt_evolution_service=_PromptService(),
    )

    events = list(service.analyze_stream("600519", MarketCode.CN))

    prompt_events = [event for event in events if event.get("event") == "prompt"]
    assert prompt_events[0]["prompt_version"] == "prompt-v1"
    assert prompt_events[0]["prompt_hash"] == "0123456789abcdef"
