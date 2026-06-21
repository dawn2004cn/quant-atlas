"""Tests for Sprint 6: Ollama CB, committee DecisionContext, portfolio_risk context."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.modules.ai_agent.services.ai_committee_selection_service import AICommitteeSelectionService
from app.core.circuit_breaker import CircuitBreakerOpenError, CircuitBreakerRegistry
from app.infrastructure.adapters.ollama_prompt_adapter import OllamaPromptAdapter


@pytest.fixture(autouse=True)
def _reset_ollama_breaker():
    CircuitBreakerRegistry._breakers.pop("ollama_generate", None)
    yield
    CircuitBreakerRegistry._breakers.pop("ollama_generate", None)


def test_ollama_adapter_degrades_when_circuit_open():
    adapter = OllamaPromptAdapter()
    with patch.object(adapter, "_call_ollama", side_effect=CircuitBreakerOpenError("open")):
        out = adapter.analyze(symbol="600519", market="CN", context={})
    assert out["degraded"] is True
    assert "熔断" in out["analysis"]


def test_ai_committee_run_selection_includes_decision():
    market = MagicMock()
    market.list_quotes.return_value = [{"code": "sh000001", "change_pct": 1.2}]
    svc = AICommitteeSelectionService(market_service=market)
    payload = svc.run_selection(user_id=1, capital=500_000, min_positions=1, max_positions=2)
    assert "decision_id" in payload
    assert payload["decision"]["schema_version"] == "v1"
    assert payload["decision"]["subject"].startswith("committee:")


def test_portfolio_routes_use_portfolio_risk_context():
    import importlib

    importlib.import_module("app.presentation.api.routes_v1_portfolio")
    importlib.import_module("app.presentation.api.routes_v1_risk")
    from app.core.registry import _route_registry

    assert _route_registry["portfolio"]["context"] == "portfolio_risk"
    assert _route_registry["risk"]["context"] == "portfolio_risk"
