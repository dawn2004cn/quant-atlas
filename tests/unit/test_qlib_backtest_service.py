"""QlibBacktestService delegation and demo fallback."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from app.domain.enums import MarketCode
from app.modules.data.services.qlib_backtest_service import QlibBacktestService


def test_unified_buy_hold_delegates_to_pipeline(tmp_path: Path):
    pipeline = MagicMock()
    pipeline.unified_buy_hold_backtest.return_value = {
        "symbol": "600519",
        "metrics": {"total_return": 0.12},
        "backtest_engine": "pandas_adapter_buy_hold",
    }
    svc = QlibBacktestService(tmp_path, pipeline_service=pipeline)

    result = svc.unified_buy_hold_backtest("600519", "2024-01-01", "2024-12-31")

    pipeline.unified_buy_hold_backtest.assert_called_once_with(
        "600519",
        MarketCode.CN,
        start="2024-01-01",
        end="2024-12-31",
    )
    assert result["metrics"]["total_return"] == 0.12
    assert "meta" not in result or result.get("meta", {}).get("demo") is not True


def test_run_backtest_demo_when_qlib_unavailable(tmp_path: Path):
    svc = QlibBacktestService(tmp_path)

    result = svc.run_backtest("buy_hold", ["600519"], {"start_date": "2024-01-01"})

    assert result["meta"]["demo"] is True
    assert result["meta"]["reason"] == "qlib_runtime_unavailable"


def test_simple_backtest_demo_without_pipeline(tmp_path: Path):
    svc = QlibBacktestService(tmp_path)

    result = svc.simple_backtest("buy_hold", ["600519"], "2024-01-01", "2024-12-31")

    assert result["meta"]["demo"] is True
    assert result["total_return"] == 0.0
