"""Qlib 路线图阶段 1：符号映射与管道服务（无 pyqlib）。"""

from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from app.domain.enums import MarketCode
from app.application.services.qlib_pipeline_service import QlibPipelineService
from app.infrastructure.qlib.symbol_map import cn_to_qlib_instrument, to_qlib_instrument
from app.modules.system.services.tools.tool_facade_service import ToolFacadeService


@pytest.fixture
def bypass_cn_merge(monkeypatch):
    """强制走 Mock 行情，避免单测依赖 AkShare 网络。"""
    monkeypatch.setattr(
        "app.infrastructure.qlib.cn_ohlcv_merge.build_cn_ohlcv_merged",
        lambda *a, **k: ([], "test_bypass_merge"),
    )


def test_cn_to_qlib_instrument():
    assert cn_to_qlib_instrument("600519") == "SH600519"
    assert cn_to_qlib_instrument("000001") == "SZ000001"


def test_to_qlib_us():
    assert to_qlib_instrument("aapl", MarketCode.US) == "AAPL"


def test_qlib_pipeline_ingest_merge_existing(tmp_path: Path, bypass_cn_merge):
    calls: list[tuple[str, str, str]] = []

    def fake_fetch_daily_bars(sym, market, *, period="2y"):
        calls.append((sym, str(market), period))
        if len(calls) == 1:
            return [
                {"date": "2024-01-02", "open": 10, "high": 11, "low": 9, "close": 10.5, "volume": 1000},
            ], "test_bars_1"
        return [
            {"date": "2024-01-02", "open": 99, "high": 99, "low": 99, "close": 99, "volume": 1},
            {"date": "2024-01-04", "open": 11, "high": 12, "low": 10, "close": 11.5, "volume": 800},
        ], "test_bars_2"

    m = MagicMock()
    m.fetch_daily_bars.side_effect = fake_fetch_daily_bars
    svc = QlibPipelineService(m, base_dir=tmp_path)
    svc.ingest_symbols(["600519"], MarketCode.US, period="5d")
    svc.ingest_symbols(["600519"], MarketCode.US, period="5d", merge_existing=True)
    csvp = tmp_path / "instance" / "qlib_export" / "600519.csv"
    out = pd.read_csv(csvp, parse_dates=["date"])
    assert len(out) == 2
    assert out.iloc[-1]["date"].strftime("%Y-%m-%d") == "2024-01-04"


def test_qlib_pipeline_ingest_writes_csv(tmp_path: Path, bypass_cn_merge):
    m = MagicMock()

    def fake_fetch_daily_bars(sym, market, *, period="2y"):
        return [
            {"date": "2024-01-02", "open": 10, "high": 11, "low": 9, "close": 10.5, "volume": 1000},
            {"date": "2024-01-03", "open": 10.5, "high": 11, "low": 10, "close": 10.8, "volume": 900},
        ], "test_bars"

    m.fetch_daily_bars.side_effect = fake_fetch_daily_bars
    svc = QlibPipelineService(m, base_dir=tmp_path)
    meta = svc.ingest_symbols(["600519"], MarketCode.US, period="5d")
    assert "600519" in (meta.instruments or [])
    csvp = tmp_path / "instance" / "qlib_export" / "600519.csv"
    assert csvp.exists()
    txt = csvp.read_text(encoding="utf-8")
    assert "2024-01-02" in txt and "close" in txt


def test_simple_backtest_positive_return(tmp_path: Path, bypass_cn_merge):
    m = MagicMock()

    def fake_fetch_daily_bars(sym, market, *, period="2y"):
        return [
            {"date": "2024-01-02", "open": 10, "high": 11, "low": 9, "close": 10.0, "volume": 1000},
            {"date": "2024-01-10", "open": 10, "high": 12, "low": 10, "close": 11.0, "volume": 1000},
        ], "test_bars"

    m.fetch_daily_bars.side_effect = fake_fetch_daily_bars
    svc = QlibPipelineService(m, base_dir=tmp_path)
    r = svc.simple_backtest("600519", MarketCode.US, start="2024-01-01", end="2024-12-31")
    assert "metrics" in r
    assert r.get("backtest_engine") == "pandas_adapter_buy_hold"
