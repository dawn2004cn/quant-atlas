"""Smoke tests for quant-atlas-mcp tool wrappers (no live MCP transport)."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_server_module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "mcp-servers" / "quant-atlas-mcp" / "server.py"
    spec = importlib.util.spec_from_file_location("quant_atlas_mcp_server", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_execute_backtest_runs_process_sandbox(monkeypatch):
    monkeypatch.setenv("STRATEGY_SANDBOX", "process")
    mod = _load_server_module()
    out = mod.execute_backtest("print({'ok': True})", {"symbol": "600519"})
    assert out["ok"] is True
    assert out["data"]["sandbox"] == "process"
    assert out["data"]["status"] == "completed"
    assert "evidence" in out and "confidence" in out


def test_get_portfolio_status_structured():
    mod = _load_server_module()
    out = mod.get_portfolio_status()
    assert "ok" in out
    assert "evidence" in out
    assert isinstance(out.get("data"), dict)


def test_get_historical_kline_returns_structured_payload():
    mod = _load_server_module()
    out = mod.get_historical_kline("600519", "1d", 10)
    assert "ok" in out
    assert "evidence" in out
    assert "confidence" in out
