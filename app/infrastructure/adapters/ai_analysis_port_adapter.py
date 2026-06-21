from __future__ import annotations
"""Infrastructure adapter for ``AiAnalysisPort`` (default: Ollama prompt)."""

from typing import Any

from app.domain.ports.ai_analysis_port import AiAnalysisPort
from app.infrastructure.adapters.ollama_prompt_adapter import OllamaPromptAdapter


class AiAnalysisPortAdapter(AiAnalysisPort):
    def __init__(self, adapter: OllamaPromptAdapter | None = None) -> None:
        self._adapter = adapter or OllamaPromptAdapter()

    def analyze(self, *, symbol: str, market: str, context: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        return self._adapter.analyze(symbol=symbol, market=market, context=context, **kwargs)
