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


def test_get_cn_quotes_uses_http_envelope(monkeypatch):
    monkeypatch.setenv("QUANT_ATLAS_API_URL", "http://127.0.0.1:5000")
    mod = _load_server_module()

    def _fake_http(path: str, timeout: float = 8.0):
        assert "quotes/page" in path
        return {
            "success": True,
            "data": {
                "items": [{"code": "600519", "name": "茅台", "price": 1600.0, "change_pct": 1.2}],
                "total": 1,
                "stats": {"up": 1, "down": 0, "flat": 0},
            },
        }

    monkeypatch.setattr(mod, "_http_json", _fake_http)
    out = mod.get_cn_quotes(limit=10)
    assert out["ok"] is True
    assert out["data"]["items"][0]["price"] == 1600.0
    assert out["evidence"].startswith("http:")


def test_get_market_panorama_uses_http(monkeypatch):
    monkeypatch.setenv("QUANT_ATLAS_API_URL", "http://127.0.0.1:5000")
    mod = _load_server_module()
    monkeypatch.setattr(
        mod,
        "_http_json",
        lambda path, timeout=8.0: {
            "data": {
                "rankings": {
                    "gainers": [{"code": "300112", "price": 10.55, "change_pct": 20.02}],
                    "losers": [],
                }
            }
        },
    )
    out = mod.get_market_panorama()
    assert out["ok"] is True
    assert out["data"]["rankings"]["gainers"][0]["code"] == "300112"


def test_get_stock_quote_http(monkeypatch):
    monkeypatch.setenv("QUANT_ATLAS_API_URL", "http://127.0.0.1:5000")
    mod = _load_server_module()
    monkeypatch.setattr(
        mod,
        "_http_json",
        lambda path, timeout=8.0: {"data": {"stocks": [{"code": "000001", "price": 12.3}]}},
    )
    out = mod.get_stock_quote("000001")
    assert out["ok"] is True
    assert out["data"]["stocks"][0]["price"] == 12.3


def test_search_capabilities_includes_mcp_catalog():
    mod = _load_server_module()
    out = mod.search_capabilities("行情")
    assert out["ok"] is True
    names = {item["name"] for item in out["data"]["items"]}
    assert "get_cn_quotes" in names
    assert "get_market_panorama" in names
