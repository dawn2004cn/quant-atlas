"""Ollama-only AI adapter (no TradingAgents)."""

from unittest.mock import patch

from app.infrastructure.adapters.ollama_prompt_adapter import OllamaPromptAdapter


def test_ollama_adapter_analyze():
    adapter = OllamaPromptAdapter()
    with patch.object(adapter, "_call_ollama", return_value="neutral"):
        out = adapter.analyze(symbol="600519", market="CN", context={"quote": {}, "news": []})
    assert out["mode"] == "ollama_prompt"
    assert out["analysis"] == "neutral"
