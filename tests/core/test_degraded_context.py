"""Tests for degraded-mode context and wiring order."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core.circuit_breaker import CircuitBreakerOpenError, CircuitBreakerRegistry
from app.core.middleware.degraded_context import (
    clear_degraded_state,
    get_degraded_reasons,
    is_system_degraded,
    mark_system_degraded,
)
from app.infrastructure.adapters.fingpt_adapter import FinGPTSentimentAdapter
from app.infrastructure.adapters.ollama_prompt_adapter import OllamaPromptAdapter


@pytest.fixture(autouse=True)
def _reset_state():
    clear_degraded_state()
    CircuitBreakerRegistry._breakers.pop("fingpt_sentiment", None)
    yield
    clear_degraded_state()
    CircuitBreakerRegistry._breakers.pop("fingpt_sentiment", None)


def test_mark_system_degraded_tracks_reasons():
    mark_system_degraded("openbb")
    mark_system_degraded("ollama")
    assert is_system_degraded() is True
    assert get_degraded_reasons() == ["openbb", "ollama"]


def test_fingpt_adapter_degrades_on_circuit_open():
    llm = MagicMock()
    adapter = FinGPTSentimentAdapter(llm)
    with patch.object(adapter, "_analyze_sentiment_llm", side_effect=CircuitBreakerOpenError("open")):
        out = adapter.analyze_sentiment("market rally continues")
    assert out.get("degraded") is True
    assert is_system_degraded() is True
    assert "fingpt" in get_degraded_reasons()


def test_request_middleware_sets_degraded_header():
    from flask import Flask

    from app.core.middleware.request_context import init_request_context_middleware

    app = Flask(__name__)
    init_request_context_middleware(app)

    @app.get("/_test/degraded")
    def _degraded_probe():
        mark_system_degraded("test_source")
        return {"ok": True}

    with app.app_context():
        with app.test_request_context("/_test/degraded"):
            clear_degraded_state()
            mark_system_degraded("test_source")
            from flask import jsonify

            response = jsonify({"ok": True})
            for func in app.after_request_funcs.get(None, []):
                response = func(response)
    assert response.headers.get("X-System-Degraded") == "true"
    assert "test_source" in (response.headers.get("X-System-Degraded-Reason") or "")


def test_ollama_degraded_marks_context():
    adapter = OllamaPromptAdapter()
    with patch.object(adapter, "_call_ollama", side_effect=CircuitBreakerOpenError("open")):
        adapter.analyze(symbol="600519", market="CN", context={})
    assert "ollama" in get_degraded_reasons()
