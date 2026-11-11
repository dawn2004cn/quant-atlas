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


def _disable_tdx(monkeypatch, mod) -> None:
    monkeypatch.setattr(mod, "_tdx_daily_kline", lambda *a, **k: ([], ""))
    monkeypatch.setattr(mod, "_tdx_realtime_quotes", lambda symbols: [])


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


def test_get_historical_kline_returns_structured_payload(monkeypatch):
    mod = _load_server_module()
    _disable_tdx(monkeypatch, mod)
    out = mod.get_historical_kline("600519", "1d", 10)
    assert "ok" in out
    assert "evidence" in out
    assert "confidence" in out


def test_get_historical_kline_prefers_tdx_file(monkeypatch):
    mod = _load_server_module()
    bars = [
        {
            "date": "2026-01-05",
            "open": 1400.0,
            "high": 1420.0,
            "low": 1390.0,
            "close": 1410.0,
            "volume": 1000,
            "source": "tdx_file",
        }
    ]
    monkeypatch.setattr(mod, "_tdx_daily_kline", lambda *a, **k: (bars, "tdx_file"))
    monkeypatch.setattr(
        mod,
        "_http_data",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("http must not run when TDX hits")),
    )
    out = mod.get_historical_kline("600519", "1d", 10)
    assert out["ok"] is True
    assert out["data"]["source"] == "tdx_file"
    assert out["data"]["bars"][0]["close"] == 1410.0
    assert out["evidence"].startswith("tdx:")


def test_get_cn_quotes_uses_http_envelope(monkeypatch):
    monkeypatch.setenv("QUANT_ATLAS_API_URL", "http://127.0.0.1:5000")
    mod = _load_server_module()
    _disable_tdx(monkeypatch, mod)

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


def test_get_cn_quotes_prefers_tdx_realtime(monkeypatch):
    monkeypatch.setenv("QUANT_ATLAS_API_URL", "http://127.0.0.1:5000")
    mod = _load_server_module()
    monkeypatch.setattr(
        mod,
        "_tdx_realtime_quotes",
        lambda symbols: [
            {"code": "000001", "price": 11.2, "change_pct": 2.5, "source": "tdx"},
            {"code": "600519", "price": 1600.0, "change_pct": 0.5, "source": "tdx"},
        ],
    )
    monkeypatch.setattr(
        mod,
        "_http_json",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("http must not run when TDX hits")),
    )
    out = mod.get_cn_quotes(limit=10)
    assert out["ok"] is True
    assert out["data"]["items"][0]["code"] == "000001"
    assert out["evidence"] == "tdx:realtime_hq"


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
    _disable_tdx(monkeypatch, mod)
    monkeypatch.setattr(
        mod,
        "_http_json",
        lambda path, timeout=8.0: {"data": {"stocks": [{"code": "000001", "price": 12.3}]}},
    )
    out = mod.get_stock_quote("000001")
    assert out["ok"] is True
    assert out["data"]["stocks"][0]["price"] == 12.3


def test_get_stock_quote_prefers_tdx_realtime(monkeypatch):
    monkeypatch.setenv("QUANT_ATLAS_API_URL", "http://127.0.0.1:5000")
    mod = _load_server_module()
    monkeypatch.setattr(
        mod,
        "_tdx_realtime_quotes",
        lambda symbols: [{"code": "000001", "price": 11.5, "change_pct": 1.1, "source": "tdx"}],
    )
    monkeypatch.setattr(
        mod,
        "_http_json",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("http must not run when TDX hits")),
    )
    out = mod.get_stock_quote("000001")
    assert out["ok"] is True
    assert out["data"]["stocks"][0]["price"] == 11.5
    assert out["evidence"] == "tdx:realtime_hq"


def test_search_capabilities_includes_mcp_catalog():
    mod = _load_server_module()
    out = mod.search_capabilities("行情")
    assert out["ok"] is True
    names = {item["name"] for item in out["data"]["items"]}
    assert "get_cn_quotes" in names
    assert "get_market_panorama" in names
